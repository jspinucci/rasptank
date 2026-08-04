// =========================
// TANK DRIVE JOYSTICK (SCALED)
// =========================
const tankJoy = new Joystick("tankJoy", "tankStick", (x, y) => {
    fetch("/api/motors/incremental", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            drive: y * 4.0,   // scaled forward/back
            turn: x * 4.0     // scaled left/right
        })
    });
});

// =========================
// CAMERA PAN/TILT JOYSTICK (SCALED + CORRECT FIELD NAMES)
// =========================
const camJoy = new Joystick("camJoy", "camStick", (x, y) => {
    fetch("/api/servos/pantilt_incremental", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            dx: x * 30.0,   // scaled pan
            dy: y * 30.0   // scaled tilt
        })
    });
});


// =========================
// CAMERA FEED
// =========================
document.getElementById("cameraFeed").src = "/video_feed";

// =========================
// BUTTONS
// =========================
function stopTank() {
    fetch("/api/motors/stop", { method: "POST" });

    tankJoy.reset();  // reset joystick visually
}

// Center camera servos AND F/G sliders
function centerCamera() {
    // Center via backend (pan/tilt neutral)
    fetch("/api/servos/camera_center", { method: "POST" });

    // Reset sliders visually
    const f = document.getElementById("servoF");
    const g = document.getElementById("servoG");

    camJoy.reset();  // reset joystick visually

    if (f) {
        f.value = 0;
        f.dispatchEvent(new Event("input"));   // triggers servos.js handler
    }
    if (g) {
        g.value = 0;
        g.dispatchEvent(new Event("input"));   // triggers servos.js handler
    }
}

function centerArm() {
    fetch("/api/servos/center_arm", { method: "POST" });

    ["A", "B", "C", "D", "E"].forEach(name => {
        const slider = document.getElementById(`servo${name}`);
        if (!slider) return;

        slider.dataset.ignore = "1";   // prevent phantom input
        slider.value = 90;
        lastAngles[name] = 90;         // sync internal state
        slider.dispatchEvent(new Event("input"));
        slider.dataset.ignore = "0";
    });
}



