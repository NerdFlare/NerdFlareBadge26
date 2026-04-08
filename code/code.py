
'''
   _  __           ________             ___  ____
  / |/ /__ _______/ / __/ /__ ________ |_  |/ __/
 /    / -_) __/ _  / _// / _ `/ __/ -_) __// _ \ 
/_/|_/\__/_/  \_,_/_/ /_/\_,_/_/  \__/____/\___/ 
                                        
Firmware Version 0.1
'''

import neopixel
import board
import time
import digitalio
from busio import UART
from adafruit_led_animation.animation.rainbowcomet import RainbowComet
#from adafruit_led_animation.animation.sparkle import Sparkle
from adafruit_led_animation.animation.SparklePulse import SparklePulse
#from adafruit_led_animation.animation.rainbow import Rainbow
#from adafruit_led_animation.animation.rainbowsparkle import RainbowSparkle
#from adafruit_led_animation.sequence import AnimationSequence
from adafruit_led_animation.color import WHITE
import asyncio
import pwmio
import storage
import json
import microcontroller
import random


# SETTINGS (overwritten from settings.json if available)
BADGE_MODE = 0
NUM_MODES = 2
SPARKLE_MODE = 0
GAME_MODE = 1
COLORS = ["RED",  "YEL",  "BLU", "GRE"]
COLOR_DICT = {"RED":(255,0,0), "BLU":(0,0,255), "GRE":(0,255,0), "YEL":(255,255,0)}
CURRENT_LEVEL = 0

# LED and NEOPIXEL animation settings
FADE_DUR = 0
FADE_OFF = 0
BLINK_DUR = 0.5

#DEBUG Mode
DEBUG = False

if DEBUG:
    print("starting", microcontroller.cpu.uid[:4])

#Shuffle the colors based on CPU UID
random.seed(int.from_bytes(microcontroller.cpu.uid[:4])) #Seed the RNG so we get a deterministic shuffle
temp = list(COLORS)
shuffled = []
while temp:
    item = random.choice(temp)
    shuffled.append(item)
    temp.remove(item)
COLORS=shuffled

if DEBUG:
    COLORS = ["RED",  "YEL",  "BLU", "GRE"]

#Try to load settings.json
FS_WRITABLE = False 
try:
    storage.remount("/", readonly=False) # This is only possible when not in USB disk mode
    FS_WRITABLE = True
    with open("settings.json") as f:
        settings = json.load(f)
    f.close()
    CURRENT_LEVEL = settings["level"]
    BADGE_MODE = settings["mode"]
    if DEBUG:
        print("Got settings:", json.dumps(settings))
except Exception as e:
    if DEBUG:
        print("Can't mount the file system. Using Defaults.")
    FS_WRITABLE = False
   
#If we've won, start the LED animation
if CURRENT_LEVEL > 3:
    FADE_DUR = 300
    FADE_OFF = 150


level_lock = asyncio.Lock()

# Randomly blink the LEDs at some interval
async def led_sparkle(leds, speed_ms):
    speed = speed_ms / 1000

    # Ensure all LEDs start off
    for led in leds:
        led.value = False

    # wait a random amount around the requested speed
    wait_time = random.uniform(speed * 0.5, speed * 1.5)
    await asyncio.sleep(wait_time)

    led = random.choice(leds)
    led2 = random.choice(leds)

    # random sparkle duration
    sparkle_time = random.uniform(0.03, 0.2)

    led.value = True
    led2.value = True
    await asyncio.sleep(sparkle_time)
    led.value = False
    led2.value = False

#fade PWM LEDs with staggered start times.
#pwms (list): List of PWMOut objects.
#fade_duration_ms (int): Time for one LED to fade on and off (ms).
#start_offset_ms (int): Time between successive LEDs starting (ms).
async def cascade_fade(pwms, fade_duration_ms, start_offset_ms):

    if fade_duration_ms == 0 or start_offset_ms == 0:
        await asyncio.sleep(0)
        return

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


#Async Task that handles discreet LEDs
async def leds_task():
    global BADGE_MODE, FADE_DUR, FADE_OFF
    
    #v0 LEDs are GP8,15, 17, 21
    #v0.1 LEDs are GP1, 2, 6, 14, 16, 19, 26
    while True:
        if BADGE_MODE == GAME_MODE:
            pwms = [pwmio.PWMOut(board.GP1, frequency=5000, duty_cycle=0), pwmio.PWMOut(board.GP2, frequency=5000, duty_cycle=0), pwmio.PWMOut(board.GP6, frequency=5000, duty_cycle=0),pwmio.PWMOut(board.GP14, frequency=5000, duty_cycle=0),pwmio.PWMOut(board.GP16, frequency=5000, duty_cycle=0),pwmio.PWMOut(board.GP19, frequency=5000, duty_cycle=0),pwmio.PWMOut(board.GP26, frequency=5000, duty_cycle=0)]
            await cascade_fade(pwms, fade_duration_ms=FADE_DUR, start_offset_ms=FADE_OFF)
            for pwm in pwms:
                pwm.deinit()
        elif BADGE_MODE == SPARKLE_MODE:
            D1 = digitalio.DigitalInOut(board.GP1)
            D1.direction = digitalio.Direction.OUTPUT
            D2 = digitalio.DigitalInOut(board.GP2)
            D2.direction = digitalio.Direction.OUTPUT
            D3 = digitalio.DigitalInOut(board.GP6)
            D3.direction = digitalio.Direction.OUTPUT
            D4 = digitalio.DigitalInOut(board.GP14)
            D4.direction = digitalio.Direction.OUTPUT
            D5 = digitalio.DigitalInOut(board.GP16)
            D5.direction = digitalio.Direction.OUTPUT
            D6 = digitalio.DigitalInOut(board.GP19)
            D6.direction = digitalio.Direction.OUTPUT
            D7 = digitalio.DigitalInOut(board.GP26)
            D7.direction = digitalio.Direction.OUTPUT
            leds = [D1, D2, D3, D4, D5, D6, D7]
            await led_sparkle(leds, speed_ms=250)
            for led in leds:
                led.deinit()
        else:
            pwms = [pwmio.PWMOut(board.GP8, frequency=5000, duty_cycle=0), pwmio.PWMOut(board.GP15, frequency=5000, duty_cycle=0), pwmio.PWMOut(board.GP17, frequency=5000, duty_cycle=0),pwmio.PWMOut(board.GP21, frequency=5000, duty_cycle=0)]
            for pwm in pwms:
                pwm.duty_cycle = 65535
                await asyncio.sleep(0)
            for pwm in pwms:
                pwm.deinit()
                

#Async task that handles button presses
async def button_task(interval):

    global BADGE_MODE
    
    #v0 is GP16
    #v0.1 is GP0
    button_pin = board.GP0
    button =  digitalio.DigitalInOut(button_pin)
    button.direction = digitalio.Direction.INPUT
    button.pull = digitalio.Pull.UP
    prev_state = True
    while True:
        cur_state = button.value
        if cur_state != prev_state:
            if cur_state == False: #button down
                
                BADGE_MODE = (BADGE_MODE + 1) % NUM_MODES
                if DEBUG:
                    print("Badge mode:", BADGE_MODE)
                if FS_WRITABLE:
                    settings["mode"] = BADGE_MODE
                    with open("settings.json", "w") as f:
                        json.dump(settings, f)
                    f.close()
                
            prev_state = cur_state
        await asyncio.sleep(interval)

#Controls the neopixles during game mode
async def neopixel_play_game(pixels):
    global BLINK_DUR
    
    async with level_lock:
        if CURRENT_LEVEL > 3:
            await asyncio.sleep(0)
        else:
            pixels.fill((0,0,0))
            pixels.show()
            await asyncio.sleep(.5)
            
            #Fill in neopixels up to current level
            for i in range(CURRENT_LEVEL + 1):
                pixels[i] = COLOR_DICT[COLORS[i]]
                pixels.show()
                await asyncio.sleep(.5)
                
                #print(f"Setting {i} to {colors[i]}")
            
            
            #Blink current level
            for i in range(3):
                pixels[CURRENT_LEVEL] = (0,0,0)
                pixels.show()
                await asyncio.sleep(BLINK_DUR)
                pixels[CURRENT_LEVEL] = COLOR_DICT[COLORS[CURRENT_LEVEL]]
                pixels.show()
                await asyncio.sleep(BLINK_DUR)
        
    

#Async task that handles neopixels
async def neopixels_task(interval):
    #v0 is GP0
    #v0.1 is GP17
    pixel_pin = board.GP17
    num_pixels = 4
    
    with neopixel.NeoPixel(pixel_pin, num_pixels, brightness=0.5, auto_write=True) as pixels:
        rainbow_comet = RainbowComet(pixels, speed=.075, tail_length=8, bounce=True )
        sparkle_pulse = SparklePulse(pixels, speed=0.13, period=1, color=WHITE)
        while True:
            if BADGE_MODE == SPARKLE_MODE:
                sparkle_pulse.animate()
                await asyncio.sleep(interval)
            elif BADGE_MODE == GAME_MODE:
                if CURRENT_LEVEL > 3:
                    rainbow_comet.animate()
                    await asyncio.sleep(interval)
                else:
                    await neopixel_play_game(pixels)

#Animation that plays when there's a match in game mode            
async def match_animation():
    global FADE_DUR, FADE_OFF, BLINK_DUR
    
    FADE_DUR=1500
    FADE_OFF=750
    
    BLINK_DUR=0.4
    
    for i in range(4):
        FADE_DUR = int(FADE_DUR/2)
        FADE_OFF = int(FADE_OFF/2)
        BLINK_DUR = BLINK_DUR - 0.1
        await asyncio.sleep((FADE_DUR * 4)/1000)
    FADE_DUR = 3000
    FADE_OFF = 1
    await asyncio.sleep(3)

    FADE_DUR=0
    FADE_OFF=0
    BLINK_DUR = 0.5

#Async task that handles UART
# This handles both write and reading of color packets over UART
async def uart_task(interval):
    global COLORS, FADE_DUR, FADE_OFF, CURRENT_LEVEL

    UPDATE_INTERVAL = 3.0 #How often do we trasmit color packets
    last_time_sent = 0
    message_started = False

    #v0 broken. Bodged to TX GP12, RX GP13
    #v0.1 RX GP4, TX GP5
    with UART(rx=board.GP5, tx=board.GP4, baudrate=9600, timeout=0) as uart:
        while True:
            if BADGE_MODE == SPARKLE_MODE or CURRENT_LEVEL > 3: #Ignore UART if not in game mode or game is beaten
                await asyncio.sleep(interval)
                continue
            
            color = COLORS[CURRENT_LEVEL]
            now = time.monotonic()
            if now - last_time_sent >= UPDATE_INTERVAL: #Only transmit color once every UPDATE_INTERVAL
                uart.write(bytes(f"<{color}>", "ascii"))
                last_time_sent = now
            
            if uart.in_waiting: #If there's data to read
                byte_read = uart.read(1) #read a single byte
                if DEBUG:
                    print("UART got:",chr(byte_read[0]))
                if byte_read is not None:
                    if byte_read == b"<": #Start a packet
                        if DEBUG:
                            print("packet started")
                        message_buffer = []
                        message_started = True
                        continue
                    if message_started:
                        if byte_read == b">": #End of packet
                            message = "".join([b for b in message_buffer])
                            if DEBUG:
                                print(message, COLORS[CURRENT_LEVEL])
                                print("packet ended")
                            message_started = False
                            
                            if message == COLORS[CURRENT_LEVEL]: #Did we get a match?
                                async with level_lock:
                                    await match_animation() 
                                
                                
                                    CURRENT_LEVEL = CURRENT_LEVEL + 1
                                    
                                    if FS_WRITABLE:
                                        settings["level"] = CURRENT_LEVEL
                                        with open("settings.json", "w") as f:
                                            json.dump(settings, f)
                                        f.close()
                                    if CURRENT_LEVEL > 3: #If we'ce won, set the animation sequence
                                        FADE_DUR=300
                                        FADE_OFF=150
                                    else: #Otherwise turn off LEDs
                                        FADE_DUR=0
                                        FADE_OFF=0
                        else:
                            message_buffer.append(chr(byte_read[0]))

            await asyncio.sleep(interval)

async def main():
    neopixels_t = asyncio.create_task(neopixels_task(0))
    uart_t = asyncio.create_task(uart_task(0.5))
    leds_t = asyncio.create_task(leds_task())
    button_t = asyncio.create_task(button_task(0))
    await asyncio.gather(neopixels_t, uart_t, leds_t, button_t)
    if DEBUG:
        print("done") #We should never get here
    
asyncio.run(main())

        


