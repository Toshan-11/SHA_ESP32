import socket
import logging
from typing import Literal, Optional, Dict
import time

import random
from itertools import cycle

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(filename)s:%(lineno)d] %(message)s"
)
logger = logging.getLogger("ESP32Interactor")

RETRY_SECS = 2
SOCKET_TIMEOUT = 1

ALLOWED_PINS = [13, 12, 14, 27, 26, 25, 33, 32, 35, 34]  # Optional validation


class ESP32Interactor:
    def __init__(self, host: str, port: int = 1234, retry_count: int = 10):
        self.host = host
        self.port = port
        self.sock: Optional[socket.socket] = None
        self.retry_count = retry_count
        self.pin_states: Dict[int, Literal[0, 1]] = {}

    def connect(self):
        """Establish TCP connection with ESP32."""
        if self.retry_count < 1:
            logger.error("Failed to establish connection. Exceeded retries.")
            return
        if self.sock:
            logger.warning("Already connected.")
            return

        try:
            self.retry_count -= 1
            logger.info(f"Connecting to ESP32 at {self.host}:{self.port}...")
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(SOCKET_TIMEOUT)
            self.sock.connect((self.host, self.port))
            logger.info("Connection established.")
        except Exception as e:
            logger.warning("Failed to connect to ESP32.")
            self.sock = None
            logger.info(f"Sleeping for {RETRY_SECS} before retrying...")
            time.sleep(RETRY_SECS)
            self.connect()

    def disconnect(self):
        """Close the socket connection."""
        if self.sock:
            try:
                self.sock.close()
                logger.info("Disconnected from ESP32.")
            finally:
                self.sock = None

    def _read_line(self) -> str:
        """Read data until newline from ESP32."""
        if not self.sock:
            raise RuntimeError("Not connected to ESP32.")
        buffer = ""
        while "\n" not in buffer:
            data = self.sock.recv(1).decode()
            if not data:
                raise ConnectionError("Disconnected unexpectedly.")
            buffer += data
        return buffer.strip()

    def set_pin_state(self, pin: int, state: Literal[0, 1]):
        """Send pin state command to ESP32 and track it locally."""
        self.connect()

        if pin not in ALLOWED_PINS:
            raise ValueError(f"Pin {pin} is not allowed.")

        if state not in (0, 1):
            raise ValueError("State must be 0 or 1.")

        command = f"{pin} {state}\n"
        logger.info(f"Sending command: {command.strip()}")
        self.sock.sendall(command.encode())
        response = self._read_line()

        if "OK" in response:
            self.pin_states[pin] = state  # Update local state
            logger.info(f"Pin {pin} updated to {state}")
        else:
            logger.warning(f"ESP32 did not confirm state change: {response}")

        return response

    def get_all_pin_states(self) -> Dict[int, Literal[0, 1]]:
        """Return the locally known pin states."""
        return dict(self.pin_states)  # Return a copy

    def __del__(self):
        """Ensure clean shutdown."""
        self.disconnect()


def cli_mainloop():
    """Simple CLI loop to control pins via ESP32."""
    esp = ESP32Interactor("192.168.137.24", 1234)

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
    esp = ESP32Interactor("192.168.137.24", 1234)
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
    patterns = cycle([
        linear_sweep,
        alternate_blink,
        odd_even_chase,
        flash_all,
        ping_pong,
        random_chaos
    ])

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

if __name__ == "__main__":
    # cli_mainloop()
    blinker()
