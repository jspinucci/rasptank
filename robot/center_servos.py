from adafruit_servokit import ServoKit
import time

# Your PCA9685 board at address 0x5f, 16 channels
kit = ServoKit(channels=16, address=0x5f)

# Servo A–E are channels 0–4
ARM_CHANNELS = {
    "A": 0,
    "B": 1,
    "C": 2,
    "D": 3,
    "E": 4,
    "F": 5,
    "G": 6
}

print("Centering servos A–E to 90 degrees...")

for name, ch in ARM_CHANNELS.items():
    kit.servo[ch].angle = 90
    print(f"Servo {name} (channel {ch}) set to 90°")
    time.sleep(0.2)

print("Done.")
