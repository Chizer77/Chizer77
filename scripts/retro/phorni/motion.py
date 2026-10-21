"""像素姿势位移补间：不混色、不交叉淡化，也不产生半透明重影。"""

import numpy as np
from PIL import Image


def smooth(values, radius):
    # 积分图保留连续位移精度，仅平滑位移场，不模糊角色像素。
    pixels = np.pad(values, radius, mode='edge')
    integral = np.pad(pixels, ((1, 0), (1, 0))).cumsum(0).cumsum(1)
    width = 2 * radius + 1
    return (integral[width:, width:] - integral[:-width, width:]
            - integral[width:, :-width] + integral[:-width, :-width]) / width ** 2


def displacement(first, second):
    scale = 1 if first.width <= 48 else 2
    size = (first.width // scale, first.height // scale)
    start = np.array(first.resize(size, Image.Resampling.NEAREST), dtype=np.float32) / 255
    end = np.array(second.resize(size, Image.Resampling.NEAREST), dtype=np.float32) / 255
    start[:, :, :3] *= start[:, :, 3:4]
    end[:, :, :3] *= end[:, :, 3:4]
    height, width = start.shape[:2]
    padded = np.pad(end, ((5, 5), (5, 5), (0, 0)))
    best = np.full((height, width), np.inf)
    flow = np.zeros((height, width, 2), dtype=np.float32)
    for vertical in range(-5, 6):
        for horizontal in range(-5, 6):
            candidate = padded[5 + vertical:5 + vertical + height, 5 + horizontal:5 + horizontal + width]
            cost = smooth(((start - candidate) ** 2).sum(axis=2), 2)
            cost += (vertical ** 2 + horizontal ** 2) * 0.0015
            selected = cost < best
            best[selected] = cost[selected]
            flow[selected] = horizontal * scale, vertical * scale
    return np.stack([np.asarray(Image.fromarray(smooth(flow[:, :, axis], 2)).resize(first.size,
                          Image.Resampling.BILINEAR)) for axis in range(2)], axis=2)


def warp(frame, flow, progress):
    pixels = np.asarray(frame)
    vertical, horizontal = np.indices(pixels.shape[:2])
    source_x = np.rint(horizontal - flow[:, :, 0] * progress).astype(int)
    source_y = np.rint(vertical - flow[:, :, 1] * progress).astype(int)
    source_x = np.clip(source_x, 0, frame.width - 1)
    source_y = np.clip(source_y, 0, frame.height - 1)
    return Image.fromarray(pixels[source_y, source_x])


def transition(first, second, steps):
    if first.tobytes() == second.tobytes():
        return [first] * steps
    forward, backward = displacement(first, second), displacement(second, first)
    frames = []
    for index in range(1, steps + 1):
        progress = index / steps
        eased = progress * progress * (3 - 2 * progress)
        frame = warp(first, forward, eased) if eased < 0.5 else warp(second, backward, 1 - eased)
        frames.append(frame)
    return frames
