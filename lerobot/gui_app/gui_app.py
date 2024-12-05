import os
import cv2
import threading
import signal

from typing import Dict, List, Optional

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse

# project imports
from robot_control import RobotControl

SHUTDOWN_APP = False

global_config = {
    "robot_cfg_file": "lerobot/configs/robot/koch.yaml",
}
teleop_config = {
    "fps": 30
}

record_config = {
    "fps": 30,
    "root": "data/",
    "repo_id": "default/custom_task",
    "local_files_only": False,
    "warmup_time_s": 10,
    "episode_time_s": 40,
    "reset_time_s": 10,
    "num_episodes": 50,
    "run_compute_stats": True,
    "push_to_hub": False,
    "tags": "",
    "num_image_writer_processes": 0,
    "num_image_writer_threads_per_camera": 4,
    "resume": False,
    "pretrained_policy_name_or_path": "",
    "policy_overrides": "",
}

replay_config = {
    "fps": 30,
    "root": "data/",
    "repo_id": "default/custom_task",
    "local_files_only": False,
    "episode": 50,
}

calibrate_config = {
    "arms": ""
}

app = FastAPI()
app.mount(
    "/static", 
    StaticFiles(
        directory=os.path.join(os.path.dirname(__file__), 'static'),
    ),
    name='static'
)

robot = RobotControl()

def fetch_cam_frame(device_id: int):
    while not SHUTDOWN_APP:
        if not robot.cam_buffer is None:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + robot.cam_buffer.tobytes() + b'\r\n')

@app.get("/video/{device_id}")
async def video_feed(device_id: int):
    return StreamingResponse(
        fetch_cam_frame(device_id),
        media_type='multipart/x-mixed-replace; boundary=frame'
    )

@app.get("/select_mode/{mode}")
async def select_control_mode(mode: str):
    print(f"Triggering mode : {mode}")
    robot.select_robot_control_mode(mode)
    return {"status": "success"}

@app.get("/stop")
async def stop_robot():
    print(f"Stopping robot")
    robot.stop()
    return {"status": "success"}

if __name__ == "__main__":
    import uvicorn

    def handle_interrupt(signum, frame):
        SHUTDOWN_APP = True
        print("Interrupt received, stopping the voice prompter...")
        robot.stop()

    signal.signal(signal.SIGINT, handle_interrupt)
    uvicorn.run(app, host="0.0.0.0", port=8000)