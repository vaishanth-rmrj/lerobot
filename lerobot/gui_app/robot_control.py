import cv2
import time
import threading
import logging

from omegaconf.dictconfig import DictConfig

# project imports
from lerobot.common.robot_devices.control_utils import init_keyboard_listener, busy_wait 
from lerobot.common.utils.utils import init_hydra_config
from lerobot.common.robot_devices.robots.factory import make_robot
from lerobot.common.datasets.lerobot_dataset import LeRobotDataset
from lerobot.common.datasets.image_writer import safe_stop_image_writer

class RobotControl:
    def __init__(
            self,
            config: DictConfig
        ) -> None:

        self.config = config
        self.is_shutdown = False
        self.cam_buffer = None

        self.is_process_active = False

        self.listener, self.events = init_keyboard_listener()          
        self.robot = self.init_robot(self.config.robot_cfg_file)          

        
    
    def init_robot(self, config_path: str):
        self.stop_all_processes()

        logging.info(f"Provided robot config file: {config_path}")
        robot_cfg = init_hydra_config(config_path)
        if hasattr(self, 'robot'):
            self.robot.__del__()
        robot = make_robot(robot_cfg)
        return robot
    
    def stop_all_processes(self):
        if self.is_process_active:
            logging.info("Stopping all processes")
            self.events["exit_early"] = True
            time.sleep(1)
            self.is_process_active = False
        else:
            logging.info("No background processes running !!")
    
    def stop(self):
        self.stop_all_processes()
    
    @safe_stop_image_writer
    def control_loop(
            self,
            robot,
            control_time_s=None,
            teleoperate=False,
            display_cameras=False,
            dataset: LeRobotDataset | None = None,
            events=None,
            policy=None,
            device=None,
            use_amp=None,
            fps=None,
        ):

        if not robot.is_connected:
            robot.connect()

        if events is None:
            events = {"exit_early": False}

        if control_time_s is None:
            control_time_s = float("inf")
        
        if teleoperate and policy is not None:
            raise ValueError("When `teleoperate` is True, `policy` should be None.")
        
        if dataset is not None and fps is not None and dataset.fps != fps:
            raise ValueError(f"The dataset fps should be equal to requested fps ({dataset['fps']} != {fps}).")

        timestamp = 0
        start_episode_t = time.perf_counter()
        logging.info("Starting control loop...")
        while timestamp < control_time_s:
            logging.info("Running control loop")
            start_loop_t = time.perf_counter()

            # logic comes here
            if teleoperate:
                observation, action = robot.teleop_step(record_data=True)
            else:
                observation = robot.capture_observation()
            
            # if display_cameras and not is_headless():
            image_keys = [key for key in observation if "image" in key]
            for key in image_keys:            
                cam_image = cv2.cvtColor(observation[key].numpy(), cv2.COLOR_RGB2BGR)
                ret, self.cam_buffer = cv2.imencode('.jpg', cam_image)

            if fps is not None:
                dt_s = time.perf_counter() - start_loop_t
                busy_wait(1 / fps - dt_s)
            
            dt_s = time.perf_counter() - start_loop_t

            timestamp = time.perf_counter() - start_episode_t
            if self.events["exit_early"]:
                logging.info("Early exit triggered. Exiting while loop !!")
                self.events["exit_early"] = False
                break
    
    def teleop(self, config):

        if not self.is_process_active:
            self.is_process_active = True
            logging.info("Started teleop control XD")
            self.control_loop(
                self.robot,
                fps=config.fps,
                teleoperate=True,
                events=self.events,
            )
        
        else:
            logging.info("Background threads running. Please stop other threads / processes !!")
            return
    
    def select_robot_control_mode(self, mode:str):

        if mode == "teleop":
            logging.info(f"Provided robot config file: {self.config.robot_cfg_file}")
            threading.Thread(target=self.teleop, daemon=True, args=[self.config.teleop]).start()
    
    
    
    def __del__(self):
        self.robot.disconnect()


