#Fade a single LED using PWM
async def led_fade(interval):
    global BADGE_MODE
    D1 = pwmio.PWMOut(board.GP8, frequency=5000, duty_cycle=0)
    while True:
        if BADGE_MODE == SPARKLE_MODE:
            for i in range(100):
                 # PWM LED up and down
                if i < 50:
                    D1.duty_cycle = int(i * 2 * 65535 / 100)  # Up
                else:
                    D1.duty_cycle = 65535 - int((i - 50) * 2 * 65535 / 100)  # Down
                await asyncio.sleep(interval)
        elif BADGE_MODE == GAME_MODE:
            D1.duty_cycle = 65535
            await asyncio.sleep(interval)


#Blink LEDs digitally (not PWM)
async def led_blink(leds, interval):

    for led in leds:
        led.value = True
    await asyncio.sleep(interval)
    for led in leds:
        led.value = False
    await asyncio.sleep(interval)