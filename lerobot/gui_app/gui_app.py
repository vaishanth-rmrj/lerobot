import os
import cv2
import threading
import signal
import logging

from typing import Dict, List, Optional

from fastapi import FastAPI, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse

# project imports
from lerobot.common.utils.utils import init_hydra_config
from lerobot.gui_app.robot_control import RobotControl
from lerobot.common.utils.utils import init_logging

SHUTDOWN_APP = False
DEFAULT_APP_CONFIG_PATH = "lerobot/gui_app/configs/mode_cfg.yaml"

app = FastAPI()
app.mount(
    "/static", 
    StaticFiles(
        directory=os.path.join(os.path.dirname(__file__), 'static'),
    ),
    name='static'
)

def fetch_cam_frame(device_id: int):
    import time
    while not SHUTDOWN_APP:
        try:
            if robot_controller and robot_controller.cam_buffer is not None:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + robot_controller.cam_buffer.tobytes() + b'\r\n')
            time.sleep(0.001)  # Adjust delay as needed
        except Exception as e:
            print(f"Error fetching frame: {e}")
            break

@app.get("/video/{device_id}")
async def get_cam_feed(device_id: int):
    try:
        return StreamingResponse(
            fetch_cam_frame(device_id),
            media_type='multipart/x-mixed-replace; boundary=frame'
        )
    except Exception as e:
        print(f"Error in video feed: {e}")

@app.get("/select_mode/{mode}")
async def select_control_mode(mode: str):
    print(f"Triggering mode : {mode}")
    robot_controller.select_robot_control_mode(mode)
    return {"status": "success"}

@app.get("/stop")
async def stop_robot():
    print(f"Stopping robot")
    robot_controller.stop()
    return {"status": "success"}

@app.post("/telop/config-update")
async def process_form(robot_config: str = Form(...), fps: int = Form(...)):

    if not robot_controller.config.robot_cfg_file == robot_config:
        logging.info("Robot configuration changed")
        robot_controller.config.robot_cfg_file = robot_config
        robot_controller.stop_all_processes()
        robot_controller.init_robot(robot_config)

    if not robot_controller.config.teleop.fps == fps:
        robot_controller.stop_all_processes()
        robot_controller.config.teleop.fps = fps

def handle_interrupt(signum, frame):
    global SHUTDOWN_APP    
    logging.info("Interrupt received, terminating app !!")
    SHUTDOWN_APP = True
    robot_controller.stop()

if __name__ == "__main__":
    import uvicorn

    # init app config
    app_cfg = init_hydra_config(DEFAULT_APP_CONFIG_PATH)
    init_logging()
    
    robot_controller = RobotControl(
        config=app_cfg
    )   
    
    signal.signal(signal.SIGINT, handle_interrupt)
    uvicorn.run(app, host="0.0.0.0", port=8000, timeout_keep_alive=2)