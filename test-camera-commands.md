Test image

python3 -c "from picamera2 import Picamera2; import time; camera = Picamera2(); config = camera.create_still_configuration(); camera.configure(config); camera.start(); time.sleep(3); camera.capture_file('/home/kgotso-koete/Documents/Projects/rpi-whatsapp-security-mate/new-test-image.jpg'); camera.close()"