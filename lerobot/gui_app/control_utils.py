import time
import logging
import cv2
from typing import Dict

from lerobot.common.datasets.image_writer import safe_stop_image_writer
from lerobot.common.robot_devices.robots.utils import Robot
from lerobot.common.robot_devices.utils import busy_wait
from lerobot.common.robot_devices.control_utils import predict_action
from lerobot.common.datasets.lerobot_dataset import LeRobotDataset
from lerobot.common.policies.pretrained import PreTrainedPolicy
from lerobot.common.utils.utils import get_safe_torch_device, has_method

from lerobot.gui_app.robot_control import reinit_event_flags, RobotState
from lerobot.gui_app.utils import init_image_buffers

def update_robot_state(robot_state:RobotState, observation:Dict, action:Dict, fps:float) -> None:

    if observation is None or action is None:
        return
    
    if not isinstance(observation, Dict) or not isinstance(action, Dict):
        raise ValueError("Observation and action must be dictionaries.")

    image_keys = [key for key in observation if "image" in key]
    for key in image_keys:
        ret, robot_state.camera_image_buffers[key] = cv2.imencode(
            '.jpg', 
            cv2.cvtColor(observation[key].numpy(), cv2.COLOR_RGB2BGR)
        )        
        if not ret: logging.info(f"Control Loop: Error encoding cam:{key} feed")
    
    robot_state.camera_fps = fps
    robot_state.state = observation["observation.state"]           
    robot_state.action = action["action"]   

def reset_camera_image_buffers(robot_state:RobotState) -> None:
    img_size = robot_state.camera_image_buffers[robot_state.camera_image_buffers.keys()[0]].shape
    cam_info = {"name":name.split(".")[-1] for name in robot_state.camera_image_buffers.keys()}
    robot_state.camera_image_buffers = init_image_buffers(img_size, cam_info)

def check_force_stop(events):
    if events["force_stop"]:
        logging.info("Force Stop Triggered !!")            
        return True
    else:
        return False

@safe_stop_image_writer
def control_loop(
    robot:Robot,
    robot_state: RobotState,
    control_time_s:int=None,
    teleoperate:bool=False,
    display_cameras:bool=False,
    dataset: LeRobotDataset | None = None,
    events:Dict=None,
    policy: PreTrainedPolicy = None,
    fps:int=None,
    single_task: str | None = None,
) -> None:
    """
    main control loop to run different control modes.

    Args:
        robot (Robot): robot object
        control_time_s (int, optional): total time to execute the control loop. Defaults to None.
        teleoperate (bool, optional): enable robot teleop. Defaults to False.
        display_cameras (bool, optional): Not req since cam feed is displayed in the GUI. Defaults to False.
        dataset (LeRobotDataset | None, optional): lerobot dataset object. Defaults to None.
        events (Dict, optional): keyboard btn press events. Defaults to None.
        policy (optional): policy object for evaluation. Defaults to None.
        device (optional): Device to run the policy on. Defaults to None.
        use_amp (optional): ???. Defaults to None.
        fps (int, optional): FPS to execute the control loop. Defaults to None.
    """
    # re-initialize event flags to prevent
    # accidental loop triggers from prev executions
    reinit_event_flags(events)

    if not robot.is_connected:
        robot.connect()

    if events is None:
        raise ValueError("Events dict is None. Please pass a valid events dict to the control loop.")

    if control_time_s is None:
        control_time_s = float("inf")
    
    if teleoperate and policy is not None:
        raise ValueError("When `teleoperate` is True, `policy` should be None.")
    
    if dataset is not None and single_task is None:
        raise ValueError("You need to provide a task as argument in `single_task`.")
    
    if dataset is not None and fps is not None and dataset.fps != fps:
        raise ValueError(f"The dataset fps should be equal to requested fps ({dataset['fps']} != {fps}).")

    timestamp = 0
    start_episode_t = time.perf_counter()
    events["control_loop_active"] = True
    logging.info("Started control loop.")
    while timestamp < control_time_s:
        start_loop_t = time.perf_counter()

        if teleoperate:
            observation, action = robot.teleop_step(record_data=True)
        else:
            observation = robot.capture_observation()

            if policy is not None:
                pred_action = predict_action(
                    observation, 
                    policy, 
                    get_safe_torch_device(policy.config.device), 
                    policy.config.use_amp
                )
                # Action can eventually be clipped using `max_relative_target`,
                # so action actually sent is saved in the dataset.
                action = robot.send_action(pred_action)
                action = {"action": action}
        
        if dataset is not None and events["start_recording"]:
            frame = {**observation, **action, "task": single_task}
            dataset.add_frame(frame)

        update_robot_state(robot_state, observation, action, fps)

        if fps is not None:
            dt_s = time.perf_counter() - start_loop_t
            busy_wait(1 / fps - dt_s)        
        dt_s = time.perf_counter() - start_loop_t
        # TODO: update implementation for gui
        # log_control_info(robot, dt_s, fps=fps)

        timestamp = time.perf_counter() - start_episode_t
        if events["exit_early"]:
            logging.info("Early exit triggered. Exiting while loop !!")
            events["exit_early"] = False
            reset_camera_image_buffers(robot_state)
            break
        
        if check_force_stop(events): 
            reset_camera_image_buffers(robot_state)
            break
    
    events["control_loop_active"] = False