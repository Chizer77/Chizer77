import math

import numpy as np

CYCLE_SECONDS = .8
STEP_SECONDS = .01
LAUNCH_SECONDS = .72
FORWARD_PULSE_GAIN = .65


def ease(progress):
    progress = min(1, max(0, progress))
    return progress * progress * (3 - 2 * progress)


def wing_force(seconds):
    phase = seconds % CYCLE_SECONDS
    if not .04 < phase < .32:
        return 0.
    return math.sin(math.pi * (phase - .04) / .28) ** 2


def landing_settle(times, heights, vertical_speed, duration):
    start = int(round((duration - .48) / STEP_SECONDS))
    height, speed = heights[start], vertical_speed[start]
    for index in range(start, len(times)):
        progress = (times[index] - times[start]) / .48
        heights[index] = ((2 * progress ** 3 - 3 * progress ** 2 + 1) * height
                          + (progress ** 3 - 2 * progress ** 2 + progress) * .48 * speed
                          + (-2 * progress ** 3 + 3 * progress ** 2) * 3)


def integrate_flight(cycles, distance):
    duration = cycles * CYCLE_SECONDS
    times = np.arange(round(duration / STEP_SECONDS) + 1) * STEP_SECONDS
    heights, vertical_speed, forward_speed = [3.], [18.], [0.]
    height = 28 + min(abs(distance) / 30, 12)
    propulsion, previous_target = 0., 3.
    descent_seconds = min(1.4, duration / 2)
    for seconds in times[1:]:
        force = wing_force(seconds)
        propulsion += (force - propulsion) * STEP_SECONDS / .12
        launch = ease(seconds / LAUNCH_SECONDS)
        envelope = launch * ease((duration - seconds) / .64)
        forward_speed.append((1 + FORWARD_PULSE_GAIN * propulsion * launch) * envelope)
        target = 3 + height * ease(seconds / .8) * (1 - ease((seconds - duration + descent_seconds) / descent_seconds))
        target_speed = (target - previous_target) / STEP_SECONDS
        acceleration = 16 * (target - heights[-1]) + 7 * (target_speed - vertical_speed[-1]) + 150 * (force - .175)
        previous_target = target
        vertical_speed.append(vertical_speed[-1] + acceleration * STEP_SECONDS)
        heights.append(heights[-1] + vertical_speed[-1] * STEP_SECONDS)
    landing_settle(times, heights, vertical_speed, duration)
    distances = np.cumsum(np.r_[0, (np.array(forward_speed[1:]) + forward_speed[:-1]) * STEP_SECONDS / 2])
    return times, distances / distances[-1], np.array(heights)


def sample_flight(cycles, distance, phase_times):
    times, progress, heights = integrate_flight(cycles, distance)
    sample_times = [cycle * CYCLE_SECONDS + phase / 1000
                    for cycle in range(cycles) for phase in phase_times]
    sample_times.append(cycles * CYCLE_SECONDS)
    return list(zip(np.interp(sample_times, times, progress), np.interp(sample_times, times, heights)))
