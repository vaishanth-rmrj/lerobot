# import cv2
# import numpy as np

# # Create a black image of size 500x500 with 3 color channels (RGB)
# black_image = np.zeros((500, 500, 3), dtype=np.uint8)

# # Display the black image
# cv2.imshow("Black Image", black_image)

# # Wait for a key press and close the window
# cv2.waitKey(0)
# cv2.destroyAllWindows()






# from lerobot.common.robot_devices.cameras.opencv import OpenCVCamera

# camera = OpenCVCamera(camera_index=0)
# camera.connect()
# color_image = camera.read()

# print(color_image.shape)
# print(color_image.dtype)

# # Display the black image
# cv2.imshow("Image", color_image)

# # Wait for a key press and close the window
# cv2.waitKey(0)
# cv2.destroyAllWindows()




import cv2

# Open the default camera (0 is typically the default camera)
camera = cv2.VideoCapture(0)

if not camera.isOpened():
    print("Error: Could not open camera.")
    exit()

# Loop to capture and display the video feed
while True:
    ret, frame = camera.read()  # Read a frame from the camera
    if not ret:
        print("Error: Could not read frame.")
        break

    # Display the frame
    cv2.imshow("Camera Feed", frame)

    # Exit the loop when 'q' is pressed
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Release the camera and close OpenCV windows
camera.release()
cv2.destroyAllWindows()