import logging
from datetime import datetime
from pathlib import Path
import cv2 
import numpy as np
from dataclasses import dataclass, asdict, replace
import copy
from typing import Dict, List

from omegaconf import OmegaConf
from omegaconf.dictconfig import DictConfig
import draccus

# project imports
# from lerobot.gui_app.robot_control import RobotController
from lerobot.gui_app.configs.gui_control_configs import GUIControlPipelineConfig

draccus.set_config_type("yaml")

@dataclass
class RobotState:
    type:str
    camera_image_buffers: Dict[str, np.ndarray]
    camera_fps: float
    state: List[float]
    action: List[float]

# Custom handler to store logs in a list
class ListHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.log_list = []

    def emit(self, record):
        log_entry = self.format(record)
        self.log_list.append(log_entry)

# Function to initialize logging
def init_logging():
    def custom_format(record):
        dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        fnameline = f"{record.pathname}:{record.lineno}"
        message = f"{record.levelname} {dt} {fnameline[-15:]:>15} {record.msg}"
        return message

    # Reset root handlers
    logging.basicConfig(level=logging.INFO)
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    # Create a formatter that uses custom_format
    formatter = logging.Formatter()
    formatter.format = custom_format

    # Console handler for logging to terminal
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # Custom ListHandler to store logs in a list
    list_handler = ListHandler()
    list_handler.setFormatter(formatter)

    # Add handlers to the root logger
    root_logger = logging.getLogger()
    root_logger.addHandler(console_handler)
    root_logger.addHandler(list_handler)

    # Return the list handler for later use
    return list_handler

def cache_config(config: GUIControlPipelineConfig, cache_path:str = ".cache/gui_app/gui_control_pipeline_config.yaml"):
    """
    cache config to update control mode config during consective launches

    Args:
        config (DictConfig): config to cache
        dir (str, optional): dir to save cache files. Defaults to ".cache".
    """
    cache_path = Path(cache_path).resolve()
    cache_path.parent.mkdir(parents=True, exist_ok=True)   
    draccus.dump(config, open(str(cache_path),'w'))
    logging.info(f"Config cached to: {str(cache_path)}")

def check_config_change_asdict(new_cfg:Dict, old_cfg:Dict):
    """
    Compare a plain dictionary with a Hydra config object and return changes.

    Args:
        dict_config (dict): The plain dictionary to compare.
        hydra_config: The Hydra config object to compare.

    Returns:
        dict: A dictionary with differences found.
    """    
    # Find differences
    differences = {}
    for key in set(new_cfg.keys()).intersection(old_cfg.keys()):
        dict_value = new_cfg.get(key, None)
        hydra_value = old_cfg.get(key, None)
        if dict_value != hydra_value:
            differences[key] = dict_value
    
    return differences

def load_config(robot_type:str, cache_path:str = ".cache/gui_app/gui_control_pipeline_config.yaml", load_cache:bool = True) -> DictConfig:
    """
    load control modes config from file or load previosuly save config cache

    Args:
        config_path (str, optional): path to config file. Defaults to "lerobot/gui_app/configs/mode_cfg.yaml".
        load_cache (bool, optional): load prev saved cache. Defaults to True.

    Returns:
        DictConfig: omega config obj
    """
    
    is_cache_available = False
    if load_cache:
        cache_path = Path(cache_path).resolve()
        if cache_path.exists():
            logging.info(f"Loading config from cache: {cache_path}")
            is_cache_available = True

    cfg = draccus.parse(
        config_class=GUIControlPipelineConfig,
        args=[f"--robot.type={robot_type}"],
    )
    
    if is_cache_available:
        cfg_cache = draccus.parse(
            config_class=GUIControlPipelineConfig, 
            config_path=str(cache_path), 
            args=[f"--robot.type={robot_type}"],
        )
        cfg_robot = copy.copy(cfg.robot)
        cfg = cfg_cache
        cfg.robot = cfg_robot
        draccus.dump(cfg, open(str(cache_path),'w'))
    else:
        logging.info("App cache not found. Creating cache from config!!")
        # cache the config as yaml file
        draccus.dump(cfg, open(str(cache_path),'w'))
    return cfg

def compare_update_cache_config(
        new_config:Dict, 
        controller, 
        mode:str
    ) -> None:
    """
    Compare config updates from GUI and cache it to permanent memory
    Args:
        prev_config (DictConfig): config from previous session
        new_config (Dict): updated config
        new_robot_config (str): updated robot config path
        controller (RobotController)
        mode (str): control mode type
    """

    if mode == "teleop":
        cfg = controller.config.teleoperate_control
    elif mode == "record":
        cfg = controller.config.record_control 
    elif mode == "eval":
        cfg = controller.config.eval_control 
    else:
        logging.warning(f"Unkown config mode triggered in backend: {mode}")
        return {"error": f"Invalid mode: {mode}"}  


    updated_attrs = check_config_change_asdict(new_config, asdict(cfg))

    if len(updated_attrs.keys()) > 0:

        if mode == "teleop":
            controller.config.teleoperate_control = replace(cfg, **updated_attrs) 
        elif mode == "record":
            controller.config.record_control = replace(cfg, **updated_attrs) 
        elif mode == "eval":
            controller.config.eval_control = replace(cfg, **updated_attrs)     

        logging.info(f"Updated Configs: {controller.config}") 

    cache_config(controller.config)

def get_pretrained_models_info(output_dir_path: str) -> List[Dict]:
    """
    Function to gather information about pretrained models from a given directory structure.
    
    Args:
        output_dir_path (str): The path to the root directory containing subdirectories for each date,
                                where each date contains subdirectories for runs and checkpoints.
    
    Returns:
        List[Dict]: A list of dictionaries containing the following information:
            - "date": The date of the run (from the directory name).
            - "run_name": Dir name for the run
            - "dir_path": Path to the run directory.
            - "checkpoints": A list of checkpoint numbers that contain a 'pretrained_model' directory 
                             with a 'model.safetensors' file.
    """
    models_info = []
    output_dir = Path(output_dir_path)
    
    # iterate over the runs directories
    for runs_dir_path in output_dir.iterdir():
        checkpoints_dir_path = runs_dir_path / "checkpoints"
        
        # skip if checkpoints directory does not exist
        if not checkpoints_dir_path.exists():
            continue
        
        # gather all checkpoints with a valid pretrained model
        available_checkpoints = [
            checkpoint_dir.name
            for checkpoint_dir in checkpoints_dir_path.iterdir()
            if (checkpoint_dir / "pretrained_model").exists() and
                any(file.name == "model.safetensors" for file in (checkpoint_dir / "pretrained_model").iterdir())
        ]

        # append the information for the current run
        models_info.append({
            "run_name": runs_dir_path.name,
            "dir_path": runs_dir_path,
            "checkpoints": available_checkpoints
        })

    return models_info

def init_image_buffers(img_size:tuple, cam_info:Dict, display_text:str="No feed!") -> Dict[str, bytes]:
    """
    init cam image buffers
    """
    w, h = img_size
    no_feed_img = cv2.putText(
        img=np.zeros((h, w, 3), dtype=np.uint8), text=str(display_text), org=(w // 2 - 70, h // 2),
        fontFace=cv2.FONT_HERSHEY_SIMPLEX, fontScale=1.0, color=(0, 0, 255), thickness=2, lineType=cv2.LINE_AA
    )    
    image_buffers = { f"observation.images.{info['name']}": cv2.imencode('.jpg', no_feed_img)[1] for info in cam_info}
    image_buffers["img_size"] = img_size
    return image_buffers

def reinit_event_flags(events:Dict) -> None:
    events["force_stop"] = False
    events["start_recording"] = False
    events["control_loop_active"] = False
    events["exit_early"] = False
    events["rerecord_episode"] = False
    events["stop_recording"] = False