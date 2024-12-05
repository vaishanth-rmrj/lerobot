import os
import cv2
import threading
import signal
import logging
import asyncio
import time 

from typing import Dict, List, Optional

from fastapi import FastAPI, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse

# project imports
from lerobot.common.utils.utils import init_hydra_config
from lerobot.gui_app.robot_control import RobotControl
# from lerobot.common.utils.utils import init_logging
from lerobot.gui_app.utils import init_logging

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

# def fetch_cam_frame(device_id: int):
#     import time
#     while not SHUTDOWN_APP:
#         try:
#             if robot_controller and robot_controller.cam_buffer is not None:
#                 yield (b'--frame\r\n'
#                        b'Content-Type: image/jpeg\r\n\r\n' + robot_controller.cam_buffer.tobytes() + b'\r\n')
#             time.sleep(0.001)  # Adjust delay as needed
#         except Exception as e:
#             print(f"Error fetching frame: {e}")
#             break

# @app.get("/video/{device_id}")
# async def get_cam_feed(device_id: int):
#     try:
#         return StreamingResponse(
#             fetch_cam_frame(device_id),
#             media_type='multipart/x-mixed-replace; boundary=frame'
#         )
#     except Exception as e:
#         print(f"Error in video feed: {e}")

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

# @app.get('/stream')
# async def stream_output():
#     async def event_generator():
#         while not SHUTDOWN_APP:  # Only stream while should_stream is True
#             if not output_queue.empty():
#                 yield {'data': await output_queue.get()}
#             await asyncio.sleep(0.1)
#         # Send a final message to indicate stream end
#         yield {'data': '--- Streaming ended ---'}

#     return EventSourceResponse(event_generator())

@app.get("/stream")
async def stream():
    async def event_generator():
        while not SHUTDOWN_APP:   
            if len(log_list_handler.log_list):  
                yield f"data: {log_list_handler.log_list.pop(0)}\n\n"
            await asyncio.sleep(0.001)

    return StreamingResponse(event_generator(), media_type="text/event-stream")

def handle_interrupt(signum, frame):
    global SHUTDOWN_APP    
    logging.info("Interrupt received, terminating app !!")
    SHUTDOWN_APP = True
    robot_controller.stop()

if __name__ == "__main__":
    import uvicorn

    # init app config
    app_cfg = init_hydra_config(DEFAULT_APP_CONFIG_PATH)

    # init logging and capture the custom list handler
    log_list_handler = init_logging()

    # Example logging
    logging.info("Initializing the system.")
    logging.info("Processing data.")
    logging.error("An error occurred!")

    # Access logs from the list
    # print("Logs stored in the list:")
    
    
    robot_controller = RobotControl(
        config=app_cfg
    )   
    
    signal.signal(signal.SIGINT, handle_interrupt)
    uvicorn.run(app, host="0.0.0.0", port=8000, timeout_keep_alive=2)