"""
Legacy views for log streaming and other utilities
These remain at root level for backwards compatibility
"""
from flask import Response, render_template
import subprocess

from app import application as app

LOG_PATH = '/home/kgotso-koete/Documents/Projects/rpi-whatsapp-security-mate/app/logs/'

def tail(filepath, num_lines="20"):
    """Tail a file"""
    proc = subprocess.Popen(
        ['tail', '-n', num_lines, filepath], stdout=subprocess.PIPE)
    return proc.stdout.read()


@app.route('/logz')
def logz():
    """Log viewer page"""
    return render_template('logz.html')


@app.route('/flask_app_logstream')
def flask_app_logstream():
    """Flask app log stream"""
    contents = tail(LOG_PATH + 'app.log', '50')
    return Response(contents, mimetype='text/plain')


@app.route('/flask_access_logstream')
def flask_access_logstream():
    """Flask access log stream"""
    contents = tail(LOG_PATH + 'access.log', '50')
    return Response(contents, mimetype='text/plain')


@app.route('/security_system_logstream')
def security_system_logstream():
    """Security system log stream"""
    contents = tail(LOG_PATH + 'security_system.log', '50')
    return Response(contents, mimetype='text/plain')


@app.route('/s3_upload_logstream')
def s3_upload_logstream():
    """S3 upload log stream"""
    contents = tail(LOG_PATH + 's3_upload.log', '50')
    return Response(contents, mimetype='text/plain')