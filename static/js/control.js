// ======================================================
// A-SERIES CONTROL PIPELINE (A1 → A9)
// Clean, stable, hardware-independent
// ======================================================


window.debugMode = true;

function jsControl(msg) {
    fetch("/js_debug", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ctl_message: msg })
    });
}


// =========================
// A1 DEADZONE + MIN TORQUE
// =========================

function applyDeadzone(v) {
    return Math.abs(v) < CONFIG.deadzone ? 0 : v;
}

function applyMinTorque(v) {
    return v === 0 ? 0 : Math.sign(v) * CONFIG.minTorque;
}

// =========================
// A2 SMOOTHING
// =========================

let smoothDrive = 0;
let smoothTurn = 0;

function smoothStep(current, target) {
    return current + (target - current) * CONFIG.smoothingAccel;
}

// =========================
// A3 EXPONENTIAL STEERING CURVE
// =========================

function expoCurve(v) {
    return v * v * v;
}

// =========================
// A4 DUAL-RATE STEERING
// =========================

function dualRateSteer(x) {
    const low = expoCurve(x);
    const high = x;
    const blend = Math.abs(x);
    return low * (1 - blend) + high * blend;
}

// =========================
// A5 NONLINEAR THROTTLE CURVE
// =========================

function throttleCurve(y) {
    return y * (0.6 + CONFIG.throttleCurveStrength * Math.abs(y));
}

// =========================
// A6 TRACTION CONTROL
// =========================

function tractionControl(left, right) {
    const slipLimit = CONFIG.slipLimit;
    const diff = left - right;

    if (Math.abs(diff) > slipLimit) {
        if (diff > 0) {
            left -= (diff - slipLimit);
        } else {
            right -= (-diff - slipLimit);
        }
    }

    return { left, right };
}

// =========================
// A7 DYNAMIC TURN COMPENSATION
// =========================

function dynamicTurnCompensation(drive, turn) {
    const k = CONFIG.turnCompStrength;
    const scale = 1 - k * Math.abs(drive);
    return { drive, turn: turn * scale };
}

// =========================
// A8 ADAPTIVE TORQUE BIAS
// =========================

function adaptiveTorqueBias(drive, turn) {
    const maxTurn = CONFIG.maxTurn;
    const k = CONFIG.torqueBiasStrength;
    const bias = k * (turn / maxTurn) * (1 - Math.abs(drive));
    return { drive, turn, bias };
}

// =========================
// A9 INERTIA SIMULATION
// =========================

let inertiaDrive = 0;
let inertiaTurn = 0;

function inertiaSim(drive, turn) {
    const mass = CONFIG.inertiaMass;
    const drag = CONFIG.inertiaDrag;

    inertiaDrive = inertiaDrive * (1 - drag) + drive * mass;
    inertiaTurn  = inertiaTurn  * (1 - drag) + turn  * mass;

    return { drive: inertiaDrive, turn: inertiaTurn };
}

// ======================================================
// TANK DRIVE JOYSTICK (A1 → A9)
// ======================================================

const tankJoy = new Joystick("tankJoy", "tankStick", (x, y) => {
    if (!tankJoy.active) return;

    safetyHeartbeat();

    // A1: Deadzone + Min Torque
    let dx = applyDeadzone(x);
    let dy = applyDeadzone(y);

    dx = applyMinTorque(dx);
    dy = applyMinTorque(dy);

    // A2 smoothing (applied to raw dx/dy)
    smoothDrive = smoothStep(smoothDrive, dy);
    smoothTurn  = smoothStep(smoothTurn, dx);

    // A3/A4/A5 steering + throttle curves
    const curvedTurn  = dualRateSteer(smoothTurn);
    const curvedDrive = throttleCurve(smoothDrive);

    // A7 dynamic turn compensation
    const dtc = dynamicTurnCompensation(curvedDrive, curvedTurn);

    // A8 adaptive torque bias
    const atb = adaptiveTorqueBias(dtc.drive, dtc.turn);

    let drive = atb.drive;
    let turn  = atb.turn;

    drive *= (1 + atb.bias);
    turn  *= (1 - atb.bias);

    // A9 inertia simulation
    const inertia = inertiaSim(drive, turn);

    // Final motor mixing (correct place)
    let left  = inertia.drive + inertia.turn;
    let right = inertia.drive - inertia.turn;

    // A6 traction control (correct place)
    const tc = tractionControl(left, right);


    logUpdate({
        dx: dx.toFixed(3),
        dy: dy.toFixed(3),
        smoothDrive: smoothDrive.toFixed(3),
        smoothTurn: smoothTurn.toFixed(3),
        curvedDrive: curvedDrive.toFixed(3),
        curvedTurn: curvedTurn.toFixed(3),
        dtcDrive: dtc.drive.toFixed(3),
        dtcTurn: dtc.turn.toFixed(3),
        bias: atb.bias.toFixed(3),
        inertiaDrive: inertia.drive.toFixed(3),
        inertiaTurn: inertia.turn.toFixed(3),
        left: left.toFixed(3),
        right: right.toFixed(3)
    });

    safetyFetch("/api/motors/incremental", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            left: tc.left,
            right: tc.right
        })
    });
});

// ======================================================
// CAMERA PAN/TILT JOYSTICK
// ======================================================

const camJoy = new Joystick("camJoy", "camStick", (x, y) => {
    fetch("/api/servos/pantilt_incremental", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            dx: x * 30.0,
            dy: y * 30.0
        })
    });
});

// ======================================================
// CAMERA FEED
// ======================================================

document.getElementById("cameraFeed").src = "/video_feed";

// ======================================================
// BUTTONS
// ======================================================

function stopTank() {
    fetch("/api/motors/stop", { method: "POST" });
    if(window.debugMode) jsControl("Stop Tank FIRED");
    tankJoy.reset();
}

function centerCamera() {
    fetch("/api/servos/camera_center", { method: "POST" });

    if(window.debugMode) jsControl("Camera Center FIRED");
    console.log("Camera Center FIRED");
    camJoy.reset();

    const f = document.getElementById("servoF");
    const g = document.getElementById("servoG");

    if (f) {
        f.value = 0;
        f.dispatchEvent(new Event("input"));
    }
    if (g) {
        g.value = 0;
        g.dispatchEvent(new Event("input"));
    }
}

function centerArm() {
    fetch("/api/servos/center_arm", { method: "POST" });
    if(window.debugMode) jsControl("Center Arm FIRED");

    ["A", "B", "C", "D", "E"].forEach(name => {
        const slider = document.getElementById(`servo${name}`);
        if (!slider) return;

        slider.dataset.ignore = "1";
        slider.value = 90;
        lastAngles[name] = 90;
        slider.dispatchEvent(new Event("input"));
        slider.dataset.ignore = "0";
    });
}

window.addEventListener("load", () => {
    tankJoy.reset();
});
