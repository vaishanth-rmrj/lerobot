import reflex as rx

import asyncio
from PIL import Image
import requests
import cv2

class State(rx.State):
    url = f"https://picsum.photos/id/1/200/300"
    image = Image.open(requests.get(url, stream=True).raw)
    image_text:str = "hello"

    video_captures = {}

    is_cam_feed_fetch_active: bool = False

    def get_video_capture(self, device_id: int):
        if device_id not in self.video_captures:
            cap = cv2.VideoCapture(device_id)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.video_captures[device_id] = cap
        return self.video_captures[device_id]


# def generate_frames(device_id: int):
    
#     while True:
#         success, frame = cap.read()
#         if not success:
#             break
#         else:
#             ret, buffer = cv2.imencode('.jpg', frame)
#             if not ret:
#                 continue
#             yield (b'--frame\r\n'
#                    b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

    @rx.event(background=True)
    async def fetch_cam_feed(self):

        # async with self:    
        #     if self.is_cam_feed_fetch_active:
        #         print("Background event already running")
        #         return 

        async with self:
            cap = self.get_video_capture(0)

        counter = 0
        while True:
            print("looping")

            async with self:
                success, frame = cap.read()
                self.image = Image.fromarray(frame)
            if not success:
                break
            # else:
            #     async with self:
            #         ret, self.image = cv2.imencode('.jpg', frame)

            # async with self:
            #     self.image_text = f"hello {counter}"
            
            #     if not self.is_cam_feed_fetch_active:
            #         return 
            
            # counter += 1

            await asyncio.sleep(0.001)


    @rx.event
    def on_cont_mount(self):
        print("mount function called")
        if not self.is_cam_feed_fetch_active:
            self.is_cam_feed_fetch_active = True
            return State.fetch_cam_feed

    @rx.event
    def on_cont_unmount(self):
        print("unmount function called")
        if self.is_cam_feed_fetch_active:
            self.is_cam_feed_fetch_active = False

            

    def enable_cam_feed(self):
        self.is_cam_feed_fetch_active = True
        return State.fetch_cam_feed
        
    def teleop(self):
        print("Clicked on teleop")
        if not self.is_cam_feed_fetch_active:
            self.is_cam_feed_fetch_active = True
            return State.fetch_cam_feed

    