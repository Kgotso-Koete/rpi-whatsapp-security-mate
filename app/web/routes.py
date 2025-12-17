"""
Web UI routes - HTML page rendering
"""
import logging
from flask import Blueprint, render_template, Response
import cv2

from app.api import CameraController

LOGGER = logging.getLogger(__name__)

# Create Web UI blueprint
web_bp = Blueprint('web', __name__, 
                   template_folder='templates',
                   static_folder='static',
                   static_url_path='/web/static')


@web_bp.route('/')
def index():
    """Dashboard / Home page"""
    # Get current status for dashboard
    result = CameraController.get_status()
    status = result.get('data', {}) if result['success'] else {}
    
    return render_template('index.html', status=status)


@web_bp.route('/camera')
def camera():
    """Live camera view with controls"""
    result = CameraController.get_status()
    status = result.get('data', {}) if result['success'] else {}
    
    return render_template('camera.html', status=status)


@web_bp.route('/gallery')
def gallery():
    """Image gallery page"""
    return render_template('gallery.html')


@web_bp.route('/settings')
def settings():
    """Settings page"""
    result = CameraController.get_status()
    status = result.get('data', {}) if result['success'] else {}
    
    return render_template('settings.html', status=status)


@web_bp.route('/logs')
def logs():
    """System logs viewer"""
    return render_template('logs.html')


@web_bp.route('/video_feed')
def video_feed():
    """MJPEG video stream endpoint
    
    Returns live camera feed as multipart JPEG stream
    """
    def generate():
        """Generate MJPEG frames"""
        try:
            # Import here to avoid circular dependency
            from app.security_system import MotionDetector
            
            detector = MotionDetector()
            
            for frame, frame_delta, contours in detector.stream():
                # Encode frame as JPEG
                ret, buffer = cv2.imencode('.jpg', frame, 
                                          [cv2.IMWRITE_JPEG_QUALITY, 80])
                
                if not ret:
                    continue
                
                frame_bytes = buffer.tobytes()
                
                # Yield frame in multipart format
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + 
                       frame_bytes + b'\r\n')
                
        except Exception as e:
            LOGGER.error(f'Error in video stream: {e}')
    
    return Response(generate(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')