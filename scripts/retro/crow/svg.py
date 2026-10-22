"""导出背景和角色共用坐标系、可随 README 宽度缩放的独立 SVG。"""

import base64
import io
import math
from xml.etree import ElementTree as ET

from PIL import Image
from scripts.retro.crow.scene import SOURCE, SVG_HEIGHT, SVG_GROUND

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
    # 共用 viewBox，窄屏缩放时背景墙顶和角色脚底不会产生相对位移。
    root = ET.Element(f"{{{NAMESPACE}}}svg", width=str(size[0]), height=str(size[1]),
                      viewBox=f"0 0 {size[0]} {size[1]}",
                      preserveAspectRatio="xMidYMid meet",
                      role="img", **{"aria-labelledby": "title", "overflow": "hidden"})
    element(root, "title", id="title").text = "crow"
    background = base64.b64encode(SOURCE.read_bytes()).decode("ascii")
    # 雾化背景使用平滑缩放，角色图集仍保留像素风格。
    element(root, "image", id="background", width=size[0], height=SVG_HEIGHT,
            href=f"data:image/png;base64,{background}", preserveAspectRatio="xMidYMid meet",
            **{"image-rendering": "auto"})
    layer = element(root, "g", id="crow-layer", transform=f"translate(0 {SVG_GROUND - 128})")
    position = add_route(layer, timeline, size)
    add_pose(position, timeline, atlas_size, encoded)
    ET.indent(root)
    path.write_text(ET.tostring(root, encoding="unicode") + "\n", encoding="utf-8")
    return path


def add_route(root, timeline, size):
    # 路线使用场景坐标，外层统一缩放；避免百分比坐标受外部容器比例影响。
    positions = [f"{record['x']} {record['y']}" for record in timeline]
    route = element(root, "g", id="route")
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
