// ======================================================
// LOGGING OVERLAY (A-series debug panel)
// ======================================================

// Create floating debug panel
const logPanel = document.createElement("div");
logPanel.id = "logPanel";
logPanel.style.position = "fixed";
logPanel.style.bottom = "10px";
logPanel.style.right = "10px";
logPanel.style.width = "260px";
logPanel.style.maxHeight = "50vh";
logPanel.style.overflowY = "auto";
logPanel.style.background = "rgba(0,0,0,0.65)";
logPanel.style.color = "#00ffcc";
logPanel.style.fontSize = "12px";
logPanel.style.padding = "10px";
logPanel.style.borderRadius = "8px";
logPanel.style.zIndex = "9999";
logPanel.style.fontFamily = "monospace";
logPanel.style.pointerEvents = "none"; // never block joystick
document.body.appendChild(logPanel);

// Write text to panel

function logUpdate(obj) {
    obj.watchdogArmed = window.watchdogArmed ? "YES" : "NO";

    let out = "";
    for (const key in obj) {
        out += `${key}: ${obj[key]}\n`;
    }
    logPanel.textContent = out;
}


