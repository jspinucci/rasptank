"""
Unified servo controller for RaspTank using Adeept Robot HAT V3.2
Servos A–E: physical 0–180° control
Servos F/G: pan/tilt logical control (-90..+90 pan, -45..+45 tilt)
All servos share ONE ServoKit instance to avoid I2C conflicts.
"""

import logging
import threading
import time

last_servo_update = 0

log = logging.getLogger(__name__)

try:
    from adafruit_servokit import ServoKit
    _KIT_AVAILABLE = True
    log.info("adafruit_servokit loaded - hardware servo mode")
except ImportError:
    _KIT_AVAILABLE = False
    log.warning("adafruit_servokit not available - running in STUB mode")


# ------------------------------------------------------------
# Shared ServoKit instance (CRITICAL FIX)
# ------------------------------------------------------------

class _StubServo:
    angle = 90.0

class _ServoKitStub:
    def __init__(self, **_):
        self.servo = [_StubServo() for _ in range(16)]

KIT = ServoKit(channels=16, address=0x5f) if _KIT_AVAILABLE else _ServoKitStub()


# ============================================================
# PAN/TILT CONTROLLER (F/G)
# ============================================================

class ServoController:
    _SERVO_MIN = 0
    _SERVO_MAX = 180
    _SERVO_CENTER = 90

    PAN_LIMIT = 90.0
    TILT_LIMIT = 45.0

    PAN_CHANNEL = 5   # F
    TILT_CHANNEL = 6  # G

    def __init__(
        self,
        pan_channel: int = PAN_CHANNEL,
        tilt_channel: int = TILT_CHANNEL,
        pan_trim: float = 0.0,
        tilt_trim: float = 0.0,
        pan_inverted: bool = False,
        tilt_inverted: bool = False,
    ):
        self._lock = threading.Lock()
        self._pan_ch = pan_channel
        self._tilt_ch = tilt_channel
        self._pan_trim = pan_trim
        self._tilt_trim = tilt_trim
        self._pan_inv = pan_inverted
        self._tilt_inv = tilt_inverted
        self._pan_deg = 0.0
        self._tilt_deg = 0.0

        self.center()
        log.info("Pan/Tilt ready - channels F=%d, G=%d", pan_channel, tilt_channel)

    def set_pan_tilt(self, pan: float, tilt: float) -> None:
        pan = max(-self.PAN_LIMIT, min(self.PAN_LIMIT, float(pan)))
        tilt = max(-self.TILT_LIMIT, min(self.TILT_LIMIT, float(tilt)))

        with self._lock:
            self._pan_deg = pan
            self._tilt_deg = tilt
            self._apply_pan(pan)
            self._apply_tilt(tilt)

    def set_pan(self, pan: float) -> None:
        self.set_pan_tilt(pan, self._tilt_deg)

    def set_tilt(self, tilt: float) -> None:
        self.set_pan_tilt(self._pan_deg, tilt)

    def center(self) -> None:
        self.set_pan_tilt(0.0, 0.0)

    def smooth_servo_move(self, channel, target_angle, step=2, delay=0.01):
        current = self.current_angles[channel]

        # Clamp angles to safe range
        target_angle = max(10, min(170, target_angle))

        while abs(current - target_angle) > step:
            if target_angle > current:
                current += step
            else:
                current -= step

            self.pwm.set_angle(channel, current)
            time.sleep(delay)

        self.current_angles[channel] = target_angle

    def smooth_move(self, pan: float, tilt: float, steps: int = 20, delay: float = 0.015) -> None:
        start_pan = self._pan_deg
        start_tilt = self._tilt_deg
        for i in range(1, steps + 1):
            t = i / steps
        self.set_pan_tilt(start_pan + (pan - start_pan) * t,
        start_tilt + (tilt - start_tilt) * t)
        time.sleep(delay)

    @property


    def update_servo_smooth(channel, angle):
        global last_servo_update
        now = time.time()

        if now - last_servo_update < 0.03:  # 30 ms
            return
            
        last_servo_update = now
        servo.smooth_servo_move(channel, angle)

    def position(self) -> dict:
        return {"pan": self._pan_deg, "tilt": self._tilt_deg}

    def cleanup(self) -> None:
        self.center()

    def _logical_to_physical(self, logical_deg: float, trim: float, inverted: bool) -> float:
        angle = self._SERVO_CENTER + logical_deg + trim
        if inverted:
            angle = self._SERVO_CENTER - logical_deg + trim
        return max(self._SERVO_MIN, min(self._SERVO_MAX, angle))

    def _apply_pan(self, pan: float) -> None:
        KIT.servo[self._pan_ch].angle = self._logical_to_physical(
            pan, self._pan_trim, self._pan_inv
        )

    def _apply_tilt(self, tilt: float) -> None:
        KIT.servo[self._tilt_ch].angle = self._logical_to_physical(
            tilt, self._tilt_trim, self._tilt_inv
        )


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
        log.info("Arm servos ready (A–E on channels 0–4)")

    def set_servo(self, name: str, angle: float) -> None:
        if name not in self.ARM_CHANNELS:
            log.error("Invalid arm servo name: %s", name)
            return

        angle = max(0, min(180, float(angle)))
        ch = self.ARM_CHANNELS[name]

        with self._lock:
            KIT.servo[ch].angle = angle

    def center(self):
        for name in self.ARM_CHANNELS:
            self.set_servo(name, 90)
