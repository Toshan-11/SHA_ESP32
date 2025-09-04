import speech_recognition as sr
from interactor import ESP32Interactor

# Initialize ESP32Interactor
esp = ESP32Interactor("192.168.137.230")

# Define devices and pins
DEVICE_PINS = {
    "light": 13,
    "fan": 14,
    "door": 27
}

COMMAND_MAP = {
    "turn on light": ("light", 1),
    "turn off light": ("light", 0),
    "turn on fan": ("fan", 1),
    "turn off fan": ("fan", 0),
    "open door": ("door", 1),
    "close door": ("door", 0)
}

def recognize_command():
    recognizer = sr.Recognizer()
    mic = sr.Microphone()
    
    with mic as source:
        print("🎤 Listening...")
        recognizer.adjust_for_ambient_noise(source)
        audio = recognizer.listen(source)

    try:
        command = recognizer.recognize_google(audio).lower()
        print(f"🔊 You said: {command}")
        return command
    except sr.UnknownValueError:
        print("❌ Could not understand audio.")
    except sr.RequestError:
        print("❌ Speech service error.")
    return None

def execute_command(command):
    for phrase, (device, state) in COMMAND_MAP.items():
        if phrase in command:
            pin = DEVICE_PINS[device]
            esp.set_pin_state(pin, state)
            print(f"✅ {device.capitalize()} set to {'ON' if state else 'OFF'}")
            return
    print("⚠️ Command not recognized.")

if __name__ == "__main__":
    while True:
        cmd = recognize_command()
        if cmd:
            execute_command(cmd)
