import cv2
import numpy as np
import time
import threading
import logging
from pathlib import Path
from typing import List, Dict

import torch
from omegaconf.dictconfig import DictConfig

# project imports
from lerobot.common.robot_devices.control_utils import init_keyboard_listener, busy_wait 
from lerobot.common.utils.utils import init_hydra_config
from lerobot.common.robot_devices.robots.factory import make_robot
from lerobot.common.datasets.lerobot_dataset import LeRobotDataset
from lerobot.common.datasets.image_writer import safe_stop_image_writer
from lerobot.common.robot_devices.robots.utils import Robot
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

class RobotControl:
    def __init__(
            self,
            config: DictConfig
        ) -> None:

        self.config = config
        self.running_threads = {}

        self.listener, self.events = init_keyboard_listener()  
        if self.events is not None:
            # add additional event flags
            self.events["force_stop"] = False
            self.events["start_recording"] = False
            self.events["interrupt_policy"] = False
            self.events["take_control"] = False

        self.robot = self.init_robot(self.config.robot_cfg_file)  
        self.cams_image_buffer = self.init_cam_image_buffers()
    
    def reinit_event_flags(self) -> None:
        self.events["force_stop"] = False
        self.events["start_recording"] = False
        self.events["interrupt_policy"] = False
        self.events["take_control"] = False
    
    def init_cam_image_buffers(self):
        """
        init cam image buffers
        """
        cams_image_buffers = {}

        w, h = 640, 480
        no_feed_img = cv2.putText(
            img=np.zeros((h, w, 3), dtype=np.uint8),
            text="No feed!",
            org=(w // 2 - 70, h // 2),
            fontFace=cv2.FONT_HERSHEY_SIMPLEX,
            fontScale=1.0,
            color=(0, 0, 255),
            thickness=2, 
            lineType=cv2.LINE_AA
        )
        ret, encoded_no_feed_img = cv2.imencode('.jpg', no_feed_img)
        for cam_info in self.get_camera_info():
            cams_image_buffers["observation.images."+str(cam_info["name"])] = encoded_no_feed_img
        
        return cams_image_buffers
    
    def init_robot(self, config_path: str)-> Robot:
        """
        init robot object from the provided config file using hydra

        Args:
            config_path (str): path to config file

        Returns:
            Robot: Manipulator robot object
        """
        logging.info(f"Provided robot config file: {config_path}")
        robot_cfg = init_hydra_config(config_path)
        if hasattr(self, 'robot'):
            self.robot.__del__()
        robot = make_robot(robot_cfg)
        return robot
    
    @property
    def num_cameras(self):
        return self.robot.cameras
    
    @property
    def is_connected(self):
        return self.robot.is_connected
    
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
                "video_url": "/robot/get-cam-feed/observation.images."+str(cam_name)
            })        
        return cam_info
        
    def check_force_stop(self, events):
        if events["force_stop"]:
            logging.info("Force Stop Triggered !!")            
            return True
        else:
            return False
    
    @safe_stop_image_writer
    def control_loop(
            self,
            robot:Robot,
            control_time_s:int=None,
            teleoperate:bool=False,
            display_cameras:bool=False,
            dataset: LeRobotDataset | None = None,
            events:Dict=None,
            policy=None,
            device=None,
            use_amp=None,
            fps:int=None,
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
        self.reinit_event_flags()

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
        logging.info("Started control loop.")
        while timestamp < control_time_s:
            start_loop_t = time.perf_counter()

            if teleoperate:
                observation, action = robot.teleop_step(record_data=True)
            else:
                observation = robot.capture_observation()

                if policy is not None:
                    pred_action = predict_action(observation, policy, device, use_amp)
                    # Action can eventually be clipped using `max_relative_target`,
                    # so action actually sent is saved in the dataset.
                    action = robot.send_action(pred_action)
                    action = {"action": action}
            
            if dataset is not None and events["start_recording"]:
                frame = {**observation, **action}
                dataset.add_frame(frame)

            image_keys = [key for key in observation if "image" in key]
            for key in image_keys:            
                cam_image = cv2.cvtColor(observation[key].numpy(), cv2.COLOR_RGB2BGR)
                ret, self.cams_image_buffer[key] = cv2.imencode('.jpg', cam_image)
                if not ret:
                    logging.info(f"Control Loop: Error encoding cam:{key} feed")

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
                self.cams_image_buffer = self.init_cam_image_buffers()
                break
            
            if self.check_force_stop(events): 
                self.cams_image_buffer = self.init_cam_image_buffers()
                return
                

    def record(
        self,
        robot: Robot,
        root: Path,
        repo_id: str,
        single_task: str,
        pretrained_policy_name_or_path: str | None = None,
        policy_overrides: List[str] | None = None,
        fps: int | None = None,
        warmup_time_s: int | float = 0,
        episode_time_s: int | float = 10,
        reset_time_s: int | float = 0,
        num_episodes: int = 50,
        video: bool = True,
        run_compute_stats: bool = True,
        push_to_hub: bool = True,
        tags: list[str] | None = None,
        num_image_writer_processes: int = 0,
        num_image_writer_threads_per_camera: int = 4,
        display_cameras: bool = False,
        play_sounds: bool = False,
        resume: bool = False,
        local_files_only: bool = False,
        events = None,
        enable_auto_record: bool = False,
    ):
        """
        control model to just record and eval with recording

        Args:
            robot (Robot): robot object
            root (Path): root dir path to save dataset
            repo_id (str): dataset identifier moslty used for hub push
            single_task (str): brief description of task
            pretrained_policy_name_or_path (str | None, optional): path to trained policy. Defaults to None.
            policy_overrides (List[str] | None, optional): policy overrides. Defaults to None.
            fps (int | None, optional): control fps at which recording is perfomed. Defaults to None.
            warmup_time_s (int | float, optional): warmup the robot and cam feed. Defaults to 10.
            episode_time_s (int | float, optional): Max time within which the dataset has to be recorded. Defaults to 60.
            reset_time_s (int | float, optional): Not required since record is triggered from GUI. Defaults to 0.
            num_episodes (int, optional): number of episodes to record. Defaults to 50.
            video (bool, optional): convert to video. Defaults to True.
            run_compute_stats (bool, optional): computer mean std min max stats for the datatset. Defaults to True.
            push_to_hub (bool, optional): push the dataset to hub. Defaults to True.
            tags (list[str] | None, optional): tags for datatset on the hub. Defaults to None.
            num_image_writer_processes (int, optional): num of processes to run for async image writer. Defaults to 0.
            num_image_writer_threads_per_camera (int, optional): num of threads to run for async image writer. Defaults to 4.
            display_cameras (bool, optional): Not req since displaying the cam feed on the GUI. Defaults to False.
            play_sounds (bool, optional): Play audio notifications. Defaults to False.
            resume (bool, optional): resume recordingh using prev dataset. Defaults to False.
            local_files_only (bool, optional): use local datatset files and not search on the hub. Defaults to False.
            events (_type_, optional): keyboard button press events. Defaults to None.
            enable_auto_record (bool, optional): Only enabled during eval with recording. This does not wait for GUI input to start rec. Defaults to False.
        """        
        listener = self.listener
        events = events
        policy = None
        device = None
        use_amp = None

        if single_task:
            task = single_task
        else:
            raise NotImplementedError("Only single-task recording is supported for now")

        # load pretrained policy
        if pretrained_policy_name_or_path is not None:
            logging.info(f"Loading pretrained policy: {pretrained_policy_name_or_path}")
            policy, policy_fps, device, use_amp = init_policy(pretrained_policy_name_or_path, policy_overrides)

            if fps is None:
                fps = policy_fps
                logging.warning(f"No fps provided, so using the fps from policy config ({policy_fps}).")
            elif fps != policy_fps:
                logging.warning(
                    f"There is a mismatch between the provided fps ({fps}) and the one from policy config ({policy_fps})."
                )

        if resume:
            logging.info("Resume enebaled. Loading existing dataset.")
            dataset = LeRobotDataset(
                repo_id,
                root=root,
                local_files_only=local_files_only,
            )
            dataset.start_image_writer(
                num_processes=num_image_writer_processes,
                num_threads=num_image_writer_threads_per_camera * len(robot.cameras),
            )
            sanity_check_dataset_robot_compatibility(dataset, robot, fps, video)
        else:
            # Create empty dataset or load existing saved episodes
            logging.info("Creating new dataset for recording.")
            sanity_check_dataset_name(repo_id, policy)
            dataset = LeRobotDataset.create(
                repo_id,
                fps,
                root=root,
                robot=robot,
                use_videos=video,
                image_writer_processes=num_image_writer_processes,
                image_writer_threads=num_image_writer_threads_per_camera * len(robot.cameras),
            )
        logging.info("Success: Dataset created.")

        
        if not robot.is_connected:
            robot.connect()

        enable_teleoperation = policy is None
        if warmup_time_s > 0:
            logging.info("Warming up robot ...")
            self.control_loop(
                robot=robot,
                control_time_s=warmup_time_s,
                events=events,
                fps=fps,
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
            
            self.control_loop(
                dataset=dataset,
                robot=robot,
                control_time_s=episode_time_s,                
                events=events,
                policy=policy,
                device=device,
                use_amp=use_amp,
                fps=fps,
                teleoperate=policy is None,
            )

            if self.check_force_stop(events): return

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
            
            logging.info(f"Saving Episode {dataset.num_episodes}. Please wait ...")
            dataset.save_episode(task)
            logging.info(f"Success: Episode {dataset.num_episodes} saved.")

            recorded_episodes += 1

            if events["stop_recording"]:
                break

            if self.check_force_stop(events): return
        
        logging.info("Stop recording")
        stop_recording(robot, listener, display_cameras=False)

        if run_compute_stats: logging.info("Computing dataset statistics")            
        dataset.consolidate(run_compute_stats)
        if run_compute_stats: logging.info("Success: Dataset statistics computed.")      

        if push_to_hub:
            logging.info("Pushing dataset to hub. Please wait ...")
            dataset.push_to_hub(tags=tags)
            logging.info("Success: Dataset pushed to hub.")

        logging.info("Exiting record loop")
    
    def eval_policy(
        self,
        robot: Robot,
        pretrained_policy_name_or_path: str,
        policy_overrides: List[str] | None = None,
        fps: int | None = None,
        warmup_time_s: int | float = 10,
        episode_time_s: int | float = 60,
        play_sounds: bool = False,
        events = None,
    ) -> None:
        """
        evalutae policy on real robot without recording or manual teleoperation.

        Args:
            robot (Robot): robot object
            pretrained_policy_name_or_path (str): path to trained policy.
            policy_overrides (List[str] | None, optional): policy overrides. Defaults to None.
            fps (int | None, optional): control fps at which eval is perfomed. Defaults to None.
            warmup_time_s (int | float, optional): warmup the robot and cam feed. Defaults to 10.
            episode_time_s (int | float, optional): Max time the robot gets to complete the task. Defaults to 60.
            play_sounds (bool, optional): Play audio notifications. Defaults to True.
            events (_type_, optional): keyboard button press events. Defaults to None.
        """
        
        listener = self.listener
        events = events
        policy = None
        device = None
        use_amp = None

        # load pretrained policy
        if pretrained_policy_name_or_path is not None:
            logging.info(f"Loading pretrained policy: {pretrained_policy_name_or_path}")
            policy, policy_fps, device, use_amp = init_policy(pretrained_policy_name_or_path, policy_overrides)

            if fps is None:
                fps = policy_fps
                logging.warning(f"No fps provided, so using the fps from policy config ({policy_fps}).")
            elif fps != policy_fps:
                logging.warning(
                    f"There is a mismatch between the provided fps ({fps}) and the one from policy config ({policy_fps})."
                )
        else:
            raise ValueError("No pretrained policy provided for evaluation !!")
            return

        if not robot.is_connected:
            robot.connect()

        logging.info("Warming up robot ...")
        self.control_loop(
            robot=robot,
            control_time_s=warmup_time_s,
            events=events,
            fps=fps,
            teleoperate=False,
        )

        if has_method(robot, "teleop_safety_stop"):
            robot.teleop_safety_stop()

        logging.info("Evaluating policy on robot...")
        self.control_loop(
            robot=robot,
            control_time_s=episode_time_s,                
            events=events,
            policy=policy,
            device=device,
            use_amp=use_amp,
            fps=fps,
            teleoperate=False,
        )
        
        logging.info("Stopping eval")
        stop_recording(robot, listener, display_cameras=False)
        logging.info("Exiting eval policy")
    
    @safe_disconnect
    def calibrate(self, robot:Robot, arm_name:str, thread_id:str):

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

    def perform_smooth_transition(self, robot:Robot, fps:int = 30, max_transition_time_s:float = 2.0) -> bool:

        # slow down motor acceleration 
        # to prevent agressive motion when transitioning
        for name in robot.follower_arms:
            robot.follower_arms[name].write("Acceleration", 2)
                
        timestamp = 0.0
        start_t = time.perf_counter()
        while timestamp < max_transition_time_s:
            start_loop_t = time.perf_counter()

            # sync leader and follower joint states
            robot.teleop_step()

            if fps is not None:
                dt_s = time.perf_counter() - start_loop_t
                busy_wait(1 / fps - dt_s)

            timestamp = time.perf_counter() - start_t
        
        # reset the motor acceleration val
        for name in robot.follower_arms:
            robot.follower_arms[name].write("Acceleration", 254)

        return True

    def hg_dagger_loop(
            self,
            robot: Robot,
            root: Path,
            repo_id: str,
            single_task: str,
            pretrained_policy_name_or_path: str | None = None,
            policy_overrides: List[str] | None = None,
            fps: int | None = None,
            video: bool = True,
            num_image_writer_processes: int = 0,
            num_image_writer_threads_per_camera: int = 4,
            local_files_only: bool = False,
            num_epochs:int = 10,
            curr_epoch:int = 0,
            num_rollouts:int = 4,
            max_rollout_time_s:int = 60,
            warmup_time_s: int | float = 0,
            reset_time_s: int | float = 0,
            run_compute_stats: bool = True,
            push_to_hub: bool = True,
            resume: bool = False,
            events:Dict=None,
        ) -> None:

        if single_task:
            task = single_task
        else:
            raise NotImplementedError("Only single-task recording is supported for now")

        # warmup the camera feed
        if warmup_time_s > 0:
            logging.info("Warming up robot ...")
            self.control_loop(
                robot=robot,
                control_time_s=warmup_time_s,
                events=events,
                fps=fps,
                teleoperate=False,
            )

        # load pretrained policy
        if pretrained_policy_name_or_path is not None:
            logging.info(f"Loading pretrained policy: {pretrained_policy_name_or_path}")
            policy, policy_fps, device, use_amp = init_policy(pretrained_policy_name_or_path, policy_overrides)

            if fps is None:
                fps = policy_fps
                logging.warning(f"No fps provided, so using the fps from policy config ({policy_fps}).")
            elif fps != policy_fps:
                logging.warning(
                    f"There is a mismatch between the provided fps ({fps}) and the one from policy config ({policy_fps})."
                )
        else:
            raise ValueError(f"Invalid pretrained policy path: {pretrained_policy_name_or_path}")

        # init lerobot dataset
        logging.info(f"Loading existing dataset with id: {repo_id}.")
        dataset = LeRobotDataset(
            repo_id,
            root=root,
            local_files_only=local_files_only,
        )
        dataset.start_image_writer(
            num_processes=num_image_writer_processes,
            num_threads=num_image_writer_threads_per_camera * len(robot.cameras),
        )
        sanity_check_dataset_robot_compatibility(dataset, robot, fps, video)
        # FUTURE: init I -> [] for learning risk metrics

        is_leader_pose_matched = False
        # loop epoch
        for epoch in range(curr_epoch, num_epochs):

            # loop rollout
            for rollout_id in range(num_rollouts):

                # loop timestep
                timestamp = 0
                start_rollout_t = time.perf_counter()
                # control loop
                while timestamp < max_rollout_time_s:
                    start_loop_t = time.perf_counter()

                    if events["take_control"]:
                        if not is_leader_pose_matched:
                            is_leader_pose_matched = self.perform_smooth_transition(robot, fps, max_transition_time_s=2.0)
                        observation, action = robot.teleop_step(record_data=True)
                    else:
                        observation = robot.capture_observation()
                    
                    pred_action = predict_action(observation, policy, device, use_amp)

                    if not events["interrupt_policy"] and not events["take_control"]:

                        if is_leader_pose_matched:
                            # TODO: FIX this section
                            # torch.allclose(leader_joint_pos, follower_joint_pos, atol=abs_tol)

                            max_transition_time_s = 1.0
                            policy_transition_timestamp = 0.0
                            start_policy_t = time.perf_counter()
                            counter = 0
                            while counter < 5:
                                start_policy_loop_t = time.perf_counter()

                                observation = robot.capture_observation()
                                pred_action = predict_action(observation, policy, device, use_amp)
                                logging.info(pred_action)
                                counter += 1

                                if fps is not None:
                                    dt_s = time.perf_counter() - start_policy_loop_t
                                    busy_wait(1 / fps - dt_s)

                                policy_transition_timestamp = time.perf_counter() - start_policy_t

                            is_leader_pose_matched = False
                        
                        # Action can eventually be clipped using `max_relative_target`,
                        # so action actually sent is saved in the dataset.
                        action = robot.send_action(pred_action)
                        action = {"action": action}

                    # if expert has control record expert labels
                    if dataset is not None and events["take_control"]:
                        frame = {**observation, **action}
                        dataset.add_frame(frame)
                    
                    image_keys = [key for key in observation if "image" in key]
                    for key in image_keys:            
                        cam_image = cv2.cvtColor(observation[key].numpy(), cv2.COLOR_RGB2BGR)
                        ret, self.cams_image_buffer[key] = cv2.imencode('.jpg', cam_image)
                        if not ret:
                            logging.info(f"Control Loop: Error encoding cam:{key} feed")

                    if fps is not None:
                        dt_s = time.perf_counter() - start_loop_t
                        busy_wait(1 / fps - dt_s)

                    timestamp = time.perf_counter() - start_rollout_t
                    if events["exit_early"]:
                        logging.info("Early exit triggered. Exiting while loop !!")
                        events["exit_early"] = False
                        self.cams_image_buffer = self.init_cam_image_buffers()
                        break
                    
                    if self.check_force_stop(events): 
                        self.cams_image_buffer = self.init_cam_image_buffers()
                        return          

                    # FUTURE: if expert taking control record doubt frames to I -> []

                # append collected expert dataset
                if dataset.episode_buffer is not None:
                    logging.info(f"Saving Episode {dataset.num_episodes}. Please wait ...")
                    dataset.save_episode(task)
                    logging.info(f"Success: Episode {dataset.num_episodes} saved.")
                # FUTURE: append doubt frames to I-> []

                if self.check_force_stop(events): return
            
            if run_compute_stats: logging.info("Computing dataset statistics")            
            dataset.consolidate(run_compute_stats)
            if run_compute_stats: logging.info("Success: Dataset statistics computed.")  
            # train a novice model on newly collected dataset
            # save the model based on epoch
        
        # FUTURE: calc risk metric using collected doubt frames        
    
    def run_teleop(self, config: DictConfig):
        """
        run teleop control mode

        Args:
            config (DictConfig): teleop config
        """

        logging.info("Started teleop control XD")
        self.control_loop(
            self.robot,
            fps=config.fps,
            teleoperate=True,
            events=self.events,
        )   
        self.events["force_stop"] = False
        
    def run_record(self, config: DictConfig):
        """
        run record control mode

        Args:
            config (DictConfig): record config
        """
        logging.info("Started record control XD")
        self.record(
            robot = self.robot,
            root = config.root,
            repo_id = config.repo_id,
            single_task = config.single_task,
            fps = config.fps,
            episode_time_s = config.episode_time_s,
            num_episodes = config.num_episodes,
            video = True,
            run_compute_stats = config.run_compute_stats,
            push_to_hub = config.push_to_hub,
            tags = config.tags,
            num_image_writer_processes = config.num_image_writer_processes,
            num_image_writer_threads_per_camera = config.num_image_writer_threads_per_camera,
            play_sounds = False,
            resume = config.resume,
            local_files_only = config.local_files_only,
            events=self.events,
        )
        self.events["force_stop"] = False

    def run_eval(self, config: DictConfig):
        """
        run eval control mode with or without recording episodes

        Args:
            config (DictConfig): eval config
        """
        logging.info("Started eval control XD")
        if not config.record_eval_episodes:
            self.eval_policy(
                robot = self.robot,
                pretrained_policy_name_or_path = config.pretrained_policy_path,
                fps= config.fps,
                warmup_time_s = config.warmup_time_s,
                episode_time_s = config.episode_time_s,
                events = self.events,
            )
        else:
            # evalutate policy and record episodes
            self.record(
                robot = self.robot,
                pretrained_policy_name_or_path = config.pretrained_policy_path,
                root = config.root,
                repo_id = config.repo_id,
                single_task = config.single_task,
                fps = config.fps,
                episode_time_s = config.episode_time_s,
                warmup_time_s= config.warmup_time_s,
                num_episodes = config.num_episodes,
                video = True,
                run_compute_stats = True,
                push_to_hub = config.push_to_hub,
                tags = config.tags,
                num_image_writer_processes = config.num_image_writer_processes,
                num_image_writer_threads_per_camera = config.num_image_writer_threads_per_camera,
                play_sounds = False,
                local_files_only = True,
                events=self.events,
                enable_auto_record = True, # only enable auto record for eval ds recording
            )
        
        self.events["force_stop"] = False
    
    def run_calibration(self, arm_name:str):
        """
        run arm calibration on separate thread

        Args:
            arm_name (str): name of the arm to calibrate
        """
        if len(self.running_threads) > 0:
            logging.info("select_robot_control_mode : Background threads running. Please stop other threads / processes !!")
            return False
        
        thread_id = "calibrate"
        logging.info("Started calibration control XD")
        thread = threading.Thread(
            target=self.calibrate, 
            daemon=True, 
            args=[self.robot, arm_name, thread_id]
        )

        self.running_threads[thread_id] = thread
        thread.start()
    
    def run_hg_dagger(self, config:DictConfig) -> None:

        logging.info("Started HG-DAgger control XD")
        self.hg_dagger_loop(
            robot = self.robot,
            root = config.root,
            repo_id = config.repo_id,
            single_task = config.single_task,
            pretrained_policy_name_or_path = config.pretrained_policy_path,
            fps = config.fps,
            video = True,
            num_image_writer_processes = config.num_image_writer_processes,
            num_image_writer_threads_per_camera = config.num_image_writer_threads_per_camera,
            local_files_only = config.local_files_only,
            num_epochs = config.num_epochs,
            curr_epoch = config.curr_epoch,
            num_rollouts = config.num_rollouts,
            max_rollout_time_s = config.max_rollout_time_s,
            warmup_time_s = config.warmup_time_s,
            reset_time_s = config.reset_time_s,
            run_compute_stats = config.run_compute_stats,
            push_to_hub = config.push_to_hub,
            resume = config.resume,
            events = self.events,
        )
        self.events["force_stop"] = False
    
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
                args=[self.config.teleop],
                daemon=True,
            )
        elif mode == "record":
            thread = threading.Thread(
                target=self.run_record, 
                daemon=True, 
                args=[self.config.record]
            )
        elif mode == "eval":
            thread = threading.Thread(
                target=self.run_eval, 
                daemon=True, 
                args=[self.config.eval]
            )  
        elif mode == "hg_dagger":   
            thread = threading.Thread(
                target=self.run_hg_dagger, 
                daemon=True, 
                args=[self.config.hg_dagger]
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
        
        # resetting events
        self.events["force_stop"] = False
        self.events["interrupt_policy"] = False
        self.events["take_control"] = False
        
        return True if len(self.running_threads) > 0 else False
    
    
    def __del__(self):
        if self.robot.is_connected:
            self.robot.disconnect()


