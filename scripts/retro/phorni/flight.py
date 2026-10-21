"""从旧像素画分离小翅膀，在身体后方连续拍动，保持原色与轮廓。"""

import math

from PIL import Image, ImageDraw
from scripts.retro.phorni.art import precise_wing_mask, remove_short_hair_branch

# 翼根沿肩背移动；侧身时远侧翅膀被身体遮住。
ANCHORS = [
    ((15, 40, 1), (33, 40, 1)), ((15, 40, 1), (33, 40, 1)),
    ((17, 41, 1), (30, 41, 0.25)), ((16, 40, 1), (28, 41, 0)),
    ((15, 44, 1), (33, 44, 1)), ((15, 44, 1), (33, 44, 1)),
    ((15, 44, 1), (33, 44, 1)), ((17, 43, 1), (34, 40, 1)),
]
# 小精灵以翼尖轻颤维持悬停，保留快拍频率但只在中位附近小幅摆动。
WING_ANGLES = (-8, -3, 5, 10, 7, 2, -4, -7)


def flex_inner_wing(wing):
    # 内侧翼片离枢轴太近，纯旋转取整后会凝固；轻弯一格，肩背连接点仍固定。
    bent = wing.copy()
    # 保留靠肩一侧的翼膜，让弯曲后的内翼与身体之间始终连通。
    bent.alpha_composite(wing.crop((12, 1, 15, wing.height)), (12, 0))
    return bent


class FlightRig:
    def __init__(self, poses):
        self.bodies = []
        for index, pose in enumerate(poses):
            body = pose.copy()
            mask = precise_wing_mask(pose.size, index)
            body.paste((0, 0, 0, 0), (0, 0), mask)
            self.bodies.append(remove_short_hair_branch(body, index))
        self.wing = Image.new('RGBA', poses[0].size)
        # 用原翅膀的三档颜色补齐连通轮廓，旋转后不会散成孤立的碎像素。
        draw = ImageDraw.Draw(self.wing)
        draw.polygon([(7, 35), (10, 35), (13, 37), (16, 40), (14, 41), (11, 40), (9, 38)], fill=(186, 155, 134))
        draw.polygon([(8, 36), (10, 36), (13, 38), (15, 40), (12, 39), (10, 38)], fill=(239, 209, 183))
        draw.line([(8, 36), (10, 37), (12, 38)], fill=(252, 235, 210))
        self.bent_wing = flex_inner_wing(self.wing)

    def paint(self, body, anchors, tick):
        result = Image.new('RGBA', body.size)
        angle = WING_ANGLES[tick % len(WING_ANGLES)]
        for side, (horizontal, vertical, visibility) in enumerate(anchors):
            if visibility <= 0:
                continue
            wing = self.transformed_wing(horizontal, vertical, visibility, angle, side)
            result.alpha_composite(wing)
        # 身体最后覆盖翼根，翅膀不会越过头发、脸或衣服。
        result.alpha_composite(body)
        return result

    def transformed_wing(self, horizontal, vertical, visibility, angle, side):
        radians = math.radians(angle)
        cosine, sine = math.cos(radians), math.sin(radians)
        direction = -1 if side else 1
        scale = max(0.15, visibility)
        # 反向取样固定肩背枢轴；像素只做最近邻位移，不改变颜色或透明度。
        a, b = direction * cosine / scale, -sine
        d, e = direction * sine / scale, cosine
        coefficients = (a, b, 15 - a * horizontal - b * vertical,
                        d, e, 40 - d * horizontal - e * vertical)
        wing = self.bent_wing if angle <= -4 else self.wing
        return wing.transform(wing.size, Image.Transform.AFFINE, coefficients,
                              Image.Resampling.NEAREST)


def interpolate_anchors(first, second, progress):
    return tuple(tuple(start + (end - start) * progress for start, end in zip(left, right))
                 for left, right in zip(first, second))
