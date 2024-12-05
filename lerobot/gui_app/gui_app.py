import os
import cv2
import threading
import signal

from typing import Dict, List, Optional

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse

# project imports
from lerobot.common.utils.utils import init_hydra_config
from lerobot.gui_app.robot_control import RobotControl

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
    while not SHUTDOWN_APP:
        if not robot_controller.cam_buffer is None:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + robot_controller.cam_buffer.tobytes() + b'\r\n')

@app.get("/video/{device_id}")
async def video_feed(device_id: int):
    return StreamingResponse(
        fetch_cam_frame(device_id),
        media_type='multipart/x-mixed-replace; boundary=frame'
    )

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

def handle_interrupt(signum, frame):
    SHUTDOWN_APP = True
    print("Interrupt received, stopping the voice prompter...")
    robot_controller.stop()

if __name__ == "__main__":
    import uvicorn

    # init app config
    app_cfg = init_hydra_config(DEFAULT_APP_CONFIG_PATH)
    
    robot_controller = RobotControl(
        robot_path=app_cfg.robot_cfg_file
    )   
    
    signal.signal(signal.SIGINT, handle_interrupt)
    uvicorn.run(app, host="0.0.0.0", port=8000)