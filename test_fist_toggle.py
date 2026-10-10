import unittest
from types import SimpleNamespace

import gestures


class FistToggleTests(unittest.TestCase):
    def setUp(self):
        self.now = 0
        self.toggle = gestures.FistToggle(lambda: self.now)
        self.hand = [SimpleNamespace(x=0, y=1) for _ in range(21)]
        self.hand[0] = SimpleNamespace(x=0, y=0)
        for tip in (8, 12, 16, 20):
            self.hand[tip].y = .5

    def feed(self, seconds, closed=True, hands=1):
        self.now = seconds
        self.hand[8].y = .5 if closed else 1.5
        return self.toggle.update(SimpleNamespace(hand_landmarks=[self.hand] * hands))

    def hold(self, start):
        duration = self.toggle.required_hold_seconds
        for step in range(round(duration / .25)):
            self.assertFalse(self.feed(start + step * .25))
        self.assertTrue(self.feed(start + duration))

    def test_enable_release_and_stop(self):
        self.hold(0)
        self.assertTrue(self.toggle.enabled)
        for step in range(1, 13):
            self.assertFalse(self.feed(2 + step * .25))
        self.assertTrue(self.toggle.enabled)
        self.feed(5.1, closed=False)
        self.hold(5.2)
        self.assertFalse(self.toggle.enabled)
        self.assertEqual(self.toggle.hold_seconds, 1.0)
        self.assertIn("1.00/1.00s", self.toggle.hold_label)

    def test_open_hand_interrupts_hold(self):
        self.feed(0)
        self.feed(.5)
        self.feed(1, closed=False)
        self.hold(1.1)

    def test_gap_does_not_count_as_hold_or_disable(self):
        self.feed(0)
        self.assertFalse(self.feed(2))
        self.assertFalse(self.toggle.enabled)
        self.hold(3)
        self.feed(5.1, hands=0)
        self.assertTrue(self.toggle.enabled)
        self.assertFalse(self.feed(5.2))

    def test_multiple_hands_interrupt_hold(self):
        self.feed(0)
        self.feed(.5, hands=2)
        self.hold(.6)

    def test_rotation_and_mirror(self):
        self.assertTrue(gestures.is_closed_fist(self.hand))
        for point in self.hand:
            point.x, point.y = -point.y, point.x
        self.assertTrue(gestures.is_closed_fist(self.hand))

    def test_timer_feedback_tracks_and_resets(self):
        self.assertEqual(self.toggle.hold_seconds, 0)
        self.assertIn("waiting", self.toggle.hold_label)
        self.feed(0)
        self.assertIn("tracking", self.toggle.hold_label)
        self.feed(.5)
        self.assertEqual(self.toggle.hold_seconds, .5)
        self.feed(.6, closed=False)
        self.assertEqual(self.toggle.hold_seconds, 0)
        self.assertIn("waiting", self.toggle.hold_label)
        self.hold(1)
        self.assertEqual(self.toggle.hold_seconds, 1.25)
        self.assertIn("release", self.toggle.hold_label)
        self.feed(3.1, hands=0)
        self.assertEqual(self.toggle.hold_seconds, 0)
        self.toggle.reset()
        self.assertIn("waiting", self.toggle.hold_label)
