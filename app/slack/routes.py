"""
Slack slash command routes (refactored from views.py)
All business logic moved to shared API layer
"""
import json
import os
import subprocess
import logging
from functools import wraps

from flask import Blueprint, request, make_response

from app import config
from app import utils
from app.api import CameraController, SystemController

logging.basicConfig(level=logging.DEBUG)
LOGGER = logging.getLogger(__name__)
CONF = config.load_private_config()

# Create Slack blueprint
slack_bp = Blueprint('slack', __name__, url_prefix='/slack')


def slack_verification(user=None):
    """Verify post request came from Slack by checking the token sent with the
    request. Optionally verify that the request came from a specific user

    Args:
        user (str, optional): User ID to verify, defaults to None
    """
    def actual_decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            data = utils.parse_slash_post(request.form)
            token = data.get('token', None)
            if not utils.validate_slack(token):
                return 'Un-authenticated'
            if user:
                if data.get('user_id', None) != user:
                    return 'No access to this command'
            return func(*args, **kwargs)
        return wrapper
    return actual_decorator


@slack_bp.route('/initialize', methods=["POST"])
@slack_verification(CONF['ian_uid'])
def initialize():
    """Initialize the security system app"""
    result = SystemController.initialize()
    return result['message'] if result['success'] else f"Error: {result.get('error')}"


@slack_bp.route('/status', methods=["GET", "POST"])
@slack_verification()
def status():
    """Get the status of the current redis configuration and camera position"""
    result = CameraController.get_status()
    
    if not result['success']:
        return f"Error: {result.get('error')}"
    
    data = result['data']
    summary = """**PI SUMMARY**:
    pi_temperature: {}
    camera_position: Panned to {}. Tilted to {}
    camera_status: {}
    camera_notifications: {}
    auto_detect_status: {}
    home: {}
    """
    return summary.format(
        data['temperature'],
        data['pan'],
        data['tilt'],
        data['camera_on'],
        data['notifications_on'],
        data['auto_detect_on'],
        data['home']
    )


@slack_bp.route('/interactive', methods=["POST"])
def interactive():
    """Handle Slack interactive button clicks (occupied/unoccupied tagging)"""
    data = utils.parse_slash_post(request.form)
    payload = json.loads((data['payload']))
    action = payload['actions'][0]
    action_value = eval(action['value'])
    tag = action_value['occupied']
    img_filename = action_value['filename']

    # Save tag file
    filename = "{}_{}.txt".format(tag, img_filename.replace('.jpg', ''))
    filepath = os.path.join(config.TRAIN_DIR, filename)
    open(filepath, 'w').close()

    # Delete file from Slack
    utils.slack_delete_file(action_value['file_id'])
    
    return 'Response for {} logged'.format(img_filename)


@slack_bp.route('/pycam_on', methods=["POST"])
@slack_verification(CONF['ian_uid'])
def pycam_on():
    """Turn on the camera"""
    result = CameraController.turn_on()
    return result['message'] if result['success'] else f"Error: {result.get('error')}"


@slack_bp.route('/pycam_off', methods=["POST"])
@slack_verification(CONF['ian_uid'])
def pycam_off():
    """Turn off the camera"""
    result = CameraController.turn_off()
    return result['message'] if result['success'] else f"Error: {result.get('error')}"


@slack_bp.route('/auto_detect_on', methods=["POST"])
@slack_verification(CONF['ian_uid'])
def auto_detect_on():
    """Turn on auto-detect"""
    result = CameraController.toggle_auto_detect(enable=True)
    return result['message'] if result['success'] else f"Error: {result.get('error')}"


@slack_bp.route('/auto_detect_off', methods=["POST"])
@slack_verification(CONF['ian_uid'])
def auto_detect_off():
    """Turn off auto-detect"""
    result = CameraController.toggle_auto_detect(enable=False)
    return result['message'] if result['success'] else f"Error: {result.get('error')}"


@slack_bp.route('/notifications_off', methods=["POST"])
@slack_verification(CONF['ian_uid'])
def notifications_off():
    """Disable motion detected notifications"""
    result = CameraController.toggle_notifications(enable=False)
    return result['message'] if result['success'] else f"Error: {result.get('error')}"


@slack_bp.route('/notifications_on', methods=["POST"])
@slack_verification(CONF['ian_uid'])
def notifications_on():
    """Enable motion detected notifications"""
    result = CameraController.toggle_notifications(enable=True)
    return result['message'] if result['success'] else f"Error: {result.get('error')}"


@slack_bp.route('/rotate', methods=["POST"])
@slack_verification(CONF['ian_uid'])
def rotate():
    """Rotate the camera"""
    data = utils.parse_slash_post(request.form)
    args = data['text'].split()

    if len(args) != 2:
        return ("Incorrect input. Please provide as two integers separated by "
                "a space. i.e. '0 0'")
    
    result = CameraController.rotate(args[0], args[1])
    return result['message'] if result['success'] else f"Error: {result.get('error')}"


@slack_bp.route('/current_position', methods=["POST"])
@slack_verification()
def current_position():
    """Get the current position of the camera"""
    result = CameraController.get_position()
    
    if not result['success']:
        return f"Error: {result.get('error')}"
    
    data = result['data']
    return f"Panned to {data['pan']}. Tilted to {data['tilt']}"


@slack_bp.route("/last_image", methods=["POST"])
@slack_verification(CONF['ian_uid'])
def last_image():
    """Return the last image taken"""
    data = utils.parse_slash_post(request.form)
    
    result = CameraController.get_latest_image()
    
    if not result['success']:
        return result.get('error', 'No image available')
    
    image_path = result['data']['path']
    utils.slack_upload(image_path, channel=data['channel_id'])
    return 'Latest image uploaded'


@slack_bp.route('/top', methods=["GET", "POST"])
@slack_verification()
def top():
    """Get top system info"""
    with open('top.log', 'w') as outfile:
        subprocess.call("top -n1 -b -c", shell=True, stdout=outfile)

    with open('top.log', 'r') as f:
        contents = "".join([next(f) for x in range(20)])
    return contents


@slack_bp.route("/listening", methods=["GET", "POST"])
def hears():
    """Listen for incoming events from Slack"""
    str_response = request.data.decode('utf-8')
    slack_event = json.loads(str_response)
    LOGGER.info('slack event: %s', slack_event)

    # Slack URL Verification
    if "challenge" in slack_event:
        return make_response(slack_event["challenge"], 200,
                             {"content_type": "application/json"})

    token = slack_event.get("token")
    if not utils.validate_slack(token):
        message = "Invalid Slack verification token"
        return make_response(message, 403, {"X-Slack-No-Retry": 1})

    return make_response("[NO EVENT IN SLACK REQUEST] These are not the droids "
                         "you're looking for.", 404, {"X-Slack-No-Retry": 1})