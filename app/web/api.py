"""
Web UI API endpoints - JSON responses for AJAX calls
"""
import logging
from flask import jsonify, request, send_file
import os

from app.api import CameraController, SystemController
from app import config

LOGGER = logging.getLogger(__name__)


def register_api_routes(web_bp):
    """Register API routes on the web blueprint
    
    Args:
        web_bp: Flask blueprint instance
    """
    
    @web_bp.route('/api/status', methods=['GET'])
    def api_get_status():
        """Get system status (JSON)"""
        result = CameraController.get_status()
        return jsonify(result)
    
    @web_bp.route('/api/camera/on', methods=['POST'])
    def api_camera_on():
        """Turn camera on (JSON)"""
        result = CameraController.turn_on()
        return jsonify(result)
    
    @web_bp.route('/api/camera/off', methods=['POST'])
    def api_camera_off():
        """Turn camera off (JSON)"""
        result = CameraController.turn_off()
        return jsonify(result)
    
    @web_bp.route('/api/camera/toggle', methods=['POST'])
    def api_camera_toggle():
        """Toggle camera on/off (JSON)"""
        current = CameraController.get_status()
        if not current['success']:
            return jsonify(current)
        
        if current['data']['camera_on']:
            result = CameraController.turn_off()
        else:
            result = CameraController.turn_on()
        
        return jsonify(result)
    
    @web_bp.route('/api/camera/rotate', methods=['POST'])
    def api_camera_rotate():
        """Rotate camera (JSON)
        
        Expects JSON body: {"pan": 0, "tilt": 0}
        """
        data = request.get_json()
        
        if not data or 'pan' not in data or 'tilt' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing pan or tilt parameter'
            }), 400
        
        result = CameraController.rotate(data['pan'], data['tilt'])
        return jsonify(result)
    
    @web_bp.route('/api/camera/position', methods=['GET'])
    def api_camera_position():
        """Get current camera position (JSON)"""
        result = CameraController.get_position()
        return jsonify(result)
    
    @web_bp.route('/api/notifications/toggle', methods=['POST'])
    def api_notifications_toggle():
        """Toggle notifications on/off (JSON)"""
        data = request.get_json() or {}
        enable = data.get('enable')  # Can be True, False, or None (toggle)
        
        result = CameraController.toggle_notifications(enable)
        return jsonify(result)
    
    @web_bp.route('/api/auto-detect/toggle', methods=['POST'])
    def api_auto_detect_toggle():
        """Toggle auto-detect on/off (JSON)"""
        data = request.get_json() or {}
        enable = data.get('enable')  # Can be True, False, or None (toggle)
        
        result = CameraController.toggle_auto_detect(enable)
        return jsonify(result)
    
    @web_bp.route('/api/system/initialize', methods=['POST'])
    def api_system_initialize():
        """Initialize the system (JSON)"""
        result = SystemController.initialize()
        return jsonify(result)
    
    @web_bp.route('/api/image/latest', methods=['GET'])
    def api_latest_image():
        """Get latest image file"""
        result = CameraController.get_latest_image()
        
        if not result['success']:
            return jsonify(result), 404
        
        try:
            return send_file(
                result['data']['path'],
                mimetype='image/jpeg',
                as_attachment=False,
                download_name=result['data']['filename']
            )
        except Exception as e:
            LOGGER.error(f'Error serving image: {e}')
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @web_bp.route('/api/images/list', methods=['GET'])
    def api_list_images():
        """List all captured images (JSON)"""
        try:
            imgs_dir = config.IMG_DIR
            
            if not os.path.exists(imgs_dir):
                return jsonify({
                    'success': True,
                    'data': {'images': []}
                })
            
            # Get all .jpg files
            images = []
            for filename in sorted(os.listdir(imgs_dir), reverse=True):
                if filename.endswith('.jpg'):
                    filepath = os.path.join(imgs_dir, filename)
                    stat = os.stat(filepath)
                    
                    images.append({
                        'filename': filename,
                        'size': stat.st_size,
                        'created': stat.st_ctime,
                        'url': f'/web/api/image/{filename}'
                    })
            
            return jsonify({
                'success': True,
                'data': {'images': images}
            })
            
        except Exception as e:
            LOGGER.error(f'Error listing images: {e}')
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @web_bp.route('/api/image/<filename>', methods=['GET'])
    def api_get_image(filename):
        """Get specific image by filename"""
        try:
            # Security: prevent directory traversal
            if '..' in filename or '/' in filename:
                return jsonify({
                    'success': False,
                    'error': 'Invalid filename'
                }), 400
            
            filepath = os.path.join(config.IMG_DIR, filename)
            
            if not os.path.exists(filepath):
                return jsonify({
                    'success': False,
                    'error': 'Image not found'
                }), 404
            
            return send_file(
                filepath,
                mimetype='image/jpeg',
                as_attachment=False,
                download_name=filename
            )
            
        except Exception as e:
            LOGGER.error(f'Error serving image {filename}: {e}')
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500