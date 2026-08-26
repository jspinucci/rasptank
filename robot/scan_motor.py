#!/usr/bin/env python3
import time
from board import SCL, SDA
import busio
from adafruit_pca9685 import PCA9685
from adafruit_motor import motor

i2c = busio.I2C(SCL, SDA)
pca = PCA9685(i2c, address=0x5f)
pca.frequency = 50

def test_pair(ch1, ch2, label):
    print(f"\n=== Testing pair {label}: channels {ch1}, {ch2} ===")
    m = motor.DCMotor(pca.channels[ch1], pca.channels[ch2])
    m.throttle = 0.4
    print("  -> throttle = 0.4 (watch motors)")
    time.sleep(2)
    m.throttle = -0.4
    print("  -> throttle = -0.4 (watch motors)")
    time.sleep(2)
    m.throttle = 0
    print("  -> throttle = 0 (stop)")
    time.sleep(1)

pairs = [
    (15, 14, "P15/14"),
    (12, 13, "P12/13"),
    (11, 10, "P11/10"),
    (8, 9,  "P8/9"),
    (7, 6,  "P7/6"),
    (5, 4,  "P5/4"),
    (3, 2,  "P3/2"),
    (1, 0,  "P1/0"),
]

try:
    for ch1, ch2, label in pairs:
        test_pair(ch1, ch2, label)
finally:
    pca.deinit()
    print("\nScan complete.")
