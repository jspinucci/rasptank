// joystick.js — actual joystick implementation

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
        this.container.addEventListener("touchstart", this.start.bind(this));

        this.container.addEventListener("mousemove", this.move.bind(this));
        this.container.addEventListener("touchmove", this.move.bind(this));

        document.addEventListener("mouseup", this.end.bind(this));
        document.addEventListener("touchend", this.end.bind(this));
    }

    start(event) {
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
  
        this.stick.style.left = `${this.centerX - this.stick.offsetWidth / 2}px`;
        this.stick.style.top = `${this.centerY - this.stick.offsetHeight / 2}px`;

       if(!this.active) return;

        // Send zero movement to backend
        this.callback(0, 0);
    }



    end() {
        this.active = false;
	if(typeof stopTank === "function") {
            stopTank();
        }
        this.reset();
     }
}
