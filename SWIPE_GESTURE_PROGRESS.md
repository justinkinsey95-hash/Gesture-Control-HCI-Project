# Swipe Gesture Development: Progress and Iterations

This document explains how the project's swipe-up and swipe-down feature developed through implementation and hands-on testing. It is intended for someone who does not code and needs to write a project progress summary.

**Current outcome:** The user reports that the feature now works well enough for the project's current needs. This is a working prototype, rather than a claim that every hand position or camera setup has been solved.

## 1. What we were building

The goal was to recognize an intentional upward or downward movement of the index finger using a webcam. The system also needed to avoid treating ordinary movements, such as bringing a hand into view or returning the finger to rest, as commands.

The project already used MediaPipe, a hand-tracking tool, to locate points on a hand. These points are called **landmarks**. The ones discussed during this work were:

- **8: index fingertip** — the main point whose movement is measured.
- **5: index finger base** — where the index finger connects to the hand.
- **4: thumb tip** — explored as a reference for angled hand positions.
- **0: wrist** — a reference for movement of the hand as a whole.

The camera shows where these points are. Our gesture logic decides whether their movement should count as a command.

```text
Webcam captures a picture
            |
            v
Hand tracker finds landmarks
            |
            v
Compare their positions over recent pictures
            |
            v
Decide: swipe up, swipe down, or no command
            |
            v
Show the result on the camera feed
```

## 2. Starting design decisions

We kept the project organized into small functions rather than introducing a new class or a separate background process. The existing camera loop supplies each new picture to the gesture functions.

We also used a **recent-history buffer**: a short list of landmark positions that forgets older entries as new ones arrive. In Python this is called a `deque`. It allows the system to judge movement rather than just one pose.

The initial buffer held 15 pictures. This was a placeholder, not an exact duration: 15 pictures cover different amounts of time depending on camera processing speed.

A speed-based calculation was discussed early, but the implementation focused on position, direction, and a recent time window to keep the logic readable.

The user had previously experienced crashes when using a clock-based timestamp for MediaPipe. The cause was not confirmed. We preserved the increasing counter already used by the hand tracker. Later, a separate clock was added only for gesture timing; it is not passed to MediaPipe.

## 3. Changes made through testing

### Iteration 1: Start near the wrist

**Approach:** An upward swipe began with the index fingertip near the wrist, followed by upward movement. A downward swipe used the reverse idea. Sideways movement was limited, and the recent movement was cleared after a detection to prevent repeated reports of the same swipe.

**Issue found:** This did not match the user's natural motion. When preparing to swipe up, the fingertip was closer to the index finger's base than the wrist.

**What we learned:** A plausible starting pose on a hand diagram is not necessarily the pose people actually use.

### Iteration 2: Start near the index finger base

**Change:** The upward starting reference changed from wrist 0 to finger base 5. The upward movement requirement was reduced from 100 to 60 pixels.

The user described a movement lasting roughly three quarters of a second, so the history changed to cover up to one second, with a maximum of 120 stored pictures.

**Issue found:** After swiping down, returning the finger to its natural raised position could be detected as a new swipe up.

### Iteration 3: Ignore the return to rest

**Change:** After a recognized swipe, the system waits for the finger to settle before listening again. The initial pause was 0.3 seconds. Swipe down was also changed to end near landmark 5.

**Purpose:** Treat the return movement as part of completing the interaction, rather than automatically treating it as a second command.

```text
Intentional swipe
       |
       v
Report one command
       |
       v
Ignore the return movement
       |
       v
Wait for a brief steady position
       |
       v
Allow another gesture
```

### Iteration 4: Support an angled hand using the thumb

**Issue found:** Users do not always face their palm directly toward the camera. In one natural angled pose, the index fingertip moved from above the thumb to below it during a downward swipe, without necessarily approaching landmark 5.

**Change:** We added an alternative pattern: the index fingertip crossing the thumb's height. Crossing upward could indicate swipe up; crossing downward could indicate swipe down.

The finger still had to move a meaningful distance. A small buffer around thumb height reduced accidental triggers, and moderate diagonal movement was allowed.

**Issue found:** Another starting angle still did not reliably register swipe up. Several pose-specific rules were accumulating without covering all natural positions.

### Iteration 5: Try movement along the hand's direction

**Change attempted:** We added calculations that measured finger extension along the wrist-to-finger-base direction and adjusted distances to the visible hand size.

**User feedback:** The changes became too sensitive and appeared to register only the left hand reliably. The user undid them.

**Outcome:** That orientation-based approach was not kept. The exact cause of the observed hand difference was not established from the screenshots or simulated tests.

**What we learned:** Passing artificial movement tests does not guarantee comfortable behavior with a real hand and camera.

### Iteration 6: Require a steady hand before listening

**Issue found:** Simply bringing a hand into view could trigger a swipe.

**Change:** The system now waits until the fingertip, finger base, and wrist remain approximately steady for 0.3 seconds. Each point can move within a 12-pixel tolerance, allowing some tracking jitter.

Movement recorded while entering the frame is discarded. Losing hand tracking requires this steady-hand step again. The camera interface shows whether the system is waiting or ready.

### Iteration 7: Simplify direction detection

**Issue found:** The right hand still registered poorly, and intended upward swipes could be reported as downward swipes. The user suspected that the calculations had become overtuned.

**Change:** We removed the required thumb-crossing and finger-base poses. Direction instead came from the fingertip's current vertical movement after the hand had settled.

We also added a direction-reversal check. When the finger reverses by more than a small tolerance, the new movement begins at the turning point. An older section of the path should not determine the current direction.

**Outcome:** The user reported an improvement, but two issues remained: lowering the hand out of view could count as swipe down, and swipe up still missed too often.

### Iteration 8: Separate finger movement from whole-hand movement

**Issue found:** When the whole hand leaves the frame downward, the fingertip moves down too. Tracking only that point can mistake hand withdrawal for a command.

**Change:** The system now estimates a palm reference using the midpoint between the wrist and index finger base. It measures how much the fingertip moves relative to that reference.

For example:

- Finger moves down 70 pixels and palm moves down 70 pixels: almost no independent finger movement, so this should not count as a swipe.
- Finger moves up 50 pixels and palm stays nearly still: meaningful finger movement remains, so this can count.

The fingertip must also genuinely move in the camera image in the same direction. This avoids treating a moving palm beneath a stationary fingertip as a swipe.

**Additional change for missed swipes:** The movement requirement now adjusts to visible hand size rather than always requiring 60 pixels. It uses 45% of the wrist-to-index-base distance, limited to a range of 25–60 pixels. This lets a smaller hand image use a shorter movement while retaining a minimum to reject tiny motions.

This size adjustment is separate from the earlier, undone hand-orientation calculation. Up and down still mean up and down in the camera image.

**Outcome:** After these changes, the user reported that the feature was functioning well enough for current needs.

## 4. How the current version works

```text
                 [New camera picture]
                          |
                          v
               [Exactly one hand visible?]
                    /             \
                  No              Yes
                  |                |
                  v                v
          [Clear history]   [Waiting to become ready?]
          [Wait for hand]         /          \
                               Yes          No
                                |            |
                                v            |
                    [Hand steady for 0.3s?]  |
                         /          \        |
                       No           Yes      |
                       |             |       |
                 [Keep waiting] [Discard old motion]
                                [Show Ready] |
                                      \     /
                                       v   v
                          [Measure finger movement
                             relative to the palm]
                                       |
                                       v
                          [Enough movement, acceptable
                           sideways drift, and actual
                           finger travel in that direction?]
                                /              \
                              No               Yes
                              |                 |
                       [Keep watching]          v
                                      [Report UP or DOWN]
                                                |
                                                v
                                    [Wait for steady hand
                                     before listening again]
```

The pause applies both when a hand first appears and after a recognized swipe. During the pause, entry and return movements are not used as gesture evidence.

## 5. What remains in the code

- `camera.py` captures camera pictures and works with the hand tracker.
- `main.py` connects tracking to gesture detection and displays the result and readiness messages.
- `gestures.py` stores recent positions, waits for steadiness, measures movement, and decides the gesture.
- `test_gestures.py` checks behavior using simulated landmark movements.

The thumb position is still stored, but crossing the thumb is no longer required. Likewise, the fingertip does not have to begin near landmark 5. The wrist and finger base now provide a reference for removing shared hand movement and estimating hand size.

The function-based structure remains, so later gestures can be added without putting all recognition rules inside the camera loop.

## 6. Verification and current limits

The final automated run passed **19 tests**. These cover examples including both swipe directions, mirrored hand positions, entry motion, return motion, direction changes, small tracking fluctuations, movement of the whole hand, smaller hand images, and finger movement with some palm drift.

These are simulated tests, not a measured recognition accuracy across many people. The real-world feedback came from the user's webcam trials and drove the changes described above.

Current practical limits include:

- One visible hand is supported at a time; seeing multiple hands resets detection.
- Users need a short steady moment before a gesture and between recognized gestures.
- Up and down are interpreted in the camera image, not in full three-dimensional space.
- Hand rotation, partial visibility, lighting, and tracking errors can still affect recognition.
- The system recognizes and displays gesture events; this work did not add control of another application.

## 7. Suggested project-summary wording

The project progressed from webcam hand tracking to a working prototype for recognizing upward and downward index-finger swipes. Development used repeated hands-on testing to identify missed gestures and accidental activations. Early versions relied on the fingertip approaching the wrist, approaching the finger base, or crossing the thumb, but these conditions were unreliable across natural hand positions. The final approach first waits for the hand to settle, then measures fingertip movement relative to the palm. It also adjusts the required movement to visible hand size and pauses after a detection to ignore the return motion. Nineteen simulated tests passed, and the user confirmed that the current behavior meets the project's immediate needs. Broader testing would be needed before claiming reliable recognition across users and camera conditions.
