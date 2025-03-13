import time
import logging
import cv2
import torch
from pathlib import Path
from typing import Dict

from lerobot.common.datasets.image_writer import safe_stop_image_writer
from lerobot.common.robot_devices.robots.utils import Robot
from lerobot.common.robot_devices.utils import busy_wait
from lerobot.common.datasets.lerobot_dataset import LeRobotDataset
from lerobot.common.policies.pretrained import PreTrainedPolicy
from lerobot.common.utils.utils import get_safe_torch_device, has_method
from lerobot.common.policies.factory import make_policy
from lerobot.common.robot_devices.control_utils import (
    predict_action,
    control_loop,
    sanity_check_dataset_name,
    sanity_check_dataset_robot_compatibility,
    stop_recording,
)

from lerobot.gui_app.utils import reinit_event_flags, RobotState
from lerobot.gui_app.utils import init_image_buffers
from lerobot.gui_app.configs.gui_control_configs import (
    RecordControlConfig,
    EvalControlConfig,
    ReplayControlConfig,
)

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
    if isinstance(observation["observation.state"], torch.Tensor):
        robot_state.state = observation["observation.state"].tolist()  
    else:
        robot_state.state = observation["observation.state"]   

    if isinstance(action["action"], torch.Tensor):        
        robot_state.action = action["action"].tolist()  
    else:
        robot_state.action = action["action"] 

def reset_camera_image_buffers(robot_state:RobotState) -> None:
    img_size = robot_state.camera_image_buffers["img_size"]
    cam_info = [{"name":name.split(".")[-1]} for name in robot_state.camera_image_buffers.keys() if "image" in name]
    robot_state.camera_image_buffers = init_image_buffers(img_size, cam_info)

def check_force_stop(events):
    if events["force_stop"]:
        logging.info("Force Stop Triggered !!")            
        return True
    else:
        return False

def convert_config_from_eval_to_record(eval_config: EvalControlConfig) -> RecordControlConfig:
    return RecordControlConfig(
        repo_id=eval_config.repo_id,
        single_task=eval_config.single_task,
        root=eval_config.root,
        policy=eval_config.policy,
        fps=eval_config.fps,
        warmup_time_s=eval_config.warmup_time_s,
        episode_time_s=eval_config.episode_time_s,
        reset_time_s=eval_config.reset_time_s,
        num_episodes=eval_config.num_episodes,
        video=eval_config.video,
        push_to_hub=eval_config.push_to_hub,
        private=eval_config.private,
        tags=eval_config.tags,
        num_image_writer_processes=eval_config.num_image_writer_processes,
        num_image_writer_threads_per_camera=eval_config.num_image_writer_threads_per_camera,
        display_cameras=eval_config.display_cameras,
        play_sounds=eval_config.play_sounds,
        resume=eval_config.resume,
    )

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
        robot_state (RobotState): robot state
        control_time_s (int, optional): total time to execute the control loop. Defaults to None.
        teleoperate (bool, optional): enable robot teleop. Defaults to False.
        display_cameras (bool, optional): Not req since cam feed is displayed in the GUI. Defaults to False.
        dataset (LeRobotDataset | None, optional): lerobot dataset object. Defaults to None.
        events (Dict, optional): keyboard btn press events. Defaults to None.
        policy (optional): policy object for evaluation. Defaults to None.
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

def record(
    robot: Robot,
    robot_state: RobotState,
    cfg: RecordControlConfig,    
    local_files_only: bool = False,
    events = None,
    enable_auto_record: bool = False,
)->None:
    """
    control model to just record and eval with recording

    Args:
        robot (Robot): robot object
        local_files_only (bool, optional): use local datatset files and not search on the hub. Defaults to False.
        events (_type_, optional): keyboard button press events. Defaults to None.
        enable_auto_record (bool, optional): Only enabled during eval with recording. This does not wait for GUI input to start rec. Defaults to False.
    """        
    if cfg.resume:
        logging.info("Resume enabled. Loading existing dataset.")
        dataset = LeRobotDataset(
            cfg.repo_id,
            root=cfg.root,
        )
        if len(robot.cameras) > 0:
            dataset.start_image_writer(
                num_processes=cfg.num_image_writer_processes,
                num_threads=cfg.num_image_writer_threads_per_camera * len(robot.cameras),
            )
        sanity_check_dataset_robot_compatibility(dataset, robot, cfg.fps, cfg.video)
    else:
        # Create empty dataset or load existing saved episodes
        logging.info("Creating new dataset for recording.")
        sanity_check_dataset_name(cfg.repo_id, cfg.policy)
        if Path(cfg.repo_id).exists():
            raise ValueError(f"Dataset with name {cfg.repo_id} already exists. Please choose a different name or del previous dataset.")
        dataset = LeRobotDataset.create(
            cfg.repo_id,
            cfg.fps,
            root=cfg.root,
            robot=robot,
            use_videos=cfg.video,
            image_writer_processes=cfg.num_image_writer_processes,
            image_writer_threads=cfg.num_image_writer_threads_per_camera * len(robot.cameras),
        )
    logging.info("Success: Dataset created.")

    # Load pretrained policy
    logging.info(f"Loading pretrained policy type: {cfg.policy.type}")
    policy = None if cfg.policy is None else make_policy(cfg.policy, ds_meta=dataset.meta)

    if not robot.is_connected:
        robot.connect()

    enable_teleoperation = policy is None
    if cfg.warmup_time_s > 0:
        logging.info("Warming up robot ...")
        control_loop(
            robot=robot,
            robot_state=robot_state,
            control_time_s=cfg.warmup_time_s,
            events=events,
            fps=cfg.fps,
            teleoperate=enable_teleoperation,
        )

    if has_method(robot, "teleop_safety_stop"):
        robot.teleop_safety_stop()

    recorded_episodes = 0
    num_episodes -= dataset.num_episodes
    while True:
        if recorded_episodes >= num_episodes:
            break   
        
        if enable_auto_record:
            events["start_recording"] = True    

            logging.info(f"Auto record enabled. Recording episode {dataset.num_episodes}...")    
        else:
            logging.info(f"Ready to record episode {dataset.num_episodes}. Press the record button to start recording.")
        
        control_loop(
            robot=robot,
            robot_state=robot_state, 
            control_time_s=cfg.episode_time_s,                
            teleoperate=policy is None,
            dataset=dataset,
            policy=policy,
            fps=cfg.fps,       
            events=events,
            single_task=cfg.single_task,
        )

        if check_force_stop(events): return

        # Execute a few seconds without recording to give time to manually reset the environment
        # Current code logic doesn't allow to teleoperate during this time.
        if not events["stop_recording"] and (
            (dataset.num_episodes < num_episodes - 1) or events["rerecord_episode"]
        ):
            logging.info("Reset the environment")
            events["start_recording"] = False

        if events["rerecord_episode"]:
            logging.info("Re-record episode")
            events["rerecord_episode"] = False
            events["exit_early"] = False

            logging.info("Clearing episode buffer")
            dataset.clear_episode_buffer()
            logging.info("Success: Episode buffer cleared.")
            continue
        
        if dataset.episode_buffer is not None:
            logging.info(f"Saving Episode {dataset.num_episodes}. Please wait ...")
            dataset.save_episode()
            logging.info(f"Success: Episode {dataset.num_episodes-1} saved.")
        else:
            logging.warning(f"Episode {dataset.num_episodes} buffer is empty. No data was recorded. Forgot to trigger recording ?")

        recorded_episodes += 1

        if events["stop_recording"]:
            break

        if check_force_stop(events): return
    
    logging.info("Stop recording")
    stop_recording(robot, listener=None, display_cameras=False)   

    if cfg.push_to_hub:
        logging.info("Pushing dataset to hub. Please wait ...")
        dataset.push_to_hub(tags=cfg.tags, private=cfg.private)
        logging.info("Success: Dataset pushed to hub.")

    logging.info("Exiting record loop")

def eval(
    robot: Robot,
    robot_state: RobotState,
    cfg: EvalControlConfig,
    events = None,
) -> None:
    """
    evalutae policy on real robot without recording or manual teleoperation.

    Args:
        robot (Robot): robot object
        robot_state (RobotState): robot state
        cfg (EvalControlConfig): config for evaluation            
        events (_type_, optional): keyboard button press events. Defaults to None.
    """

    record_control_config = convert_config_from_eval_to_record(cfg)

    record(
        robot,
        robot_state,
        cfg=record_control_config,
        events=events,
        enable_auto_record=cfg.record_eval_episodes,
    )