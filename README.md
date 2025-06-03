# ST7796_RPi5
ST7796 Driver for Raspberry Pi 5

This library can show text and graphics on a LCD display with ST7796 controller using a Rpi5,
useful for IoT projects or embbebed systems.

* SPI Frec: 80 MHz.
* Supports rotation (0, 90, 180, 270). 
* Optimized drawing functions (text, lines, triangles and circles).
* Supports multiple fonts and sizes.
* Compatible with Rpi 4b and 5.

<h2>Installation</h2>

From Pypi:
```
pip install ST7796_RPi5
```
Manual installation:
```
git clone https://www.github.com/AndGonZ1/ST7796_RPi5.git
cd ST7796_RPi5
pip install -e .
```
<h2>Wiring</h2>

VCC = 5V (ST7796 board has a level convertion circuit from 5 to 3.3V)

GND = GND

LCD_CS = GPIO22

LCD_RST = GPIO6

LCD_RS = GPIO5

SDI (MOSI) = GPIO10  

SCK (SCLK) = GPIO11


<h2>First Use</h2>

```
from st7796_rpi import ST7796
from st7796_rpi.graphics import Graphics, BLACK, WHITE, RED, GREEN, BLUE

# Init display
display = ST7796(
    dc_pin=5,
    reset_pin=6,
    cs_pin=22,
    rotation=0
)

# Graphic object
graphics = Graphics(display)

# Clean screen
display.fill_screen(BLACK)

# Draw text
graphics.draw_text(10, 30, "¡Hola mundo!", 2, WHITE)

# Draw forms
graphics.draw_rectangle(10, 80, 100, 40, RED)
graphics.draw_circle(160, 100, 30, BLUE)

# Draw lines
graphics.draw_line(10, 160, 200, 160, GREEN)
```

<h2>Compatibility</h2>

* Raspberry Pi 2, 3, 4 and 5.
* Python 3.6+
* Requires spidev and RPi.GPIO
