import cv2
import mediapipe as mp
from interactor import ESP32Interactor
import time

# Maps: thumb to pinky → pin list
FINGER_TO_PIN = {
    0: 13,  # Thumb
    1: 12,  # Index
    2: 14,  # Middle
    3: 27,  # Ring
    4: 26   # Pinky
}

mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils

def get_finger_states(hand_landmarks) -> list[int]:
    """
    Returns a list of 5 binary values (1 for extended, 0 for folded)
    Order: [Thumb, Index, Middle, Ring, Pinky]
    """
    fingers = []

    # Thumb: compare tip x to IP x (left/right flip based on handedness later)
    thumb_tip = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP]
    thumb_ip  = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_IP]
    fingers.append(int(thumb_tip.x < thumb_ip.x))  # Assuming one hand facing palm

    # For other fingers: tip y < pip y → extended
    finger_tips = [mp_hands.HandLandmark.INDEX_FINGER_TIP,
                   mp_hands.HandLandmark.MIDDLE_FINGER_TIP,
                   mp_hands.HandLandmark.RING_FINGER_TIP,
                   mp_hands.HandLandmark.PINKY_TIP]
    
    finger_pips = [mp_hands.HandLandmark.INDEX_FINGER_PIP,
                   mp_hands.HandLandmark.MIDDLE_FINGER_PIP,
                   mp_hands.HandLandmark.RING_FINGER_PIP,
                   mp_hands.HandLandmark.PINKY_PIP]

    for tip_idx, pip_idx in zip(finger_tips, finger_pips):
        tip = hand_landmarks.landmark[tip_idx]
        pip = hand_landmarks.landmark[pip_idx]
        fingers.append(int(tip.y < pip.y))  # Lower y means higher in image

    return fingers

def gesture():
    cap = cv2.VideoCapture(0)
    esp = ESP32Interactor("192.168.137.24", 1234)
    last_state = [0, 0, 0, 0, 0]  # Store previous finger states

    with mp_hands.Hands(static_image_mode=False, max_num_hands=1, min_detection_confidence=0.6) as hands:
        try:
            print("Starting gesture control. Press 'q' to quit.")
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                frame = cv2.flip(frame, 1)
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                result = hands.process(rgb)

                if result.multi_hand_landmarks:
                    for hand_landmarks in result.multi_hand_landmarks:
                        mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

                        states = get_finger_states(hand_landmarks)

                        # Send pin updates if changed
                        for i, state in enumerate(states):
                            pin = FINGER_TO_PIN[i]
                            if state != last_state[i]:
                                esp.set_pin_state(pin, state)
                        last_state = states

                cv2.imshow("Hand Gesture", frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
        finally:
            cap.release()
            cv2.destroyAllWindows()
            esp.disconnect()

gesture()