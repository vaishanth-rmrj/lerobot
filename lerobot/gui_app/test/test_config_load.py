from lerobot.common.utils.utils import init_hydra_config

CFG_FILE_PATH = "lerobot/gui_app/configs/mode_cfg.yaml"

app_cfg = init_hydra_config(CFG_FILE_PATH)

print(type(app_cfg))

print(app_cfg.robot_cfg_file)

print(app_cfg.record.root)
print(app_cfg.record.fps)