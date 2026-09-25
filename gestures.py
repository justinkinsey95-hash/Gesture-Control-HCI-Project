from collections import deque
from math import hypot
from time import perf_counter
from statistics import median


# Keep up to one second of frames, with a safety cap on memory.
# Coordinates below are in pixels.
history = deque(maxlen=120)
HISTORY_SECONDS = 1.0

# Starting values to tune while trying the gestures with your camera.
SWIPE_DISTANCE = 60
MIN_SWIPE_DISTANCE = 25
PALM_DISTANCE_FRACTION = 0.45
DIRECTION_CHANGE_DISTANCE = 12
SIDEWAYS_LIMIT = 50
REST_SECONDS = 0.3
REST_MOVEMENT_LIMIT = 12

# On entry and after a swipe, wait for the hand to settle before reading motion.
waiting_for_rest = True
rest_position = None
rest_started_at = None


def reset():
    global waiting_for_rest, rest_position, rest_started_at
    history.clear()
    waiting_for_rest = True
    rest_position = None
    rest_started_at = None


def update_history(result, timestamp_ms, frame_width, frame_height):
    """Store index tip (8), thumb tip (4), index base (5), and wrist (0)."""
    # Clear on tracking gaps or multiple hands to avoid mixing their paths.
    if len(result.hand_landmarks) != 1:
        reset()
        return

    hand = result.hand_landmarks[0]
    index_tip = hand[8]
    thumb_tip = hand[4]
    index_base = hand[5]
    wrist = hand[0]
    # This clock only measures gesture history; MediaPipe keeps its counter.
    recorded_at = perf_counter()
    if history and recorded_at - history[-1]["recorded_at"] > 0.5:
        # A camera stall is not evidence that the hand held still.
        reset()
    history.append({
        "time": timestamp_ms,
        "recorded_at": recorded_at,
        "index": (index_tip.x * frame_width, index_tip.y * frame_height),
        "thumb": (thumb_tip.x * frame_width, thumb_tip.y * frame_height),
        "index_base": (index_base.x * frame_width, index_base.y * frame_height),
        "wrist": (wrist.x * frame_width, wrist.y * frame_height),
    })
    while history and recorded_at - history[0]["recorded_at"] > HISTORY_SECONDS:
        history.popleft()


def finger_relative_to_palm(sample):
    """Subtract shared hand movement using the wrist/base midpoint."""
    palm_x = (sample["wrist"][0] + sample["index_base"][0]) / 2
    palm_y = (sample["wrist"][1] + sample["index_base"][1]) / 2
    return sample["index"][0] - palm_x, sample["index"][1] - palm_y


def required_swipe_distance():
    """Smaller hands in the image need less pixel travel, with a noise floor."""
    if not history:
        return SWIPE_DISTANCE
    palm_sizes = [hypot(sample["index_base"][0] - sample["wrist"][0],
                        sample["index_base"][1] - sample["wrist"][1])
                  for sample in history]
    return max(MIN_SWIPE_DISTANCE,
               min(SWIPE_DISTANCE, median(palm_sizes) * PALM_DISTANCE_FRACTION))


def current_swipe_motion():
    """Return current finger travel relative to the palm, in camera Y direction."""
    if len(history) < 2:
        return 0

    samples = list(history)
    positions = [finger_relative_to_palm(sample) for sample in samples]
    start_position = 0
    extreme_position = 0
    direction = 0

    for position in range(1, len(samples)):
        y = positions[position][1]
        extreme_y = positions[extreme_position][1]
        change = y - extreme_y

        if direction == 0:
            if abs(change) >= DIRECTION_CHANGE_DISTANCE:
                direction = 1 if change > 0 else -1
                extreme_position = position
        elif change * direction > 0:
            extreme_position = position
        elif change * direction <= -DIRECTION_CHANGE_DISTANCE:
            # A real reversal starts a new stroke at the previous turning point.
            start_position = extreme_position
            extreme_position = position
            direction = -direction

    start_x, start_y = positions[start_position]
    end_y = positions[-1][1]
    vertical_distance = end_y - start_y
    # A moving palm under a stationary fingertip is not a finger swipe.
    image_distance = samples[-1]["index"][1] - samples[start_position]["index"][1]
    if image_distance * vertical_distance <= 0:
        return 0
    if abs(image_distance) < required_swipe_distance() * 0.5:
        return 0
    sideways_limit = max(SIDEWAYS_LIMIT, abs(vertical_distance) * 0.75)
    if any(abs(x - start_x) > sideways_limit
           for x, y in positions[start_position:]):
        return 0
    return vertical_distance


def detect_swipe_up():
    """Image Y decreases when the fingertip moves up, for either hand."""
    return current_swipe_motion() <= -required_swipe_distance()


def detect_swipe_down():
    """Image Y increases when the fingertip moves down, for either hand."""
    return current_swipe_motion() >= required_swipe_distance()


def wait_for_finger_to_rest():
    """Discard entry/recovery motion until the fingertip and palm are steady."""
    global waiting_for_rest, rest_position, rest_started_at
    latest = history[-1]
    now = latest["recorded_at"]
    positions = {name: latest[name] for name in ("index", "index_base", "wrist")}

    if rest_position is None:
        rest_position = positions
        rest_started_at = now
    else:
        moved = any(
            hypot(point[0] - rest_position[name][0],
                  point[1] - rest_position[name][1]) > REST_MOVEMENT_LIMIT
            for name, point in positions.items()
        )
        if moved:
            rest_position = positions
            rest_started_at = now
        elif now - rest_started_at >= REST_SECONDS:
            waiting_for_rest = False
            rest_position = None
            rest_started_at = None

    # Never let the return path become the next gesture's history.
    history.clear()
    history.append(latest)


def detect_gesture():
    global waiting_for_rest, rest_position, rest_started_at
    if not history:
        return None
    if waiting_for_rest:
        wait_for_finger_to_rest()
        return None

    gesture = None
    if detect_swipe_up():
        gesture = "SWIPE_UP"
    elif detect_swipe_down():
        gesture = "SWIPE_DOWN"

    if gesture:
        # Consume this movement so overlapping windows don't report it again.
        latest = history[-1]
        history.clear()
        history.append(latest)
        waiting_for_rest = True
        rest_position = {name: latest[name] for name in ("index", "index_base", "wrist")}
        rest_started_at = latest["recorded_at"]

    return gesture
