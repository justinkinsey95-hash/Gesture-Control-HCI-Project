import cv2
import mediapipe as mp
import time
import camera
import gestures


# the boilerplate new API setup for configuring the detector
BaseOptions = mp.tasks.BaseOptions
HandLandmarker = mp.tasks.vision.HandLandmarker
HandLandmarkerOptions = mp.tasks.vision.HandLandmarkerOptions
RunningMode = mp.tasks.vision.RunningMode

options = HandLandmarkerOptions(
    base_options=BaseOptions(
        model_asset_path="hand_landmarker.task"
    ),
    running_mode=RunningMode.VIDEO,
    num_hands=2
)

landmarker = HandLandmarker.create_from_options(options)

def main():
    cap = camera.setup_camera()
    timestamp_ms = 0
    gesture_label = "Show one hand to swipe"
    label_frames_left = 0
    gestures.reset()

    while cap.isOpened():
        success, frame = cap.read()
        attempts = 0

        while not success and attempts <= 5:  # caps our attempts to retry getting frames
            time.sleep(1)
            attempts += 1
            success, frame = cap.read()

        if not success:
            print("Frame is not being captured in main")
            break

        # Prepare the frame
        image, mp_image = camera.prepare_frame(frame) # image -> mirroring, mp_image -> mediapipe

        # Mediapipe needs a timestamp for video mode
        timestamp_ms += 1

        # detect landmarks
        result = camera.track_hands(
            landmarker,
            mp_image,
            timestamp_ms
        )

        height, width = image.shape[:2]
        gestures.update_history(result, timestamp_ms, width, height)
        gesture = gestures.detect_gesture()
        if gesture:
            print(gesture)
            gesture_label = gesture.replace("_", " ")
            label_frames_left = 30

        # draw landmarks
        image = camera.draw_landmarks_on_hands(image, result)

        if label_frames_left > 0:
            label_frames_left -= 1
        else:
            if len(result.hand_landmarks) != 1:
                gesture_label = "Show one hand to swipe"
            elif gestures.waiting_for_rest:
                gesture_label = "Hold hand steady"
            else:
                gesture_label = "Ready to swipe"
        cv2.putText(image, gesture_label, (20, 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

        # Display landmarked hand(s)
        cv2.imshow("Frame", image)

        # how to close the window capture by breaking the while loop
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break



    cap.release()
    cv2.destroyAllWindows()
    landmarker.close()



if __name__ == "__main__":
    main()
