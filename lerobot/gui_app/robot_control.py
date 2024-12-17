import cv2
import numpy as np
import time
import threading
import logging
from pathlib import Path
from typing import List

from omegaconf.dictconfig import DictConfig

# project imports
from lerobot.common.robot_devices.control_utils import init_keyboard_listener, busy_wait 
from lerobot.common.utils.utils import init_hydra_config
from lerobot.common.robot_devices.robots.factory import make_robot
from lerobot.common.datasets.lerobot_dataset import LeRobotDataset
from lerobot.common.datasets.image_writer import safe_stop_image_writer, AsyncImageWriter
from lerobot.common.robot_devices.robots.utils import Robot
from lerobot.common.robot_devices.control_utils import (
    control_loop,
    has_method,
    init_keyboard_listener,
    init_policy,
    log_control_info,
    record_episode,
    reset_environment,
    sanity_check_dataset_name,
    sanity_check_dataset_robot_compatibility,
    stop_recording,
    warmup_record,
    predict_action,
)

class RobotControl:
    def __init__(
            self,
            config: DictConfig
        ) -> None:

        self.config = config
        self.is_shutdown = False
        

        self.is_process_active = False
        self.running_threads = {}

        self.listener, self.events = init_keyboard_listener()  
        if self.events is not None:
            # add additional event flags
            self.events["force_stop"] = False
            self.events["start_recording"] = False

        self.robot = self.init_robot(self.config.robot_cfg_file)  
        self.cams_image_buffer = self.init_cam_image_buffers()

        # self.dataset_image_writer = AsyncImageWriter(
        #     num_processes=self.config.record.num_image_writer_processes,
        #     num_threads=self.config.record.num_image_writer_threads_per_camera * len(self.robot.cameras),
        # ) 
    
    def init_cam_image_buffers(self):
        cams_image_buffers = {}

        w, h = 640, 480
        no_feed_img = cv2.putText(
            img=np.zeros((h, w, 3), dtype=np.uint8),
            text="No feed found!",
            org=(w // 2 - 150, h // 2),
            fontFace=cv2.FONT_HERSHEY_SIMPLEX,
            fontScale=1.2,
            color=(0, 0, 255),
            thickness=3, 
            lineType=cv2.LINE_AA
        )
        ret, encoded_no_feed_img = cv2.imencode('.jpg', no_feed_img)
        for cam_info in self.get_camera_info():
            cams_image_buffers["observation.images."+str(cam_info["name"])] = encoded_no_feed_img
        
        return cams_image_buffers
    
    def init_robot(self, config_path: str):
        logging.info(f"Provided robot config file: {config_path}")
        robot_cfg = init_hydra_config(config_path)
        if hasattr(self, 'robot'):
            self.robot.__del__()
        robot = make_robot(robot_cfg)
        return robot
    
    @property
    def num_cameras(self):
        return self.robot.cameras
    
    def get_camera_info(self) -> List:
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
        ) -> None:

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
                    logging.info(f"Error encoding cam:{key} feed")

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
        play_sounds: bool = True,
        resume: bool = False,
        local_files_only: bool = False,
        events = None,
    ):
        
        listener = self.listener
        events = events
        policy = None
        device = None
        use_amp = None

        if single_task:
            task = single_task
        else:
            raise NotImplementedError("Only single-task recording is supported for now")

        # Load pretrained policy
        # if pretrained_policy_name_or_path is not None:
        #     policy, policy_fps, device, use_amp = init_policy(pretrained_policy_name_or_path, policy_overrides)

        #     if fps is None:
        #         fps = policy_fps
        #         logging.warning(f"No fps provided, so using the fps from policy config ({policy_fps}).")
        #     elif fps != policy_fps:
        #         logging.warning(
        #             f"There is a mismatch between the provided fps ({fps}) and the one from policy config ({policy_fps})."
        #         )

        if resume:
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
        
        # dataset.image_writer.stop()
        # time.sleep(2)
        # dataset.image_writer = self.dataset_image_writer

        if not robot.is_connected:
            robot.connect()

        enable_teleoperation = policy is None
        # logging.info("Warmup record")
        # self.control_loop(
        #     robot=robot,
        #     control_time_s=warmup_time_s,
        #     events=events,
        #     fps=fps,
        #     teleoperate=enable_teleoperation,
        # )

        if has_method(robot, "teleop_safety_stop"):
            robot.teleop_safety_stop()

        recorded_episodes = 0
        while True:
            if recorded_episodes >= num_episodes:
                break            

            logging.info(f"Ready to record episode {dataset.num_episodes}")
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
            # TODO(rcadene): add an option to enable teleoperation during reset
            # Skip reset for the last episode to be recorded
            if not events["stop_recording"] and (
                (dataset.num_episodes < num_episodes - 1) or events["rerecord_episode"]
            ):
                logging.info("Reset the environment")
                events["start_recording"] = False

            if events["rerecord_episode"]:
                logging.info("Re-record episode")
                events["rerecord_episode"] = False
                events["exit_early"] = False
                dataset.clear_episode_buffer()
                continue
            
            logging.info(f"Saving Episode {dataset.num_episodes}. Please wait ...")
            dataset.save_episode(task)
            recorded_episodes += 1

            if events["stop_recording"]:
                break

            if self.check_force_stop(events): return
        
        logging.info("Stop recording")
        stop_recording(robot, listener, display_cameras=False)

        if run_compute_stats:
            logging.info("Computing dataset statistics")
        dataset.consolidate(run_compute_stats)

        if push_to_hub:
            dataset.push_to_hub(tags=tags)

        logging.info("Exiting")
    
    def run_teleop(self, config):

        logging.info("Started teleop control XD")
        self.control_loop(
            self.robot,
            fps=config.fps,
            teleoperate=True,
            events=self.events,
        )   
        self.events["force_stop"] = False
        
    def run_record(self, config: DictConfig):

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
            display_cameras = False,
            play_sounds = False,
            resume = config.resume,
            local_files_only = config.local_files_only,
            events=self.events,
        )
        self.events["force_stop"] = False
    
    def select_robot_control_mode(self, mode:str):

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

        # start the thread and store it
        self.running_threads[mode] = thread
        thread.start()
        return True

    def stop_threads(self):
        
        active_threads = len(self.running_threads)
        if active_threads > 0:
            logging.info(f"stop_threads : {active_threads} background threads running. Terminating all threads !!")

            for thread_id in list(self.running_threads.keys()):
                self.events["force_stop"] = True
                self.running_threads[thread_id].join()
                del self.running_threads[thread_id]
                logging.info(f"{thread_id} background thread was stopped. XD")
                self.events["force_stop"] = False
            
            # self.dataset_image_writer.stop()
        else:
            logging.info(f"stop_threads : No background threads running. XD")
            self.events["force_stop"] = False
        
        return True if len(self.running_threads) > 0 else False
    
    
    def __del__(self):
        if self.robot.is_connected:
            self.robot.disconnect()


