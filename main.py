import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import time

# https://www.youtube.com/watch?v=1lN4L74BwWo

"""
mp_hands is old and the new API requires more work.
API expects you to explicitly load a hand-landmarker model file and configure how you're using it
"""
#mp_hands = mp.solutions.hands        # finds the hands
#mp_draw = mp.solutions.drawing_utils # draws on the hands

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


cap = cv2.VideoCapture(0)            # 0 is default webcam

def main():

    # MediaPipe video mode requires each timestamp to be greater than the last
    timestamp_ms = 0

    # success means capture is good and the frame object is called "frame"
    while True:
        success, frame = cap.read()
        attempts = 0
        while not success and attempts <= 5:   # caps our retries when the frame isn't read
            time.sleep(1)
            attempts += 1
            success, frame = cap.read()
        if not success:                         # lets the use know the frame isn't captured
            print("Frame is not being captured in main")
            break

        #---------Prepare the frame----------#
        image = cv2.flip(frame, 1) # flip the captured frame for mirroring

        # OpenCV BGR -> RGB
        rgb_frame = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # OpenCV image -> MediaPipe image
        mp_image = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=rgb_frame
        )

        #----------------MEDIAPIPE----------------#

        # MediaPipe needs a timestamp for video mode
        timestamp_ms += 1

        # Send this frame to the hand detector
        result = landmarker.detect_for_video(
            mp_image,
            timestamp_ms
        )

        # just to see if hands were found
        print("Number of hands:", len(result.hand_landmarks))

        # Draw each detected hand's landmarks
        height, width, _ = image.shape

        for hand in result.hand_landmarks:
            for landmark in hand:
                # Convert MediaPipe coordinates to OpenCV pixel coordinates
                x = int(landmark.x * width)
                y = int(landmark.y * height)

                cv2.circle(image, (x, y), 5, (0, 255, 0), -1)

        # ---------------- DISPLAY ----------------

        cv2.imshow("Frame", image)


        # how to close the window capture by breaking the while loop
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    landmarker.close()



if __name__ == "__main__":
    main()
