"""
Utils module, contains utility functions used throughout the postgrez codebase.
"""
import logging
import logging.config
import glob
import os
import sys
import subprocess
import ast
import signal
import time
import shutil

import cv2
import psutil
import boto3
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import redis


try:
    from app import config
    from app.pan_tilt_controller import PanTiltController
except:
    import config
    from pan_tilt_controller import PanTiltController

LOGGER = logging.getLogger(__name__)
CONF = config.load_private_config()
REDIS_CONN = redis.StrictRedis(
    host='localhost',
    port=6379,
    decode_responses=True
)

SLACK_BOT_TOKEN = CONF['rpi_cam_app']['bot_token']

pan_tilt = PanTiltController()

def redis_get(key):
    """Fetch a key from redis

    Args:
        key (str): Key to fetch

    Returns:
        Value associated with redis key
    """
    str_obj = REDIS_CONN.get(key)
    
    if str_obj is None:
        return None

    # Handle boolean strings
    if str_obj in ('True', 'False'):
        return str_obj == 'True'
    
    # Need to research a better way of parsing underlying Python object types
    # from strings redis returns..
    try:
        value = ast.literal_eval(str_obj)
    except ValueError:
        value = str_obj
    except SyntaxError:
        value = str_obj
    return value

def redis_set(key, value):
    """Set a value in Redis

    Args:
        key (str): Redis key name
        value (): Value to be associated with key
    """
    # Convert boolean and other types to string for Redis
    if isinstance(value, bool):
        value = str(value)
    REDIS_CONN.set(key, value)

def save_image(filepath, frame):
    """Save an image
    Args:
        filepath (str): Filepath to save image to
        frame (numpy.ndarray): Image to save
    """
    LOGGER.debug('Saving image to %s' % filepath)
    cv2.imwrite(filepath, frame)
    return

def get_tilt():
    """Get the current tilt value
    Returns:
        int: Current tilt value in degrees
    """
    return pan_tilt.get_tilt()

def get_pan():
    """Get the current pan value
    Returns:
        int: Current pan value in degrees
    """
    return pan_tilt.get_pan()

def validate_slack(token):
    """Verify the request is coming from Slack by checking that the
    verification token in the request matches our app's settings

    Args:
        token (str): Slack token

    Returns:
        bool: Indicate whether token received matches known verification token
    """
    if CONF['rpi_cam_app']['verification_token'] != token:
        return False
    return True

def parse_slash_post(form):
    """Parses the Slack slash command data

    Args:
        form (ImmutableMultiDict): Info from the POST request, as an IMD object.

    Returns :
        data (dict): dictionary representation of the IMD if request was
            verified. Otherwise, returns False
    """
    raw_dict = form.to_dict(flat=False)
    data = {k:v[0] for k, v in raw_dict.items()}
    return data

def slack_post_interactive(response):
    """Ingest the picture upload response and add a follow up message with
    buttons to tag the image

    Args:
        response (dict): Slack response from the image upload
    """
    if response['ok']:
        file_id = response['file']['id']
        filename = response['file']['title']
        slack_client = WebClient(token=SLACK_BOT_TOKEN)
        
        # Use modern blocks instead of legacy attachments
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Tag Image {filename}*"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "How should this image be tagged?"
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Occupied",
                            "emoji": True
                        },
                        "style": "primary",
                        "value": str({
                            'occupied': True,
                            'file_id': file_id,
                            'filename': filename
                        })
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Unoccupied",
                            "emoji": True
                        },
                        "style": "danger",
                        "value": str({
                            'occupied': False,
                            'file_id': file_id,
                            'filename': filename
                        })
                    }
                ]
            }
        ]
        
        response = slack_client.chat_postMessage(
            channel=CONF['alerts_channel'],
            text=f'Tag Image {filename}',
            blocks=blocks
        )
    else:
        LOGGER.error('Failed image upload %s', response)

def slack_delete_file(file_id):
    """Delete a file in slack

    Args:
        file_id (str): File to delete

    Returns:
        dict: Slack response object
    """
    slack_client = WebClient(token=SLACK_BOT_TOKEN)
    response = slack_client.files_delete(file=file_id)
    return response

def slack_post(message, channel=CONF['alerts_channel'],
               token=SLACK_BOT_TOKEN):
    """Post a message to a channel

    Args:
        message (str): Message to post
        channel (str): Channel id. Defaults to alerts_channel specified in
            private.yml
        token (str): Token to use with SlackClient. Defaults to bot_token
            specified in private.yml
    """
    LOGGER.debug("Posting to slack")
    slack_client = WebClient(token=token)
    try:
        response = slack_client.chat_postMessage(
            channel=channel,
            text=message
        )
        if response['ok']:
            LOGGER.info('Posted succesfully')
        else:
            LOGGER.error('Unable to post, response: %s', response)
    except SlackApiError as e:
        LOGGER.error('Error posting to Slack: %s', e.response['error'])
    
    return

def slack_upload(fname, title=None, channel=CONF['alerts_channel'],
                 token=SLACK_BOT_TOKEN):
    """Upload a file to a channel with better error handling"""
    if title is None:
        title = os.path.basename(fname)
    slack_client = WebClient(token=token)
    
    max_retries = 3
    retry_delay = 2  # seconds
    
    for attempt in range(max_retries):
        try:
            response = slack_client.files_upload_v2(
                channel=channel,
                file=fname,
                title=title
            )
            return response
            
        except SlackApiError as e:
            LOGGER.error(f'Slack API error (attempt {attempt + 1}/{max_retries}): {e.response["error"]}')
            if attempt == max_retries - 1:  # Last attempt
                return {'ok': False, 'error': e.response['error']}
            time.sleep(retry_delay)
            
        except Exception as e:
            LOGGER.error(f'Network error (attempt {attempt + 1}/{max_retries}): {str(e)}')
            if attempt == max_retries - 1:  # Last attempt
                return {'ok': False, 'error': str(e)}
            time.sleep(retry_delay)
    
    return {'ok': False, 'error': 'All retry attempts failed'}

def spawn_python_process(fname):
    """Spawn a python process.

    Args:
        fname (str): Name of the python job to start

    Returns:
        pid (int): process identification number of spawned process
    """
    pid = None
    try:
        LOGGER.info('Spawning python job %s', fname)
        process = subprocess.Popen(
            [sys.executable, fname],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
            )
        pid = process.pid
        LOGGER.info('Process succesfully spawned: %s', pid)
    except Exception as exc:
        LOGGER.error('Unable to spawn process due to error: \n %s', str(exc))
    return pid

def kill_python_process(pid):
    """Kill a running python process by name.

    Args:
        pid (int): process identification number of process to kill

    Returns:
        killed (bool): True if process was killed, otherwise False.
    """
    killed = False
    LOGGER.info('Attempting to kill %s', pid)
    try:
        if check_process(pid):
            LOGGER.info('Killing pid: %s', pid)
            os.kill(pid, signal.SIGKILL)
            time.sleep(2)
            status = check_process(pid)
            if not status:
                LOGGER.info('Successfully killed process')
                killed = True
        else:
            killed = True
    except Exception as exc:
        LOGGER.error('Unable to kill process due to error %s', str(exc))

    return killed

def check_process(pid):
    """Check if process is running.
    Args:
        pid (int): process identification number of process to check
    Returns:
        (bool): True if process is running, otherwise False
    """
    LOGGER.info('Checking if %s is running', pid)
    try:
        os.kill(pid, 0)
        proc = psutil.Process(pid)
        if proc.status() == psutil.STATUS_ZOMBIE:
            status = False
        else:
            LOGGER.info('Process %s is running', pid)
            status = True
    except OSError:
        status = False

    return status


def latest_file(path, ftype='*'):
    """Return the last file created in a directory.

    Args:
        path (str): Path of the directory
        ftype (str): Filetype to match. For example, supply '*.csv' to get the
            latest csv, or 'Master*'' to get the latest filename starting with
            'Master'. Defaults to '*' which matches all files.
    Returns:
        last_file (str): Last file created in the directory.
    """
    last_file = None
    if not os.path.isdir(path):
        LOGGER.error('Please supply a valid directory')
        return None

    if not path.endswith('/'):
        path += '/'

    list_of_files = glob.glob(path + ftype) # all filetypes
    list_of_files = [f for f in list_of_files if os.path.isfile(f)]
    if list_of_files:
        last_file = max(list_of_files, key=os.path.getctime)
    else:
        LOGGER.error('No files in directory')

    return last_file

def search_path(path, filetypes=None):
    """Recursively search a path, optionally matching specific filetypes, and
    return all filenames.

    Args:
        path (str): Path to search
        filetypes (list, optional): Filetypes to return

    Returns:
        files (list): List of files
    """
    files = []
    for (dirpath, dirnames, filenames) in os.walk(path):
        if filetypes:
            files.extend([os.path.join(dirpath, file) for file in filenames
                          if file.endswith(tuple(filetypes))])
        else:
            files.extend([os.path.join(dirpath, file) for file in filenames])
    return files

def upload_to_s3(s3_bucket, local, key):
    """Upload a list of files to S3.

    Args:
        s3_bucket (str): Name of the S3 bucket.
        files (list): List of files to upload
    """
    LOGGER.info("Attempting to load %s to s3 bucket: s3://%s, key: %s", local,
                s3_bucket, key)
    s3 = boto3.resource('s3')
    data = open(local, 'rb')
    s3.Bucket(s3_bucket).put_object(
        Key=key, Body=data, ServerSideEncryption='AES256')

def clean_dir(path, exclude=None):
    """Clear folders and files in a specified path

    Args:
        path (str): Path to clean files/folders
        exclude (list, optiona): Filenames to exclude from deletion
    """
    if not exclude:
        exclude = []

    for file in os.listdir(path):
        full_path = os.path.join(path, file)
        if os.path.isdir(full_path):
            shutil.rmtree(full_path)
            assert not os.path.isdir(full_path)
        elif os.path.isfile(full_path) and file not in exclude:
            os.remove(full_path)
            assert not os.path.isfile(full_path)

def measure_temp():
    temp = os.popen("vcgencmd measure_temp").readline()
    parsed_temp = temp.replace("temp=", "").split("'C")[0]
    return float(parsed_temp)