import cv2
import mediapipe as mp
import camera
import gestures
import computer_inputs
import ui

WINDOW_TITLE = "Gesture Control"


def main():
    ui.enable_windows_dpi_awareness()
    backend = computer_inputs.WindowsInput()
    scrolling = computer_inputs.ScrollController(backend)
    fist = gestures.FistToggle()
    finger = gestures.FingerScrollGesture()
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
            cv2.namedWindow(WINDOW_TITLE, cv2.WINDOW_NORMAL | cv2.WINDOW_FREERATIO)
            cv2.resizeWindow(WINDOW_TITLE, *ui.DEFAULT_SIZE)
            backend.pin_preview(WINDOW_TITLE)
            while cap.isOpened():
                toggle_pause, quit_requested = backend.shortcuts()
                if quit_requested:
                    break
                if toggle_pause:
                    paused = not paused
                    scrolling.cancel()
                    gestures.reset()
                    fist.reset()
                    finger.reset()
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
                    fist.reset()
                    finger.reset()
                previous_target = target
                allowed = not paused and target is not None
                if allowed and fist.update(result):
                    gestures.reset()
                    finger.reset()
                    if not fist.enabled:
                        scrolling.cancel()
                if allowed and fist.enabled and not scrolling.direction:
                    gesture = finger.update(result, width, height)
                    if gesture:
                        scrolling.start(gesture, target)
                else:
                    finger.reset()
                scrolling.tick(allowed)

                presentation = ui.derive_ui_state(
                    paused=paused, target_available=target is not None,
                    fist_enabled=fist.enabled, fist_visible=fist.fist_visible,
                    hold_seconds=fist.hold_seconds,
                    required_hold_seconds=fist.required_hold_seconds,
                    scrolling_direction=scrolling.direction,
                    hand_count=len(result.hand_landmarks), finger_label=finger.label,
                    fist_latched=fist.latched,
                )
                image = camera.draw_landmarks_on_hands(image, result)
                cv2.imshow(WINDOW_TITLE, ui.compose_frame(
                    image, presentation, ui.window_render_size(WINDOW_TITLE)))
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
