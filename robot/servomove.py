"""
robot/servomove.py - PCA9685 servo driver using smbus2 direct writes.
"""
import logging, time, smbus2

log = logging.getLogger(__name__)

_ADDR      = 0x5f
_MODE1     = 0x00
_PRESCALE  = 0xFE
_LED0_ON_L = 0x06

_bus = None
_initialised = False

def _get_bus():
    global _bus
    if _bus is None:
        _bus = smbus2.SMBus(1)
    return _bus

def _init_pca(frequency=50):
    global _initialised
    bus = _get_bus()
    bus.write_byte_data(_ADDR, _MODE1, 0x11)
    time.sleep(0.005)
    prescale = round(25_000_000 / (4096 * frequency)) - 1
    bus.write_byte_data(_ADDR, _PRESCALE, prescale)
    bus.write_byte_data(_ADDR, _MODE1, 0x01)
    time.sleep(0.005)
    bus.write_byte_data(_ADDR, _MODE1, 0x81)
    time.sleep(0.005)
    _initialised = True
    log.info("PCA9685 init OK — 0x70 all-call, %dHz, prescale=%d", frequency, prescale)

def set_servo_angle(channel, angle):
    if not _initialised:
        _init_pca(50)
    angle = max(0.0, min(180.0, float(angle)))
    pulse_us = 500.0 + (angle / 180.0) * 2000.0
    off_tick = int((pulse_us / 20000.0) * 4096)
    base = _LED0_ON_L + 4 * channel
    bus  = _get_bus()
    bus.write_byte_data(_ADDR, base + 0, 0)
    bus.write_byte_data(_ADDR, base + 1, 0)
    bus.write_byte_data(_ADDR, base + 2, off_tick & 0xFF)
    bus.write_byte_data(_ADDR, base + 3, (off_tick >> 8) & 0x0F)
    print(f"[SERVO DEBUG] Channel {channel} → {angle}°")
