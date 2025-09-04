from interactor import ESP32Interactor, logger
import time


import random
from itertools import cycle

def cli_mainloop():
    """Simple CLI loop to control pins via ESP32."""
    esp = ESP32Interactor()

    try:
        esp.connect()
        while True:
            print("\n" + "*" * 30)
            user_input = input("Enter pin,state | 'get' | 'exit': ").strip().lower()
            if user_input in {"exit", "quit"}:
                logger.info("Exiting CLI.")
                break

            if user_input == "get":
                states = esp.get_all_pin_states()
                print("Current known pin states:")
                for pin, state in sorted(states.items()):
                    print(f"  Pin {pin}: {state}")
                continue

            try:
                parts = user_input.split(",")
                if len(parts) != 2:
                    raise ValueError(f"Expected format 'pin,state', got {user_input!r}")

                pin = int(parts[0])
                state = int(parts[1])
                esp.set_pin_state(pin, state)

            except Exception as e:
                logger.error(f"Error: {e}")
    finally:
        esp.disconnect()


def blinker():
    pins = [13, 12, 14, 27, 26]
    esp = ESP32Interactor()
    delay = 0.0  # seconds

    def off_all():
        for p in pins:
            esp.set_pin_state(p, 0)

    def linear_sweep():
        for p in pins:
            esp.set_pin_state(p, 1)
            time.sleep(delay)
            esp.set_pin_state(p, 0)

    def alternate_blink():
        group1 = pins[::2]
        group2 = pins[1::2]
        for _ in range(3):
            for p in group1:
                esp.set_pin_state(p, 1)
            for p in group2:
                esp.set_pin_state(p, 0)
            time.sleep(delay)
            for p in group1:
                esp.set_pin_state(p, 0)
            for p in group2:
                esp.set_pin_state(p, 1)
            time.sleep(delay)
            off_all()

    def odd_even_chase():
        odds = [p for p in pins if p % 2 == 1]
        evens = [p for p in pins if p % 2 == 0]
        for _ in range(2):
            for p in odds:
                esp.set_pin_state(p, 1)
            time.sleep(delay)
            for p in odds:
                esp.set_pin_state(p, 0)
            for p in evens:
                esp.set_pin_state(p, 1)
            time.sleep(delay)
            for p in evens:
                esp.set_pin_state(p, 0)

    def flash_all(times=3):
        for _ in range(times):
            for p in pins:
                esp.set_pin_state(p, 1)
            time.sleep(delay)
            off_all()
            time.sleep(delay)

    def ping_pong():
        sequence = pins + pins[::-1][1:-1]
        for p in sequence:
            off_all()
            esp.set_pin_state(p, 1)
            time.sleep(delay)
        off_all()

    def random_chaos(times=10):
        for _ in range(times):
            p = random.choice(pins)
            s = random.choice([0, 1])
            esp.set_pin_state(p, s)
            time.sleep(delay)

    # Pattern cycle
    patterns = cycle(
        [
            linear_sweep,
            alternate_blink,
            odd_even_chase,
            flash_all,
            ping_pong,
            random_chaos,
        ]
    )

    print("Running LED blinker patterns (Ctrl+C to stop)")
    try:
        while True:
            pattern = next(patterns)
            print(f"\n[Pattern: {pattern.__name__}]")
            pattern()
    except KeyboardInterrupt:
        print("Stopping blinker...")
        off_all()
        esp.disconnect()


# from interactor import ESP32Interactor, logger
# esp = -----------------192.168.137.2.168.137.237.106")
# ALLOWED_PINS = [13, 12, 14, 27, 26, 25, 33, 32, 35, 34]
# def basic_example():
#     esp.set_pin_state(13,1)
# def print_state():
#   esp.get_all_pin_states() # {pin_int:pin_state_0_1,pin_int::pin_state_0_1}
# ligth_pin = 13

# @onmessage("lights on")
# def ligh_on():
#     esp.set_pin_state(ligth_pin,1)


# @onmessage("lights off")
# def ligh_off():
#     esp.set_pin_state(ligth_pin,0)

if __name__ == "__main__":
    # cli_mainloop()
    blinker()
