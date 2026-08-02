let uiReady = false;
window.addEventListener("load", () => uiReady = true);

const lastAngles = {
    A: 90, B: 90, C: 90, D: 90, E: 90
};

// servos.js — slider control for servos A–G

function postJSON(url, data) {
    fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data)
    });
}

// -----------------------------
// ARM SERVOS A–E (0–180°)
// -----------------------------

["A", "B", "C", "D", "E"].forEach(name => {
    const slider = document.getElementById(`servo${name}`);
    if (!slider) return;

    let lastSent = 0;

    slider.addEventListener("input", function () {
        if (!uiReady) return;                  // ignore page-load phantom events
        if (this.dataset.ignore === "1") return;  // ignore Center Arm resets

        const angle = parseFloat(this.value);

        // Only send if the value actually changed
        if (angle === lastAngles[name]) return;
        lastAngles[name] = angle;

        const now = Date.now();
        if (now - lastSent < 120) return;      // debounce
        lastSent = now;

        postJSON("/api/servo/arm", { name: name, angle: angle });
    });
});


// -----------------------------
// PAN/TILT SERVOS F & G
// F = pan  (-90 to +90)
// G = tilt (-45 to +45)
// -----------------------------

// Servo F (Pan)
const servoF = document.getElementById("servoF");
if (servoF) {
    servoF.addEventListener("input", function () {
        const pan = parseFloat(this.value);
        if (!uiReady) return;
        postJSON("/api/servo/pan", { pan: parseFloat(this.value) });
    });
}

// Servo G (Tilt)
const servoG = document.getElementById("servoG");
if (servoG) {
    servoG.addEventListener("input", function () {
        const tilt = parseFloat(this.value);
        if (!uiReady) return;
        postJSON("/api/servo/tilt", { tilt: parseFloat(this.value) });
    });
}
