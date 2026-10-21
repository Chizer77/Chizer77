import json
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
TICK = 50


def shared_color_table(sequences):
    visible = []
    for frames in sequences.values():
        for frame in frames:
            pixels = np.asarray(frame)
            visible.append(pixels[pixels[:, :, 3] > 0, :3])
    colors = np.unique(np.concatenate(visible), axis=0)
    assert len(colors) < 255, "源素材必须能无损存入透明 GIF 色板"
    return colors


def indexed(frame, colors):
    pixels = np.asarray(frame)
    indices = np.zeros(pixels.shape[:2], dtype=np.uint8)
    for index, color in enumerate(colors, 1):
        indices[np.all(pixels[:, :, :3] == color, axis=2) & (pixels[:, :, 3] > 0)] = index
    image = Image.fromarray(indices, "P")
    table = [0, 0, 0] + colors.ravel().tolist()
    image.putpalette(table + [0] * (768 - len(table)))
    image.info["transparency"] = 0
    return image


def place(sprite, position, size=(96, 96)):
    canvas = Image.new("RGBA", size)
    canvas.alpha_composite(sprite, tuple(round(value) for value in position))
    return canvas


def rgba_pixels(frame):
    pixels = np.array(frame.convert("RGBA"))
    pixels[pixels[:, :, 3] == 0] = 0
    return pixels


def verify_gif(path, frames, durations):
    index = 0
    with Image.open(path) as animation:
        assert animation.info["loop"] == 0 and animation.size == frames[0].size
        for number in range(animation.n_frames):
            animation.seek(number)
            remaining = animation.info["duration"]
            while remaining:
                assert index < len(frames)
                assert np.array_equal(rgba_pixels(animation), rgba_pixels(frames[index])), index
                remaining -= durations[index]
                assert remaining >= 0
                index += 1
        assert index == len(frames)
        return {"file": path.name, "size": animation.size, "frames": animation.n_frames,
                "duration_ms": sum(durations), "decoded_pixels_match": True}


def save_gif(path, frames, durations):
    path.parent.mkdir(parents=True, exist_ok=True)
    colors = shared_color_table({"frames": frames})
    images = [indexed(frame, colors) for frame in frames]
    images[0].save(path, save_all=True, append_images=images[1:], duration=durations,
                   transparency=0, background=0, disposal=2, loop=0, optimize=False)
    return verify_gif(path, frames, durations)


def load_source(name):
    sources = Path(__file__).resolve().parent / name / "sources"
    metadata = json.loads((sources / "poses.json").read_text(encoding="utf-8"))
    frames = []
    with Image.open(sources / "poses.gif") as source:
        for index in range(source.n_frames):
            source.seek(index)
            frames.append(Image.fromarray(rgba_pixels(source)))
    assert len(frames) == metadata["pose_count"]
    return frames, metadata
