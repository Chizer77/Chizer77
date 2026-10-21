"""用完整动作图集导出独立 SVG，并核对保存后的每帧像素与时序。"""

import base64
import io
from xml.etree import ElementTree as ET

from PIL import Image

NAMESPACE = 'http://www.w3.org/2000/svg'
ET.register_namespace('', NAMESPACE)


def export_svg(data, atlas, path):
    width, height = data['width'], data['height']
    duration = data['time_ms'][-1]
    viewboxes = []
    for record in data['timeline']:
        column = record['sprite'] % data['columns']
        row = record['sprite'] // data['columns']
        viewboxes.append(f'{column * width} {row * height} {width} {height}')
    root = ET.Element(f'{{{NAMESPACE}}}svg', width=str(width), height=str(height),
                      viewBox=f'0 0 {width} {height}', role='img',
                      **{'aria-labelledby': 'title'})
    ET.SubElement(root, 'title', id='title').text = 'phorni'
    pose = ET.SubElement(root, 'svg', width=str(width), height=str(height),
                         viewBox=viewboxes[0], overflow='hidden')
    # 离散切换保留原像素和 30 ms 帧时长，不做混色或形变插值。
    ET.SubElement(pose, 'animate', attributeName='viewBox', calcMode='discrete',
                  dur=f'{duration}ms', repeatCount='indefinite',
                  values=';'.join(viewboxes + [viewboxes[-1]]),
                  keyTimes=';'.join(f'{time / duration:.10f}' for time in data['time_ms']))
    with io.BytesIO() as buffer:
        atlas.save(buffer, format='PNG')
        encoded = base64.b64encode(buffer.getvalue()).decode('ascii')
    # 图集留在 SVG 内部，作为 README 图片加载时不依赖外部资源。
    ET.SubElement(pose, 'image', width=str(atlas.width), height=str(atlas.height),
                  href=f'data:image/png;base64,{encoded}', **{'image-rendering': 'pixelated'})
    ET.indent(root)
    path.write_text(ET.tostring(root, encoding='unicode') + '\n', encoding='utf-8')
    return path


def verify_svg(path, frames, tick):
    root = ET.parse(path).getroot()
    animation = root.find(f'.//{{{NAMESPACE}}}animate')
    image = root.find(f'.//{{{NAMESPACE}}}image')
    assert animation is not None and image is not None
    assert animation.get('calcMode') == 'discrete'
    duration = len(frames) * tick
    assert animation.get('dur') == f'{duration}ms'
    times = [float(value) for value in animation.get('keyTimes').split(';')]
    views = animation.get('values').split(';')
    assert len(times) == len(views) == len(frames) + 1
    assert times[-1] == 1 and views[-1] == views[-2]
    content = base64.b64decode(image.get('href').split(',', 1)[1])
    with Image.open(io.BytesIO(content)) as atlas:
        for index, frame in enumerate(frames):
            assert abs(times[index] * duration - index * tick) < 0.001
            x, y, width, height = map(int, views[index].split())
            restored = atlas.crop((x, y, x + width, y + height)).convert('RGBA')
            assert restored.tobytes() == frame.tobytes(), f'SVG 第 {index} 帧不一致'
