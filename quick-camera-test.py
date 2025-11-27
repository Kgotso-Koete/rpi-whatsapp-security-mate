from picamera2 import Picamera2
import cv2
import time

camera = Picamera2()

# Configure for video with specific controls
config = camera.create_video_configuration(
    main={"size": (640, 480), "format": "RGB888"},
    controls={"FrameRate": 32}
)
camera.configure(config)

print('Warming up camera')
camera.start()
time.sleep(2)

i = 0
try:
    while i <= 5: 
        print(i)
        
        # Capture frame
        frame = camera.capture_array()
        
        # Convert to grayscale and save
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        cv2.imwrite('{}.png'.format(i), gray)
        
        i += 1
        
finally:
    camera.close()
    print('Camera closed')