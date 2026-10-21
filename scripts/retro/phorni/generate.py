"""用八个像素姿势生成芙铃动作，保留色板与局部修正，统一裁去透明留白。"""

import sys
from pathlib import Path

# 同时支持直接运行脚本和从项目根目录以模块方式运行。
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import json

import numpy as np
from PIL import Image

from scripts.retro.gif_assets import ROOT, load_source, save_gif
from scripts.retro.phorni.motion import transition
from scripts.retro.phorni.flight import ANCHORS, WING_ANGLES, FlightRig, interpolate_anchors
from scripts.retro.phorni.svg import export_svg, verify_svg

TICK = 30
OUTPUT = ROOT / 'assets/phorni'


class Sequence:
    def __init__(self, poses):
        self.poses = poses
        self.frames = []
        self.anchors = []
        self.stages = []

    def append(self, label, frames, anchors):
        start = len(self.frames)
        self.frames.extend(frames)
        self.anchors.extend(anchors)
        self.stages.append({'label': label, 'start': start, 'end': len(self.frames)})

    def hold(self, label, pose, milliseconds):
        count = round(milliseconds / TICK)
        self.append(label, [self.poses[pose]] * count, [ANCHORS[pose]] * count)

    def move(self, label, indices, steps):
        frames = []
        anchors = []
        for first, second in zip(indices, indices[1:]):
            frames.extend(transition(self.poses[first], self.poses[second], steps))
            for index in range(1, steps + 1):
                progress = index / steps
                eased = progress * progress * (3 - 2 * progress)
                anchors.append(interpolate_anchors(ANCHORS[first], ANCHORS[second], eased))
        self.append(label, frames, anchors)

    def blink(self, label, opened, closed):
        # 眨眼只替换眼部区域，避免旧闭眼姿势的衣服和发丝跟着跳动。
        base = self.poses[opened]
        bounds = (17, 27, 32, 35) if opened == 0 else (17, 31, 32, 40)
        shut = base.copy()
        shut.paste(self.poses[closed].crop(bounds), bounds[:2])
        half = base.copy()
        region = (bounds[0], bounds[1], bounds[2], bounds[1] + 4)
        half.paste(shut.crop(region), region[:2])
        frames = [half, half, shut, shut, shut, half, half, base]
        self.append(label, frames, [ANCHORS[opened]] * len(frames))

    def add_flight(self, rig):
        # 完整循环闭合到整拍，阶段切换不重置翅膀相位。
        padding = -len(self.frames) % len(WING_ANGLES)
        if padding:
            self.frames.extend([self.frames[-1]] * padding)
            self.anchors.extend([self.anchors[-1]] * padding)
            self.stages[-1]['end'] = len(self.frames)
        self.frames = [rig.paint(frame, anchors, index)
                       for index, (frame, anchors) in enumerate(zip(self.frames, self.anchors))]


def build_sequence():
    source, _ = load_source('phorni')
    rig = FlightRig(source)
    poses = rig.bodies
    idle = Sequence(poses)
    idle.hold('自然悬停', 0, 1000)
    idle.blink('完整眨眼', 0, 1)
    idle.hold('睁眼悬停', 0, 950)
    turn = Sequence(poses)
    turn.hold('回望前停顿', 0, 400)
    turn.move('慢慢回望', [0, 2, 3], 8)
    turn.hold('侧身观望', 3, 1000)
    turn.move('回到正面', [3, 2, 0], 8)
    turn.hold('回正后停稳', 0, 400)
    skirt = Sequence(poses)
    skirt.hold('悬空摊裙', 5, 1000)
    skirt.blink('摊裙时眨眼', 5, 6)
    skirt.hold('保持裙摆展开', 5, 950)
    full = Sequence(poses)
    for sequence in (idle, turn):
        for stage in sequence.stages:
            selection = slice(stage['start'], stage['end'])
            full.append(stage['label'], sequence.frames[selection], sequence.anchors[selection])
    full.move('抬手准备摊裙', [0, 7], 8)
    full.hold('抬手后悬停', 7, 200)
    full.move('悬空展开裙摆', [7, 4, 5], 10)
    for stage in skirt.stages:
        selection = slice(stage['start'], stage['end'])
        full.append(stage['label'], skirt.frames[selection], skirt.anchors[selection])
    # 返回不经过双手收在身前的姿势 7，直接舒展腿部、放松双臂。
    full.move('放下裙摆 · 腿部舒展', [5, 4, 0], 12)
    full.hold('回到自然悬停', 0, 650)
    assert full.frames[0].tobytes() == full.frames[-1].tobytes()
    full.add_flight(rig)
    return full


def verify_sources(sequence, poses):
    allowed = set()
    for pose in poses:
        pixels = np.asarray(pose)
        allowed.update(map(tuple, pixels[pixels[:, :, 3] > 0, :3]))
    for frame in sequence.frames:
        pixels = np.asarray(frame)
        assert frame.size == (48, 80)
        assert set(np.unique(pixels[:, :, 3])) <= {0, 255}
        assert set(map(tuple, pixels[pixels[:, :, 3] > 0, :3])) <= allowed
        assert not pixels[0, :, 3].any() and not pixels[-1, :, 3].any()
        assert not pixels[:, 0, 3].any() and not pixels[:, -1, 3].any()


def crop_frames(frames):
    # 动作仍在原坐标系生成，完成翅膀绘制后统一裁剪，避免切边和逐帧抖动。
    bounds = [frame.getchannel('A').getbbox() for frame in frames]
    visible_bounds = [bound for bound in bounds if bound is not None]
    if not visible_bounds:
        return frames
    left = min(bound[0] for bound in visible_bounds)
    top = min(bound[1] for bound in visible_bounds)
    right = max(bound[2] for bound in visible_bounds)
    bottom = max(bound[3] for bound in visible_bounds)
    return [frame.crop((left, top, right, bottom)) for frame in frames]


def sprite_data(sequence):
    width, height = sequence.frames[0].size
    unique, lookup, timeline = [], {}, []
    for frame in sequence.frames:
        key = frame.tobytes()
        if key not in lookup:
            lookup[key] = len(unique)
            unique.append(frame)
        timeline.append({'sprite': lookup[key]})
    atlas = Image.new('RGBA', (width * 8, height * ((len(unique) + 7) // 8)))
    for index, frame in enumerate(unique):
        atlas.alpha_composite(frame, (index % 8 * width, index // 8 * height))
    data = {'width': width, 'height': height,
            'columns': 8, 'time_ms': [index * TICK for index in range(len(timeline) + 1)],
            'timeline': timeline}
    return data, atlas


def main():
    poses, _ = load_source('phorni')
    sequence = build_sequence()
    verify_sources(sequence, poses)
    sequence.frames = crop_frames(sequence.frames)
    reports = [save_gif(OUTPUT / 'phorni.gif', sequence.frames, [TICK] * len(sequence.frames))]
    data, atlas = sprite_data(sequence)
    svg = export_svg(data, atlas, OUTPUT / 'phorni.svg')
    verify_svg(svg, sequence.frames, TICK)
    reports.append({'svg': str(svg.relative_to(ROOT)), 'verified_frames': len(sequence.frames)})
    print(json.dumps(reports, indent=2))


if __name__ == '__main__':
    main()
