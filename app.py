#!/usr/bin/env python3
"""
RaspTank Control System - Flask application entry point.
Serves the web UI and exposes REST + SSE endpoints for
motor, servo, camera and wakeword control.
"""

import threading
import time
import cv2
import numpy as np
import logging
from flask import (
    Flask, render_template, request,
    jsonify, Response, stream_with_context
)

from robot.motors import MotorController
from robot.servos import ServoController
from robot.camera import CameraStream
from robot.wakeword import WakewordBridge

from robot.servos import ServoController, ArmServoController

import signal
import sys

import board
import busio
import adafruit_ssd1306
from PIL import Image, ImageDraw, ImageFont

from leds import LEDController

import os

# -----------------------------
# GLOBAL CAMERA + RECORDING STATE
# -----------------------------
camera = None
recording = False
video_writer = None
recording_thread = None
stop_recording_flag = False

# Recording resolution (Option B)
REC_WIDTH = 640
REC_HEIGHT = 480
REC_FPS = 30

# -----------------------------
# INITIALIZATION
# -----------------------------
ffmpeg_proc = None  # no longer used
leds = LEDController()

i2c = busio.I2C(board.SCL, board.SDA)
oled = adafruit_ssd1306.SSD1306_I2C(128, 64, i2c)
font = ImageFont.load_default()

logging.basicConfig(level=logging.INFO)

armservos: ArmServoController | None = None

# Incremental control state
current_pan = 0.0
current_tilt = 0.0

current_speed = 0.0
current_turn = 0.0
motors_enabled = True

PAN_SPEED = 3.0
TILT_SPEED = 3.0
DRIVE_SPEED = 0.03
TURN_SPEED = 0.03

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("rasptank.app")

# LED startup animation
logging.info("Running startup LED animation...")
leds.set_mode("motor_forward")
time.sleep(2)
leds.set_mode("arm_motion")
time.sleep(2)
leds.set_mode("start_pantilt_motion")
time.sleep(2)
leds.set_mode("idle")

# -----------------------------
# SERVO SMOOTHING
# -----------------------------
last_update = {
    "A": 0, "B": 0, "C": 0, "D": 0, "E": 0,
    "PAN": 0, "TILT": 0
}

ARM_STEP = 6
PAN_STEP = 6
TILT_STEP = 6
RATE_LIMIT = 0.01

def smooth_servo(channel_name, current_angle, target_angle, step):
    now = time.time()

    if now - last_update[channel_name] < RATE_LIMIT:
        return current_angle

    last_update[channel_name] = now

    if current_angle is None:
        return target_angle

    if abs(target_angle - current_angle) <= step:
        return target_angle

    if target_angle > current_angle:
        return current_angle + step
    else:
        return current_angle - step

# -----------------------------
# OLED FACE
# -----------------------------
def draw_robot_face(eye_dx=0, eye_dy=0, blink=False):
    image = Image.new("1", (128, 64))
    draw = ImageDraw.Draw(image)

    left_eye_center = (40, 32)
    right_eye_center = (88, 32)
    eye_radius = 18
    pupil_radius = 6

    if blink:
        draw.line((left_eye_center[0] - eye_radius,
                   left_eye_center[1],
                   left_eye_center[0] + eye_radius,
                   left_eye_center[1]), fill=255, width=3)

        draw.line((right_eye_center[0] - eye_radius,
                   right_eye_center[1],
                   right_eye_center[0] + eye_radius,
                   right_eye_center[1]), fill=255, width=3)
    else:
        draw.ellipse((left_eye_center[0] - eye_radius,
                      left_eye_center[1] - eye_radius,
                      left_eye_center[0] + eye_radius,
                      left_eye_center[1] + eye_radius), outline=255)

        draw.ellipse((right_eye_center[0] - eye_radius,
                      right_eye_center[1] - eye_radius,
                      right_eye_center[0] + eye_radius,
                      right_eye_center[1] + eye_radius), outline=255)

        lx = left_eye_center[0] + eye_dx
        ly = left_eye_center[1] + eye_dy
        rx = right_eye_center[0] + eye_dx
        ry = right_eye_center[1] + eye_dy

        draw.ellipse((lx - pupil_radius, ly - pupil_radius,
                      lx + pupil_radius, ly + pupil_radius), fill=255)

        draw.ellipse((rx - pupil_radius, ry - pupil_radius,
                      rx + pupil_radius, ry + pupil_radius), fill=255)

    oled.image(image)
    oled.show()

draw_robot_face(eye_dx=5)

# -----------------------------
# FLASK APP
# -----------------------------
app = Flask(__name__)

motors: MotorController | None = None
servos: ServoController | None = None
wakeword: WakewordBridge | None = None

_hw_lock = threading.Lock()

def get_motors() -> MotorController:
    global motors
    with _hw_lock:
        if motors is None:
            motors = MotorController()
    return motors

def get_servos() -> ServoController:
    global servos
    with _hw_lock:
        if servos is None:
            servos = ServoController()
    return servos

def get_camera() -> CameraStream:
    global camera
    with _hw_lock:
        if camera is None:
            camera = CameraStream(device="/dev/video0")
        elif not camera.is_alive():
            camera.release()
            camera = CameraStream(device="/dev/video0")
    return camera

def get_wakeword() -> WakewordBridge:
    global wakeword
    with _hw_lock:
        if wakeword is None:
            wakeword = WakewordBridge()
    return wakeword

def get_armservos() -> ArmServoController:
    global armservos
    with _hw_lock:
        if armservos is None:
            armservos = ArmServoController()
    return armservos

# -----------------------------
# ROUTES
# -----------------------------
@app.route("/")
def index():
    return render_template("control.html")

# -----------------------------
# LIVE VIDEO FEED (CameraStream)
# -----------------------------
@app.route('/video_feed')
def video_feed():
    cam = get_camera()

    def gen():
        for frame in cam.frames():
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

    return Response(gen(), mimetype='multipart/x-mixed-replace; boundary=frame')

# -----------------------------
# SNAPSHOT (CameraStream)
# -----------------------------
@app.route("/snapshot")
def snapshot():
    try:
        cam = get_camera()
        frame = next(cam.frames())

        filename = f"images/snapshot_{int(time.time())}.jpg"
        with open(filename, "wb") as f:
            f.write(frame)

        print("Snapshot saved:", filename)
        leds.set_mode("idle")
        logging.info("Camera mode: Snapshot")
        return Response(frame, mimetype="image/jpeg")

    except Exception as exc:
        return f"Snapshot failed: {exc}", 500

# -----------------------------
# RECORDING THREAD (OpenCV VideoWriter)
# -----------------------------

def recording_worker(filename):
    global video_writer, stop_recording_flag

    cam = get_camera()

    while not stop_recording_flag:
        try:
            # Get JPEG frame from CameraStream
            jpeg_bytes = next(cam.frames())

            # Decode JPEG → BGR
            np_arr = np.frombuffer(jpeg_bytes, np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

            if frame is None:
                continue

            # Resize to recording resolution
            resized = cv2.resize(frame, (REC_WIDTH, REC_HEIGHT))

            # Write to AVI
            video_writer.write(resized)

        except Exception:
            break

    video_writer.release()
    video_writer = None

# -----------------------------
# START RECORDING
# -----------------------------
@app.route("/start_recording")
def start_recording():
    global recording, video_writer, recording_thread, stop_recording_flag

    if recording:
        return {"ok": False, "error": "Already recording"}

    filename = f"recordings/recording_{int(time.time())}.avi"

    # OpenCV VideoWriter
    fourcc = cv2.VideoWriter_fourcc(*"MJPG")
    video_writer = cv2.VideoWriter(filename, fourcc, REC_FPS, (REC_WIDTH, REC_HEIGHT))

    stop_recording_flag = False
    recording_thread = threading.Thread(target=recording_worker, args=(filename,))
    recording_thread.start()

    recording = True
    print("Recording started:", filename)
    return {"ok": True, "file": filename}

# -----------------------------
# STOP RECORDING
# -----------------------------
@app.route("/stop_recording")
def stop_recording():
    global recording, stop_recording_flag, recording_thread

    if not recording:
        return {"ok": False, "error": "Not recording"}

    stop_recording_flag = True
    recording_thread.join()

    recording = False
    print("Recording stopped")
    return {"ok": True}

# -----------------------------
# SERVO + MOTOR ROUTES (unchanged)
# -----------------------------
@app.route("/api/servos/pantilt", methods=["POST"])
def servos_pantilt():
    data = request.get_json(force=True, silent=True) or {}
    pan = float(data.get("pan", 0.0))
    tilt = float(data.get("tilt", 0.0))

    servos = get_servos()

    current_pan = servos._pan_deg
    current_tilt = servos._tilt_deg

    new_pan = smooth_servo("PAN", current_pan, pan, PAN_STEP)
    new_tilt = smooth_servo("TILT", current_tilt, tilt, TILT_STEP)

    servos.set_pan_tilt(new_pan, new_tilt)
    draw_robot_face(eye_dx=int(new_pan / 10))

    return jsonify({"ok": True, "pan": new_pan, "tilt": new_tilt})

@app.route("/api/servos/arm", methods=["POST"])
def servos_arm():
    data = request.get_json(force=True, silent=True) or {}

    try:
        arm = get_armservos()

        for name in ["A", "B", "C", "D", "E"]:
            if name in data:
                target = float(data[name])
                ch = arm.ARM_CHANNELS[name]

                current = arm.kit.servo[ch].angle
                new_angle = smooth_servo(name, current, target, ARM_STEP)

                if name == 'E':
                    new_angle = max(50, min(100, new_angle)) 
                arm.set_servo(name, new_angle)
                logging.info("Servo mode: api/servo/arm_2")
                draw_robot_face(eye_dx=5)

        return jsonify({"ok": True, **data})

    except Exception as exc:
        log.error("servos_arm error: %s", exc)
        return jsonify({"ok": False, "error": str(exc)}), 500




@app.route("/api/motors/stop", methods=["POST"])
def motors_stop():
    global current_speed, current_turn, motors_enabled

    current_speed = 0.0
    current_turn = 0.0
    motors_enabled = False
    try:
        get_motors().stop()
        draw_robot_face()
        leds.set_mode("idle")
        logging.info("LED mode: real_motor_stop")
        return jsonify({"ok": True})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500

"""
    Doesn't work

@app.route("/api/motors/incremental", methods=["POST"])
def motors_incremental():
    global current_speed, current_turn, motors_enabled

    print("=== RAW REQUEST BODY ===")
    print(request.data)

    data = request.get_json(force=True, silent=True) or {}

    ui_left  = float(data.get("left", 0.0))
    ui_right = float(data.get("right", 0.0))

    # Strong deadband to eliminate joystick noise
    deadband = 0.08
    if abs(ui_left) < deadband:
        ui_left = 0.0
    if abs(ui_right) < deadband:
        ui_right = 0.0

    # If joystick is centered → STOP and disable motors
    if ui_left == 0.0 and ui_right == 0.0:
        current_speed = 0.0
        current_turn  = 0.0
        motors_enabled = False
        get_motors().stop()
        logging.info("MOTOR mode: incremental_motor_stop")
        return jsonify({"ok": True, "left": 0.0, "right": 0.0})

    # If motors are disabled (STOP was pressed), ignore movement
    if not motors_enabled:
        current_speed = 0.0
        current_turn  = 0.0
        get_motors().stop()
        logging.info("MOTOR mode: disabled_stop")
        return jsonify({"ok": True, "left": 0.0, "right": 0.0})

    # Joystick moved significantly → re-enable motors
    motors_enabled = True

    # Incremental drive/turn math
    drive = (ui_left + ui_right) / 2.0
    turn  = (ui_left - ui_right) / 2.0

    current_speed += drive * TURN_SPEED
    current_turn  += turn  * TURN_SPEED

    current_speed = max(-1.0, min(1.0, current_speed))
    current_turn  = max(-1.0, min(1.0, current_turn))

    left  = current_speed + current_turn
    right = current_speed - current_turn

    left  = max(-1.0, min(1.0, left))
    right = max(-1.0, min(1.0, right))

    try:
        get_motors().set_speed(left, right)
        logging.info(f"[MOTOR DEBUG] left={left:.3f}, right={right:.3f}")
        return jsonify({"ok": True, "left": left, "right": right})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


"""

"""
       
       Worked but creeped 
       
@app.route("/api/motors/incremental", methods=["POST"])
def motors_incremental():
    global current_speed, current_turn, motors_enabled

    print("=== RAW REQUEST BODY ===")
    print(request.data)

    data = request.get_json(force=True, silent=True) or {}

    ui_left  = float(data.get("left", 0.0))
    ui_right = float(data.get("right", 0.0))

    # Deadband: treat tiny values as zero
    if abs(ui_left) < 0.02:
        ui_left = 0.0
    if abs(ui_right) < 0.02:
        ui_right = 0.0

    # If joystick is centered, just keep motors stopped and reset integrator
    if ui_left == 0.0 and ui_right == 0.0:
        current_speed = 0.0
        current_turn  = 0.0
        get_motors().stop()
        logging.info("MOTOR mode: incremental_motor_stop")
        return jsonify({"ok": True, "left": 0.0, "right": 0.0})

    # Joystick moved → re‑enable motors
    motors_enabled = True

    if not motors_enabled:
        # Safety: if somehow disabled, force stop
        current_speed = 0.0
        current_turn  = 0.0
        get_motors().stop()
        logging.info("MOTOR mode: disabled_stop")
        return jsonify({"ok": True, "left": 0.0, "right": 0.0})

    drive = (ui_left + ui_right) / 2.0
    turn  = (ui_left - ui_right) / 2.0

    current_speed += drive * TURN_SPEED
    current_turn  += turn  * TURN_SPEED

    current_speed = max(-1.0, min(1.0, current_speed))
    current_turn  = max(-1.0, min(1.0, current_turn))

    left  = current_speed + current_turn
    right = current_speed - current_turn

    left  = max(-1.0, min(1.0, left))
    right = max(-1.0, min(1.0, right))

    try:
        get_motors().set_speed(left, right)
        logging.info(f"[MOTOR DEBUG] left={left:.3f}, right={right:.3f}")
        return jsonify({"ok": True, "left": left, "right": right})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500

"""

"""
            worked, still creeps
      
@app.route("/api/motors/incremental", methods=["POST"])
def motors_incremental():
    global current_speed, current_turn, motors_enabled

    print("=== RAW REQUEST BODY ===")
    print(request.data)

    data = request.get_json(force=True, silent=True) or {}

    ui_left  = float(data.get("left", 0.0))
    ui_right = float(data.get("right", 0.0))

    # Strong deadband to eliminate joystick noise
    deadband = 0.20
    if abs(ui_left) < deadband:
        ui_left = 0.0
    if abs(ui_right) < deadband:
        ui_right = 0.0

    # If joystick is centered → STOP and disable motors
    if ui_left == 0.0 and ui_right == 0.0:
        current_speed = 0.0
        current_turn  = 0.0
        motors_enabled = False
        get_motors().stop()
        logging.info("MOTOR mode: incremental_motor_stop")
        return jsonify({"ok": True, "left": 0.0, "right": 0.0})

    # If motors are disabled (STOP was pressed), only re-enable
    # when joystick moves significantly (not noise)
    if not motors_enabled:
        # Joystick moved significantly → re-enable motors
        motors_enabled = True
        current_speed = 0.0
        current_turn  = 0.0
        logging.info("MOTOR mode: motors_reenabled")

    # Incremental drive/turn math
    drive = (ui_left + ui_right) / 2.0
    turn  = (ui_left - ui_right) / 2.0

    current_speed += drive * TURN_SPEED
    current_turn  += turn  * TURN_SPEED

    current_speed = max(-1.0, min(1.0, current_speed))
    current_turn  = max(-1.0, min(1.0, current_turn))

    left  = current_speed + current_turn
    right = current_speed - current_turn

    left  = max(-1.0, min(1.0, left))
    right = max(-1.0, min(1.0, right))

    try:
        get_motors().set_speed(left, right)
        logging.info(f"[MOTOR DEBUG] left={left:.3f}, right={right:.3f}")
        return jsonify({"ok": True, "left": left, "right": right})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500

"""


@app.route("/api/motors/incremental", methods=["POST"])
def motors_incremental():
    print("=== RAW REQUEST BODY ===")
    print(request.data)

    data = request.get_json(force=True, silent=True) or {}

    ui_left  = float(data.get("left", 0.0))
    ui_right = float(data.get("right", 0.0))

    # Strong deadband to eliminate joystick drift
    deadband = 0.20
    if abs(ui_left) < deadband:
        ui_left = 0.0
    if abs(ui_right) < deadband:
        ui_right = 0.0

    # If joystick centered → STOP
    if ui_left == 0.0 and ui_right == 0.0:
        get_motors().stop()
        logging.info("MOTOR mode: incremental_motor_stop")
        return jsonify({"ok": True, "left": 0.0, "right": 0.0})

    # Direct mapping (NO accumulation)
    left  = max(-1.0, min(1.0, ui_left))
    right = max(-1.0, min(1.0, ui_right))

    try:
        get_motors().set_speed(left, right)
        logging.info(f"[MOTOR DEBUG] left={left:.3f}, right={right:.3f}")
        return jsonify({"ok": True, "left": left, "right": right})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500



"""

@app.route("/api/motors/incremental", methods=["POST"])
def motors_incremental():
    print("=== RAW REQUEST BODY ===")
    print(request.data)

    data = request.get_json(force=True, silent=True) or {}

    ui_left  = float(data.get("left", 0.0))
    ui_right = float(data.get("right", 0.0))

    # Strong deadband to eliminate joystick noise
    deadband = 0.20
    if abs(ui_left) < deadband:
        ui_left = 0.0
    if abs(ui_right) < deadband:
        ui_right = 0.0

    # If joystick is centered → STOP
    if ui_left == 0.0 and ui_right == 0.0:
        get_motors().stop()
        logging.info("MOTOR mode: incremental_motor_stop")
        return jsonify({"ok": True, "left": 0.0, "right": 0.0})

    # NO INTEGRATOR — direct mapping
    drive = (ui_left + ui_right) / 2.0
    turn  = (ui_left - ui_right) / 2.0

    left  = drive + turn
    right = drive - turn

    # Clamp
    left  = max(-1.0, min(1.0, left))
    right = max(-1.0, min(1.0, right))

    try:
        get_motors().set_speed(left, right)
        logging.info(f"[MOTOR DEBUG] left={left:.3f}, right={right:.3f}")
        return jsonify({"ok": True, "left": left, "right": right})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500
"""

@app.route("/api/servos/pantilt_incremental", methods=["POST"])
def servos_pantilt_incremental():
    global current_pan, current_tilt

    data = request.get_json(force=True, silent=True) or {}
    dx = float(data.get("dx", 0.0))
    dy = float(data.get("dy", 0.0))

    # Joystick released → dx=0, dy=0 → STOP
    if dx == 0.0 and dy == 0.0:
        leds.set_mode("idle")
        logging.info("LED mode: idle (joystick end)")
        return jsonify({"ok": True, "pan": current_pan, "tilt": current_tilt})

    # Joystick moving
    leds.set_mode("pantilt_motion")

    current_pan += dx * PAN_SPEED
    current_tilt += dy * TILT_SPEED

    current_pan = max(-90, min(90, current_pan))
    current_tilt = max(-45, min(45, current_tilt))

    try:
        get_servos().set_pan_tilt(current_pan, current_tilt)
        logging.info(f"pantilt_incremental dx={dx} dy={dy}")
        return jsonify({"ok": True, "pan": current_pan, "tilt": current_tilt})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500

@app.route("/api/servos/camera_center", methods=["POST"])
def servos_center_camera():
    global current_pan, current_tilt
    current_pan = 0.0
    current_tilt = 0.0

    try:
        get_servos().center()
        draw_robot_face(eye_dx=-7)
        logging.info("LED mode: camera_center")
        leds.set_mode("idle")
        draw_robot_face()
        return jsonify({"ok": True})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500

@app.route("/api/servos/center_arm", methods=["POST"])
def servos_center_arm():
    try:
        get_armservos().center()
        draw_robot_face(eye_dx=-8)
        logging.info("LED mode: arm_center")
        leds.set_mode("idle")
        draw_robot_face()
        return jsonify({"ok": True})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500

@app.route("/api/servo/arm", methods=["POST"])
def api_servo_arm():
    data = request.get_json()
    name = data.get("name")
    angle = float(data.get("angle", 90))
    arm = get_armservos()
    if name == 'E':
        angle = max(70, min(110, angle)) 
    arm.set_servo(name, angle)
    draw_robot_face(eye_dx=10)
    logging.info("Servo mode: api_servo_arm_1")
    leds.set_mode("arm_motion")
    return jsonify({"status": "ok", "servo": name, "angle": angle})

@app.route("/api/wakeword/status", methods=["GET"])
def wakeword_status():
    try:
        state = get_wakeword().status()
        return jsonify({"ok 5": True, **state})
    except Exception as exc:
        log.error("wakeword_status error: %s", exc)
        return jsonify({"ok": False, "error": str(exc)}), 500

@app.route("/api/servos/center", methods=["POST"])
def servos_center():
    global current_pan, current_tilt
    current_pan = 0.0
    current_tilt = 0.0

    try:
        get_servos().center()
        get_armservos().center()
        return jsonify({"ok": True})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500

@app.route("/api/wakeword/start", methods=["POST"])
def wakeword_start():
    try:
        get_wakeword().start()
        return jsonify({"ok": True, "listening": True})
    except Exception as exc:
        log.error("wakeword_start error: %s", exc)
        return jsonify({"ok": False, "error": str(exc)}), 500

@app.route("/api/wakeword/stop", methods=["POST"])
def wakeword_stop():
    try:
        get_wakeword().stop()
        return jsonify({"ok": True, "listening": False})
    except Exception as exc:
        log.error("wakeword_stop error: %s", exc)
        return jsonify({"ok": False, "error": str(exc)}), 500

@app.route("/api/wakeword/events")
def wakeword_events():
    def event_stream():
        bridge = get_wakeword()
        while True:
            event = bridge.next_event(timeout=1.0)
            if event:
                yield f"data: {event}\n\n"
            else:
                yield ": ping\n\n"
    return Response(
        stream_with_context(event_stream()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

panTilt = ServoController()
arm = ArmServoController()

@app.route("/api/servo/pan", methods=["POST"])
def api_servo_pan():
    data = request.get_json()
    pan = float(data.get("pan", 0))
    panTilt.set_pan(pan)
    leds.set_mode("pan_motion")
    logging.info("LED mode: pan_motion")
    draw_robot_face(eye_dx=-5)
    return jsonify({"status": "ok", "pan": pan})

@app.route("/api/servo/tilt", methods=["POST"])
def api_servo_tilt():
    data = request.get_json()
    tilt = float(data.get("tilt", 0))
    panTilt.set_tilt(tilt)
    leds.set_mode("tilt_motion")
    logging.info("LED mode: tilt_motion")
    draw_robot_face(eye_dx=-5)
    return jsonify({"status": "ok", "tilt": tilt})

@app.route('/js_debug', methods=['POST'])
def js_debug():
    data = request.json
    print("JS DEBUG:", data)
    return "OK"

@app.route("/api/ping")
def ping():
    return jsonify({"ok": True, "ts": time.time()})

def handle_sigint(signum, frame):
    print("SIGINT received, releasing camera...")

    global camera
    try:
        if camera is not None:
            camera.release()
            camera = None
            print("Camera released cleanly.")
    except Exception as e:
        print(f"Camera release error: {e}")

    sys.exit(0)

signal.signal(signal.SIGINT, handle_sigint)

if __name__ == "__main__":
    log.info("Starting RaspTank control server on 0.0.0.0:5000")
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)

