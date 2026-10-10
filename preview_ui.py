"""Save illustrative UI renders using a placeholder camera image, not a webcam."""
from pathlib import Path

import cv2
import numpy as np

from ui import compose_frame, derive_ui_state


def main():
    output = Path(__file__).parent / "docs" / "images"
    output.mkdir(parents=True, exist_ok=True)
    camera = np.full((480, 640, 3), (62, 48, 36), dtype=np.uint8)
    cv2.putText(camera, "CAMERA PLACEHOLDER", (105, 225),
                cv2.FONT_HERSHEY_SIMPLEX, .8, (180, 164, 147), 1, cv2.LINE_AA)
    cv2.putText(camera, "Preview only - no webcam accessed", (95, 263),
                cv2.FONT_HERSHEY_SIMPLEX, .6, (180, 164, 147), 1, cv2.LINE_AA)
    defaults = dict(paused=False, target_available=True, fist_enabled=False,
                    fist_visible=False, hold_seconds=0, required_hold_seconds=1.25,
                    scrolling_direction=None, hand_count=1,
                    finger_label="Raise index; hold up or return down",
                    fist_latched=False)
    examples = {
        "browser-needed": dict(target_available=False),
        "activation": dict(fist_visible=True, hold_seconds=.75),
        "active": dict(fist_enabled=True),
        "finger-hold": dict(fist_enabled=True, finger_label="Finger up: 0.5/1.0s"),
        "scrolling": dict(fist_enabled=True, scrolling_direction="down", hand_count=0),
        "stop": dict(fist_enabled=True, scrolling_direction="down", fist_visible=True,
                     hold_seconds=.5, required_hold_seconds=1),
        "paused": dict(paused=True),
    }
    for name, changes in examples.items():
        state = derive_ui_state(**dict(defaults, **changes))
        path = output / f"gesture-ui-{name}.png"
        if not cv2.imwrite(str(path), compose_frame(camera, state)):
            raise RuntimeError(f"Could not save {path}")
        print(path)


if __name__ == "__main__":
    main()
