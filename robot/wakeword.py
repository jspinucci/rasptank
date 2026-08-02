"""
robot/wakeword.py - Wakeword detection bridge for RaspTank

Wraps an optional robot_wakeword module and exposes a thread-safe
interface for app.py's SSE streaming route.

Falls back to STUB mode (simulated event every 30s) if no wakeword
library is installed.
"""

import logging
import queue
import threading
import time
from typing import Optional

log = logging.getLogger(__name__)

try:
    import robot_wakeword as _rw
    _RW_AVAILABLE = True
    print("robot_wakeword module loaded - hardware wakeword active")
except Exception as e:
    _RW_AVAILABLE = False
    log.warning("robot_wakeword not found - running in STUB mode")


class WakewordBridge:
    def __init__(
        self,
        keyword: str = "hey rasptank",
        sensitivity: float = 0.5,
        event_queue_size: int = 64,
    ):
        self._keyword = keyword
        self._sensitivity = sensitivity
        self._queue = queue.Queue(maxsize=event_queue_size)
        self._thread = None
        self._stop_event = threading.Event()
        self._listening = False
        self._detection_count = 0
        log.info(
            "WakewordBridge init - keyword=%r  sensitivity=%.2f  backend=%s",
            keyword, sensitivity, "robot_wakeword" if _RW_AVAILABLE else "stub",
        )

    def start(self) -> None:
        if self._listening:
            return
        self._stop_event.clear()
        target = self._listen_real if _RW_AVAILABLE else self._listen_stub
        self._thread = threading.Thread(target=target, daemon=True, name="wakeword-listener")
        self._thread.start()
        self._listening = True
        log.info("WakewordBridge started")

    def stop(self) -> None:
        if not self._listening:
            return
        self._stop_event.set()
        if _RW_AVAILABLE and hasattr(_rw, "stop"):
            try:
                _rw.stop()
            except Exception as exc:
                log.debug("robot_wakeword.stop() error: %s", exc)
        if self._thread:
            self._thread.join(timeout=3)
        self._listening = False
        log.info("WakewordBridge stopped")

    def next_event(self, timeout: float = 0.0) -> Optional[str]:
        try:
            return self._queue.get(block=timeout > 0, timeout=timeout or None)
        except queue.Empty:
            return None

    def status(self) -> dict:
        return {
            "listening": self._listening,
            "keyword": self._keyword,
            "sensitivity": self._sensitivity,
            "backend": "robot_wakeword" if _RW_AVAILABLE else "stub",
            "detections_total": self._detection_count,
            "queue_depth": self._queue.qsize(),
        }

    def _listen_real(self) -> None:
        if hasattr(_rw, "start") and callable(_rw.start):
            self._listen_real_callback()
        elif hasattr(_rw, "listen") and callable(_rw.listen):
            self._listen_real_generator()
        else:
            log.error("robot_wakeword has no recognised interface (start/listen)")

    def _listen_real_callback(self) -> None:
        def _on_detection(payload: str):
            self._push_event(payload)
        try:
            _rw.start(callback=_on_detection)
            self._stop_event.wait()
        except Exception as exc:
            log.error("robot_wakeword start() error: %s", exc)

    def _listen_real_generator(self) -> None:
        try:
            for detection in _rw.listen(keywords=[self._keyword], sensitivity=self._sensitivity):
                if self._stop_event.is_set():
                    break
                if isinstance(detection, dict):
                    word = detection.get("keyword", self._keyword)
                    score = detection.get("score", 0.0)
                    payload = f"Wakeword '{word}' (score={score:.3f})"
                else:
                    payload = str(detection)
                self._push_event(payload)
        except Exception as exc:
            log.error("robot_wakeword generator interface error: %s", exc)

    def _listen_stub(self) -> None:
        log.info("WakewordBridge stub: simulating detections every 30 s")
        count = 0
        while not self._stop_event.is_set():
            for _ in range(300):
                if self._stop_event.is_set():
                    return
                time.sleep(0.1)
            count += 1
            self._push_event(f"[STUB] Wakeword '{self._keyword}' detected (simulation #{count})")

    def _push_event(self, payload: str) -> None:
        self._detection_count += 1
        if self._queue.full():
            try:
                self._queue.get_nowait()
            except queue.Empty:
                pass
        try:
            self._queue.put_nowait(payload)
        except queue.Full:
            pass
        log.info("Wakeword event: %s", payload)
