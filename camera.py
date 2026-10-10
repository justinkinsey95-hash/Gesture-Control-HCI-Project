import cv2
import mediapipe as mp


def setup_camera():
    cam = cv2.VideoCapture(0) # 0 for default webcam
    cam.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    return cam

def prepare_frame(frame):
    image = cv2.flip(frame, 1)  # flip the captured frame for mirroring

    # OpenCV BGR -> RGB
    rgb_frame = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    # OpenCV image -> MediaPipe image
    mp_image = mp.Image(
        image_format=mp.ImageFormat.SRGB,
        data=rgb_frame
    )

    return image, mp_image

def track_hands(landmarker, mp_image, timestamp_ms):
    """
    This method contains the landmark data.
    Sends the prepared MediaPipe image to the hand landmarker.
    Landmarker is what does the heavy lifting with tracking.
    Returns MediaPipe's detection result.
    """

    result = landmarker.detect_for_video(
        mp_image,
        timestamp_ms
    )

    return result

def draw_landmarks_on_hands(image, result):
    """
    returned image gets shown with cv2.imshow()
    :param image:
    :param result:
    :return:
    """
    height, width, _ = image.shape

    # Go through each detected hand
    for hand in result.hand_landmarks:

        # Go through the 21 landmarks for that hand
        for landmark in hand:
            # MediaPipe normalized coordinates -> OpenCV pixel coordinates
            x = int(landmark.x * width)
            y = int(landmark.y * height)

            # Draw landmark
            cv2.circle(image, (x, y), 5, (0, 255, 0), -1)

    return image
