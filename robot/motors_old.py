from gpiozero import PWMOutputDevice, DigitalOutputDevice
import time

# Motor A pins
EN1 = PWMOutputDevice(18)
IN1 = DigitalOutputDevice(23)
IN2 = DigitalOutputDevice(24)

# Motor B pins
EN2 = PWMOutputDevice(19)
IN3 = DigitalOutputDevice(27)
IN4 = DigitalOutputDevice(22)

def motorA_forward(speed):
    IN1.on()
    IN2.off()
    EN1.value = speed

def motorA_reverse(speed):
    IN1.off()
    IN2.on()
    EN1.value = speed

def motorB_forward(speed):
    IN3.on()
    IN4.off()
    EN2.value = speed

def motorB_reverse(speed):
    IN3.off()
    IN4.on()
    EN2.value = speed


#try:
#    while True:
#        print("Forward 50%")
#        motorA_forward(0.5)
#        motorB_forward(0.5)

#        time.sleep(2)

#        print("Reverse 50%")
#        motorA_reverse(0.5)
#        motorB_forward(0.5)
#        time.sleep(2)

#        print("Reverse 50%")

#        motorA_reverse(0.5)
#        motorB_reverse(0.5)
#        time.sleep(2)

#        print("Forward 100%")
#        motorA_forward(1.0)
#        motorB_forward(1.0)
#        time.sleep(2)

#        print("Stop")
#        EN1.value = 0
#        EN2.value = 0
#        time.sleep(2)

#except KeyboardInterrupt:
#    EN1.value = 0
#    EN2.value = 0



# ── MotorController class (used by app.py) ────────────────────────────────────
class MotorController:
    """Thin wrapper so app.py can use set_speed() / stop() unchanged."""

    def set_speed(self, left: float, right: float):
        """
        left/right are in range -1.0 to 1.0.
        Positive = forward, negative = reverse.
        """
        if left >= 0:
            motorA_forward(abs(left))
        else:
            motorA_reverse(abs(left))

        if right >= 0:
            motorB_forward(abs(right))
        else:
            motorB_reverse(abs(right))

    def stop(self):
        motorA_forward(0.0)
        motorB_forward(0.0)
