import socket
import logging
from typing import Literal, Optional, Dict
import time
from esp_id import get_esp_ip

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(filename)s:%(lineno)d] %(message)s"
)
logger = logging.getLogger("ESP32Interactor")

RETRY_SECS = 2
SOCKET_TIMEOUT = 1

ALLOWED_PINS = [13, 12, 14, 27, 26, 25, 33, 32, 35, 34]



class ESP32Interactor:
    def __init__(self, host: str="", port: int = 1234, retry_count: int = 10):
        if not host:
            hosts = get_esp_ip()
            if not hosts:
                raise ValueError("Could not find esp on our hotspot")
            host = hosts[0]
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
