import logging
from datetime import datetime

from omegaconf import OmegaConf

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
