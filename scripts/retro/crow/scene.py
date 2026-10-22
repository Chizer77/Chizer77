"""统一背景缩放、墙顶坐标和 GIF 色板，避免各导出格式落脚位置漂移。"""

import math
from pathlib import Path

import numpy as np
from PIL import Image

SOURCE = Path(__file__).resolve().parent / "sources/symphonic-rain.png"
SOURCE_GROUND = 447
SOURCE_SIZE = (2029, 633)
WIDTH = 800
SIZE = (WIDTH, math.ceil(SOURCE_SIZE[1] * WIDTH / SOURCE_SIZE[0]))
SCALE = WIDTH / SOURCE_SIZE[0]
SVG_HEIGHT = SOURCE_SIZE[1] * SCALE
SVG_GROUND = SOURCE_GROUND * SCALE
GROUND = round(SVG_GROUND)
ANIMATION_OFFSET = GROUND - 128


def load_background():
    with Image.open(SOURCE) as image:
        assert image.size == SOURCE_SIZE, "更换背景尺寸时需同步校准墙顶坐标"
        background = image.convert("RGBA").resize(SIZE, Image.Resampling.NEAREST)
    assert np.all(np.asarray(background)[GROUND, 72:733, 3] == 255)
    return background


def indexed_background(background, sprite_colors):
    # 优先保留乌鸦全部原色，剩余色位用于城市；GIF 不支持 PNG 的完整色彩和半透明。
    available = 255 - len(sprite_colors)
    reduced = background.convert("RGB").quantize(colors=available)
    city_colors = np.array(reduced.getpalette()[:available * 3], dtype=np.uint8).reshape(-1, 3)
    colors = np.concatenate((sprite_colors, city_colors))
    palette = Image.new("P", (1, 1))
    table = [0, 0, 0] + colors.ravel().tolist()
    palette.putpalette(table + [0] * (768 - len(table)))
    quantized = background.convert("RGB").quantize(palette=palette, dither=Image.Dither.NONE)
    indices = np.asarray(quantized).copy()
    indices[np.asarray(background)[:, :, 3] < 128] = 0
    result = Image.fromarray(indices, "P")
    result.putpalette(palette.getpalette())
    result.info["transparency"] = 0
    return result, colors


def verify_landings(choreography):
    background = np.asarray(load_background())
    checked = 0
    for stage in choreography.stages:
        if stage["action"] not in ("idle", "look"):
            continue
        for record in choreography.timeline[stage["start"]:stage["end"]]:
            sprite = choreography.sprites[record["sprite"]]
            assert record["y"] + sprite.getbbox()[3] + ANIMATION_OFFSET == GROUND
            assert np.all(background[GROUND, record["x"] + 35:record["x"] + 61, 3] == 255)
            checked += 1
    return {"ground_row": GROUND, "standing_frames_checked": checked,
            "shared_scene_coordinates": True, "responsive_landing_error_px": 0}
