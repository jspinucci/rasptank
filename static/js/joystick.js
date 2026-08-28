// joystick.js — drift‑proof joystick implementation

window.debugMode = true;

function jsDebug(msg) {
    fetch("/js_debug", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: msg })
    });
}

class Joystick {
    constructor(containerId, stickId, callback) {
        this.container = document.getElementById(containerId);
        this.stick = document.getElementById(stickId);
        this.callback = callback;

        this.centerX = this.container.offsetWidth / 2;
        this.centerY = this.container.offsetHeight / 2;

        this.stick.style.left = `${this.centerX - this.stick.offsetWidth / 2}px`;
        this.stick.style.top = `${this.centerY - this.stick.offsetHeight / 2}px`;

        this.active = false;

        // MOUSE EVENTS
        this.container.addEventListener("mousedown", this.start.bind(this));
        document.addEventListener("mousemove", (e) => {
            if (this.active) this.move(e);
        });
        document.addEventListener("mouseup", this.end.bind(this));

        // TOUCH EVENTS
        this.container.addEventListener("touchstart", (event) => {
            event.preventDefault();
            this.start(event.touches[0]);
        }, { passive: false });

        this.container.addEventListener("touchmove", (event) => {
            if (!this.active) return;
            event.preventDefault();
            this.move(event.touches[0]);
        }, { passive: false });

        // FIX: only listen for touchend on THIS joystick
        this.container.addEventListener("touchend", (event) => {
            event.preventDefault();
            this.end(event);
        }, { passive: false });
    }

    start(event) {
        if (window.debugMode) jsDebug("Joystick started");
        this.active = true;
        this.move(event);
    }

    move(event) {
        if (!this.active) return;

        const rect = this.container.getBoundingClientRect();
        const clientX = event.clientX;
        const clientY = event.clientY;

        let x = clientX - rect.left;
        let y = clientY - rect.top;

        const max = this.container.offsetWidth / 2;

        let dx = x - this.centerX;
        let dy = y - this.centerY;

        // --- TOUCH DRIFT FIX ---
        const driftLimit = 4;
        if (Math.abs(dx) < driftLimit) dx = 0;
        if (Math.abs(dy) < driftLimit) dy = 0;

        dx = Math.max(-max, Math.min(max, dx));
        dy = Math.max(-max, Math.min(max, dy));

        this.stick.style.left = `${this.centerX + dx - this.stick.offsetWidth / 2}px`;
        this.stick.style.top = `${this.centerY + dy - this.stick.offsetHeight / 2}px`;

        const normX = dx / max;
        const normY = -dy / max;

        this.callback(normX, normY);
    }

    reset() {
        if (window.debugMode) jsDebug("Joystick reset");
        this.active = false;

        this.stick.style.left = `${this.centerX - this.stick.offsetWidth / 2}px`;
        this.stick.style.top = `${this.centerY - this.stick.offsetHeight / 2}px`;

        this.callback(0, 0);
    }

    end(event) {
        if (window.debugMode) jsDebug("Joystick end");

        // Prevent bubbling
        if (event) event.stopPropagation();

        if (this.container.id === "tankJoy" && this.active) {
            if (window.debugMode) jsDebug(`Joystick end at ${this.container.id}`);
            stopTank();
            this.reset();
        } else {
            if (window.debugMode) jsDebug(`Joystick end else ${this.container.id}`);
            this.active = false;
            this.callback(0, 0);
        }
    }
}
