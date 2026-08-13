// joystick.js — actual joystick implementation

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

	this.container.addEventListener("mousedown", this.start.bind(this));
	this.container.addEventListener("touchstart", (event) => {
	    event.preventDefault();
	    this.start(event);
	}, { passive: false });

	this.container.addEventListener("mousemove", this.move.bind(this));
	this.container.addEventListener("touchmove", (event) => {
	    event.preventDefault();
	    this.move(event);
	}, { passive: false });

	document.addEventListener("mouseup", this.end.bind(this));
	document.addEventListener("touchend", (event) => {
	    this.end(event);
	}, { passive: true });
    }

    start(event) {
	jsDebug("Joystick started");
        this.active = true;
        this.move(event);
    }

    move(event) {
        if (!this.active) return;

        const rect = this.container.getBoundingClientRect();
        const clientX = event.touches ? event.touches[0].clientX : event.clientX;
        const clientY = event.touches ? event.touches[0].clientY : event.clientY;

        let x = clientX - rect.left;
        let y = clientY - rect.top;

        const max = this.container.offsetWidth / 2;

        let dx = x - this.centerX;
        let dy = y - this.centerY;

        dx = Math.max(-max, Math.min(max, dx));
        dy = Math.max(-max, Math.min(max, dy));

        this.stick.style.left = `${this.centerX + dx - this.stick.offsetWidth / 2}px`;
        this.stick.style.top = `${this.centerY + dy - this.stick.offsetHeight / 2}px`;

        const normX = dx / max;
        const normY = -dy / max;

        this.callback(normX, normY);
    }
    reset() {
	jsDebug("Joystick reset");
	jsDebug(`RESET ${this.container.id}`);
        this.active = false;
        this.rawX = 0;
        this.rawY = 0;

        this.stick.style.left = `${this.centerX - this.stick.offsetWidth / 2}px`;
        this.stick.style.top = `${this.centerY - this.stick.offsetHeight / 2}px`;

        // Send zero movement to backend
        this.callback(0, 0);
    }



    end() {
        jsDebug("Joystick end");
        if(this.container.id === "tankJoy")
	{
            jsDebug(`Joystick end at ${this.container.id}`);
            stopTank();
	    this.reset();
        }
        else {
            jsDebug(`Joystick end else ${this.container.id}`);
            this.active = false;
            this.callback(0, 0);
        }
    }
}
