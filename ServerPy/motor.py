import time
from interactor import ESP32Interactor
esp=ESP32Interactor()
esp.set_pin_state(13,0)
time.sleep(3)
esp.set_pin_state(13,1)
# esp.set_pin_state(12,0)
# time.sleep(3)
# esp.set_pin_state(13,0)