# PIR Motion Sensor Setup Guide for Raspberry Pi 5

Complete guide for setting up the HC-SR501 PIR (Passive Infrared) motion sensor with Raspberry Pi 5 for the home security system project.

---

## System Information

**Operating System:**
```
Raspbian GNU/Linux 13 (trixie)
VERSION_ID="13"
VERSION_CODENAME=trixie
```

**Hardware:**
- Raspberry Pi 5 (32-bit)
- HC-SR501 PIR Motion Sensor

---

## Hardware Components

### PIR Sensor
- **Model:** HC-SR501 Digital PIR Motion Sensor
- **Purchased from:** [Communica.co.za](https://www.communica.co.za/products/bmt-digital-pir-motion-sensor)
- **Manual:** [HC-SR501 User Manual](https://docs.google.com/document/d/1x06H7GV2lR_n0c6m5iBfodAjYrwTZKAQV4wTkl-C2-0/view?pli=1&tab=t.0)

### Specifications
- **Input Voltage:** 4.5V - 20V (powered via Pi's 5V)
- **Output Signal:** 3.3V HIGH / 0V LOW (safe for Pi GPIO)
- **Sensing Range:** 5-7 meters
- **Sensing Angle:** 100° cone
- **Delay Time:** 0.5 - 200 seconds (adjustable)
- **Current Draw:** <50µA

---

## Wiring Diagram

### Pin Connections

| PIR Sensor Pin | Raspberry Pi Pin | GPIO (BCM) | Pin Number | Wire Color |
|----------------|------------------|------------|------------|------------|
| **VCC** (Power) | 5V Power | N/A | Pin 4 | Red |
| **GND** (Ground) | Ground | N/A | Pin 6 | Black |
| **OUT** (Signal) | GPIO 21 | BCM 21 | Pin 40 | Yellow/White |

### Raspberry Pi GPIO Header Reference

```
Physical Pin Layout (Top View):

     3.3V [ 1] [ 2] 5V ← VCC (Red)
          [ 3] [ 4] 5V
          [ 5] [ 6] GND ← GND (Black)
          [ 7] [ 8]
      GND [ 9] [10]
          ...
          [39] [40] GPIO 21 ← OUT (Yellow)
                    └─ BCM 21
```

### HC-SR501 Pinout

```
Bottom view of sensor (looking at pins):

┌─────────────────────────────────┐
│        HC-SR501 PIR             │
│                                 │
│     [VCC]   [OUT]   [GND]      │
│       │       │       │         │
└───────┼───────┼───────┼─────────┘
        │       │       │
        │       │       └─ To Pi Pin 6 (GND)
        │       └─────────  To Pi Pin 40 (GPIO 21)
        └───────────────── To Pi Pin 4 (5V)
```

---

## PIR Sensor Configuration

### Jumper Setting
**Setting Used:** **L (Non-Retriggerable Mode)**

```
Back of HC-SR501:
┌──────────────────┐
│  [Sx]      [Tx]  │ ← Potentiometers
│                  │
│    [H] [L]       │ ← Jumper set to L
│       └┬┘        │
└──────────────────┘
```

**Why L Mode:**
- Provides clean on/off cycles (HIGH for set duration, then LOW)
- Better for counting discrete motion events
- Prevents sensor from staying HIGH indefinitely with continuous motion
- Works optimally with Ian's motion detection algorithm

### Potentiometer Settings

#### Time Delay (Tx)
**Setting:** Minimum to Low (~1-3 seconds)
- **Location:** Right-side potentiometer
- **Adjustment:** Turn counter-clockwise to minimum
- **Purpose:** Quick recovery time between motion detections

#### Sensitivity (Sx)
**Setting:** Medium to High
- **Location:** Left-side potentiometer  
- **Adjustment:** Start at middle position, adjust based on testing
- **Purpose:** Detection range (3-7 meters)

---

## Software Setup

### Python Environment

This project uses a **Python virtual environment** to manage dependencies locally.

#### Create and Activate Virtual Environment

```bash
cd ~/Documents/Projects/rpi-whatsapp-security-mate

# Create virtual environment (if not already created)
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate
```

### Required Libraries

#### 1. RPi.GPIO
Primary library for GPIO control, used in the main security system code.

```bash
# Install in virtual environment
pip install RPi.GPIO
```

**Usage in code:**
```python
import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BCM)
GPIO.setup(21, GPIO.IN)
pir_value = GPIO.input(21)  # Returns 0 or 1
```

#### 2. gpiozero (Optional - for testing)
Higher-level library that simplifies GPIO interactions.

```bash
# Install in virtual environment
pip install gpiozero
```

**Note:** The main security system uses `RPi.GPIO`, but `gpiozero` is useful for testing and prototyping.

---

## Testing the PIR Sensor

### Basic Test Script

Save as `test_pir.py`:

```python
#!/usr/bin/env python3
import RPi.GPIO as GPIO
import time
from datetime import datetime

PIR_PIN = 21  # GPIO 21 (BCM mode)

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(PIR_PIN, GPIO.IN)

print("PIR Sensor Test - GPIO 21")
print("Calibrating for 60 seconds...")
time.sleep(60)
print("Ready! Wave your hand to test.\n")

previous_state = 0
motion_count = 0

try:
    while True:
        current_state = GPIO.input(PIR_PIN)
        
        if current_state == 1 and previous_state == 0:
            motion_count += 1
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"🚨 [{timestamp}] MOTION DETECTED! (Event #{motion_count})")
            previous_state = 1
            
        elif current_state == 0 and previous_state == 1:
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"✓  [{timestamp}] Motion ended - Ready")
            previous_state = 0
        
        time.sleep(0.1)
        
except KeyboardInterrupt:
    print(f"\nTotal motion events: {motion_count}")
    GPIO.cleanup()
```

### Running the Test

```bash
# Activate virtual environment
source venv/bin/activate

# Run test script
python3 test_pir.py
```

**Expected Output:**
```
PIR Sensor Test - GPIO 21
Calibrating for 60 seconds...
Ready! Wave your hand to test.

🚨 [14:23:45] MOTION DETECTED! (Event #1)
✓  [14:23:47] Motion ended - Ready
🚨 [14:23:52] MOTION DETECTED! (Event #2)
✓  [14:23:54] Motion ended - Ready
```

---

## Integration with Security System

### How the PIR is Used

In `app/security_system.py`, the PIR sensor provides **supplementary motion confirmation** alongside camera-based motion detection:

```python
class MotionDetector():
    def __init__(self):
        # PIR Configuration
        self.PIR = 21
        self.pir_values = []
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.PIR, GPIO.IN)
    
    def read_pir(self):
        """Read PIR sensor state"""
        return GPIO.input(self.PIR)
    
    def store_pir(self, pir_value):
        """Store last N PIR readings"""
        self.pir_values.append(pir_value)
        self.pir_values = self.pir_values[-1*self.pir_store_cnt:]
```

### Detection Logic

The system combines:
1. **Camera background subtraction** (primary detection)
2. **PIR sensor readings** (confirmation signal)
3. **Pre-trained image classifier** (optional, reduces false positives)

```python
# Classification uses PIR as additional evidence
occupied = self.model.classify(frame, contours, self.pir_values)
```

---

## Troubleshooting

### Sensor Not Detecting Motion

**Problem:** No output when waving hand in front of sensor

**Solutions:**
1. Check wiring connections (especially VCC to 5V, not 3.3V)
2. Wait full 60 seconds for calibration after power-on
3. Increase sensitivity (turn Sx potentiometer clockwise)
4. Check jumper is properly seated
5. Try a different GPIO pin to rule out pin issues

### Sensor Always Shows HIGH

**Problem:** Sensor output stays HIGH constantly

**Solutions:**
1. Switch jumper to L (Non-retriggerable) mode
2. Reduce time delay (turn Tx counter-clockwise)
3. Point sensor away from heat sources (heaters, sunlight)
4. Reduce sensitivity if too high

### Intermittent Detection

**Problem:** Sensor works inconsistently

**Solutions:**
1. Ensure sensor has proper calibration time (60 seconds)
2. Check for loose wiring connections
3. Avoid moving during calibration period
4. Shield from air currents (AC, fans)

### Permission Errors

**Problem:** `RuntimeError: No access to /dev/mem`

**Solution:**
```bash
# Add user to gpio group
sudo usermod -a -G gpio $USER

# Log out and back in for changes to take effect
```

---

## Physical Implementation Photos

### Wiring Setup

| Front View | Back View |
|------------|-----------|
| ![PIR Front Setup](imgs/my-implementation/pir-front-setup.jpg) | ![PIR Back Setup](imgs/my-implementation/pir-back-setup.jpg) |

*Images showing the physical wiring connections and sensor configuration*

---

## Important Notes

### Calibration Period
⚠️ **Critical:** After powering on, the PIR sensor requires **60 seconds minimum** to calibrate. During this time:
- Do NOT move in front of the sensor
- Output may fluctuate briefly
- Wait for sensor to settle before testing

### GPIO Mode
The security system uses **BCM (Broadcom) pin numbering**, not physical pin numbers:
- `GPIO.setmode(GPIO.BCM)` - Uses GPIO numbers (e.g., GPIO 21)
- Physical Pin 40 = GPIO 21 in BCM mode

### Power Requirements
- PIR sensor requires **5V** input power
- Output signal is **3.3V** (safe for Pi GPIO)
- Total current draw is minimal (<50µA)

### Detection Range
- **Optimal range:** 3-5 meters
- **Maximum range:** Up to 7 meters (with high sensitivity)
- **Detection angle:** 100° cone
- **Best mounted:** 2-2.5 meters high, tilted slightly downward

---

## Configuration in `config.yml`

The PIR sensor behavior can be tuned via the main configuration file:

```yaml
# PIR sensor settings
pir_store_cnt: 10  # Number of PIR readings to store in memory

# Motion detection thresholds
min_notify_seconds: 60          # Minimum time between Slack alerts
min_occupied_fraction: 0.5      # Fraction of frames that must show motion
motion_classification_store_cnt: 10  # Motion history buffer size
```

---

## References

- [HC-SR501 Purchase Link](https://www.communica.co.za/products/bmt-digital-pir-motion-sensor)
- [HC-SR501 User Manual](https://docs.google.com/document/d/1x06H7GV2lR_n0c6m5iBfodAjYrwTZKAQV4wTkl-C2-0/view?pli=1&tab=t.0)
- [RPi.GPIO Documentation](https://sourceforge.net/p/raspberry-gpio-python/wiki/Home/)
- [gpiozero Motion Sensor Examples](https://gpiozero.readthedocs.io/en/stable/recipes.html#motion-sensor)
- [Ian Whitestone's Security System](https://github.com/ian-whitestone/rpi-security-system)

---

## Summary

✅ **Wiring:** VCC→Pin 4, GND→Pin 6, OUT→Pin 40 (GPIO 21)  
✅ **Jumper:** L (Non-retriggerable mode)  
✅ **Time Delay:** Minimum (~1-3 seconds)  
✅ **Sensitivity:** Medium to High  
✅ **Calibration:** 60 seconds required after power-on  
✅ **Libraries:** RPi.GPIO (primary), gpiozero (optional testing)  
✅ **Environment:** Python virtual environment (`venv`)

The PIR sensor is now configured and ready to provide motion confirmation signals to the Raspberry Pi security system.