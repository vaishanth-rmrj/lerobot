import logging
from datetime import datetime
from pathlib import Path

from omegaconf import OmegaConf
from omegaconf.dictconfig import DictConfig

# project imports
from lerobot.common.utils.utils import init_hydra_config

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

def compare_configs(dict_config, hydra_config):
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