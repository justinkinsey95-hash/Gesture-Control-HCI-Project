# Gesture Scrolling Update

Date: October 10, 2026

## What changed

Scrolling now uses a closed fist to enable gesture input and to stop scrolling.
The original short scroll bursts were replaced with continuous scrolling. Direction
detection now follows an index-finger movement starting from the registered fist,
rather than reading a generic vertical swipe after the hand settles.

## How to use it

1. Focus a supported browser and place the pointer over its page.
2. Show one closed fist continuously for **1.25 seconds** to enable gesture input.
3. Choose a direction from that fist pose:
   - **Scroll up:** raise the index finger and keep it raised for **1 second**.
   - **Scroll down:** raise the index finger and immediately move it back down,
     before completing the one-second hold.
4. Scrolling continues in the selected direction, including when the hand leaves view.
5. Hold a closed fist continuously for **1 second** to stop scrolling and disable
   gesture input. To start again, repeat the 1.25-second activation hold.

A fist must be released between registered holds. Keeping the same fist held after
activation does not immediately trigger the stop timer. Once scrolling starts,
additional finger gestures do not change its direction; stop and enable again to
choose another direction.

## Onscreen feedback

The camera window displays the fist timer beside its status text:

- **Waiting:** the elapsed time is zero and the required duration is shown.
- **Tracking:** elapsed time increases while one closed fist is detected.
- **Registered:** the completed duration is displayed with a release instruction.

The timer uses a **1.25-second** target for activation and a **1-second** target
for stopping. Opening the hand, losing hand tracking, or detecting multiple hands
resets the pending hold and its displayed elapsed time. Camera gaps longer than
0.5 seconds also restart a pending hold; unseen time does not count as a hold.

While choosing scroll up, the status text shows a separate finger-hold timer with
a **1-second** target. An arrow indicates the active scroll direction.

## Detection and input behavior

- A closed fist is identified by checking that all four fingertips are closer to
  the wrist than their corresponding finger joints, with a margin. The thumb is
  not required to be in a specific position.
- Direction detection records the index-finger position in the starting fist.
  It measures subsequent vertical finger motion relative to the palm and scales
  the measurement by the visible palm size.
- The outward finger movement alone does not select a direction. A downward
  return selects down; maintaining the raised position for one second selects up.
- Tracking loss discards a pending finger gesture, requiring a new fist baseline.
- Wheel input is delivered in small increments without sleeping or queuing swipes.

The finger detector uses an extension threshold of 0.45 palm lengths and a return
threshold of 0.30 palm lengths. These are initial tuning values, not measurements
validated across users or camera setups.

## Other ways scrolling stops

Continuous scrolling still respects the existing input safeguards:

- **F8** pauses/resumes the application and resets gesture activation.
- **F9**, **q** in the preview, or closing the preview exits the application.
- Changing the browser target resets activation and stops scrolling.
- Wheel input is allowed only for a supported foreground browser under the pointer.
  Holding Shift, Ctrl, or Alt prevents input.
- A scroll-controller frame gap longer than 0.15 seconds cancels scrolling.
- Camera capture failure or a wheel-input error stops scrolling.

Ordinary hand-tracking loss does not stop an already active scroll. A camera or
processing stall can still stop it through the frame-gap safeguard.

## Files changed

- `gestures.py`: added fist toggling, separate activation/stop durations, timer
  feedback, and fist-based finger direction detection.
- `computer_inputs.py`: replaced finite scroll bursts with continuous wheel input.
- `main.py`: integrated activation, direction selection, stopping, and status text.
- `camera.py`: added the fist timer beside the status text and fit both to the row.
- `test_fist_toggle.py`: tests fist timing, interruption, feedback, and release behavior.
- `test_finger_scroll.py`: tests held-up and immediate-return gestures, tracking
  gaps, small motion, whole-hand movement, scaling, and mirrored hand positions.
- `test_computer_inputs.py`: updated tests for continuous scrolling and cancellation.

The previous generic swipe helpers remain in `gestures.py`, with their existing
tests, but the application now uses `FingerScrollGesture` for direction selection.

## Validation and publication

All **41 automated tests passed**, including a simulated ten-second continuous
scroll. `git diff --check` passed. The tests use synthetic landmarks and mocked
input; live webcam sensitivity and the rendered feedback still need manual checks.

The implementation was committed as `c33eeee` and pushed to
`codex/computer-inputs`. The latest remote main was merged without conflicts, then
the result was pushed to GitHub main at `667d0a0`.

Repository: [Gesture-Control-HCI-Project](https://github.com/justinkinsey95-hash/Gesture-Control-HCI-Project)

The supplied [reference repository](https://github.com/Binhd1305/HCI_PROJECT/tree/main)
could not be retrieved during implementation. The changes were based on the local
project and the requested gesture sequence.

This documentation was written after the implementation push and is not included
in those published commits.
