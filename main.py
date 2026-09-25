import cv2
import mediapipe as mp
import camera
import gestures
import computer_inputs

WINDOW_TITLE = "Gesture Control"


def main():
    backend = computer_inputs.WindowsInput()
    scrolling = computer_inputs.ScrollController(backend)
    options = mp.tasks.vision.HandLandmarkerOptions(
        base_options=mp.tasks.BaseOptions(model_asset_path="hand_landmarker.task"),
        running_mode=mp.tasks.vision.RunningMode.VIDEO,
        num_hands=2,
    )
    cap = None
    paused = False
    previous_target = None
    timestamp_ms = 0
    gestures.reset()
    with mp.tasks.vision.HandLandmarker.create_from_options(options) as landmarker:
        try:
            cap = camera.setup_camera()
            if not cap.isOpened():
                raise RuntimeError("Could not open the webcam.")
            cv2.namedWindow(WINDOW_TITLE, cv2.WINDOW_NORMAL)
            cv2.resizeWindow(WINDOW_TITLE, 480, 360)
            backend.pin_preview(WINDOW_TITLE)
            while cap.isOpened():
                toggle_pause, quit_requested = backend.shortcuts()
                if quit_requested:
                    break
                if toggle_pause:
                    paused = not paused
                    scrolling.cancel()
                    gestures.reset()
                success, frame = cap.read()
                if not success:
                    scrolling.cancel()
                    raise RuntimeError("Webcam capture stopped. Restart the application to retry.")

                image, mp_image = camera.prepare_frame(frame)
                timestamp_ms += 1
                result = camera.track_hands(landmarker, mp_image, timestamp_ms)
                height, width = image.shape[:2]
                target = backend.target()
                if target != previous_target:
                    scrolling.cancel()
                    gestures.reset()
                previous_target = target
                allowed = not paused and target is not None and len(result.hand_landmarks) == 1
                if allowed:
                    gestures.update_history(result, timestamp_ms, width, height)
                    # Discard gestures during a burst rather than queue them.
                    gesture = gestures.detect_gesture()
                    if gesture:
                        scrolling.start(gesture, target)
                else:
                    gestures.reset()
                scrolling.tick(allowed)

                if paused:
                    label = "Paused - F8 to resume"
                elif target is None:
                    label = "Click browser; point at page"
                elif len(result.hand_landmarks) != 1:
                    label = "Show one hand to swipe"
                elif scrolling.direction:
                    label = "Scrolling " + scrolling.direction
                elif gestures.waiting_for_rest:
                    label = "Hold hand steady"
                else:
                    label = "Ready to swipe"
                image = camera.draw_landmarks_on_hands(image, result)
                camera.draw_scroll_feedback(image, scrolling.direction, label)
                cv2.imshow(WINDOW_TITLE, image)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                if cv2.getWindowProperty(WINDOW_TITLE, cv2.WND_PROP_VISIBLE) < 1:
                    break
        finally:
            scrolling.cancel()
            if cap is not None:
                cap.release()
            cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
