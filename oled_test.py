import board
import busio
import adafruit_ssd1306
from PIL import Image, ImageDraw, ImageFont
import datetime
import time

# I2C setup
i2c = busio.I2C(board.SCL, board.SDA)

# OLED setup
oled = adafruit_ssd1306.SSD1306_I2C(128, 64, i2c)
font = ImageFont.load_default()

while True:
    # Clear
    oled.fill(0)

    # Create image buffer
    image = Image.new("1", (128, 64))
    draw = ImageDraw.Draw(image)

    # Time text
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    draw.text((0, 0), f"Time:\n{now}", font=font, fill=255)

    # Display
    oled.image(image)
    oled.show()

    time.sleep(1)
