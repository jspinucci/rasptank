
import cv2
import threading
import time

class CameraStream:
    def __init__(self, device="/dev/video0", width=640, height=480):
        self.device = device
        self.width = width
        self.height = height

        self.cap = cv2.VideoCapture(self.device)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)

        self.frame = None
        self.running = False

    def start(self):
        if self.running:
            return
        self.running = True
        threading.Thread(target=self._capture_loop, daemon=True).start()

    def _capture_loop(self):
        while self.running:
            ret, frame = self.cap.read()
            if ret:
                _, jpeg = cv2.imencode(".jpg", frame)
                self.frame = jpeg.tobytes()
            time.sleep(0.01)

    def frames(self):
        self.start()
        while True:
            if self.frame:
                yield self.frame
            time.sleep(0.01)

    def snapshot(self):
        self.start()
        return self.frame

    def stop(self):
        self.running = False
        if self.cap:
            self.cap.release()

    def release(self):
        try:
            if self.cap:
                self.cap.release()
            if self.pipeline:
                self.pipeline.stop()
        except Exception:
            pass
            
    def is_alive(self):
        try:
            # If using OpenCV
            if hasattr(self, "cap"):
                return self.cap.isOpened()

            # If using libcamera or custom pipeline
            return True  # or a real check if your class supports it
        except:
            return False
