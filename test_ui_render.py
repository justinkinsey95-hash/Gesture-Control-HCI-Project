import importlib.util
import unittest
from unittest.mock import patch

from ui import DEFAULT_SIZE, compose_frame, derive_ui_state, window_render_size, wrap_text


@unittest.skipUnless(importlib.util.find_spec("cv2") and importlib.util.find_spec("numpy"),
                     "Rendering tests require OpenCV and NumPy")
class RenderTests(unittest.TestCase):
    def state(self, **changes):
        defaults = dict(paused=False, target_available=True, fist_enabled=False,
                        fist_visible=False, hold_seconds=0, required_hold_seconds=1.25,
                        scrolling_direction=None, hand_count=1, finger_label="")
        return derive_ui_state(**dict(defaults, **changes))

    def test_camera_is_not_mutated_or_stretched(self):
        import numpy as np
        camera = np.full((480, 640, 3), (1, 2, 3), dtype=np.uint8)
        original = camera.copy()
        rendered = compose_frame(camera, self.state())
        self.assertEqual(rendered.shape, (550, 550, 3))
        np.testing.assert_array_equal(camera, original)
        # The 4:3 camera occupies 301x226, centered in its 518x226 region.
        mask = np.all(rendered == (1, 2, 3), axis=2)
        ys, xs = np.where(mask)
        self.assertEqual((xs.min(), xs.max(), ys.min(), ys.max()), (124, 424, 240, 465))

    def test_only_camera_is_resized_and_ui_uses_viewport_pixels(self):
        import cv2
        import numpy as np
        camera = np.full((480, 640, 3), 50, dtype=np.uint8)
        for width, height in (DEFAULT_SIZE, (825, 825), (700, 550), (550, 700)):
            with patch.object(cv2, "resize", wraps=cv2.resize) as resize:
                rendered = compose_frame(camera, self.state(), (width, height))
                self.assertEqual(rendered.shape, (height, width, 3))
                resize.assert_called_once()
                self.assertIs(resize.call_args.args[0], camera)
                self.assertEqual(resize.call_args.kwargs["interpolation"], cv2.INTER_AREA)

    def test_wide_and_portrait_camera_aspect_ratios(self):
        import numpy as np
        for width, height in ((1280, 720), (480, 640)):
            camera = np.full((height, width, 3), (1, 2, 3), dtype=np.uint8)
            frame = compose_frame(camera, self.state())
            ys, xs = np.where(np.all(frame == (1, 2, 3), axis=2))
            actual_w, actual_h = xs.max() - xs.min() + 1, ys.max() - ys.min() + 1
            self.assertLessEqual(abs(actual_w - actual_h * width / height), 1)

    def test_wrapped_text_fits_without_shrinking(self):
        import cv2
        def measure(value, scale):
            return cv2.getTextSize(value, cv2.FONT_HERSHEY_SIMPLEX, scale, 1)[0][0]
        changes = ({"target_available": False}, {"paused": True},
                   {"fist_enabled": True}, {"fist_visible": True},
                   {"fist_enabled": True, "scrolling_direction": "down"},
                   {"fist_enabled": True, "finger_label": "Finger up: 0.9/1.0s"},
                   {"fist_enabled": True, "hand_count": 0},
                   {"fist_latched": True, "fist_visible": True})
        for change in changes:
            state = self.state(**change)
            for label, width, scale in ((state.guidance, 506, .55),
                                        (state.current, 240, .5),
                                        (state.next_action, 240, .5)):
                lines = wrap_text(label, width, scale, measure)
                self.assertLessEqual(len(lines), 2, label)
                for line in lines:
                    self.assertLessEqual(measure(line, scale), width)

    def test_window_size_follows_actual_viewport_and_falls_back(self):
        import cv2
        with patch.object(cv2, "getWindowImageRect", return_value=(0, 0, 825, 825)):
            self.assertEqual(window_render_size("test"), (825, 825))
        with patch.object(cv2, "getWindowImageRect", return_value=(0, 0, 0, 0)):
            self.assertEqual(window_render_size("test"), DEFAULT_SIZE)
        with patch.object(cv2, "getWindowImageRect", side_effect=cv2.error("unavailable")):
            self.assertEqual(window_render_size("test"), DEFAULT_SIZE)
