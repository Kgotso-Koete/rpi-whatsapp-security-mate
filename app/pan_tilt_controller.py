import time
import math
import smbus


try:
    from .PCA9685 import PCA9685
except ImportError:
    from PCA9685 import PCA9685

    
class PanTiltController:
    def __init__(self, address=0x40, debug=False):
        self.pwm = PCA9685(address, debug)
        self.pwm.setPWMFreq(50)
        
        # Initial pulse values (adjust these based on your servo requirements)
        self.HPulse = 1500  # Horizontal servo initial pulse
        self.VPulse = 1000  # Vertical servo initial pulse
        
        # Set initial positions
        self.pwm.setServoPulse(1, self.HPulse)  # Channel 1 for horizontal
        self.pwm.setServoPulse(0, self.VPulse)  # Channel 0 for vertical
        
        # Movement steps
        self.HStep = 0
        self.VStep = 0
        
    def set_pan(self, angle):
        """Set pan angle (horizontal movement)
        Args:
            angle (int): Angle in degrees (-90 to 90)
        """
        # Convert angle to pulse (500-2500 range, center at 1500)
        pulse = int(1500 + (angle * 1000 / 90))
        pulse = max(500, min(2500, pulse))
        
        self.HPulse = pulse
        self.pwm.start_PCA9685()
        self.pwm.setServoPulse(1, self.HPulse)
        
    def set_tilt(self, angle):
        """Set tilt angle (vertical movement)
        Args:
            angle (int): Angle in degrees (-90 to 90)
        """
        # Convert angle to pulse (500-2500 range, center at 1500)
        pulse = int(1500 + (angle * 1000 / 90))
        pulse = max(500, min(2500, pulse))
        
        self.VPulse = pulse
        self.pwm.start_PCA9685()
        self.pwm.setServoPulse(0, self.VPulse)
        
    def get_pan(self):
        """Get current pan position in degrees"""
        return int((self.HPulse - 1500) * 90 / 1000)
    
    def get_tilt(self):
        """Get current tilt position in degrees"""
        return int((self.VPulse - 1500) * 90 / 1000)
    
    def move_relative(self, pan_delta=0, tilt_delta=0):
        """Move relative to current position
        Args:
            pan_delta (int): Pan change in degrees
            tilt_delta (int): Tilt change in degrees
        """
        if pan_delta != 0:
            new_pan = self.get_pan() + pan_delta
            new_pan = max(-90, min(90, new_pan))
            self.set_pan(new_pan)
            
        if tilt_delta != 0:
            new_tilt = self.get_tilt() + tilt_delta
            new_tilt = max(-90, min(90, new_tilt))
            self.set_tilt(new_tilt)
    
    def stop(self):
        """Stop any movement"""
        self.HStep = 0
        self.VStep = 0
        self.pwm.exit_PCA9685()
    
    def cleanup(self):
        """Clean up resources"""
        self.pwm.exit_PCA9685()


