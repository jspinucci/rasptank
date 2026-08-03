
// static/js/servos.js

// Single Socket.IO connection for servo-related control
const socket = io();

// -----------------------------
// PAN / TILT CONTROL (real-time)
// -----------------------------

let pan = 0.0;
let tilt = 0.0;

// Absolute pan/tilt setter (e.g. from sliders)
function setPanTilt(newPan, newTilt) {
    pan  = parseFloat(newPan);
    tilt = parseFloat(newTilt);

    socket.emit("pantilt", { pan, tilt });
}

// Incremental pan/tilt (e.g. from joystick or buttons)
function panTiltIncrement(dx, dy) {
    socket.emit("pantilt_incremental", {
        dx: parseFloat(dx),
        dy: parseFloat(dy),
    });
}

// Example hook for UI sliders:
// <input type="range" oninput="onPanSlider(this.value)" ...>
// <input type="range" oninput="onTiltSlider(this.value)" ...>
function onPanSlider(value) {
    setPanTilt(value, tilt);
}

function onTiltSlider(value) {
    setPanTilt(pan, value);
}


// -----------------------------
// ARM SERVOS A–E (real-time)
// -----------------------------

// Send absolute positions for arm servos A–E
// Example: setArmServos({ A: 90, B: 120, E: 80 });
function setArmServos(angles) {
    socket.emit("arm", angles);
}

// Called by individual servo sliders
// name: "A", "B", "C", "D", or "E"
// value: angle in degrees
function onServoSliderChange(name, value) {
    const angle = parseFloat(value);
    const payload = {};
    payload[name] = angle;
    socket.emit("arm", payload);
}


// -----------------------------
// OPTIONAL: Listen for state / errors
// -----------------------------

socket.on("pantilt_state", (state) => {
    // If you later emit pantilt_state from server, you can sync UI here.
    // console.log("PanTilt state:", state);
});

socket.on("arm_state", (state) => {
    // If you later emit arm_state from server, you can sync UI here.
    // console.log("Arm state:", state);
});

socket.on("error", (err) => {
    console.error("Servo/WebSocket error:", err);
});
