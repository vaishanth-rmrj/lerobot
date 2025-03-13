import cv2
import numpy as np
import time
import threading
import logging
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict

import torch
from omegaconf.dictconfig import DictConfig

# project imports
from lerobot.common.robot_devices.control_utils import busy_wait 
from lerobot.common.robot_devices.robots.utils import Robot, make_robot_from_config
from lerobot.common.datasets.lerobot_dataset import LeRobotDataset
from lerobot.common.robot_devices.utils import safe_disconnect
from lerobot.common.robot_devices.control_utils import (
    has_method,
    init_keyboard_listener,
    init_policy,
    sanity_check_dataset_name,
    sanity_check_dataset_robot_compatibility,
    stop_recording,
    predict_action,
)
from lerobot.gui_app.configs.gui_control_configs import GUIControlPipelineConfig
from lerobot.common.robot_devices.robots.configs import RobotConfig
from lerobot.gui_app.utils import init_image_buffers
from lerobot.gui_app.control_utils import (
    control_loop,
    record,
    eval,
)
from lerobot.gui_app.configs.gui_control_configs import (
    CalibrateControlConfig,
    GUIControlPipelineConfig,
    RecordControlConfig,
    EvalControlConfig,
    ReplayControlConfig,
    TeleoperateControlConfig,
)

def reinit_event_flags(events:Dict) -> None:
    events["force_stop"] = False
    events["start_recording"] = False
    events["control_loop_active"] = False
    events["exit_early"] = False
    events["rerecord_episode"] = False
    events["stop_recording"] = False

@dataclass
class RobotState:
    type:str
    camera_image_buffers: Dict[str, np.ndarray]
    camera_fps: float
    state: List[float]
    action: List[float]

class RobotController:
    def __init__(
            self,
            config: GUIControlPipelineConfig
        ) -> None:

        self.config = config
        self.running_threads = {}

        self.events = {}
        reinit_event_flags(self.events)            

        self.robot = None
        self.init_robot(self.config.robot) 
        
        self.robot_state = RobotState(
            type=self.config.robot.type,
            camera_image_buffers=init_image_buffers((640, 480), self.get_camera_info()),
            camera_fps=30,
            state=[None] * self.num_joints,
            action=[None] * self.num_joints
        )
    
    def get_fps(self):
        return self.robot_state.camera_fps
    
    def init_robot(self, config: RobotConfig)-> Robot:
        """
        make robot object from the provided config
        """
        if hasattr(self, 'robot') and self.robot is not None:
            logging.info("Deleting previous robot object.")
            self.robot.__del__()
        
        self.robot = make_robot_from_config(config)
    
    @property
    def num_cameras(self):
        return self.robot.cameras
    
    @property
    def is_connected(self):
        return self.robot.is_connected
    
    @property
    def num_joints(self):
        num_joints = self.robot.motor_features["observation.state"]["shape"][0]   
        if isinstance(num_joints, torch.Tensor):
            return num_joints.item()
        return num_joints
    
    def get_joint_names(self):
        joint_names = self.robot.motor_features["observation.state"]["names"] 
        if isinstance(joint_names, torch.Tensor):
            return joint_names.tolist()
        return joint_names
    
    def get_state(self):
        return self.robot_state.state
    
    def get_action(self):
        return self.robot_state.action
    
    def get_camera_info(self) -> List:
        """
        get camera info for the robot to init GUI camera feed display elements

        Returns:
            List: cam info for each cam provided in the config file
        """
        cam_info = []
        for cam_id, cam_name in enumerate(self.robot.cameras.keys()):
            cam_info.append({
                "id": cam_id,
                "name": str(cam_name),
                "video_url": f"/robot/get-cam-feed/observation.images.{cam_name}",
            })        
        return cam_info
    
    def set_home(self):        
        self.config.home_pose = self.get_state()     
    
    @safe_disconnect
    def calibrate(self, robot:Robot, arm_name:str, thread_id:str):
        raise NotImplementedError("calibrate : This function is not implemented for this robot !!")

        if not isinstance(arm_name, str):
            logging.info(f"calibrate : Invalid input type {arm_name}. Accepted inputs is str() type !!")
            return False

        if arm_name not in robot.available_arms:
            logging.info(f"calibrate : Invalid arm name {arm_name}. Please select valid arm name !!")
            return False
        
        arm_calib_path = robot.calibration_dir / f"{arm_name}.json"
        if arm_calib_path.exists():
            logging.info(f"Removing '{arm_calib_path}'")
            arm_calib_path.unlink()
        else:
            logging.info(f"Calibration file not found '{arm_calib_path}'")
        
        if robot.is_connected:
            robot.disconnect()

        # Calling `connect` automatically runs calibration
        # when the calibration file is missing
        logging.info(f"Starting calibration for arm: {arm_name}. Please follow the instructions on the terminal.")
        robot.connect()
        robot.disconnect()
        logging.info("Success: Calibration is done.")

        # stop calibration thread
        self.running_threads[thread_id].join()
        del self.running_threads[thread_id]   
    
    def run_teleop(self, cfg: TeleoperateControlConfig):
        """
        run teleop control mode

        Args:
            config (DictConfig): teleop config
        """

        logging.info("Started teleop control XD")
        control_loop(
            self.robot,
            self.robot_state,
            fps=cfg.fps,
            teleoperate=True,
            events=self.events,
        )   
        self.events["force_stop"] = False
        
    def run_record(self, cfg: RecordControlConfig):
        """
        run record control mode

        Args:
            config (DictConfig): record config
        """
        logging.info("Started record control XD")
        record(
            self.robot,
            self.robot_state,
            cfg = cfg,
            local_files_only=False, # not implemented
            events=self.events,
        )
        self.events["force_stop"] = False

    def run_eval(self, cfg: EvalControlConfig):
        """
        run eval control mode with or without recording episodes

        Args:
            config (DictConfig): eval config
        """
        logging.info("Started eval control XD")

        eval(
            self.robot,
            self.robot_state,
            cfg=cfg,
            events=self.events,
        )        
        self.events["force_stop"] = False
    
    def run_calibration(self, arm_name:str):
        """
        run arm calibration on separate thread

        Args:
            arm_name (str): name of the arm to calibrate
        """
        raise NotImplementedError("run_calibration : This function is not implemented for this robot !!")
    
    def home_robot(self, fps:int = 30, abs_tol:int = 5.0):

        # TODO: need to somehow store home pose for each follower robot
        # hardcoded sample
        homing_joint_pos = {
            'main': torch.tensor(self.config.home_pose),
        }

        if not self.robot.is_connected:
            self.robot.connect()

        # slow down motor acceleration 
        # to prevent agressive motion
        logging.info("Decreasing motor acceleration to 2")
        for name in self.robot.follower_arms:
            self.robot.follower_arms[name].write("Acceleration", 2)

        home_pose = []
        for name in self.robot.follower_arms:
            if name in homing_joint_pos:
                home_pose.append(homing_joint_pos[name])
        home_pose = torch.cat(home_pose)

        logging.info(f"Sending home pose to robot: {home_pose}")
        self.robot.send_action(home_pose)
                
        timestamp = 0.0
        start_t = time.perf_counter()
        logging.info("Homing robot. Please wait ...")
        while True:
            start_loop_t = time.perf_counter()

            if timestamp > 5:
                logging.info("Homing robot timed out. Exiting while loop !!")
                break

            # sync leader and follower joint states
            # self.robot.teleop_step()

            target_reached = False
            for name in self.robot.follower_arms:
                curr_pose = torch.from_numpy(self.robot.follower_arms[name].read("Present_Position"))
                target_pose = homing_joint_pos[name]

                target_reached = torch.allclose(curr_pose, target_pose, atol=abs_tol)
            
            if target_reached: 
                logging.info("Robot is homed. Exiting while loop !!")
                break

            if fps is not None:
                dt_s = time.perf_counter() - start_loop_t
                busy_wait(1 / fps - dt_s)

            timestamp = time.perf_counter() - start_t
        
        # reset the motor acceleration val
        for name in self.robot.follower_arms:
            self.robot.follower_arms[name].write("Acceleration", 254)

        return True

    def select_robot_control_mode(self, mode:str):
        """
        main func to execute robot control mode in different threads

        note: Only one control mode can be active at a time and multiple threads are not allowed.
        already running threads should be stopped before starting a new thread.

        Args:
            mode (str): mode of control. Options: teleop, record, eval, calibrate, hg-dagger

        Returns:
            bool: success / fail status of thread execution
        """

        if len(self.running_threads) > 0:
            logging.info("select_robot_control_mode : Background threads running. Please stop other threads / processes !!")
            return False

        if mode == "teleop":
            thread = threading.Thread(
                target=self.run_teleop,                  
                args=[self.config.teleoperate_control],
                daemon=True,
            )
        elif mode == "record":
            thread = threading.Thread(
                target=self.run_record, 
                daemon=True, 
                args=[self.config.record_control]
            )
        elif mode == "eval":
            thread = threading.Thread(
                target=self.run_eval, 
                daemon=True, 
                args=[self.config.eval_control]
            )
        else:
            logging.info(f"select_robot_control_mode : Invalid control mode {mode}. Please select valid control mode !!")
            return False

        # start the thread and store it
        self.running_threads[mode] = thread
        thread.start()
        return True

    def stop_threads(self):
        """
        stop all active threads running different control modes

        Returns:
            bool: success / fail status of stopping threads
        """        
        active_threads = len(self.running_threads)
        if active_threads > 0:
            logging.info(f"stop_threads : {active_threads} background threads running. Terminating all threads !!")

            for thread_id in list(self.running_threads.keys()):
                self.events["force_stop"] = True
                self.running_threads[thread_id].join()
                del self.running_threads[thread_id]
                logging.info(f"{thread_id} background thread was stopped. XD")              
            
        else:
            logging.info(f"stop_threads : No background threads running. XD")
        
        # resetting events flag
        reinit_event_flags(self.events)        
        return True if len(self.running_threads) > 0 else False    
    
    def __del__(self):
        if self.robot.is_connected:
            self.robot.disconnect()


