import unittest

from computer_inputs import ScrollController, SCROLL_AMOUNT, MAX_STEP


class FakeBackend:
    def __init__(self):
        self.window = 123
        self.events = []

    def target(self):
        return self.window

    def wheel(self, delta):
        self.events.append(delta)


class ScrollTests(unittest.TestCase):
    def setUp(self):
        self.now = 0
        self.backend = FakeBackend()
        self.scroll = ScrollController(self.backend, lambda: self.now)

    def advance(self, seconds, allowed=True):
        self.now = seconds
        self.scroll.tick(allowed)

    def test_smooth_burst_both_directions(self):
        for gesture, sign in (("SWIPE_UP", 1), ("SWIPE_DOWN", -1)):
            with self.subTest(gesture=gesture):
                self.setUp()
                self.assertTrue(self.scroll.start(gesture, 123))
                self.assertEqual(self.backend.events, [])
                for frame in range(1, 16):
                    self.advance(frame / 30)
                self.assertEqual(sum(self.backend.events), SCROLL_AMOUNT * sign)
                self.assertGreater(len(self.backend.events), 8)
                self.assertTrue(all(0 < abs(delta) <= MAX_STEP for delta in self.backend.events))
                self.assertIsNone(self.scroll.direction)

    def test_focus_change_cancels_without_input(self):
        self.scroll.start("SWIPE_UP", 123)
        self.backend.window = 456
        self.advance(.03)
        self.assertEqual(self.backend.events, [])
        self.assertIsNone(self.scroll.direction)

    def test_pause_or_tracking_loss_cancels_without_resume(self):
        self.scroll.start("SWIPE_UP", 123)
        self.advance(.03, allowed=False)
        self.advance(.06)
        self.assertEqual(self.backend.events, [])
        self.assertIsNone(self.scroll.direction)

    def test_stall_does_not_replay_missed_input(self):
        self.scroll.start("SWIPE_UP", 123)
        self.advance(.25)
        self.advance(.28)
        self.assertEqual(self.backend.events, [])
        self.assertIsNone(self.scroll.direction)

    def test_repeated_swipes_are_not_queued(self):
        self.scroll.start("SWIPE_UP", 123)
        self.assertFalse(self.scroll.start("SWIPE_DOWN", 123))
        for frame in range(1, 20):
            self.advance(frame / 30)
        self.assertEqual(sum(self.backend.events), SCROLL_AMOUNT)

    def test_invalid_gesture_or_target_is_ignored(self):
        self.assertFalse(self.scroll.start("SWIPE_UP", None))
        self.assertFalse(self.scroll.start("OTHER", 123))

    def test_input_failure_clears_arrow(self):
        def fail(delta):
            raise OSError("blocked")
        self.backend.wheel = fail
        self.scroll.start("SWIPE_UP", 123)
        with self.assertRaises(OSError):
            self.advance(.04)
        self.assertIsNone(self.scroll.direction)

    def test_slow_frames_never_flush_large_remainder(self):
        self.scroll.start("SWIPE_UP", 123)
        for index in range(1, 6):
            self.advance(index * .1)
        self.assertTrue(all(delta <= MAX_STEP for delta in self.backend.events))
        self.assertLess(sum(self.backend.events), SCROLL_AMOUNT)
        self.assertIsNone(self.scroll.direction)


if __name__ == "__main__":
    unittest.main()
