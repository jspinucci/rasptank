# RaspTank Robot Project

A Raspberry Pi–powered tracked robot featuring:

- Real-time motor control (WebSockets)
- Pan/Tilt camera servos
- 5-DOF robotic arm (servos A–E)
- Live MJPEG video streaming
- Snapshot + recording system
- OLED robot face animations
- LED status indicators
- Wakeword detection module
- Flask + Flask-SocketIO backend
- Joystick-based web UI

## Project Structure

rasptank/
├── app.py                # Main Flask + WebSocket server
├── robot/                # Motor, servo, camera, wakeword modules
├── static/js/            # Control scripts (joystick, servos)
├── static/css/           # UI styling
├── templates/            # HTML control interface
├── recordings/           # Saved video files
└── images/               # Snapshots


## Setup

1. Clone the repo  
2. Create a Python virtual environment  
3. Install dependencies  
4. Run `python3 app.py`

## Branches

- `main` — stable archive  
- `websocket-upgrade` — active development branch

## License

Personal robotics project — not licensed for commercial use.

