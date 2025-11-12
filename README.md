The project involves the use of a Raspberry PI PICO 2 W as a microcontroller programmed in PYTHON, an OLED display with SSD1306 chip and a rotary encoder with integrated switch. The time displayed on the OLED display can be changed or locked via a web page loaded on the Android phone. The web page is called "Index.html" and must be sent via email to your Android phone.

Connections :
VCC (or VDD) Display --> Connects to a 3V3 (3.3V) pin on the Pico (for example, Pin 36 or Pin 1).
GND Display --> Connects to a GND pin on the Pico (for example, Pin 3, Pin 13, or Pin 38).
SDA Display --> Pin GP14 (the physical pin 19).
SCL Display --> Pin GP15 (the physical pin 20).
Encoder CLK --> GP6 (the physical pin 9).
Encore DT   --> GP7 (the physical pin 10).
Encoder SW (Button) --> GP8 (the physical pin 11).
Encoder + -> 3.3V
Encoder GND -> GND
