import os
from pathlib import Path
import signal
import logging
import asyncio
from typing import Dict, List, Optional

from omegaconf import OmegaConf

from fastapi import FastAPI, Form, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse, RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
import urllib.parse
import uvicorn

# project imports
from lerobot.gui_app.robot_control import RobotControl
from lerobot.common.robot_devices.cameras.opencv import find_cameras
from lerobot.gui_app.utils import (
    init_logging, 
    load_config,
    compare_update_cache_config
)

#  global vars
robot_controller = None
log_list_handler = None
is_shutdown = False

app = FastAPI()
app.mount(
    "/static", 
    StaticFiles(
        directory=os.path.join(os.path.dirname(__file__), 'static'),
    ),
    name='static'
)

# templates directory
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), 'templates'))

#### common api ####
@app.get("/", response_class=HTMLResponse)
async def read_control_panel(request: Request):
    return templates.TemplateResponse("control_panel.html", {"request": request})
    
@app.get("/robot/configs-path")
async def get_robot_config_files_path():
    configs_dir = (Path(__file__).resolve().parent / ".." / "configs/robot").resolve()
    sliced_config_dir = "/".join(configs_dir.parts[-3:])
    return [f"{sliced_config_dir}/{file.name}" for file in configs_dir.iterdir() if file.is_file()]

@app.get("/robot/cameras")
async def get_cameras():
    return robot_controller.get_camera_info()

@app.get("/robot/get-cam-feed/{device_id}")
async def get_cam_feed(device_id: str):

    def fetch_cam_frame(device_id: str):
        global is_shutdown
        import time
        while not is_shutdown:
            try:
                if robot_controller:
                    yield (b'--frame\r\n'
                            b'Content-Type: image/jpeg\r\n\r\n' + robot_controller.cams_image_buffer[device_id].tobytes() + b'\r\n')
                        
                time.sleep(0.001)  # Adjust delay as needed
            except Exception as e:
                logging.info(f"Error fetching frame: {e} !!")

    try:
        return StreamingResponse(
            fetch_cam_frame(device_id),
            media_type='multipart/x-mixed-replace; boundary=frame'
        )
    except Exception as e:
        logging.info(f"Error in video feed: {e}")

@app.get("/select_mode/{mode}")
async def select_control_mode(mode: str):
    logging.info(f"app : Triggering {mode} mode")

    active_threads = len(robot_controller.running_threads)
    if active_threads > 0:
        logging.info(f"app : {active_threads} background threads running. Stop the threads before proceding !!")
        return {"status": "fail"}
    
    success = robot_controller.select_robot_control_mode(mode)
    if success:        
        return {"status": "success"}
    else:
        return {"status": "fail"}
    
@app.get("/robot/stream-logs")
async def stream():
    async def event_generator():
        while not is_shutdown:   
            if len(log_list_handler.log_list):  
                yield f"data: {log_list_handler.log_list.pop(0)}\n\n"
            await asyncio.sleep(0.001)

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.get("/robot/stop")
async def stop_robot():
    success = robot_controller.stop_threads()
    if success:        
        return {"status": "success"}
    else:
        return {"status": "fail"}

@app.get("/robot/get-control-config/{mode}")
async def get_config(mode:str):
    mode = mode.lower()

    config = None
    if mode == "teleop":
        config = robot_controller.config.teleop
    elif mode == "record":
        config = robot_controller.config.record
    elif mode == "eval":
        config = robot_controller.config.eval
    elif mode == "replay":
        raise NotImplementedError("Relay Config fetch not implemented !!!")
    elif mode == "calibrate":
        raise NotImplementedError("Calibrate Config fetch not implemented !!!")
    else:
        logging.warning(f"Unkown config mode triggered in backend: {mode}")
        return {"error": f"Invalid mode: {mode}"}
    
    dict_cfg = OmegaConf.to_container(config, resolve=True)
    dict_cfg['robot_config'] = robot_controller.config.robot_cfg_file
    return dict_cfg    

@app.post("/api/check-directory-exists")
async def check_dir_exist(request: Request):
    data = await request.json()
    path = data.get("dir_path")
    decoded_path = urllib.parse.unquote(path)
    dir_path = Path(decoded_path)
    if dir_path.exists() and dir_path.is_dir():
        return {"exists": True}
    return {"exists": False}

@app.post("/api/keyboard-input")
async def receive_keyboard_input(request: Request):
    body = await request.json()
    key = body.get("data", "")
    logging.info(f"Received keyboard input: {key}")   

    if not robot_controller.events["control_loop_active"]:
        return {"status": "success"}

    # processing keyboard inputs to trigger event flags
    if key == "r":
        if not robot_controller.events["start_recording"]:
            robot_controller.events["start_recording"] = True
        else:
            logging.warning("Already recording episode!!")

    elif key == "ArrowRight":
        if not robot_controller.events["exit_early"]:
            robot_controller.events["exit_early"] = True
        else:
            logging.warning("Already triggered early exit!!")

    elif key == "ArrowLeft":
        if not robot_controller.events["rerecord_episode"]:
            robot_controller.events["rerecord_episode"] = True
            robot_controller.events["exit_early"] = True
        else:
            logging.warning("Already canceled episode recording!!")
    
    elif key == "escape":
        if not robot_controller.events["stop_recording"]:
            robot_controller.events["stop_recording"] = True
            robot_controller.events["exit_early"] = True
        else:
            logging.warning("Already stopped recording!!")

    return {"status": "success"}

@app.get("/api/reinit-robot")
async def stop_robot():
    
    active_threads = len(robot_controller.running_threads)
    if active_threads > 0:
        logging.info(f"app : {active_threads} background threads running. Stop the threads before proceding !!")
        return {"status": "fail"}
    
    curr_cfg = load_config()
    robot_controller.init_robot(curr_cfg.robot_cfg_file) 
    return {"status": "success"}

@app.get("/api/home-robot")
async def home_robot():
    logging.info("app : Triggering home robot")
    
    active_threads = len(robot_controller.running_threads)
    if active_threads > 0:
        logging.info(f"app : {active_threads} background threads running. Stop the threads before proceding !!")
        return {"status": "fail"}
    
    robot_controller.home_robot() 
    return {"status": "success"}

#### teleop api ####
@app.post("/robot/telop/config-update")
async def update_teleop_config(robot_config: str = Form(...), fps: int = Form(...)):

    new_teleop_config = {
        "fps": fps,
    }
    compare_update_cache_config(
        prev_config = robot_controller.config.teleop, 
        new_config = new_teleop_config, 
        new_robot_config = robot_config, 
        controller = robot_controller,
        mode="teleop",
    )


#### record api ####
@app.post("/robot/record/config-update")
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
        episode_time_s: int = Form(...),
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
        "episode_time_s": episode_time_s,
        "num_episodes": num_episodes,
        "num_image_writer_processes": num_image_writer_processes,
        "num_image_writer_threads_per_camera": num_image_writer_threads_per_camera,
        "single_task": single_task,
    }
    compare_update_cache_config(
        prev_config = robot_controller.config.record, 
        new_config = new_record_config, 
        new_robot_config = robot_config, 
        controller = robot_controller,
        mode="record",
    )

@app.get("/robot/record/event/{event}")
async def update_record_event(event:str):
    """
    endpoint to update robot recording events based on input.
        - valid events: 'start', 'finish', 'cancel'.
    """
    event = event.lower()

    if event == "start":
        if not robot_controller.events["start_recording"]:
            robot_controller.events["start_recording"] = True
        else:
            logging.warning("Already recording episode!!")

    elif event == "finish":
        if not robot_controller.events["exit_early"]:
            robot_controller.events["exit_early"] = True
        else:
            logging.warning("Already triggered early exit!!")

    elif event == "cancel":
        if not robot_controller.events["rerecord_episode"]:
            robot_controller.events["rerecord_episode"] = True
            robot_controller.events["exit_early"] = True
        else:
            logging.warning("Already canceled episode recording!!")
    
    else:
        logging.warning(f"Unkown record event triggered in backend: {event}")
        return {"error": f"Invalid event: {event}"}
    
    return {"status": "success", "event": event}



#### eval api ####
@app.post("/robot/eval/config-update")
async def update_record_config(
        robot_config: str = Form(...), 
        policy_path: str = Form(...), 
        record_episodes: bool = Form(False),
        push_to_hub: bool = Form(False),
        root_dir: str = Form(...), 
        repo_id: str = Form(...), 
        tags: str = Form(...), 
        fps: int = Form(...),  
        warmup_time_s: int = Form(...),      
        episode_time_s: int = Form(...),
        num_episodes: int = Form(...),
        num_image_writer_processes: int = Form(...),
        num_image_writer_threads_per_camera: int = Form(...),
        single_task: str = Form(...),
    ):

    new_eval_config = {
        "root": root_dir,
        "pretrained_policy_path": policy_path,
        "record_eval_episodes": record_episodes,
        "repo_id": repo_id,
        "tags": tags,
        "fps": fps,
        "push_to_hub": push_to_hub,
        "warmup_time_s": warmup_time_s,
        "episode_time_s": episode_time_s,
        "num_episodes": num_episodes,
        "num_image_writer_processes": num_image_writer_processes,
        "num_image_writer_threads_per_camera": num_image_writer_threads_per_camera,
        "single_task": single_task,
    }
    compare_update_cache_config(
        prev_config = robot_controller.config.eval, 
        new_config = new_eval_config, 
        new_robot_config = robot_config, 
        controller = robot_controller,
        mode="eval",
    )

#### calibrate api ####
@app.get("/robot/calibrate/get-arms-name")
def get_arms_name():
    return robot_controller.robot.available_arms

@app.get("/robot/calibrate/get-connected-cams-port")
def get_connected_cams_port():
    return find_cameras()

@app.get("/robot/calibrate/{arm_name}")
def calibrate_arm(arm_name: str):
    logging.info(f"app : Triggering calibration for arm: {arm_name}")
    robot_controller.run_calibration(arm_name)
    return True

def handle_interrupt(signum, frame):
    global is_shutdown, dataset_visualizer  
    logging.info("Interrupt received, terminating app !!")
    is_shutdown = True
    robot_controller.stop_threads()

def run_web_app():
    global robot_controller, log_list_handler
    # init logging and capture the custom list handler
    log_list_handler = init_logging()   
    # load config / cache
    cfg = load_config()     
    
    robot_controller = RobotControl(config=cfg)   
    
    signal.signal(signal.SIGINT, handle_interrupt)
    uvicorn.run(app, host="0.0.0.0", port=8000, timeout_keep_alive=2)

if __name__ == "__main__":   
    run_web_app()