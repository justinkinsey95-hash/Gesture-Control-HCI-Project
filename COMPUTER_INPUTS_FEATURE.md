# Gesture-Controlled Browser Scrolling

Status: implemented on `codex/computer-inputs`; live browser smoothness still needs hands-on validation.

## Interaction

1. Start the application and position the webcam preview in a convenient corner.
2. Open a browser and click the webpage. The browser receives input while the webcam preview stays on top, showing live feedback without taking focus as it updates.
3. Keep the pointer over the webpage. Once the existing detector is ready, swipe up to scroll toward the top or down to scroll toward the bottom.
4. Each accepted swipe produces one short, smooth scroll and a matching green arrow in the preview. The existing steady-hand requirement still applies between swipes.

## Scrolling and feedback

- Prefer simulated mouse-wheel input over arrow keys.
- Distribute small scroll increments over approximately 300–500 ms, with a gentle start and stop. Avoid a single large jump. Tune distance separately from duration in the actual browser.
- Use elapsed time, not frame counts. Keep webcam processing responsive; do not block the camera loop with a scrolling sleep loop or replay overdue increments after a stall.
- Draw an outlined green arrow near the preview edge, approximately one-quarter of the frame height. Show it for the active scroll operation and clear it on completion or cancellation.
- The arrow confirms input being sent, not measured page movement; the page may already be at its limit.
- Do not accumulate a backlog of swipes during an active scroll.

## Window behavior

- Always-on-top visibility and input focus are separate. The preview stays above the browser while the browser remains active.
- Preview refreshes must not activate the webcam window. If clicking the preview takes focus, pause scrolling until the browser is active again.
- Initially require an active supported browser and the pointer over its page, outside the preview. Verify wheel routing on the target Windows setup, including nested scroll areas.
- Cancel pending scrolling on focus loss, tracking loss, multiple visible hands, pause, or shutdown. Require the detector to settle again after resuming so stale movement cannot trigger input.
- Provide a pause/stop shortcut usable while the browser is active; the existing preview-only `q` handling is insufficient.

## Code organization

`computer_inputs.py` owns operating-system input, browser-target checks, scroll timing, cancellation, and the active direction exposed to the preview. Two small classes separate Windows calls from the independently testable scroll controller; existing gesture and camera helpers remain functions.

Keep recognition in `gestures.py`, drawing and preview setup in `camera.py`, and orchestration in `main.py`. This separates recognizing a swipe from deciding whether and how to send computer input, and allows input behavior to be tested without sending real events.

## Completion checks

- Both directions scroll visibly and smoothly without a large initial jump.
- The browser remains usable while the preview and arrow stay visible above it.
- Arrow direction and lifetime match the active scroll operation.
- Switching windows, clicking the preview, losing tracking, and pausing stop further input without queued scrolling on return.
- Repeated gestures retain the existing rest requirement and do not build a scroll backlog.
- Test pointer-over-page versus pointer-over-preview behavior, text fields, nested scroll regions, page limits, and slower camera processing.

## Delivery order

Push the existing `swipe-gesture` branch first, then create `codex/computer-inputs` from that revision. Keep this feature note on the new branch before implementing application changes.

## Running the implementation

Run `main.py` with the project's Python environment. Position the 480-by-360 preview, click the browser page, and leave the pointer over the page. Chrome, Edge, Firefox, Brave, and Opera are supported by process name. The preview stays on top; clicking it pauses input until a browser is active again.

- F8 toggles pause/resume, including while the browser is active.
- F9 exits from either window. These shortcuts are polled and are not swallowed, so the browser may also react to them.
- `q` also exits when the preview has focus; closing the preview exits.
- Holding Ctrl, Shift, or Alt suspends scrolling to avoid modified-wheel actions such as zoom.
- Tune `SCROLL_SECONDS` (default 0.45) and `SCROLL_AMOUNT` (default 120 wheel units, one notch) in `computer_inputs.py`. Windows/browser settings determine the resulting distance. Small deltas are sent per camera frame; browsers that accumulate wheel deltas may still step, so final smoothness requires a real browser trial.
- Slow frames never flush a large accumulated scroll. Gaps longer than 150 ms cancel the operation; lower frame rates may produce less total scrolling.

The target check identifies the browser window, not page elements. Keep the pointer away from browser tabs/toolbars and place it over the intended page or nested scroll area.

Validation: 27 unit tests pass (19 gesture tests and 8 scroll-controller tests). Input tests use a fake backend and do not send events to other applications.
