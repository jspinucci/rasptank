// ======================================================
// SAFETY SYSTEM (watchdog, disconnect protection, failsafe)
// ======================================================

// Last time a joystick command was sent
let motorsAreStopped = true;
let lastCommandTime = Date.now();
window.watchdogArmed = false;  // watchdog disarmed when motors stop

// Watchdog interval (checks every 250ms)

setInterval(() => {
    const now = Date.now();
    const elapsed = now - lastCommandTime;

    // watchdog only fires when motors are active
    if (!motorsAreStopped && elapsed > 2000) {
        emergencyStop();
    }

    // keep indicator updated
    window.watchdogArmed = !motorsAreStopped;
}, 250);


// Called by control.js whenever a joystick command is sent
function safetyHeartbeat() {
    lastCommandTime = Date.now();
    motorsAreStopped = false;
    window.watchdogArmed = true;

}

// HARD STOP — guaranteed motor shutdown

function emergencyStop() {
    if (!motorsAreStopped) {
        fetch("/api/motors/stop", { method: "POST" })
            .catch(() => {});
        motorsAreStopped = true;
    }

    if (typeof tankJoy !== "undefined") {
        tankJoy.reset();
    }
}


// Stop motors if the page unloads (refresh, close, navigate)
window.addEventListener("beforeunload", () => {
    emergencyStop();
});

// Stop motors if browser loses focus (optional but recommended)
window.addEventListener("blur", () => {
    emergencyStop();
});

// Stop motors if backend fetch fails
function safetyFetch(url, options) {
    return fetch(url, options).catch(() => {
        emergencyStop();
    });
}
