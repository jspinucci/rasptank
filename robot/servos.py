"""
Unified servo controller for RaspTank using Adeept Robot HAT V3.2
CLEAN VERSION — NO SMOOTHING HERE
Smoothing will be applied in app.py where it belongs.
"""

import logging
import threading

log = logging.getLogger(__name__)

try:
    from adafruit_servokit import ServoKit
    KIT = ServoKit(channels=16, address=0x5f)
    log.info("adafruit_servokit loaded - hardware servo mode")
except ImportError:
    class _StubServo:
        angle = 90.0
    class _ServoKitStub:
        def __init__(self):
            self.servo = [_StubServo() for _ in range(16)]
    KIT = _ServoKitStub()
    log.warning("adafruit_servokit not available - running in STUB mode")


# ============================================================
# PAN/TILT CONTROLLER (F/G)
# ============================================================

class ServoController:
    PAN_CHANNEL = 5
    TILT_CHANNEL = 6

    PAN_LIMIT = 90.0
    TILT_LIMIT = 45.0

    def __init__(self):
        self._lock = threading.Lock()
        self._pan_deg = 0.0
        self._tilt_deg = 0.0
        self.center()

    def set_pan_tilt(self, pan, tilt):
        pan = max(-self.PAN_LIMIT, min(self.PAN_LIMIT, float(pan)))
        tilt = max(-self.TILT_LIMIT, min(self.TILT_LIMIT, float(tilt)))

        with self._lock:
            self._pan_deg = pan
            self._tilt_deg = tilt
            KIT.servo[self.PAN_CHANNEL].angle = 90 + pan
            KIT.servo[self.TILT_CHANNEL].angle = 90 + tilt

    def set_pan(self, pan):
        self.set_pan_tilt(pan, self._tilt_deg)

    def set_tilt(self, tilt):
        self.set_pan_tilt(self._pan_deg, tilt)

    def center(self):
        self.set_pan_tilt(0.0, 0.0)


# ============================================================
# ARM SERVO CONTROLLER (A–E)
# ============================================================

class ArmServoController:
    ARM_CHANNELS = {
        "A": 0,
        "B": 1,
        "C": 2,
        "D": 3,
        "E": 4,
    }

    def __init__(self):
        self._lock = threading.Lock()

    def set_servo(self, name, angle):
        if name not in self.ARM_CHANNELS:
            return

        angle = max(0, min(180, float(angle)))
        ch = self.ARM_CHANNELS[name]

        with self._lock:
            KIT.servo[ch].angle = angle

    def center(self):
        for name in self.ARM_CHANNELS:
            self.set_servo(name, 90)
