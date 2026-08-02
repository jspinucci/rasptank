"""
Unified servo controller for RaspTank using Adeept Robot HAT V3.2
Hybrid smoothing:
- Pan/Tilt: gentle step-based smoothing
- Arm servos: fast minimal smoothing
"""

import logging
import threading
import time

log = logging.getLogger(__name__)

try:
    from adafruit_servokit import ServoKit
    _KIT_AVAILABLE = True
    log.info("adafruit_servokit loaded - hardware servo mode")
except ImportError:
    _KIT_AVAILABLE = False
    log.warning("adafruit_servokit not available - running in STUB mode")


# ------------------------------------------------------------
# Shared ServoKit instance
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

    # ------------------------------------------------------------
    # HYBRID SMOOTHING FOR PAN/TILT
    # ------------------------------------------------------------

    def _smooth_angle(self, start, target, steps=4, delay=0.005):
        """Gentle smoothing for pan/tilt."""
        for i in range(1, steps + 1):
            t = i / steps
            yield start + (target - start) * t
            time.sleep(delay)

    def set_pan_tilt(self, pan: float, tilt: float) -> None:
        """Smooth pan/tilt movement."""
        pan = max(-self.PAN_LIMIT, min(self.PAN_LIMIT, float(pan)))
        tilt = max(-self.TILT_LIMIT, min(self.TILT_LIMIT, float(tilt)))

        with self._lock:
            start_pan = self._pan_deg
            start_tilt = self._tilt_deg

            for new_pan, new_tilt in zip(
                self._smooth_angle(start_pan, pan),
                self._smooth_angle(start_tilt, tilt)
            ):
                self._pan_deg = new_pan
                self._tilt_deg = new_tilt
                self._apply_pan(new_pan)
                self._apply_tilt(new_tilt)

    def set_pan(self, pan: float) -> None:
        self.set_pan_tilt(pan, self._tilt_deg)

    def set_tilt(self, tilt: float) -> None:
        self.set_pan_tilt(self._pan_deg, tilt)

    def center(self) -> None:
        self.set_pan_tilt(0.0, 0.0)

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

    # ------------------------------------------------------------
    # HYBRID SMOOTHING FOR ARM SERVOS (FAST BUT SOFTENED)
    # ------------------------------------------------------------

    def _smooth_arm(self, start, target, steps=8, delay=0.004):
        """Minimal smoothing for arm servos."""
        for i in range(1, steps + 1):
            t = i / steps
            yield start + (target - start) * t
            time.sleep(delay)

    def set_servo(self, name: str, angle: float) -> None:
        if name not in self.ARM_CHANNELS:
            log.error("Invalid arm servo name: %s", name)
            return

        angle = max(0, min(180, float(angle)))
        ch = self.ARM_CHANNELS[name]

        with self._lock:
            start = KIT.servo[ch].angle or 90

            for new_angle in self._smooth_arm(start, angle):
                KIT.servo[ch].angle = new_angle

    def center(self):
        for name in self.ARM_CHANNELS:
            self.set_servo(name, 90)
