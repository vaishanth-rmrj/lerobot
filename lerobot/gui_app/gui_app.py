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