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

FIST_HOLD_SECONDS = 1.25
FIST_STOP_SECONDS = 1.0


def is_closed_fist(hand):
    """Four curled fingers, independent of hand side and image rotation."""
    wrist = hand[0]
    def distance(point):
        return hypot(point.x - wrist.x, point.y - wrist.y)
    return all(distance(hand[tip]) < distance(hand[pip]) * 0.9
               for pip, tip in ((6, 8), (10, 12), (14, 16), (18, 20)))


class FingerScrollGesture:
    """Read extension/return from a fist before choosing a scroll direction."""
    HOLD_SECONDS = 1.0
    EXTEND_DISTANCE = 0.45
    RETURN_DISTANCE = 0.30

    def __init__(self, clock=perf_counter):
        self.clock = clock
        self.reset()

    def reset(self):
        self.baseline = self.peak = self.raised_at = self.last_seen = None
        self.hold_seconds = 0.0

    @property
    def label(self):
        if self.raised_at is not None:
            return f"Finger up: {self.hold_seconds:.1f}/1.0s"
        if self.baseline is None:
            return "Close fist to set start pose"
        return "Raise index; hold up or return down"

    def update(self, result, width, height):
        now = self.clock()
        if len(result.hand_landmarks) != 1:
            self.reset()
            return None
        if self.last_seen is not None and now - self.last_seen > 0.5:
            self.reset()
        self.last_seen = now
        hand = result.hand_landmarks[0]
        palm_size = hypot((hand[5].x - hand[0].x) * width,
                          (hand[5].y - hand[0].y) * height)
        if palm_size < 1:
            self.reset()
            return None
        # Remove whole-hand translation and scale by the visible palm size.
        position = (hand[8].y - (hand[0].y + hand[5].y) / 2) * height / palm_size
        closed = is_closed_fist(hand)
        if self.baseline is None:
            if closed:
                self.baseline = position
            return None
        extension = self.baseline - position
        if self.raised_at is None:
            if closed:
                self.baseline = position
            elif extension >= self.EXTEND_DISTANCE:
                self.raised_at = now
                self.peak = extension
            return None
        self.peak = max(self.peak, extension)
        # Wait for the return before assigning down; the outward stroke alone
        # cannot distinguish a quick down gesture from a held up gesture.
        if self.peak - extension >= self.RETURN_DISTANCE or closed:
            self.reset()
            return "SWIPE_DOWN"
        self.hold_seconds = now - self.raised_at
        if self.hold_seconds >= self.HOLD_SECONDS:
            self.reset()
            return "SWIPE_UP"
        return None


class FistToggle:
    """Require a fresh, continuously observed fist hold per toggle."""
    def __init__(self, clock=perf_counter):
        self.clock = clock
        self.reset()

    def reset(self):
        self.enabled = False
        self.started = self.last_seen = None
        self.latched = False
        self.fist_visible = False
        self.registered_seconds = None

    @property
    def required_hold_seconds(self):
        return FIST_STOP_SECONDS if self.enabled else FIST_HOLD_SECONDS

    @property
    def hold_seconds(self):
        """Elapsed observed hold time for feedback, reset on interruption."""
        if not self.fist_visible:
            return 0.0
        if self.latched:
            return self.registered_seconds
        if self.started is None:
            return 0.0
        return min(self.required_hold_seconds, max(0.0, self.last_seen - self.started))

    @property
    def hold_label(self):
        if self.fist_visible and self.latched:
            return f"Fist: {self.registered_seconds:.2f}/{self.registered_seconds:.2f}s - release"
        state = "tracking" if self.fist_visible else "waiting"
        return f"Fist: {self.hold_seconds:.2f}/{self.required_hold_seconds:.2f}s - {state}"

    def update(self, result):
        now = self.clock()
        if self.last_seen is not None and now - self.last_seen > 0.5:
            self.started = None
        self.last_seen = now
        self.fist_visible = (len(result.hand_landmarks) == 1
                             and is_closed_fist(result.hand_landmarks[0]))
        if len(result.hand_landmarks) != 1:
            self.started = None
            return False
        if not is_closed_fist(result.hand_landmarks[0]):
            self.started = None
            self.latched = False
            return False
        if self.latched:
            return False
        if self.started is None:
            self.started = now
        if now - self.started >= self.required_hold_seconds:
            self.registered_seconds = self.required_hold_seconds
            self.enabled = not self.enabled
            self.latched = True
            self.started = None
            return True
        return False


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
