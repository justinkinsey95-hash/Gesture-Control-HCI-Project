import unittest

from ui import derive_ui_state


class PresentationTests(unittest.TestCase):
    def state(self, **changes):
        values = dict(paused=False, target_available=True, fist_enabled=False,
                      fist_visible=False, hold_seconds=0, required_hold_seconds=1.25,
                      scrolling_direction=None, hand_count=1,
                      finger_label="Raise index; hold up or return down",
                      fist_latched=False)
        values.update(changes)
        return derive_ui_state(**values)

    def test_pause_has_highest_precedence(self):
        state = self.state(paused=True, target_available=False, fist_enabled=True,
                           scrolling_direction="up", fist_visible=True, hold_seconds=.5)
        self.assertEqual(state.status, "PAUSED")
        self.assertIsNone(state.progress)
        self.assertIsNone(state.direction)
        self.assertEqual(state.next_action, "Press F8 to resume")

    def test_missing_browser_overrides_activation_and_scroll(self):
        state = self.state(target_available=False, fist_enabled=True,
                           scrolling_direction="down", fist_visible=True)
        self.assertEqual(state.status, "BROWSER NEEDED")
        self.assertEqual(state.steps, ("current", "upcoming", "upcoming", "upcoming"))
        self.assertIsNone(state.progress)
        self.assertIsNone(state.direction)

    def test_browser_ready_is_not_activation(self):
        state = self.state()
        self.assertEqual(state.status, "INACTIVE")
        self.assertEqual(state.current, "Browser selected")
        self.assertEqual(state.steps[1], "current")
        self.assertIsNone(state.progress)

    def test_activation_progress_and_interruption(self):
        state = self.state(fist_visible=True, hold_seconds=.5)
        self.assertEqual(state.progress, .4)
        self.assertIn("1.25", state.timer)
        self.assertIn("activate", state.guidance)
        interrupted = self.state(fist_visible=False, hold_seconds=.5)
        self.assertIsNone(interrupted.progress)
        self.assertEqual(interrupted.timer, "")

    def test_activation_latch_does_not_show_stop_progress(self):
        state = self.state(fist_enabled=True, fist_visible=True, fist_latched=True,
                           hold_seconds=1.25, required_hold_seconds=1)
        self.assertEqual(state.status, "ACTIVE")
        self.assertEqual(state.steps[2], "current")
        self.assertIsNone(state.progress)

    def test_finger_hold_feedback(self):
        state = self.state(fist_enabled=True, finger_label="Finger up: 0.5/1.0s")
        self.assertIn("0.5/1.0s", state.guidance)
        self.assertEqual(state.next_action, "Hold up or return down")

    def test_scroll_persists_without_hand_and_offers_stop(self):
        for direction in ("up", "down"):
            state = self.state(fist_enabled=True, scrolling_direction=direction, hand_count=0)
            self.assertEqual(state.status, "ACTIVE")
            self.assertEqual(state.steps, ("complete", "complete", "complete", "current"))
            self.assertEqual(state.next_action, "Hold fist to stop")
            self.assertEqual(state.direction, direction)
            self.assertIn("Scrolling", state.guidance)

    def test_stop_progress_uses_one_second(self):
        state = self.state(fist_enabled=True, scrolling_direction="down",
                           fist_visible=True, hold_seconds=.5, required_hold_seconds=1)
        self.assertEqual(state.progress, .5)
        self.assertIn("1.00", state.timer)
        self.assertIn("stop", state.guidance)

    def test_stop_before_scroll_is_also_represented(self):
        state = self.state(fist_enabled=True, fist_visible=True,
                           hold_seconds=.2, required_hold_seconds=1)
        self.assertEqual(state.steps[3], "current")
        self.assertEqual(state.next_action, "Hold fist to stop")

    def test_stopped_fist_needs_release_before_new_activation(self):
        state = self.state(fist_visible=True, fist_latched=True, hold_seconds=1)
        self.assertEqual(state.status, "INACTIVE")
        self.assertEqual(state.next_action, "Release fist")
        self.assertIsNone(state.progress)

    def test_one_hand_needed_only_before_scroll(self):
        for hand_count in (0, 2):
            state = self.state(hand_count=hand_count, fist_visible=True)
            self.assertEqual(state.guidance, "Show one hand to the camera.")
            self.assertIsNone(state.progress)
            enabled = self.state(hand_count=hand_count, fist_enabled=True)
            self.assertEqual(enabled.status, "NOT READY")
            self.assertEqual(enabled.next_action, "Show one hand")

    def test_steps_return_to_activation_after_target_loss_or_stop(self):
        active = self.state(fist_enabled=True)
        lost = self.state(target_available=False)
        ready_again = self.state()
        self.assertEqual(active.steps[2], "current")
        self.assertEqual(lost.steps[0], "current")
        self.assertEqual(ready_again.steps[1], "current")


if __name__ == "__main__":
    unittest.main()
