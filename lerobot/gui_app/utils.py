import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from omegaconf import OmegaConf
from omegaconf.dictconfig import DictConfig

# project imports
from lerobot.common.utils.utils import init_hydra_config
from lerobot.gui_app.robot_control import RobotControl

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

def cache_config(config: DictConfig, dir_name:str ="gui_app", filename:str = "mode_cfg.yaml"):
    """
    cache config to update control mode config during consective launches

    Args:
        config (DictConfig): config to cache
        dir (str, optional): dir to save cache files. Defaults to ".cache".
    """
    cache_dir = (Path(__file__).resolve().parent.parent.parent / ".cache" / dir_name).resolve()
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / filename

    OmegaConf.save(config, cache_file)    
    logging.info(f"Config cached to: {cache_file}")

def check_config_change(dict_config:Dict, hydra_config:DictConfig):
    """
    Compare a plain dictionary with a Hydra config object and return changes.

    Args:
        dict_config (dict): The plain dictionary to compare.
        hydra_config: The Hydra config object to compare.

    Returns:
        dict: A dictionary with differences found.
    """
    # Convert Hydra config to a plain dictionary
    hydra_dict = OmegaConf.to_container(hydra_config, resolve=True)
    
    # Find differences
    differences = {}
    for key in set(dict_config.keys()).union(hydra_dict.keys()):
        dict_value = dict_config.get(key, None)
        hydra_value = hydra_dict.get(key, None)
        if dict_value != hydra_value:
            differences[key] = dict_value
    
    return differences

def load_config(config_path:str = "lerobot/gui_app/configs/mode_cfg.yaml", load_cache:bool = True) -> DictConfig:
    """
    load control modes config from file or load previosuly save config cache

    Args:
        config_path (str, optional): path to config file. Defaults to "lerobot/gui_app/configs/mode_cfg.yaml".
        load_cache (bool, optional): load prev saved cache. Defaults to True.

    Returns:
        DictConfig: omega config obj
    """

    if load_cache:
        config_filename = Path(config_path).name
        cache_file = (Path(__file__).resolve().parent.parent.parent / ".cache/gui_app" / config_filename).resolve()
        if cache_file.exists():
            logging.info("App cache found. Loading config from cache.")        
            cfg = init_hydra_config(cache_file)
            return cfg
        else:
            logging.info("App cache not found. Creating cache from config!!")  

    cfg = init_hydra_config(config_path) 
    return cfg

def compare_update_cache_config(
        prev_config: DictConfig, 
        new_config:Dict, 
        new_robot_config:str, 
        controller:RobotControl, 
        mode:str
    ) -> None:
    """
    Compare config updates from GUI and cache it to permanent memory
    Args:
        prev_config (DictConfig): config from previous session
        new_config (Dict): updated config
        new_robot_config (str): updated robot config path
        controller (RobotControl)
        mode (str): control mode type
    """
    updated_attrs = check_config_change(new_config, prev_config)
    active_threads = len(controller.running_threads)

    if not controller.config.robot_cfg_file == new_robot_config:
        logging.info("Robot configuration changed")
        controller.config.robot_cfg_file = new_robot_config
        if active_threads: controller.stop_threads()
        controller.init_robot(new_robot_config)

    if len(updated_attrs.keys()) > 0:
        if active_threads: controller.stop_threads()

        if mode == "teleop":
            controller.config.teleop = OmegaConf.create(new_config)  
        elif mode == "record":
            controller.config.record = OmegaConf.create(new_config)  
        elif mode == "eval":
            controller.config.eval = OmegaConf.create(new_config)  
        elif mode == "replay":
            raise NotImplementedError("Relay Config update not implemented !!!")
        elif mode == "calibrate":
            raise NotImplementedError("Calibrate Config update not implemented !!!")
        elif mode == "hg_dagger":
            controller.config.hg_dagger = OmegaConf.create(new_config)  
        else:
            logging.warning(f"Unkown config mode triggered in backend: {mode}")
            return {"error": f"Invalid mode: {mode}"}        

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
    
    for date_dir_path in output_dir.iterdir():

        # skip empty directories
        if not any(date_dir_path.iterdir()):
            continue        
        
        date = date_dir_path.name
        
        # iterate over the runs directories within each date directory
        for runs_dir_path in date_dir_path.iterdir():
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
                "date": date,
                "run_name": runs_dir_path.name,
                "dir_path": runs_dir_path,
                "checkpoints": available_checkpoints
            })

    return models_info