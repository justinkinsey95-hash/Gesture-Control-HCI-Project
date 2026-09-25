import unittest
from types import SimpleNamespace
from unittest.mock import patch

import gestures


class SwipeTests(unittest.TestCase):
    def setUp(self):
        gestures.reset()

    def feed(self, positions, settle=True):
        if settle:
            y = positions[0][1]
            self.feed([(-.4, y), (0, y)], settle=False)
        detected = []
        for seconds, y in positions:
            gestures.history.append({
                "recorded_at": seconds,
                "index": (300, y),
                "thumb": (240, 400),
                "index_base": (300, 300),
                "wrist": (300, 410),
            })
            gesture = gestures.detect_gesture()
            if gesture:
                detected.append(gesture)
        return detected

    def test_down_then_return_does_not_trigger_up(self):
        detected = self.feed([
            (0, 200), (.15, 240), (.3, 280), (.45, 300),
            (.6, 270), (.75, 240), (.9, 200), (1.25, 200),
        ])
        self.assertEqual(detected, ["SWIPE_DOWN"])
        self.assertFalse(gestures.waiting_for_rest)

    def test_up_then_return_does_not_trigger_down(self):
        detected = self.feed([
            (0, 300), (.2, 270), (.4, 230), (.6, 200),
            (.8, 230), (1, 270), (1.2, 300), (1.55, 300),
        ])
        self.assertEqual(detected, ["SWIPE_UP"])
        self.assertFalse(gestures.waiting_for_rest)

    def test_deliberate_swipe_after_rest_is_detected(self):
        detected = self.feed([
            (0, 200), (.15, 240), (.3, 280), (.45, 300),
            (.6, 270), (.75, 240), (.9, 200), (1.25, 200),
            (1.4, 240), (1.55, 280),
        ])
        self.assertEqual(detected, ["SWIPE_DOWN", "SWIPE_DOWN"])

    def feed_thumb_path(self, points, settle=True):
        if settle:
            # Hold the first pose long enough to arm before exercising the path.
            x, y, thumb_y = points[0]
            for seconds in (-.4, 0):
                gestures.history.append({
                    "recorded_at": seconds, "index": (x, y),
                    "thumb": (100, thumb_y), "index_base": (500, 400),
                    "wrist": (500, 500),
                })
                gestures.detect_gesture()
        detected = []
        for frame, (x, y, thumb_y) in enumerate(points):
            gestures.history.append({
                "recorded_at": frame * 0.15,
                "index": (x, y),
                "thumb": (100, thumb_y),
                # The base position must not restrict which poses can swipe.
                "index_base": (500, 400),
                "wrist": (500, 500),
            })
            gesture = gestures.detect_gesture()
            if gesture:
                detected.append(gesture)
        return detected

    def test_angled_down_and_return(self):
        self.assertEqual(self.feed_thumb_path([
            (300, 200, 250), (330, 250, 250), (360, 300, 250),
            (330, 250, 250), (300, 200, 250),
        ]), ["SWIPE_DOWN"])

    def test_angled_up_and_return(self):
        self.assertEqual(self.feed_thumb_path([
            (360, 300, 250), (330, 250, 250), (300, 200, 250),
            (330, 250, 250), (360, 300, 250),
        ]), ["SWIPE_UP"])

    def test_thumb_movement_alone_does_not_trigger(self):
        self.assertEqual(self.feed_thumb_path([
            (300, 250, 300), (300, 250, 250), (300, 250, 200),
        ]), [])

    def test_small_crossing_does_not_trigger(self):
        self.assertEqual(self.feed_thumb_path([
            (300, 245, 250), (302, 255, 250),
        ]), [])

    def test_sideways_detour_does_not_trigger(self):
        self.assertEqual(self.feed_thumb_path([
            (300, 200, 250), (450, 250, 250), (300, 300, 250),
        ]), [])

    def test_entry_motion_is_ignored(self):
        self.assertEqual(self.feed([(0, 300), (.1, 270), (.2, 200)], settle=False), [])
        self.assertTrue(gestures.waiting_for_rest)
        self.assertEqual(self.feed([(.6, 200)], settle=False), [])
        self.assertFalse(gestures.waiting_for_rest)
        self.assertEqual(len(gestures.history), 1)

    def test_palm_must_be_steady_too(self):
        self.feed([(0, 300)], settle=False)
        sample = dict(gestures.history[-1])
        sample.update(recorded_at=.4, wrist=(330, 410))
        gestures.history.append(sample)
        self.assertIsNone(gestures.detect_gesture())
        self.assertTrue(gestures.waiting_for_rest)

    def test_tracking_loss_requires_settling_again(self):
        self.feed([(0, 300)])
        self.assertFalse(gestures.waiting_for_rest)
        gestures.update_history(SimpleNamespace(hand_landmarks=[]), 1, 640, 480)
        self.assertTrue(gestures.waiting_for_rest)
        self.assertEqual(self.feed([(1, 300), (1.1, 200)], settle=False), [])

    def test_either_mirrored_hand_can_arm_and_swipe(self):
        for mirror in (False, True):
            with self.subTest(mirror=mirror):
                gestures.reset()
                detected = []
                for seconds, y in ((0, 300), (.2, 300), (.4, 300), (.55, 270), (.7, 200)):
                    hand = [SimpleNamespace(x=.5, y=.5) for _ in range(21)]
                    for number, x, pixel_y in ((0, 300, 410), (5, 300, 300),
                                                (8, 300, y), (4, 240, 400)):
                        hand[number] = SimpleNamespace(x=(640-x if mirror else x)/640, y=pixel_y/480)
                    with patch.object(gestures, "perf_counter", return_value=seconds):
                        gestures.update_history(SimpleNamespace(hand_landmarks=[hand]), 1, 640, 480)
                    result = gestures.detect_gesture()
                    if result:
                        detected.append(result)
                self.assertEqual(detected, ["SWIPE_UP"])

    def test_swipes_do_not_require_crossing_thumb_or_nearing_base(self):
        for mirror in (False, True):
            for ys, expected in (([220, 190, 150], "SWIPE_UP"),
                                 ([150, 180, 220], "SWIPE_DOWN")):
                with self.subTest(mirror=mirror, expected=expected):
                    gestures.reset()
                    x = 200 if mirror else 440
                    self.assertEqual(self.feed_thumb_path([(x, y, 400) for y in ys]), [expected])

    def test_old_downward_path_cannot_win_after_upward_reversal(self):
        # Directly inspect a window that contains both directions.
        for seconds, y in enumerate((200, 240, 280, 300, 270)):
            gestures.history.append({"index": (300, y), "recorded_at": seconds * .1,
                                     "index_base": (300, 300), "wrist": (300, 410)})
        self.assertFalse(gestures.detect_swipe_down())
        self.assertFalse(gestures.detect_swipe_up())
        gestures.history.append({"index": (300, 230), "recorded_at": .5,
                                 "index_base": (300, 300), "wrist": (300, 410)})
        self.assertTrue(gestures.detect_swipe_up())
        self.assertFalse(gestures.detect_swipe_down())

    def test_small_jitter_does_not_reset_direction(self):
        self.assertEqual(self.feed([(0, 300), (.1, 275), (.2, 280),
                                    (.3, 260), (.4, 235)]), ["SWIPE_UP"])

    def feed_relative_motion(self, frames, palm_size=100, mirror=False):
        detected = []
        for seconds, hand_y, finger_y in frames:
            x = 220 if mirror else 420
            gestures.history.append({
                "recorded_at": seconds,
                "index": (x, hand_y + finger_y),
                "index_base": (x, hand_y),
                "wrist": (x, hand_y + palm_size),
                "thumb": (x + (-30 if mirror else 30), hand_y + 30),
            })
            result = gestures.detect_gesture()
            if result:
                detected.append(result)
        return detected

    def test_whole_hand_leaving_frame_is_not_a_swipe(self):
        self.assertEqual(self.feed_relative_motion([
            (0, 250, -40), (.4, 250, -40), (.5, 280, -40),
            (.6, 320, -38), (.7, 390, -42), (.8, 450, -40),
        ]), [])

    def test_small_hand_can_swipe_both_directions(self):
        for mirror in (False, True):
            for sign, expected in ((-1, "SWIPE_UP"), (1, "SWIPE_DOWN")):
                with self.subTest(mirror=mirror, expected=expected):
                    gestures.reset()
                    self.assertEqual(self.feed_relative_motion([
                        (0, 250, -40), (.4, 250, -40),
                        (.55, 250, -40 + sign * 15), (.7, 250, -40 + sign * 30),
                    ], palm_size=50, mirror=mirror), [expected])

    def test_finger_swipe_with_small_palm_drift(self):
        self.assertEqual(self.feed_relative_motion([
            (0, 250, 0), (.4, 250, 0), (.55, 255, -25), (.7, 260, -55),
        ]), ["SWIPE_UP"])

    def test_moving_palm_under_stationary_tip_is_not_swipe(self):
        self.assertEqual(self.feed_relative_motion([
            (0, 250, -40), (.4, 250, -40), (.55, 280, -70), (.7, 310, -100),
        ]), [])


if __name__ == "__main__":
    unittest.main()
