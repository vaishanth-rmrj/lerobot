import cv2
import time
import threading

# project imports
from lerobot.common.robot_devices.control_utils import init_keyboard_listener, busy_wait 
from lerobot.common.utils.utils import init_hydra_config
from lerobot.common.robot_devices.robots.factory import make_robot
from lerobot.common.datasets.lerobot_dataset import LeRobotDataset
from lerobot.common.datasets.image_writer import safe_stop_image_writer

class RobotControl:
    def __init__(
            self,
            robot_path="lerobot/configs/robot/so100.yaml"
        ) -> None:

        self.name = "so100_arm"
        self.is_shutdown = False
        self.counter = 0
        self.cam_image = None
        self.cam_buffer = None


        robot_cfg = init_hydra_config(robot_path, None)
        self.robot = make_robot(robot_cfg)
        self.listener, self.events = init_keyboard_listener()    
    
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
        while timestamp < control_time_s:
            start_loop_t = time.perf_counter()

            # logic comes here
            if teleoperate:
                observation, action = robot.teleop_step(record_data=True)
            else:
                observation = robot.capture_observation()
            
            # if display_cameras and not is_headless():
            image_keys = [key for key in observation if "image" in key]
            for key in image_keys:            
                self.cam_image = cv2.cvtColor(observation[key].numpy(), cv2.COLOR_RGB2BGR)
                ret, self.cam_buffer = cv2.imencode('.jpg', self.cam_image)

            if fps is not None:
                dt_s = time.perf_counter() - start_loop_t
                busy_wait(1 / fps - dt_s)
            
            dt_s = time.perf_counter() - start_loop_t

            timestamp = time.perf_counter() - start_episode_t
            if self.events["exit_early"]:
                print("Exiting while loop")
                self.events["exit_early"] = False
                break
    
    def teleop(self):
        self.control_loop(
            self.robot,
            control_time_s=None,
            fps=30,
            teleoperate=True,
            display_cameras=False,
            events=self.events,
        )
    
    def select_robot_control_mode(self, mode:str):

        if mode == "teleop":
            threading.Thread(target=self.teleop, daemon=True).start()
    
    def stop(self):
        self.events["exit_early"] = True
    
    def __del__(self):
        self.robot.disconnect()


