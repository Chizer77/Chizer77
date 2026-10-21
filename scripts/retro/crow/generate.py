"""把乌鸦动作编排成可直接嵌入 README 的透明横向动画。"""

import sys
from pathlib import Path

# 同时支持直接运行脚本和从项目根目录以模块方式运行。
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import hashlib
import json

import numpy as np
from PIL import Image

from scripts.retro.gif_assets import ROOT, TICK, indexed, shared_color_table, load_source
from scripts.retro.crow.flight import sample_flight
from scripts.retro.crow.svg import export_svg

OUTPUT = ROOT / "assets/crow"
# 地板位于 50 + 78 = 128；只去掉脚底以下的透明留白。
SIZE = (800, 128)
GROUND_TOP = 50
# 同一轮仍为 800ms；完整保留 16 姿势，下拍加速，回收留出惯性。
WING_DURATIONS = (50, 40, 40, 30, 30, 40, 40, 50, 60, 60, 60, 50, 50, 60, 70, 70)
WING_TIMES = np.cumsum((0,) + WING_DURATIONS[:-1]).tolist()



# 长短距离与停顿交错，闭合路线保证循环处不瞬移。
ROUTE = [
    ("idle", 116, 2.40), ("face", 116, 1), ("hop", 162, 0),
    ("idle", 162, 2.40), ("fly", 624, 4), ("look", 624, 0),
    ("face", 624, -1), ("idle", 624, 2.75), ("hop", 592, 0),
    ("fly", 390, 3), ("idle", 390, 3.05), ("face", 390, 1),
    ("fly", 708, 4), ("idle", 708, 2.40), ("face", 708, -1),
    ("fly", 244, 5), ("idle", 244, 2.40), ("hop", 210, 0),
    ("look", 210, 0), ("fly", 116, 3), ("idle", 116, 2.65),
]
LABELS = {"idle": "停驻眨眼", "face": "三足跳转", "hop": "向前小跳",
          "fly": "起飞巡游并落地", "look": "回望观察"}


def smoothstep(progress):
    progress = min(1, max(0, progress))
    return progress * progress * (3 - 2 * progress)


class Choreography:
    def __init__(self, sequences):
        self.sequences = sequences
        self.sprites, self.lookup, self.timeline, self.stages = [], {}, [], []
        self.position, self.direction = 116, -1

    def append(self, frame, position, lift=0, direction=None, duration=TICK):
        digest = hashlib.sha256(frame.tobytes()).hexdigest()
        if digest not in self.lookup:
            self.lookup[digest] = len(self.sprites)
            self.sprites.append(frame)
        self.timeline.append({"sprite": self.lookup[digest], "x": round(position - 48),
                              "y": round(GROUND_TOP - lift),
                              "flip": (self.direction if direction is None else direction) > 0,
                              "stage": len(self.stages), "duration_ms": duration})

    def idle(self, duration):
        frames = self.sequences["idle"]
        # 保留完整的睁眼、闭合、睁开和回稳周期，额外停顿只接在末尾。
        for frame in frames:
            self.append(frame, self.position)
        extra = max(0, round(duration * 1000 / TICK) - len(frames))
        for _ in range(extra):
            self.append(frames[-1], self.position)

    def observe(self):
        # 沿用已确认的 1.85 秒回望，包含看定目标与恢复后的停顿。
        for frame in self.sequences["turn"]:
            self.append(frame, self.position)

    def turn_around(self, destination):
        base = self.sequences["idle"][0]
        for _ in range(4):
            self.append(base, self.position)
        # 跳起后才改变朝向，三足收起、伸展和缓冲由对应原画完成。
        phases = [0, 1, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 14, 15]
        lifts = [0, 0, 0, 0, 2, 7, 11, 14, 16, 16, 14, 11, 7, 2, 0, 0, 0, 0]
        for phase, lift in zip(phases, lifts):
            self.append(self.sequences["body-turn"][phase], self.position, lift)
        self.direction = destination
        for _ in range(8):
            self.append(base, self.position)

    def hop(self, destination):
        for index, frame in enumerate(self.sequences["hop"]):
            # 仅在腾空段移动，蹬地与落地的脚不会沿地面滑动。
            progress = smoothstep((index - 10) / 13)
            position = self.position + (destination - self.position) * progress
            self.append(frame, position)

    def fly(self, destination, cycles):
        transitions = self.sequences["takeoff"]
        for frame in transitions:
            self.append(frame, self.position)
        count = cycles * 16
        path = sample_flight(cycles, destination - self.position, WING_TIMES)
        for index in range(count):
            phase = index % 16
            progress, lift = path[index]
            position = self.position + (destination - self.position) * progress
            self.append(self.sequences["flight"][phase], position, lift, duration=WING_DURATIONS[phase])
        self.append(self.sequences["flight"][0], destination, path[-1][1])
        for frame in reversed(transitions):
            self.append(frame, destination)

    def build(self):
        for action, destination, parameter in ROUTE:
            start, origin = len(self.timeline), self.position
            if action == "idle":
                self.idle(parameter)
            elif action == "face":
                self.turn_around(int(parameter))
            elif action == "look":
                self.observe()
            else:
                assert (destination - origin) * self.direction > 0
                self.hop(destination) if action == "hop" else self.fly(destination, parameter)
            self.position = destination
            self.stages.append({"action": action, "label": LABELS[action], "start": start,
                                "end": len(self.timeline), "from": origin, "to": destination})
        return self


def oriented_sprites(sprites):
    return {(index, flip): frame.transpose(Image.Transpose.FLIP_LEFT_RIGHT) if flip else frame
            for index, frame in enumerate(sprites) for flip in (False, True)}


def render_frame(record, sprites):
    frame = Image.new("RGBA", SIZE)
    frame.alpha_composite(sprites[record["sprite"], record["flip"]], (record["x"], record["y"]))
    return frame


def export_gif(choreography, colors):
    sprites = oriented_sprites([indexed(frame, colors) for frame in choreography.sprites])
    frames, durations, previous = [], [], None
    palette = next(iter(sprites.values())).getpalette()
    for record in choreography.timeline:
        key = (record["sprite"], record["flip"], record["x"], record["y"])
        if key == previous:
            durations[-1] += record["duration_ms"]
            continue
        frame = Image.new("P", SIZE, 0)
        frame.putpalette(palette)
        frame.paste(sprites[key[:2]], key[2:])
        frames.append(frame)
        durations.append(record["duration_ms"])
        previous = key
    path = OUTPUT / "crow.gif"
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=durations,
                   transparency=0, background=0, disposal=2, loop=0, optimize=False)
    return path


def verify_export(path, choreography):
    sprites = oriented_sprites(choreography.sprites)
    tick, bounds = 0, []
    with Image.open(path) as gif:
        assert gif.info["loop"] == 0 and gif.size == SIZE
        for index in range(gif.n_frames):
            gif.seek(index)
            actual = np.array(gif.convert("RGBA"))
            actual[actual[:, :, 3] == 0, :3] = 0
            remaining = gif.info["duration"]
            assert remaining % 10 == 0 and remaining >= 20
            while remaining:
                record = choreography.timeline[tick]
                expected = render_frame(record, sprites)
                assert np.array_equal(actual, np.asarray(expected)), tick
                sprite = sprites[record["sprite"], record["flip"]]
                assert np.count_nonzero(actual[:, :, 3]) == np.count_nonzero(np.asarray(sprite)[:, :, 3])
                bounds.append(expected.getbbox())
                remaining -= record["duration_ms"]
                assert remaining >= 0, "GIF 时长必须精确覆盖原画的停留时间"
                tick += 1
        encoded = gif.n_frames
    assert tick == len(choreography.timeline)
    assert render_frame(choreography.timeline[0], sprites).tobytes() == render_frame(choreography.timeline[-1], sprites).tobytes()
    positions = np.array([[record["x"], record["y"]] for record in choreography.timeline])
    durations = np.array([record["duration_ms"] for record in choreography.timeline])
    # 不等时帧比较速度而不是单帧距离，避免把较长停留误判成瞬移。
    speed = np.abs(np.diff(positions, axis=0)) * TICK / durations[:-1, None]
    assert speed.max() <= 12
    return {"size": SIZE, "duration_ms": int(durations.sum()), "timeline_ticks": tick,
            "encoded_frames": encoded, "bytes": path.stat().st_size,
            "decoded_pixels_match": True, "loop_seam_identical": True, "no_clipping": True,
            "visible_bounds": [min(b[0] for b in bounds), min(b[1] for b in bounds),
                               max(b[2] for b in bounds), max(b[3] for b in bounds)],
            "max_step_px": np.abs(np.diff(positions, axis=0)).max(axis=0).tolist(),
            "max_speed_px_per_50ms": speed.max(axis=0).tolist()}


def load_sequences():
    frames, metadata = load_source("crow")
    return {name: [frames[index] for index in indices] for name, indices in metadata["actions"].items()}


def verify_rhythm(choreography):
    sprites = oriented_sprites(choreography.sprites)
    reports = []
    for stage in choreography.stages:
        records = choreography.timeline[stage["start"]:stage["end"]]
        if stage["action"] not in ("idle", "look"):
            continue
        key = "idle" if stage["action"] == "idle" else "turn"
        reference = choreography.sequences[key]
        assert len(records) >= len(reference)
        for record, expected in zip(records, reference):
            actual = sprites[record["sprite"], record["flip"]]
            if record["flip"]:
                expected = expected.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
            assert actual.tobytes() == expected.tobytes(), (stage["start"], key)
        # 任何多出的等待都必须停在恢复睁眼的站姿，不允许闭眼接入下一阶段。
        final = reference[-1]
        for record in records[len(reference):]:
            assert choreography.sprites[record["sprite"]].tobytes() == final.tobytes()
        reports.append({"action": stage["action"], "start": stage["start"],
                        "duration_ms": len(records) * TICK, "full_original_cycle": True})
    return {"stages": reports, "idle_reference_ms": 2400, "look_reference_ms": 1850,
            "body_turn_frames": len(choreography.sequences["body-turn"])}


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    sequences = load_sequences()
    choreography = Choreography(sequences).build()
    path = export_gif(choreography, shared_color_table(sequences))
    report = verify_export(path, choreography)
    report["rhythm"] = verify_rhythm(choreography)
    svg = export_svg(choreography, OUTPUT / "crow.svg", SIZE)
    report["svg"] = {"file": svg.name, "bytes": svg.stat().st_size,
                     "responsive_width": True, "fixed_height": SIZE[1]}
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
