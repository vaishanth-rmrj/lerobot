import os
import cv2
import threading
import signal
import logging
import asyncio
import time 
from omegaconf import OmegaConf

from typing import Dict, List, Optional

from fastapi import FastAPI, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse

# project imports
from lerobot.common.utils.utils import init_hydra_config
from lerobot.gui_app.robot_control import RobotControl
from lerobot.gui_app.utils import init_logging, compare_configs

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
    print(f"app : Triggering {mode} mode")

    active_threads = len(robot_controller.running_threads)
    if active_threads > 0:
        logging.info(f"app : {active_threads} background threads running. Stop the threads before proceding !!")
        return {"status": "fail"}
    
    success = robot_controller.select_robot_control_mode(mode)
    if success:        
        return {"status": "success"}
    else:
        return {"status": "fail"}

@app.get("/stop")
async def stop_robot():
    success = robot_controller.stop_threads()
    if success:        
        return {"status": "success"}
    else:
        return {"status": "fail"}

@app.post("/telop/config-update")
async def update_teleop_config(robot_config: str = Form(...), fps: int = Form(...)):

    active_threads = len(robot_controller.running_threads)
    if not robot_controller.config.robot_cfg_file == robot_config:
        logging.info("Robot configuration changed")
        robot_controller.config.robot_cfg_file = robot_config
        if active_threads: robot_controller.stop_threads()
        robot_controller.init_robot(robot_config)

    if not robot_controller.config.teleop.fps == fps:
        if active_threads: robot_controller.stop_threads()
        robot_controller.config.teleop.fps = fps

@app.get("/record/get-config")
async def get_config():
    record_dict_cfg = OmegaConf.to_container(robot_controller.config.record, resolve=True)
    record_dict_cfg['robot_config'] = robot_controller.config.robot_cfg_file
    return record_dict_cfg

@app.post("/record/config-update")
async def update_record_config(
        robot_config: str = Form(...), 
        root_dir: str = Form(...), 
        repo_id: str = Form(...), 
        tags: str = Form(...), 
        fps: int = Form(...),
        resume: bool = Form(False),
        local_files_only: bool = Form(False),
        run_compute_stats: bool = Form(False),
        push_to_hub: bool = Form(False),
        warmup_time_s: int = Form(...),
        episode_time_s: int = Form(...),
        reset_time_s: int = Form(...),
        num_episodes: int = Form(...),
        num_image_writer_processes: int = Form(...),
        num_image_writer_threads_per_camera: int = Form(...),
        single_task: str = Form(...),
    ):

    new_record_config = {
        "root": root_dir,
        "repo_id": repo_id,
        "tags": tags,
        "fps": fps,
        "resume": resume,
        "local_files_only": local_files_only,
        "run_compute_stats": run_compute_stats,
        "push_to_hub": push_to_hub,
        "warmup_time_s": warmup_time_s,
        "episode_time_s": episode_time_s,
        "reset_time_s": reset_time_s,
        "num_episodes": num_episodes,
        "num_image_writer_processes": num_image_writer_processes,
        "num_image_writer_threads_per_camera": num_image_writer_threads_per_camera,
        "single_task": single_task,
    }

    diff = compare_configs(new_record_config, robot_controller.config.record)
    active_threads = len(robot_controller.running_threads)

    if not robot_controller.config.robot_cfg_file == robot_config:
        logging.info("Robot configuration changed")
        robot_controller.config.robot_cfg_file = robot_config
        if active_threads: robot_controller.stop_threads()
        robot_controller.init_robot(robot_config)

    if len(diff.keys()) > 0:
        if active_threads: robot_controller.stop_threads()
        logging.info(f"Modified Configs: {diff}")
        robot_controller.config.record = OmegaConf.create(new_record_config)
        logging.info(f"Updated Configs: {robot_controller.config.record}")

@app.get("/record/start_recording")
async def start_recording():
    robot_controller.events["start_recording"] = True

@app.get("/record/cancel_recording")
async def cancel_recording():
    robot_controller.events["rerecord_episode"] = True
    robot_controller.events["exit_early"] = True

@app.get("/record/finish_recording")
async def finish_recording():
    robot_controller.events["exit_early"] = True

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
    robot_controller.stop_threads()

if __name__ == "__main__":
    import uvicorn

    # init app config
    app_cfg = init_hydra_config(DEFAULT_APP_CONFIG_PATH)

    # init logging and capture the custom list handler
    log_list_handler = init_logging()    
    
    robot_controller = RobotControl(
        config=app_cfg
    )   
    
    signal.signal(signal.SIGINT, handle_interrupt)
    uvicorn.run(app, host="0.0.0.0", port=8000, timeout_keep_alive=2)