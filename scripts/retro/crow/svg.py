"""导出自适应 README 宽度、角色像素尺寸固定的独立 SVG。"""

import base64
import io
import math
from xml.etree import ElementTree as ET

from PIL import Image

NAMESPACE = "http://www.w3.org/2000/svg"
SPRITE_SIZE = 96
ATLAS_COLUMNS = 10
ET.register_namespace("", NAMESPACE)


def element(parent, tag, **attributes):
    return ET.SubElement(parent, f"{{{NAMESPACE}}}{tag}",
                         {key: str(value) for key, value in attributes.items()})


def animate(parent, attribute, values, timeline, transform=False):
    duration = sum(record["duration_ms"] for record in timeline)
    times, changes, elapsed = [], [], 0
    # 合并静止段，但保留每个姿势的原始切换时间，不插值重画像素。
    for value, record in zip(values, timeline):
        if not changes or value != changes[-1]:
            times.append(f"{elapsed / duration:.10f}")
            changes.append(value)
        elapsed += record["duration_ms"]
    attributes = dict(attributeName=attribute, attributeType="XML", dur=f"{duration}ms", repeatCount="indefinite",
                      calcMode="discrete", keyTimes=";".join(times + ["1"]),
                      values=";".join(changes + [changes[-1]]))
    if transform:
        attributes["type"] = "translate"
    element(parent, "animateTransform" if transform else "animate", **attributes)


def sprite_atlas(sprites):
    rows = math.ceil(len(sprites) * 2 / ATLAS_COLUMNS)
    atlas = Image.new("RGBA", (ATLAS_COLUMNS * SPRITE_SIZE, rows * SPRITE_SIZE))
    for index, sprite in enumerate(sprites):
        for flip in (False, True):
            tile = index * 2 + int(flip)
            oriented = sprite.transpose(Image.Transpose.FLIP_LEFT_RIGHT) if flip else sprite
            atlas.alpha_composite(oriented, (tile % ATLAS_COLUMNS * SPRITE_SIZE,
                                             tile // ATLAS_COLUMNS * SPRITE_SIZE))
    with io.BytesIO() as buffer:
        atlas.save(buffer, format="PNG")
        return atlas.size, base64.b64encode(buffer.getvalue()).decode("ascii")


def pose_viewbox(record):
    tile = record["sprite"] * 2 + int(record["flip"])
    return f"{tile % ATLAS_COLUMNS * SPRITE_SIZE} {tile // ATLAS_COLUMNS * SPRITE_SIZE} 96 96"


def export_svg(choreography, path, size):
    timeline = choreography.timeline
    atlas_size, encoded = sprite_atlas(choreography.sprites)
    # 根节点不设 viewBox，避免 README 变宽时连角色一起放大。
    root = ET.Element(f"{{{NAMESPACE}}}svg", width="100%", height=str(size[1]),
                      role="img", **{"aria-labelledby": "title", "overflow": "hidden"})
    element(root, "title", id="title").text = "迷你像素乌鸦巡游"
    position = add_route(root, timeline, size)
    add_pose(position, timeline, atlas_size, encoded)
    ET.indent(root)
    path.write_text(ET.tostring(root, encoding="unicode") + "\n", encoding="utf-8")
    return path


def add_route(root, timeline, size):
    ratios = [record["x"] / (size[0] - SPRITE_SIZE) for record in timeline]
    horizontal = [f"{ratio * 100:.10f}%" for ratio in ratios]
    positions = [f"{-ratio * SPRITE_SIZE:.10f} {record['y']}"
                 for ratio, record in zip(ratios, timeline)]
    route = element(root, "svg", id="route", x=horizontal[0], width="100%",
                    height=size[1], overflow="visible")
    animate(route, "x", horizontal, timeline)
    # 百分比位移减去角色宽度对应的份额，让窄屏边界也保留完整角色。
    position = element(route, "g", id="position", transform=f"translate({positions[0]})")
    animate(position, "transform", positions, timeline, transform=True)
    return position


def add_pose(parent, timeline, atlas_size, encoded):
    viewboxes = [pose_viewbox(record) for record in timeline]
    pose = element(parent, "svg", id="pose", width=96, height=96,
                   viewBox=viewboxes[0], overflow="hidden")
    animate(pose, "viewBox", viewboxes, timeline)
    element(pose, "image", width=atlas_size[0], height=atlas_size[1],
            href=f"data:image/png;base64,{encoded}", **{"image-rendering": "pixelated"})
