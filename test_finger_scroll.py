import unittest
from types import SimpleNamespace

from gestures import FingerScrollGesture


class FingerScrollTests(unittest.TestCase):
    def setUp(self):
        self.now = 0
        self.detector = FingerScrollGesture(lambda: self.now)

    def feed(self, seconds, tip_y=350, offset=0, scale=1, mirror=False, hands=1):
        self.now = seconds
        hand = [SimpleNamespace(x=.5, y=(400 * scale + offset) / 480)
                for _ in range(21)]
        for index, y in ((0, 450), (5, 350), (6, 300), (8, tip_y),
                         (10, 300), (12, 350), (14, 300), (16, 350),
                         (18, 300), (20, 350)):
            hand[index].y = (y * scale + offset) / 480
            hand[index].x = .4 if mirror else .6
        result = SimpleNamespace(hand_landmarks=[hand] * hands)
        return self.detector.update(result, 640, 480)

    def test_up_waits_for_one_second(self):
        self.feed(0)
        self.assertIsNone(self.feed(.1, 200))
        for seconds in (.3, .6, .9, 1.09):
            self.assertIsNone(self.feed(seconds, 200))
        self.assertEqual(self.feed(1.11, 200), "SWIPE_UP")

    def test_immediate_return_means_down(self):
        self.feed(0)
        self.assertIsNone(self.feed(.1, 200))
        self.assertEqual(self.feed(.3, 350), "SWIPE_DOWN")
        self.assertIsNone(self.feed(.4, 350))

    def test_partial_return_means_down(self):
        self.feed(0)
        self.feed(.1, 200)
        self.assertEqual(self.feed(.3, 240), "SWIPE_DOWN")

    def test_tracking_loss_discards_pending_gesture(self):
        self.feed(0)
        self.feed(.1, 200)
        self.feed(.2, hands=0)
        for seconds in (.3, .6, .9, 1.2, 1.5):
            self.assertIsNone(self.feed(seconds, 200))

    def test_camera_gap_does_not_complete_hold(self):
        self.feed(0)
        self.feed(.1, 200)
        self.assertIsNone(self.feed(1.2, 200))

    def test_whole_hand_motion_does_not_trigger(self):
        self.feed(0)
        for step in range(1, 9):
            self.assertIsNone(self.feed(step * .2, offset=-step * 20))

    def test_small_motion_does_not_trigger(self):
        self.feed(0)
        self.feed(.1, 330)
        self.assertIsNone(self.feed(.3, 350))

    def test_both_directions_with_smaller_and_mirrored_hands(self):
        for mirror in (False, True):
            for scale in (.5, 1):
                for up in (False, True):
                    with self.subTest(mirror=mirror, scale=scale, up=up):
                        self.setUp()
                        self.feed(0, scale=scale, mirror=mirror)
                        self.feed(.1, 200, scale=scale, mirror=mirror)
                        if up:
                            for seconds in (.4, .7, 1):
                                self.feed(seconds, 200, scale=scale, mirror=mirror)
                            actual = self.feed(1.11, 200, scale=scale, mirror=mirror)
                        else:
                            actual = self.feed(.3, 350, scale=scale, mirror=mirror)
                        self.assertEqual(actual, "SWIPE_UP" if up else "SWIPE_DOWN")
