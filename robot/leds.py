import time
import threading
import board
import neopixel
import math

# ============================================================
# USER SETTINGS
# ============================================================

LED_PIN = board.D10          # WS2812 data pin
LED_COUNT = 8                # 2 onboard + 3 left bar + 3 right bar
LED_BRIGHTNESS = 0.5         # Medium brightness (0.0–1.0), user adjustable
ANIMATION_SPEED = 0.02       # Smoothness of animations

# ============================================================
# LED CONTROLLER CLASS
# ============================================================

class LEDController:
    def __init__(self):
        self.pixels = neopixel.NeoPixel(
            LED_PIN,
            LED_COUNT,
            brightness=LED_BRIGHTNESS,
            auto_write=False
        )

        self.mode = "idle"
        self.running = True
        self.lock = threading.Lock()

        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    # ------------------------------------------------------------
    # MODE SETTERS (priority handled externally)
    # ------------------------------------------------------------

    def set_mode(self, mode):
        with self.lock:
            self.mode = mode

    # ------------------------------------------------------------
    # MAIN LOOP
    # ------------------------------------------------------------

    def _run(self):
        while self.running:
            mode = None
            with self.lock:
                mode = self.mode

            if mode == "idle":
                self._idle_breathe()
            elif mode == "motor_forward":
                self._motor_wipe((0, 255, 0), forward=True)
            elif mode == "motor_reverse":
                self._motor_wipe((0, 0, 255), forward=False)
            elif mode == "motor_turn_left":
                self._motor_sweep((255, 255, 0), left=True)
            elif mode == "motor_turn_right":
                self._motor_sweep((255, 255, 0), left=False)
            elif mode == "motor_brake":
                self._flash_color((255, 0, 0))
            elif mode == "arm_motion":
                self._arm_flash()
            elif mode == "pantilt_motion":
                self._pantilt_flash()
            else:
                self._idle_breathe()

            time.sleep(ANIMATION_SPEED)

    # ------------------------------------------------------------
    # ANIMATION FUNCTIONS
    # ------------------------------------------------------------

    def _idle_breathe(self):
        t = time.time()
        intensity = (math.sin(t * 1.5) + 1) / 2  # 0–1 smooth
        color = (int(255 * intensity), 0, 0)
        self._fill(color)

    def _motor_wipe(self, color, forward=True):
        for i in range(LED_COUNT):
            idx = i if forward else (LED_COUNT - 1 - i)
            self._clear()
            self.pixels[idx] = color
            self.pixels.show()
            time.sleep(0.03)

    def _motor_sweep(self, color, left=True):
        # Left sweep = right side brighter
        # Right sweep = left side brighter
        for i in range(LED_COUNT):
            intensity = i / LED_COUNT if left else (1 - i / LED_COUNT)
            r = int(color[0] * intensity)
            g = int(color[1] * intensity)
            b = int(color[2] * intensity)
            self.pixels[i] = (r, g, b)
        self.pixels.show()

    def _flash_color(self, color):
        self._fill(color)
        time.sleep(0.1)
        self._clear()
        time.sleep(0.1)

    def _arm_flash(self):
        # Cyan → White → Cyan
        sequence = [(0, 255, 255), (255, 255, 255), (0, 255, 255)]
        for c in sequence:
            self._fill(c)
            time.sleep(0.05)
        self._clear()

    def _pantilt_flash(self):
        # Blue → White → Blue (double blink)
        sequence = [(0, 0, 255), (255, 255, 255), (0, 0, 255)]
        for c in sequence:
            self._fill(c)
            time.sleep(0.07)
        self._clear()

    # ------------------------------------------------------------
    # UTILITY FUNCTIONS
    # ------------------------------------------------------------

    def _fill(self, color):
        for i in range(LED_COUNT):
            self.pixels[i] = color
        self.pixels.show()

    def _clear(self):
        for i in range(LED_COUNT):
            self.pixels[i] = (0, 0, 0)
        self.pixels.show()

    def stop(self):
        self.running = False
        self.thread.join()
        self._clear()

# ============================================================
# TEST CODE (run this once to verify LED order)
# ============================================================

if __name__ == "__main__":
    leds = LEDController()

    print("Testing LED order...")
    for i in range(LED_COUNT):
        leds._clear()
        leds.pixels[i] = (255, 0, 0)
        leds.pixels.show()
        print(f"LED {i} should be RED")
        time.sleep(0.5)

    print("Idle breathing test...")
    leds.set_mode("idle")
    time.sleep(5)

    print("Forward wipe...")
    leds.set_mode("motor_forward")
    time.sleep(3)

    print("Arm flash...")
    leds.set_mode("arm_motion")
    time.sleep(3)

    print("Pan/Tilt flash...")
    leds.set_mode("pantilt_motion")
    time.sleep(3)

    leds.stop()
