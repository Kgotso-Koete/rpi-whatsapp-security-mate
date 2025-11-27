#!/bin/bash
cd /home/kgotso-koete/Documents/Projects/rpi-whatsapp-security-mate

echo "Stopping all security system processes..."

# Stop gunicorn processes
pkill -f "gunicorn.*run_flask"

# Stop Python processes for this project
pkill -f "python3 app/who_is_home.py"
pkill -f "python3 app/security_system.py"
pkill -f "python3 app/s3_upload.py"

# Kill any remaining Python processes from this project directory
pkill -f "rpi-whatsapp-security-mate"

echo "Stopping any camera-related processes from any project..."

# Kill Picamera2-based Python scripts
pkill -f "picamera2"
pkill -f "from picamera2"
pkill -f "import picamera2"

# Kill old picamera v1 users (rare but safe)
pkill -f "import picamera"
pkill -f "picamera.array"

# Kill common libcamera command-line tools
pkill -f "libcamera-still"
pkill -f "libcamera-vid"
pkill -f "libcamera-jpeg"
pkill -f "libcamera-raw"
pkill -f "libcamera-hello"

# Kill any Python scripts using libcamera bindings
pkill -f "libcamera"

# Kill OpenCV camera streams (optional, but safe)
pkill -f "cv2.VideoCapture"

# Kill any process holding /dev/video*
fuser -k /dev/video* 2>/dev/null

echo "All processes stopped."
echo "Waiting 2 seconds for cleanup..."
sleep 2

# Verify processes stopped
echo "Checking for remaining processes:"
ps aux | grep -E "(gunicorn|python3.*app/|libcamera|picamera2)" | grep -v grep