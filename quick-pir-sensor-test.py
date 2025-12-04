#!/usr/bin/env python3
"""
Quick PIR Test for L Mode (Non-Retriggerable)
Should show quick HIGH pulses, not sustained HIGH state

Expected behavior:
- Wave hand → HIGH for 1-3 seconds → LOW
- Each wave should be a separate HIGH pulse
"""

import RPi.GPIO as GPIO
import time
from datetime import datetime

PIR_PIN = 21

def test_pir_l_mode():
    print("=" * 60)
    print("PIR Sensor Test - Verifying L Mode Settings")
    print("=" * 60)
    print("Expected: Quick HIGH pulses (1-3s) when motion detected")
    print("If it stays HIGH for 30+ seconds, switch to L mode!")
    print("=" * 60)
    
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(PIR_PIN, GPIO.IN)
    
    print("\nCalibrating for 60 seconds...")
    print("Stay still!\n")
    
    for i in range(12, 0, -1):
        print(f"  {i*5} seconds remaining...")
        time.sleep(5)
    
    print("\n✓ Ready! Try these tests:")
    print("  1. Wave hand once - should see ONE pulse")
    print("  2. Walk past sensor - should see ONE pulse")
    print("  3. Keep moving - should see MULTIPLE pulses\n")
    print("Press CTRL+C to exit\n")
    
    motion_count = 0
    previous_state = 0
    high_start = None
    
    try:
        while True:
            current_state = GPIO.input(PIR_PIN)
            
            if current_state == 1 and previous_state == 0:
                # Motion started
                motion_count += 1
                high_start = time.time()
                timestamp = datetime.now().strftime("%H:%M:%S")
                print(f"🔴 [{timestamp}] HIGH started (pulse #{motion_count})")
                previous_state = 1
                
            elif current_state == 0 and previous_state == 1:
                # Motion ended
                high_duration = time.time() - high_start
                timestamp = datetime.now().strftime("%H:%M:%S")
                print(f"⚪ [{timestamp}] LOW - pulse lasted {high_duration:.1f}s")
                
                # Warning if pulse too long
                if high_duration > 10:
                    print("   ⚠️  Pulse > 10s - consider L mode or lower Tx!")
                
                print()  # Blank line for readability
                previous_state = 0
            
            time.sleep(0.05)  # Check 20 times per second
            
    except KeyboardInterrupt:
        print("\n" + "=" * 60)
        print(f"Total pulses detected: {motion_count}")
        print("=" * 60)
    finally:
        GPIO.cleanup()

if __name__ == "__main__":
    test_pir_l_mode()