import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "robot"))

import threading
import json
import time

# ── Hardware modules (loaded lazily in start()) ──────────────────────────────
_motors = None
_led    = None
_servo  = None

# ── Vosk state (loaded lazily in start()) ────────────────────────────────────
_model  = None
_rec    = None
_stream = None

# ── Listener thread state ────────────────────────────────────────────────────
_thread          = None
_stop_event      = threading.Event()
_callback        = None
_awaiting_cmd    = False
_last_trigger    = 0.0

TRIGGER_COOLDOWN = 1.0
WAKEWORDS        = ["robot", "robit", "row bot", "robe it", "robut"]

WORD_NUMBERS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4,
    "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
    "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
    "fourteen": 14, "fifteen": 15, "twenty": 20, "thirty": 30,
    "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70,
    "eighty": 80, "ninety": 90, "hundred": 100,
}

servo_angles = {0: 90, 1: 90, 2: 90, 3: 90, 4: 90, 5: 90}

COMMANDS = {
    "forward": "MOVE_FORWARD", "go forward": "MOVE_FORWARD",
    "move forward": "MOVE_FORWARD", "ahead": "MOVE_FORWARD",
    "back": "MOVE_BACK", "go back": "MOVE_BACK",
    "move back": "MOVE_BACK", "reverse": "MOVE_BACK",
    "motor left": "TURN_LEFT", "turn left": "TURN_LEFT",
    "motor right": "TURN_RIGHT", "turn right": "TURN_RIGHT",
    "motor stop": "STOP", "motor halt": "STOP",
    "shut down": "SHUTDOWN", "power down": "SHUTDOWN",
    "follow me": "FOLLOW_ME", "follow": "FOLLOW_ME",
    "dance": "DANCE", "lets dance": "DANCE",
    "spin": "SPIN", "lets spin": "SPIN",
    "light 1 on": "LED1_ON", "light one on": "LED1_ON",
    "lead one on": "LED1_ON", "lead 1 on": "LED1_ON",
    "light 2 on": "LED2_ON", "light two on": "LED2_ON",
    "lead to on": "LED2_ON", "lead 2 on": "LED2_ON",
    "light 1 off": "LED1_OFF", "light one off": "LED1_OFF",
    "lead one off": "LED1_OFF", "lead 1 off": "LED1_OFF",
    "light 2 off": "LED2_OFF", "light to off": "LED2_OFF",
    "lead to off": "LED2_OFF", "lead 2 off": "LED2_OFF",
    "servo 1 move": "SERVO1_MOVE", "servo one move": "SERVO1_MOVE",
    "servo 2 move": "SERVO2_MOVE", "servo to move": "SERVO2_MOVE",
    "servo 3 move": "SERVO3_MOVE", "servo three move": "SERVO3_MOVE",
    "servo 4 move": "SERVO4_MOVE", "servo four move": "SERVO4_MOVE",
}


# ── Public API ────────────────────────────────────────────────────────────────

def start(callback=None):
    """Load hardware + Vosk model and begin listening in a background thread."""
    global _motors, _led, _servo, _model, _rec, _stream, _thread, _callback

    _callback = callback
    _stop_event.clear()

    # ── Load Vosk model ───────────────────────────────────────────────────────
    from vosk import Model, KaldiRecognizer
    import sounddevice as sd

    if _model is None:
        print("[WAKEWORD] Loading Vosk model …")
        _model = Model("/home/jspinucci/vosk_model/vosk-model-small-en-us-0.15")
        _rec   = KaldiRecognizer(_model, 16000)
        print("[WAKEWORD] Model ready.")

    # ── Import hardware modules gracefully ────────────────────────────────────
    try:
        import motors as m
        _motors = m
    except Exception as e:
        print(f"[WAKEWORD] motors unavailable: {e}")

    try:
        import robot_led as l
        _led = l
    except Exception as e:
        print(f"[WAKEWORD] robot_led unavailable: {e}")

    try:
        import servomove as s
        _servo = s
        _center_all_servos()
    except Exception as e:
        print(f"[WAKEWORD] servomove unavailable: {e}")

    # ── Start audio stream ────────────────────────────────────────────────────
    _stream = sd.InputStream(samplerate=16000, channels=1, dtype='float32')
    _stream.start()

    # ── Start listener thread ─────────────────────────────────────────────────
    _thread = threading.Thread(target=_listen_loop, daemon=True, name="vosk-listener")
    _thread.start()
    print("[WAKEWORD] Listening for wake-word: 'Robot'")


def stop():
    """Stop the listener thread and audio stream."""
    _stop_event.set()
    if _stream:
        try:
            _stream.stop()
        except Exception:
            pass
    print("[WAKEWORD] Listener stopped.")


# ── Internal helpers ──────────────────────────────────────────────────────────

def _center_all_servos():
    for ch in range(6):
        servo_angles[ch] = 90
        _servo.set_servo_angle(ch, 90)


def _set_servo(channel, angle):
    angle = max(0, min(180, angle))
    servo_angles[channel] = angle
    if _servo:
        _servo.set_servo_angle(channel, angle)


def _move_servo(channel, delta):
    new_angle = max(0, min(180, servo_angles[channel] + delta))
    servo_angles[channel] = new_angle
    if _servo:
        _servo.set_servo_angle(channel, new_angle)
    print(f"[SERVO] Channel {channel} → {new_angle}°")


def _extract_number(text):
    words = text.lower().split()
    for w in words:
        if w in WORD_NUMBERS:
            return WORD_NUMBERS[w]
    if "minus" in words or "negative" in words:
        for w in words:
            if w.lstrip('-').isdigit():
                return -int(w)
    for w in words:
        cleaned = ''.join(c for c in w if c.isdigit() or c == '-')
        if cleaned.lstrip('-').isdigit():
            return int(cleaned)
    return None


def _execute_command(action, text):
    print(f"[CMD] '{text}' → {action}")

    if action == "MOVE_FORWARD":
        if _motors:
            _motors.motorA_forward(0.5)
            _motors.motorB_forward(0.5)

    elif action == "MOVE_BACK":
        if _motors:
            _motors.motorA_reverse(0.5)
            _motors.motorB_reverse(0.5)

    elif action == "TURN_LEFT":
        if _motors:
            _motors.motorA_forward(0.5)
            _motors.motorB_reverse(0.5)

    elif action == "TURN_RIGHT":
        if _motors:
            _motors.motorB_forward(0.5)
            _motors.motorA_reverse(0.5)

    elif action == "STOP":
        if _motors:
            _motors.motorA_forward(0.0)
            _motors.motorB_forward(0.0)

    elif action == "SHUTDOWN":
        if _motors:
            _motors.motorA_forward(0.0)
            _motors.motorB_forward(0.0)
        if _led:
            _led.led1_off()
            _led.led2_off()
        import subprocess
        subprocess.run(["sudo", "shutdown", "-h", "now"])

    elif action == "LED1_ON"  and _led: _led.led1_on()
    elif action == "LED1_OFF" and _led: _led.led1_off()
    elif action == "LED2_ON"  and _led: _led.led2_on()
    elif action == "LED2_OFF" and _led: _led.led2_off()

    elif action in ("SERVO1_MOVE", "SERVO2_MOVE", "SERVO3_MOVE", "SERVO4_MOVE"):
        ch = int(action[5]) - 1
        delta = _extract_number(text)
        if delta is not None:
            _move_servo(ch, delta)

    elif action in ("FOLLOW_ME", "DANCE", "SPIN"):
        print(f"[CMD] {action} not yet implemented")


def _listen_loop():
    global _awaiting_cmd, _last_trigger
    import numpy as np

    while not _stop_event.is_set():
        try:
            audio = _stream.read(4000)[0].flatten()
            pcm   = (audio * 32767).astype(np.int16).tobytes()

            if not _rec.AcceptWaveform(pcm):
                continue

            text = json.loads(_rec.Result()).get("text", "").lower().strip()
            if not text:
                continue

            print(f"[VOSK] {text}")
            now = time.time()

            if any(w in text for w in WAKEWORDS):
                if now - _last_trigger > TRIGGER_COOLDOWN:
                    _last_trigger  = now
                    _awaiting_cmd  = True
                    payload = "Wakeword 'robot' detected"
                    if _callback:
                        _callback(payload)
                    print("[WAKEWORD] Awaiting command …")

            elif _awaiting_cmd:
                matched = False
                for phrase, action in COMMANDS.items():
                    if phrase in text:
                        _execute_command(action, text)
                        matched       = True
                        _awaiting_cmd = False
                        if _callback:
                            _callback(f"Command executed: {action}")
                        break
                if not matched:
                    print(f"[WAKEWORD] No match: '{text}'")

        except Exception as e:
            if not _stop_event.is_set():
                print(f"[WAKEWORD ERROR] {e}")
