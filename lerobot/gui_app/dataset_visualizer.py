import os
import cv2
import numpy as np
from pathlib import Path
from typing import List
import threading
import time
import logging

# project imports
from lerobot.common.datasets.lerobot_dataset import LeRobotDataset
from lerobot.common.robot_devices.control_utils import busy_wait 


class DatasetVisualizer:
    def __init__(self, repo_id:str, root:str, local_files_only:bool = True):
        self.root = root
        self.dataset = LeRobotDataset(repo_id, root=root, local_files_only=local_files_only)  
        self.loop_thread = None     

        # episode vars
        self.curr_episode_id = 0
        self.cv2_video_captures = {}
        self.curr_frame_id = 0
        self.episode_task = ""
        self.videos_frame_buffer = {}
        self.num_frames = float('inf')

        self.has_state = "observation.state" in self.dataset.features
        self.has_action = "action" in self.dataset.features
        self.state_action_columns = ["timestamp"]
        if self.has_state: self.state_action_columns += ["observation.state"]
        if self.has_action: self.state_action_columns += ["action"]
        self.episode_states = []
        self.episode_actions = []
        self.curr_state = []
        self.curr_action = []

        # always init the first episode to display by default
        self.init_episode_data(episode_id=0)
    
    def get_video_info(self) -> List:
        video_info = []
        for video_id, video_key in enumerate(self.dataset.meta.video_keys):
            video_info.append({
                "id": video_id,
                "name": str(video_key),
                "video_url": "/dataset/get-video-frame/"+str(video_key),
            })        
        return video_info
    
    def get_dataset_info(self):
        dataset_info = {
            "repo_id": self.dataset.repo_id,
            "num_samples": self.dataset.num_frames,
            "num_episodes": self.dataset.num_episodes,
            "fps": self.dataset.fps,
        }
        return dataset_info
    
    def get_frame_at_index(self, cap:cv2.VideoCapture, frame_index:int):
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)  # Set the frame position
        ret, frame = cap.read()  # Read the frame
        if not ret:
            logging.warning(f"Error: Could not retrieve frame at index {frame_index}.")
            return None
        return frame
    
    def init_episode_data(self, episode_id:int):
        self.stop_loop()
        self.curr_episode_id = episode_id
        self.curr_frame_id = 0
        self.is_paused = False

        videos_num_frames = {}
        self.episode_task = self.dataset.meta.episodes[episode_id]["tasks"]
        # get the video captures for the episode
        for video_key in self.dataset.meta.video_keys:
            video_path = self.root + os.sep + str(self.dataset.meta.get_video_file_path(episode_id, video_key))
            self.cv2_video_captures[video_key] = cv2.VideoCapture(video_path)

            total_num_frames = int(self.cv2_video_captures[video_key].get(cv2.CAP_PROP_FRAME_COUNT))
            self.num_frames = min(self.num_frames, total_num_frames)
            videos_num_frames[video_key] = total_num_frames
            
            frame = self.get_frame_at_index(self.cv2_video_captures[video_key], 0)
            ret, self.videos_frame_buffer[video_key] = cv2.imencode('.jpg', frame)
            if not ret:
                logging.warning(f"Error: Could not read the first frame of video {video_key}.")
                return

        # check if all videos have the same number of frames
        if len(set(videos_num_frames.values())) != 1:
            logging.warning(f"Error: Videos have different number of frames.")
            for video_key, num_frames in videos_num_frames.items():
                logging.warning(f"Video {video_key} has {num_frames} frames.")
            return     
        
        # fetch state and action
        from_idx = self.dataset.episode_data_index["from"][episode_id]
        to_idx = self.dataset.episode_data_index["to"][episode_id]
        data = self.dataset.hf_dataset.select_columns(self.state_action_columns)

        # clear prev states and actions
        self.episode_states = []
        self.episode_actions = []
        for i in range(from_idx, to_idx):
            # row = [data[i]["timestamp"].item()]
            if self.has_state:
                frame_state = data[i]["observation.state"].tolist()
                self.episode_states.append(frame_state)
            if self.has_action:
                frame_action = data[i]["action"].tolist()
                self.episode_actions.append(frame_action)
        
        self.curr_state = self.episode_states[0]
        self.curr_action = self.episode_actions[0]

        # start the play loop
        self.play_or_resume()
    
    def next_frame(self):
        self.curr_frame_id += 1        
        for video_key, video_cap in self.cv2_video_captures.items():
            last_frame_id = int(video_cap.get(cv2.CAP_PROP_FRAME_COUNT))
            if self.curr_frame_id >= last_frame_id:
                print("Error: Reached the last frame.")
                return
            frame = self.get_frame_at_index(video_cap, self.curr_frame_id)
            ret, self.videos_frame_buffer[video_key] = cv2.imencode('.jpg', frame)
        
        self.curr_state = self.episode_states[self.curr_frame_id]
        self.curr_action = self.episode_actions[self.curr_frame_id]
    
    def prev_frame(self):
        self.curr_frame_id -= 1        
        for video_key, video_cap in self.cv2_video_captures.items():
            if self.curr_frame_id <= 0:
                print("Error: Reached the first frame.")
                return
            frame = self.get_frame_at_index(video_cap, self.curr_frame_id)
            ret, self.videos_frame_buffer[video_key] = cv2.imencode('.jpg', frame)
        
        self.curr_state = self.episode_states[self.curr_frame_id]
        self.curr_action = self.episode_actions[self.curr_frame_id]
    
    def pause(self):
        self.is_paused = True

    def play_or_resume(self):            
        if self.loop_thread is not None:
            self.stop_threads()

        self.is_paused = False
        self.loop_thread = threading.Thread(target=self.loop_frames)
        self.loop_thread.start()

    def loop_frames(self):
        
        while not self.is_paused:
            start_loop_t = time.perf_counter()
            if self.curr_frame_id >= self.num_frames-1:
                self.curr_frame_id = 0
            self.next_frame()
            print(f"self.curr_state : {len(self.curr_state)}")
            print(f"self.curr_action : {len(self.curr_action)}")

            if self.dataset.fps is not None:
                dt_s = time.perf_counter() - start_loop_t
                busy_wait(1 / self.dataset.fps - dt_s)
            
            dt_s = time.perf_counter() - start_loop_t
    
    def stop_loop(self):       
        if self.loop_thread is not None:
            logging.info(f"stop_loop : Background loop thread is running. Stopping it.")

            self.is_paused = True
            self.loop_thread.join()
            self.loop_thread.join(timeout=5)
            self.loop_thread = None            
        else:
            logging.info(f"stop_loop : Background loop thread not running.")
        
        return True if self.loop_thread is None else False