# import threading
from flask import Flask, render_template, request, jsonify
# import speech_recognition as sr
# from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from interactor import ESP32Interactor
# import os

# import logging
# import queue


# # Configure logging
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)


# # === ESP32 INTERFACE SETUP ===
# esp = ESP32Interactor()

# UPLOAD_DIR = 'uploads'
# PROCESSED_DIR = 'processed'
# os.makedirs(UPLOAD_DIR, exist_ok=True)
# os.makedirs(PROCESSED_DIR, exist_ok=True)

# video_queue = queue.Queue(maxsize=10)  # Limit queue size to prevent memory issues
# processing_active = True

# DEVICE_PINS = {
#     "light": 13,
#     "fan": 14,
#     "door": 27
# }

# COMMAND_MAP = {
#     "turn on light": ("light", 1),
#     "turn off light": ("light", 0),
#     "turn on fan": ("fan", 1),
#     "turn off fan": ("fan", 0),
#     "open door": ("door", 1),
#     "close door": ("door", 0)
# }

# # === FLASK WEB SERVER ===
# app = Flask(__name__)

# @app.route("/")
# def index():
#     return render_template("index.html")

# @app.route("/control", methods=["POST"])
# def control():
#     data = request.get_json()
#     device = data["device"]
#     state = int(data["state"])
#     pin = DEVICE_PINS.get(device)

#     if pin is not None:
#         try:
#             esp.set_pin_state(pin, state)
#             return jsonify({"success": True})
#         except Exception as e:
#             return jsonify({"success": False, "error": str(e)})
#     return jsonify({"success": False, "error": "Invalid device"})

# @app.route("/status")
# def status():
#     try:
#         pin_states = esp.get_all_pin_states()
#         result = {device: pin_states.get(pin, 0) for device, pin in DEVICE_PINS.items()}
#         return jsonify(result)
#     except Exception as e:
#         return jsonify({dev: -1 for dev in DEVICE_PINS}, error=str(e))
    
# @app.route('/upload', methods=['POST'])
# def upload():
#     """
#     Handle video upload from live stream or manual recording
#     """
#     try:
#         if 'video' not in request.files:
#             return jsonify({'error': 'No video file'}), 400
            
#         video = request.files['video']
        
#         if video.filename == '':
#             return jsonify({'error': 'No file selected'}), 400
            
#         # Get additional data
#         chunk_id = request.form.get('chunk_id')
#         timestamp = request.form.get('timestamp')
#         is_live_stream = request.form.get('is_live_stream', 'false').lower() == 'true'
        
#         # Generate filename
#         if is_live_stream:
#             filename = f"live_chunk_{chunk_id}_{int(time.time())}.webm"
#         else:
#             filename = f"recording_{int(time.time())}_{video.filename}"
            
#         filepath = os.path.join(UPLOAD_DIR, filename)
        
#         # Save the video file
#         video.save(filepath)
#         logger.info(f"Saved {'live stream chunk' if is_live_stream else 'video'}: {filepath}")
        
#         # Add to processing queue
#         try:
#             video_queue.put_nowait((filepath, chunk_id, timestamp, is_live_stream))
#         except queue.Full:
#             logger.warning("Video processing queue is full, skipping oldest item")
#             try:
#                 # Remove oldest item and add new one
#                 old_item = video_queue.get_nowait()
#                 video_queue.put_nowait((filepath, chunk_id, timestamp, is_live_stream))
#             except queue.Empty:
#                 video_queue.put_nowait((filepath, chunk_id, timestamp, is_live_stream))
        
#         return jsonify({
#             'success': True, 
#             'filename': filename,
#             'is_live_stream': is_live_stream,
#             'chunk_id': chunk_id
#         })
        
#     except Exception as e:
#         logger.error(f"Error in upload endpoint: {str(e)}")
#         return jsonify({'error': str(e)}), 500
    

# def run_web_server():
#     app.run(debug=False, port=5000, use_reloader=False)

# # === VOICE CONTROL LOOP ===
# def recognize_command():
#     recognizer = sr.Recognizer()
#     mic = sr.Microphone()
#     with mic as source:
#         print("🎤 Listening...")
#         recognizer.adjust_for_ambient_noise(source)
#         audio = recognizer.listen(source)
#     try:
#         command = recognizer.recognize_google(audio).lower()
#         print(f"🔊 You said: {command}")
#         return command
#     except sr.UnknownValueError:
#         print("❌ Could not understand audio.")
#     except sr.RequestError:
#         print("❌ Speech service error.")
#     return None

# def execute_command(command):
#     for phrase, (device, state) in COMMAND_MAP.items():
#         if phrase in command:
#             pin = DEVICE_PINS[device]
#             esp.set_pin_state(pin, state)
#             print(f"✅ {device.capitalize()} set to {'ON' if state else 'OFF'}")
#             return
#     print("⚠️ Command not recognized.")

# def voice_loop():
#     while True:
#         cmd = recognize_command()
#         if cmd:
#             execute_command(cmd)

# # === TELEGRAM BOT ===
# def start(update, context):
#     update.message.reply_text("🤖 Hello! I can control your ESP32.\n\n"
#                               "Try commands like:\n"
#                               "`turn on light`\n"
#                               "`turn off fan`\n"
#                               "`open door`\n\n"
#                               "Or type /status", parse_mode="Markdown")

# def status(update, context):
#     try:
#         states = esp.get_all_pin_states()
#         response = ""
#         for device, pin in DEVICE_PINS.items():
#             state = states.get(pin, -1)
#             status_text = "ON ✅" if state == 1 else "OFF ❌" if state == 0 else "Error ❗"
#             response += f"{device.capitalize()}: {status_text}\n"
#         update.message.reply_text(response)
#     except Exception as e:
#         update.message.reply_text(f"⚠️ Error fetching status: {e}")

# def handle_text(update, context):
#     user_command = update.message.text.lower()
#     for phrase, (device, state) in COMMAND_MAP.items():
#         if phrase in user_command:
#             try:
#                 pin = DEVICE_PINS[device]
#                 esp.set_pin_state(pin, state)
#                 update.message.reply_text(f"✅ {device.capitalize()} turned {'ON' if state else 'OFF'}")
#                 return
#             except Exception as e:
#                 update.message.reply_text(f"❌ Failed to control {device}: {e}")
#                 return
#     update.message.reply_text("❓ I didn't understand that. Try /start for help.")

# def run_telegram_bot():
#     TELEGRAM_TOKEN = "YOUR_BOT_TOKEN_HERE"  # Replace this
#     updater = Updater(TELEGRAM_TOKEN, use_context=True)
#     dp = updater.dispatcher

#     dp.add_handler(CommandHandler("start", start))
#     dp.add_handler(CommandHandler("status", status))
#     dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))

#     print("🤖 Telegram bot is running...")
#     updater.start_polling()
#     updater.idle()


# # === Gesture control ===
# import cv2
# import mediapipe as mp
# from interactor import ESP32Interactor
# import time

# # Maps: thumb to pinky → pin list
# FINGER_TO_PIN = {
#     0: 13,  # Thumb
#     1: 12,  # Index
#     2: 14,  # Middle
#     3: 27,  # Ring
#     4: 25,   # Pinky
# }

# mp_hands = mp.solutions.hands
# mp_drawing = mp.solutions.drawing_utils

# def get_finger_states(hand_landmarks) -> list[int]:
#     """
#     Returns a list of 5 binary values (1 for extended, 0 for folded)
#     Order: [Thumb, Index, Middle, Ring, Pinky]
#     """
#     fingers = []

#     # Thumb: compare tip x to IP x (left/right flip based on handedness later)
#     thumb_tip = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP]
#     thumb_ip  = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_IP]
#     fingers.append(int(thumb_tip.x < thumb_ip.x))  # Assuming one hand facing palm

#     # For other fingers: tip y < pip y → extended
#     finger_tips = [mp_hands.HandLandmark.INDEX_FINGER_TIP,
#                    mp_hands.HandLandmark.MIDDLE_FINGER_TIP,
#                    mp_hands.HandLandmark.RING_FINGER_TIP,
#                    mp_hands.HandLandmark.PINKY_TIP]
    
#     finger_pips = [mp_hands.HandLandmark.INDEX_FINGER_PIP,
#                    mp_hands.HandLandmark.MIDDLE_FINGER_PIP,
#                    mp_hands.HandLandmark.RING_FINGER_PIP,
#                    mp_hands.HandLandmark.PINKY_PIP]

#     for tip_idx, pip_idx in zip(finger_tips, finger_pips):
#         tip = hand_landmarks.landmark[tip_idx]
#         pip = hand_landmarks.landmark[pip_idx]
#         fingers.append(int(tip.y < pip.y))  # Lower y means higher in image

#     return fingers

# def gesture(video_file=None):
#     cap = cv2.VideoCapture(video_file or 0)
#     esp = ESP32Interactor()
#     last_state = [0, 0, 0, 0, 0]  # Store previous finger states

#     with mp_hands.Hands(static_image_mode=False, max_num_hands=1, min_detection_confidence=0.6) as hands:
#         try:
#             print("Starting gesture control. Press 'q' to quit.")
#             while True:
#                 ret, frame = cap.read()
#                 if not ret:
#                     break
#                 frame = cv2.flip(frame, 1)
#                 rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
#                 result = hands.process(rgb)

#                 if result.multi_hand_landmarks:
#                     for hand_landmarks in result.multi_hand_landmarks:
#                         mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

#                         states = get_finger_states(hand_landmarks)

#                         # Send pin updates if changed
#                         for i, state in enumerate(states):
#                             pin = FINGER_TO_PIN[i]
#                             if state != last_state[i]:
#                                 esp.set_pin_state(pin, state)
#                         last_state = states
#         finally:
#             cap.release()
#             cv2.destroyAllWindows()

# # === MAIN FUNCTION TO RUN ALL TOGETHER ===
# if __name__ == "__main__":
#     threads = [
#         threading.Thread(target=run_web_server),
#     ]       

#     for t in threads:
#         t.daemon = True
#         t.start()

#     print("✅ All services started. Press Ctrl+C to stop.")
#     while True:
#         pass



from flask import Flask, request, jsonify, render_template_string
import threading
import os
import time
from datetime import datetime
import queue
import logging
import cv2
import mediapipe as mp

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MediaPipe setup
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils

# ESP32 Pin mapping (adjust according to your setup)
FINGER_TO_PIN = {
    0: 13,  # Thumb
    1: 12,  # Index
    2: 14,  # Middle
    3: 27,  # Ring
    4: 25,   # Pinky
}
# Create uploads directory if it doesn't exist
UPLOAD_DIR = 'uploads'
PROCESSED_DIR = 'processed'
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)

# Device states
device_states = {
    'light': 0,
    'fan': 0,
    'door': 0
}


def get_finger_states(landmarks):
    """Extract finger states from MediaPipe hand landmarks"""
    # Finger tip and pip landmark indices
    FINGER_TIPS = [4, 8, 12, 16, 20]  # Thumb, Index, Middle, Ring, Pinky
    FINGER_PIPS = [3, 6, 10, 14, 18]  # PIP joints for each finger
    
    states = []
    
    for i, (tip, pip) in enumerate(zip(FINGER_TIPS, FINGER_PIPS)):
        if i == 0:  # Thumb (different logic due to orientation)
            # Thumb is extended if tip x-coordinate > pip x-coordinate
            is_extended = landmarks.landmark[tip].x > landmarks.landmark[pip].x
        else:  # Other fingers
            # Finger is extended if tip y-coordinate < pip y-coordinate
            is_extended = landmarks.landmark[tip].y < landmarks.landmark[pip].y
        
        states.append(1 if is_extended else 0)
    
    return states

# Video processing queue for live stream
video_queue = queue.Queue(maxsize=10)  # Limit queue size to prevent memory issues
processing_active = True

def gesture_analysis(video_path, chunk_id=None, timestamp=None, is_live=False):
    """
    Process video file for gesture recognition using MediaPipe
    """
    try:
        logger.info(f"Processing {'live stream chunk' if is_live else 'video'}: {video_path}")
        
        # Initialize ESP32 interactor
        esp = ESP32Interactor()
        last_state = [0, 0, 0, 0, 0]  # Store previous finger states
        
        # Open video file
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            logger.error(f"Could not open video file: {video_path}")
            return
        
        with mp_hands.Hands(
            static_image_mode=False, 
            max_num_hands=1, 
            min_detection_confidence=0.6,
            min_tracking_confidence=0.5
        ) as hands:
            
            frame_count = 0
            processed_frames = 0
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                    
                frame_count += 1
                
                # Process every nth frame for efficiency (adjust as needed)
                if frame_count % 3 != 0:  # Process every 3rd frame
                    continue
                    
                processed_frames += 1
                
                # Flip frame horizontally for mirror effect
                frame = cv2.flip(frame, 1)
                
                # Convert BGR to RGB for MediaPipe
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                result = hands.process(rgb)
                
                if result.multi_hand_landmarks:
                    for hand_landmarks in result.multi_hand_landmarks:
                        # Get finger states
                        states = get_finger_states(hand_landmarks)
                        
                        # Send pin updates if changed
                        for i, state in enumerate(states):
                            pin = FINGER_TO_PIN[i]
                            print(f"{pin}\n"*100)
                            if state != last_state[i]:
                                esp.set_pin_state(pin, state)
                        
                        last_state = states
                        
                        # Log finger states for debugging
                        finger_names = ['Thumb', 'Index', 'Middle', 'Ring', 'Pinky']
                        active_fingers = [finger_names[i] for i, state in enumerate(states) if state]
                        if active_fingers:
                            logger.debug(f"Active fingers: {', '.join(active_fingers)}")
        
        cap.release()
        
        logger.info(f"Gesture analysis completed for {video_path}. Processed {processed_frames} frames.")
        
        # Clean up video file after processing (for live streams)
        if is_live and os.path.exists(video_path):
            try:
                os.remove(video_path)
                logger.debug(f"Cleaned up live stream file: {video_path}")
            except Exception as e:
                logger.warning(f"Could not remove file {video_path}: {str(e)}")
        elif not is_live and os.path.exists(video_path):
            # Move processed file to processed directory
            processed_path = os.path.join(PROCESSED_DIR, os.path.basename(video_path))
            try:
                os.rename(video_path, processed_path)
                logger.info(f"Moved processed file to: {processed_path}")
            except Exception as e:
                logger.warning(f"Could not move file to processed directory: {str(e)}")
            
    except Exception as e:
        logger.error(f"Error in gesture analysis: {str(e)}")
        # Make sure to release video capture even if error occurs
        try:
            cap.release()
        except:
            pass

def control_device(device, state):
    """
    Control ESP32 device based on gesture recognition
    """
    if device in device_states:
        device_states[device] = state
        logger.info(f"Device {device} set to {'ON' if state else 'OFF'}")
        
        # Here you would send the command to your ESP32
        # For example, using HTTP requests or MQTT
        # requests.post(f'http://esp32_ip/control', json={'device': device, 'state': state})

def video_processor_worker():
    """
    Background worker to process video chunks from the queue
    """
    while processing_active:
        try:
            # Get video from queue with timeout
            video_data = video_queue.get(timeout=1)
            
            if video_data is None:  # Shutdown signal
                break
                
            video_path, chunk_id, timestamp, is_live = video_data
            
            # Process the video
            gesture_analysis(video_path, chunk_id, timestamp, is_live)
            
            # Mark task as done
            video_queue.task_done()
            
        except queue.Empty:
            continue
        except Exception as e:
            logger.error(f"Error in video processor worker: {str(e)}")

# Start background video processor
processor_thread = threading.Thread(target=video_processor_worker, daemon=True)
processor_thread.start()

@app.route('/')
def index():
    """
    Serve the HTML interface
    """
    # You can return your HTML file here or use render_template
    return render_template("index.html")

@app.route('/control', methods=['POST'])
def control():
    """
    Handle device control requests
    """
    try:
        data = request.get_json()
        device = data.get('device')
        state = data.get('state')
        
        if device in device_states:
            device_states[device] = state
            logger.info(f"Manual control: {device} set to {'ON' if state else 'OFF'}")
            
            # Send command to ESP32 here
            # Your ESP32 communication code
            
            return jsonify({'success': True, 'device': device, 'state': state})
        else:
            return jsonify({'error': 'Invalid device'}), 400
            
    except Exception as e:
        logger.error(f"Error in control endpoint: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/status', methods=['GET'])
def status():
    """
    Get current device states
    """
    return jsonify(device_states)

@app.route('/upload', methods=['POST'])
def upload():
    """
    Handle video upload from live stream or manual recording
    """
    try:
        if 'video' not in request.files:
            return jsonify({'error': 'No video file'}), 400
            
        video = request.files['video']
        
        if video.filename == '':
            return jsonify({'error': 'No file selected'}), 400
            
        # Get additional data
        chunk_id = request.form.get('chunk_id')
        timestamp = request.form.get('timestamp')
        is_live_stream = request.form.get('is_live_stream', 'false').lower() == 'true'
        
        # Generate filename
        if is_live_stream:
            filename = f"live_chunk_{chunk_id}_{int(time.time())}.webm"
        else:
            filename = f"recording_{int(time.time())}_{video.filename}"
            
        filepath = os.path.join(UPLOAD_DIR, filename)
        
        # Save the video file
        video.save(filepath)
        logger.info(f"Saved {'live stream chunk' if is_live_stream else 'video'}: {filepath}")
        
        # Add to processing queue
        try:
            video_queue.put_nowait((filepath, chunk_id, timestamp, is_live_stream))
        except queue.Full:
            logger.warning("Video processing queue is full, skipping oldest item")
            try:
                # Remove oldest item and add new one
                old_item = video_queue.get_nowait()
                video_queue.put_nowait((filepath, chunk_id, timestamp, is_live_stream))
            except queue.Empty:
                video_queue.put_nowait((filepath, chunk_id, timestamp, is_live_stream))
        
        return jsonify({
            'success': True, 
            'filename': filename,
            'is_live_stream': is_live_stream,
            'chunk_id': chunk_id
        })
        
    except Exception as e:
        logger.error(f"Error in upload endpoint: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/stream_stats', methods=['GET'])
def stream_stats():
    """
    Get streaming statistics
    """
    return jsonify({
        'queue_size': video_queue.qsize(),
        'processing_active': processing_active,
        'upload_dir_files': len(os.listdir(UPLOAD_DIR)) if os.path.exists(UPLOAD_DIR) else 0,
        'processed_dir_files': len(os.listdir(PROCESSED_DIR)) if os.path.exists(PROCESSED_DIR) else 0
    })

@app.route('/cleanup', methods=['POST'])
def cleanup():
    """
    Cleanup old video files
    """
    try:
        cleaned_files = 0
        
        # Clean upload directory
        for filename in os.listdir(UPLOAD_DIR):
            filepath = os.path.join(UPLOAD_DIR, filename)
            # Delete files older than 1 hour
            if os.path.getmtime(filepath) < time.time() - 3600:
                os.remove(filepath)
                cleaned_files += 1
                
        # Clean processed directory  
        for filename in os.listdir(PROCESSED_DIR):
            filepath = os.path.join(PROCESSED_DIR, filename)
            # Delete files older than 24 hours
            if os.path.getmtime(filepath) < time.time() - 86400:
                os.remove(filepath)
                cleaned_files += 1
                
        return jsonify({'success': True, 'cleaned_files': cleaned_files})
        
    except Exception as e:
        logger.error(f"Error in cleanup: {str(e)}")
        return jsonify({'error': str(e)}), 500

def shutdown_handler():
    """
    Graceful shutdown handler
    """
    global processing_active
    processing_active = False
    video_queue.put(None)  # Signal to stop worker
    processor_thread.join(timeout=5)

if __name__ == '__main__':
    try:
        # Run the Flask app
        app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        shutdown_handler()