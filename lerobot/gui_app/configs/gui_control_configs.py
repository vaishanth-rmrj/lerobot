from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from lerobot.common.robot_devices.robots.configs import RobotConfig
from lerobot.configs import parser
from lerobot.configs.policies import PreTrainedConfig

@dataclass
class TeleoperateControlConfig:
    # Limit the maximum frames per second. By default, no limit.
    fps: int | None = 30


@dataclass
class RecordControlConfig:
    # Dataset identifier. By convention it should match '{hf_username}/{dataset_name}' (e.g. `lerobot/test`).
    repo_id: str = "data/test"
    # A short but accurate description of the task performed during the recording (e.g. "Pick the Lego block and drop it in the box on the right.")
    single_task: str = "default task"
    # Root directory where the dataset will be stored (e.g. 'dataset/path').
    root: str | Path | None = "data/test"
    policy: PreTrainedConfig | None = None
    # Limit the frames per second. By default, uses the policy fps.
    fps: int | None = 30
    # Number of seconds before starting data collection. It allows the robot devices to warmup and synchronize.
    warmup_time_s: int | float = 10
    # Number of seconds for data recording for each episode.
    episode_time_s: int | float = 60
    # Number of seconds for resetting the environment after each episode.
    reset_time_s: int | float = 60
    # Number of episodes to record.
    num_episodes: int = 50
    # Encode frames in the dataset into video
    video: bool = True
    # Upload dataset to Hugging Face hub.
    push_to_hub: bool = True
    # Upload on private repository on the Hugging Face hub.
    private: bool = False
    # Add tags to your dataset on the hub.
    tags: list[str] | None = None
    # Number of subprocesses handling the saving of frames as PNG. Set to 0 to use threads only;
    # set to ≥1 to use subprocesses, each using threads to write images. The best number of processes
    # and threads depends on your system. We recommend 4 threads per camera with 0 processes.
    # If fps is unstable, adjust the thread count. If still unstable, try using 1 or more subprocesses.
    num_image_writer_processes: int = 0
    # Number of threads writing the frames as png images on disk, per camera.
    # Too many threads might cause unstable teleoperation fps due to main thread being blocked.
    # Not enough threads might cause low camera fps.
    num_image_writer_threads_per_camera: int = 4
    # Display all cameras on screen
    display_cameras: bool = False
    # Use vocal synthesis to read events.
    play_sounds: bool = False
    # Resume recording on an existing dataset.
    resume: bool = False

@dataclass
class EvalControlConfig:
    # Dataset identifier. By convention it should match '{hf_username}/{dataset_name}' (e.g. `lerobot/test`).
    repo_id: str = "data/eval_test"
    # A short but accurate description of the task performed during the evaluation (e.g. "Pick the Lego block and drop it in the box on the right.")
    single_task: str = "default eval task"
    # Root directory where the dataset will be stored (e.g. 'dataset/path').
    root: str | Path | None = "data/eval_test"
    policy_path:str | None = None
    policy: PreTrainedConfig | None = None
    # Limit the frames per second. By default, uses the policy fps.
    fps: int | None = 30
    # Number of seconds before starting data collection. It allows the robot devices to warmup and synchronize.
    warmup_time_s: int | float = 2
    # Number of seconds for data recording for each episode.
    episode_time_s: int | float = 120
    # Number of seconds for resetting the environment after each episode.
    reset_time_s: int | float = 60
    # Number of episodes to record.
    num_episodes: int = 50
    # Encode frames in the dataset into video
    video: bool = True
    # Upload dataset to Hugging Face hub.
    push_to_hub: bool = True
    # Upload on private repository on the Hugging Face hub.
    private: bool = False
    # Add tags to your dataset on the hub.
    tags: list[str] | None = None
    # Number of subprocesses handling the saving of frames as PNG. Set to 0 to use threads only;
    # set to ≥1 to use subprocesses, each using threads to write images. The best number of processes
    # and threads depends on your system. We recommend 4 threads per camera with 0 processes.
    # If fps is unstable, adjust the thread count. If still unstable, try using 1 or more subprocesses.
    num_image_writer_processes: int = 0
    # Number of threads writing the frames as png images on disk, per camera.
    # Too many threads might cause unstable teleoperation fps due to main thread being blocked.
    # Not enough threads might cause low camera fps.
    num_image_writer_threads_per_camera: int = 4
    # Display all cameras on screen
    display_cameras: bool = False
    # Use vocal synthesis to read events.
    play_sounds: bool = False
    # Resume recording on an existing dataset.
    resume: bool = False
    # Record evaluation episodes.
    record_eval_episodes: bool = False

    def __post_init__(self):
        if self.policy_path:
            self.policy = PreTrainedConfig.from_pretrained(self.policy_path)
            self.policy.pretrained_path = self.policy_path

@dataclass
class ReplayControlConfig:
    # Dataset identifier. By convention it should match '{hf_username}/{dataset_name}' (e.g. `lerobot/test`).
    repo_id: str = "data/test"
    # Index of the episode to replay.
    episode: int = 0
    # Root directory where the dataset will be stored (e.g. 'dataset/path').
    root: str | Path | None = "data/test"
    # Limit the frames per second. By default, uses the dataset fps.
    fps: int | None = None
    # Use vocal synthesis to read events.
    play_sounds: bool = True


@dataclass
class GUIControlPipelineConfig:
    robot: RobotConfig
    teleoperate_control: TeleoperateControlConfig = field(default_factory=TeleoperateControlConfig)
    record_control: RecordControlConfig = field(default_factory=RecordControlConfig)
    eval_control: EvalControlConfig = field(default_factory=EvalControlConfig)
    replay_control: ReplayControlConfig = field(default_factory=ReplayControlConfig)
    home_pose: List[float] = field(default_factory=list)