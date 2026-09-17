import cv2
import mediapipe as mp
import time
import camera


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

        # draw landmarks
        image = camera.draw_landmarks_on_hands(image, result)

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
