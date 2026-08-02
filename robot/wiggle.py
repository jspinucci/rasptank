from board import SCL, SDA
import busio
from adafruit_motor import servo
from adafruit_pca9685 import PCA9685
import time

i2c = busio.I2C(SCL, SDA)
pca = PCA9685(i2c, address=0x5f)
pca.frequency = 50

def wiggle(ch):
    s = servo.Servo(pca.channels[ch], min_pulse=500, max_pulse=2400)
    print("Channel", ch)
    for angle in [0, 90, 180, 90]:
        s.angle = angle
        time.sleep(0.5)

for ch in range(8):
    wiggle(ch)
