
import neopixel
import board
import time
#from machine import PWM
import digitalio
from busio import UART
from adafruit_led_animation.animation.rainbowcomet import RainbowComet
import asyncio
import pwmio


#led = pwmio.PWMOut(board.LED, frequency=5000, duty_cycle=0)
#D1.freq(1000)
#D1.duty_u16(0)

led_mode = 0
NUM_MODES = 2

print("starting")

import time

async def cascade_fade(pwms, fade_duration_ms, start_offset_ms):
    """
    Async fade of PWM LEDs with staggered start times.

    Args:
        pwms (list): List of PWMOut objects.
        fade_duration_ms (int): Time for one LED to fade on and off (ms).
        start_offset_ms (int): Time between successive LEDs starting (ms).
    """

    fade_duration = fade_duration_ms / 1000
    start_offset = start_offset_ms / 1000

    start_time = time.monotonic()
    led_count = len(pwms)

    start_times = [start_time + i * start_offset for i in range(led_count)]
    total_time = (led_count - 1) * start_offset + fade_duration

    while time.monotonic() < start_time + total_time:
        now = time.monotonic()

        for i, pwm in enumerate(pwms):
            t = now - start_times[i]

            if t < 0 or t > fade_duration:
                pwm.duty_cycle = 0
                continue

            phase = t / fade_duration

            if phase < 0.5:
                brightness = phase * 2
            else:
                brightness = (1 - phase) * 2

            pwm.duty_cycle = int(brightness * 65535)

        await asyncio.sleep(0.01)  # yield to other tasks (~10ms refresh)

    for pwm in pwms:
        pwm.duty_cycle = 0

async def cascade():
    pwms = [pwmio.PWMOut(board.GP8, frequency=5000, duty_cycle=0), pwmio.PWMOut(board.GP15, frequency=5000, duty_cycle=0), pwmio.PWMOut(board.GP17, frequency=5000, duty_cycle=0),pwmio.PWMOut(board.GP21, frequency=5000, duty_cycle=0)]
    while True:
        await cascade_fade(pwms, fade_duration_ms=500, start_offset_ms=100)

async def handle_button(interval):
    #v0 is GP16
    #v0.1 is GP0
    global led_mode
    button_pin = board.GP16
    button =  digitalio.DigitalInOut(button_pin)
    button.direction = digitalio.Direction.INPUT
    button.pull = digitalio.Pull.UP
    prev_state = True
    while True:
        cur_state = button.value
        if cur_state != prev_state:
            if cur_state == False: #button down
                led_mode = (led_mode + 1) % NUM_MODES
            prev_state = cur_state
        await asyncio.sleep(interval)
                    

async def led_fade(interval):
    global led_mode
    D1 = pwmio.PWMOut(board.GP8, frequency=5000, duty_cycle=0)
    while True:
        if led_mode == 0:
            for i in range(100):
                 # PWM LED up and down
                if i < 50:
                    D1.duty_cycle = int(i * 2 * 65535 / 100)  # Up
                else:
                    D1.duty_cycle = 65535 - int((i - 50) * 2 * 65535 / 100)  # Down
                await asyncio.sleep(interval)
        else:
            D1.duty_cycle = 65535
            await asyncio.sleep(interval)


async def led_blink(interval):
    #v0 LEDs are GP8,15, 17, 21
    #v0.1 LEDs are GP1, 2, 6, 14, 16, 19
    #D1 = digitalio.DigitalInOut(board.GP8)
    #D1.direction = digitalio.Direction.OUTPUT
    D2 = digitalio.DigitalInOut(board.GP15)
    D2.direction = digitalio.Direction.OUTPUT
    D3 = digitalio.DigitalInOut(board.GP17)
    D3.direction = digitalio.Direction.OUTPUT
    D4 = digitalio.DigitalInOut(board.GP21)
    D4.direction = digitalio.Direction.OUTPUT
    leds = [D2, D3, D4]
    while True:
        for led in leds:
            led.value = True
        await asyncio.sleep(interval)
        for led in leds:
            led.value = False
        await asyncio.sleep(interval)

async def rainbow(interval):
    #v0 is GP0
    #v0.1 is GP17
    pixel_pin = board.GP0 
    num_pixels = 4
    with neopixel.NeoPixel(pixel_pin, num_pixels, brightness=0.5, auto_write=True) as pixels:
        rainbow_comet = RainbowComet(pixels, speed=0.1, tail_length=2, bounce=True)
        while True:
            rainbow_comet.animate()
            await asyncio.sleep(interval)


async def read_uart(interval):
    #v0 broken bodged to TX GP12, RX GP13
    #v0.1 RX GP4, TX GP5
    #uart = UART(rx=board.GP13, tx=board.GP12, baudrate=9600, rxbuf=2048) 
    with UART(rx=board.GP13, tx=board.GP12, baudrate=9600) as uart:
        while True:
            uart.write("beep")
            if uart.in_waiting:
                data = uart.read(32) 
                if data is not None:
                    data_string = ''.join([chr(b) for b in data])
                    print(data_string)
            await asyncio.sleep(interval)

async def main():
    led_task = asyncio.create_task(rainbow(0))
    uart_task = asyncio.create_task(read_uart(0))
    #led_blink_task = asyncio.create_task(led_blink(1))
    #led_fade_task = asyncio.create_task(led_fade(0.01))
    led_cascade_task = asyncio.create_task(cascade())
    button_task = asyncio.create_task(handle_button(0))
    await asyncio.gather(led_task, uart_task, led_cascade_task,button_task)
    print("done")
    
asyncio.run(main())

        