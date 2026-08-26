from board import SCL, SDA
import busio
from adafruit_pca9685 import PCA9685
from adafruit_motor import motor

# PCA9685 motor channels (from schematic)
MOTOR_M1_IN1 = 15
MOTOR_M1_IN2 = 14
MOTOR_M2_IN1 = 13
MOTOR_M2_IN2 = 12


class MotorController:
    def __init__(self):
        i2c = busio.I2C(SCL, SDA)
        self.pwm = PCA9685(i2c, address=0x5f)
        self.pwm.frequency = 50

        self.motor_left = motor.DCMotor(
            self.pwm.channels[MOTOR_M1_IN1],
            self.pwm.channels[MOTOR_M1_IN2]
        )

        self.motor_right = motor.DCMotor(
            self.pwm.channels[MOTOR_M2_IN1],
            self.pwm.channels[MOTOR_M2_IN2]
        )

    def set_speed(self, left, right):
        # left/right are -1.0 to +1.0
        self.motor_left.throttle = left
        self.motor_right.throttle = right

    def stop(self):
        self.motor_left.throttle = 0
        self.motor_right.throttle = 0
