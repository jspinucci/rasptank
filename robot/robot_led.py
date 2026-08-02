from gpiozero import LED

# Define LEDs using BCM pin numbers
led1 = LED(17)
led2 = LED(16)

def led1_on():
    led1.on()
    print("[LED DEBUG] LED 1 turned ON")

def led1_off():
    led1.off()
    print("[LED DEBUG] LED 1 turned OFF")

def led2_on():
    led2.on()
    print("[LED DEBUG] LED 2 turned ON")

def led2_off():
    led2.off()
    print("[LED DEBUG] LED 2 turned OFF")

def cleanup():
    led1.off()
    led2.off()
    print("[LED DEBUG] LEDs cleaned up")

