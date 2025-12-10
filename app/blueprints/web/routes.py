# app/blueprints/web/routes.py
from flask import Blueprint, render_template, jsonify

web_bp = Blueprint('web', __name__)

@web_bp.route('/')
def dashboard():
    """Web dashboard - accessible at /rpi-security-cam/web/"""
    return render_template('web/dashboard.html')

@web_bp.route('/test')
def test():
    """Web dashboard - accessible at /rpi-security-cam/web/"""
    return "Hello world"

@web_bp.route('/stream')
def video_stream():
    """Live video stream endpoint"""
    # To be implemented
    return "Web video stream - coming soon"