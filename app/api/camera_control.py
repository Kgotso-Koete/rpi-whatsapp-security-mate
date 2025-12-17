"""
Shared API layer for camera control operations.
Used by both Slack and Web UI interfaces.
"""
import time
import os
import logging

from app import utils, config
from app.pan_tilt_controller import PanTiltController

LOGGER = logging.getLogger(__name__)

# Initialize pan/tilt controller
pan_tilt = PanTiltController()


class CameraController:
    """Handles all camera-related operations"""
    
    @staticmethod
    def get_status():
        """Get current camera and system status
        
        Returns:
            dict: Status information
        """
        try:
            status = {
                'camera_on': utils.redis_get('camera_status'),
                'notifications_on': utils.redis_get('camera_notifications'),
                'auto_detect_on': utils.redis_get('auto_detect_status'),
                'home': utils.redis_get('home'),
                'pan': utils.get_pan(),
                'tilt': utils.get_tilt(),
                'temperature': utils.measure_temp()
            }
            return {'success': True, 'data': status}
        except Exception as e:
            LOGGER.error(f'Error getting status: {e}')
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def turn_on():
        """Turn on the camera
        
        Returns:
            dict: Operation result
        """
        try:
            if utils.redis_get('camera_status'):
                return {
                    'success': True,
                    'message': 'Camera is already running',
                    'already_on': True
                }
            
            utils.redis_set('camera_status', True)
            LOGGER.info('Camera turned on via API')
            return {
                'success': True,
                'message': 'Camera has been turned on',
                'already_on': False
            }
        except Exception as e:
            LOGGER.error(f'Error turning on camera: {e}')
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def turn_off():
        """Turn off the camera
        
        Returns:
            dict: Operation result
        """
        try:
            utils.redis_set('camera_status', False)
            LOGGER.info('Camera turned off via API')
            return {
                'success': True,
                'message': 'Camera has been turned off'
            }
        except Exception as e:
            LOGGER.error(f'Error turning off camera: {e}')
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def rotate(pan, tilt):
        """Rotate the camera to specified position
        
        Args:
            pan (int): Pan angle (-90 to 90)
            tilt (int): Tilt angle (-90 to 90)
            
        Returns:
            dict: Operation result
        """
        try:
            # Validate inputs
            try:
                pan = int(pan)
                tilt = int(tilt)
            except (ValueError, TypeError):
                return {
                    'success': False,
                    'error': 'Pan and tilt must be integers'
                }
            
            # Clamp values
            pan = max(-90, min(90, pan))
            tilt = max(-90, min(90, tilt))
            
            # Stop camera temporarily if running
            curr_status = utils.redis_get('camera_status')
            if curr_status:
                utils.redis_set('camera_status', False)
                time.sleep(2)  # Wait for camera to stop
            
            # Rotate camera
            pan_tilt.set_pan(pan)
            pan_tilt.set_tilt(tilt)
            time.sleep(1)  # Wait for servos to finish
            
            # Restart camera if it was running
            if curr_status:
                utils.redis_set('camera_status', True)
            
            LOGGER.info(f'Camera rotated to pan={pan}, tilt={tilt}')
            return {
                'success': True,
                'message': f'Camera rotated to pan={pan}, tilt={tilt}',
                'pan': pan,
                'tilt': tilt
            }
        except Exception as e:
            LOGGER.error(f'Error rotating camera: {e}')
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def get_position():
        """Get current camera position
        
        Returns:
            dict: Current pan/tilt position
        """
        try:
            return {
                'success': True,
                'data': {
                    'pan': utils.get_pan(),
                    'tilt': utils.get_tilt()
                }
            }
        except Exception as e:
            LOGGER.error(f'Error getting position: {e}')
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def toggle_notifications(enable=None):
        """Toggle or set notification status
        
        Args:
            enable (bool, optional): Set to True/False, or None to toggle
            
        Returns:
            dict: Operation result
        """
        try:
            current = utils.redis_get('camera_notifications')
            
            if enable is None:
                # Toggle
                new_status = not current
            else:
                new_status = bool(enable)
            
            utils.redis_set('camera_notifications', new_status)
            
            status_text = 'enabled' if new_status else 'disabled'
            LOGGER.info(f'Notifications {status_text}')
            
            return {
                'success': True,
                'message': f'Notifications have been {status_text}',
                'notifications_on': new_status
            }
        except Exception as e:
            LOGGER.error(f'Error toggling notifications: {e}')
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def toggle_auto_detect(enable=None):
        """Toggle or set auto-detect status
        
        Args:
            enable (bool, optional): Set to True/False, or None to toggle
            
        Returns:
            dict: Operation result
        """
        try:
            current = utils.redis_get('auto_detect_status')
            
            if enable is None:
                # Toggle
                new_status = not current
            else:
                new_status = bool(enable)
            
            utils.redis_set('auto_detect_status', new_status)
            
            status_text = 'enabled' if new_status else 'disabled'
            LOGGER.info(f'Auto-detect {status_text}')
            
            return {
                'success': True,
                'message': f'Auto-detect has been {status_text}',
                'auto_detect_on': new_status
            }
        except Exception as e:
            LOGGER.error(f'Error toggling auto-detect: {e}')
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def get_latest_image():
        """Get the latest captured image
        
        Returns:
            dict: Image file path or error
        """
        try:
            latest_image = os.path.join(config.IMG_DIR, 'latest.jpg')
            
            if not os.path.exists(latest_image):
                return {
                    'success': False,
                    'error': 'No image available'
                }
            
            return {
                'success': True,
                'data': {
                    'path': latest_image,
                    'filename': 'latest.jpg'
                }
            }
        except Exception as e:
            LOGGER.error(f'Error getting latest image: {e}')
            return {'success': False, 'error': str(e)}


class SystemController:
    """Handles system-level operations"""
    
    @staticmethod
    def initialize():
        """Initialize the security system
        
        Returns:
            dict: Operation result
        """
        try:
            LOGGER.info('Initializing security system via API')
            
            # Set initial pan/tilt position
            pan_tilt.set_pan(40)
            pan_tilt.set_tilt(10)
            
            # Set Redis variables
            utils.redis_set('home', False)
            utils.redis_set('auto_detect_status', True)
            utils.redis_set('camera_status', True)
            utils.redis_set('camera_notifications', True)
            
            LOGGER.info('Initialization complete')
            
            return {
                'success': True,
                'message': 'System initialized successfully'
            }
        except Exception as e:
            LOGGER.error(f'Error initializing system: {e}')
            return {'success': False, 'error': str(e)}