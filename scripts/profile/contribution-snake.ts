import { DOMParser, XMLSerializer } from '@xmldom/xmldom'

const serializer = new XMLSerializer()
const revealEnd = 3.4

function isolateStyles(css: string, classes: string[]) {
  // 原版类名和关键帧很短，统一加前缀以免污染同一 SVG 中的文字模板。
  const names = [...new Set([...classes, ...[...css.matchAll(/@keyframes\s+([\w-]+)/g)].map(match => match[1])])]
  for (const name of names.sort((a, b) => b.length - a.length)) {
    css = css.replace(new RegExp(`(?<![\\w-])${name}(?![\\w-])`, 'g'), `snake-${name}`)
  }
  return css.replace(':root', '#activity-calendar')
}

export function renderContributionSnake(source: string, y: number) {
  const root = new DOMParser().parseFromString(source, 'image/svg+xml').documentElement!
  const css = root.getElementsByTagName('style')[0]?.textContent ?? ''
  const rectangles = Array.from(root.getElementsByTagName('rect'))
  const cells = rectangles.filter(node => node.getAttribute('class')?.split(' ').includes('c'))
  const snake = rectangles.filter(node => node.getAttribute('class')?.split(' ').includes('s'))
  if (!cells.length || !snake.length) throw new Error('原版贪吃蛇 SVG 缺少矩阵或蛇身，请重新生成')
  const size = Number(css.match(/\.c\{[^}]*width:([\d.]+)px/)?.[1])
  if (!size) throw new Error('无法读取原版贪吃蛇的格子尺寸')
  const xs = cells.map(cell => Number(cell.getAttribute('x')))
  const ys = cells.map(cell => Number(cell.getAttribute('y')))
  const left = Math.min(...xs), top = Math.min(...ys)
  const width = Math.max(...xs) - left + size
  const scale = 60 / (Math.max(...ys) - top + size)
  const classes = rectangles.flatMap(node => (node.getAttribute('class') ?? '').split(' ')).filter(Boolean)
  const styles = isolateStyles(css, classes)
  for (const node of [...cells, ...snake]) {
    node.setAttribute('class', node.getAttribute('class')!.split(' ').map(name => `snake-${name}`).join(' '))
  }
  const grid = cells.map((node, index) => {
    const delay = 0.2 + (xs[index] - left) / Math.max(1, width - size) * 2.4
    return `<g class="snake-grow" style="animation-delay:${delay.toFixed(3)}s">${serializer.serializeToString(node)}</g>`
  }).join('\n')
  // 整体等比缩放，保留原版格距、路径、线性速度和吃格时序；仅移除底部累计条。
  return `<style>${styles}
@keyframes snake-grow { from { opacity:0; transform:scale(0) } to { opacity:1; transform:scale(1) } }
@keyframes snake-show { from { opacity:0 } to { opacity:1 } }
#activity-calendar .snake-grow { transform-box:fill-box; transform-origin:center; animation:snake-grow .72s cubic-bezier(.22,1,.36,1) both }
#activity-calendar .snake-c, #activity-calendar .snake-s { animation-delay:${revealEnd}s }
#activity-calendar .snake-body { animation:snake-show .001s ${revealEnd}s both }
@media (prefers-reduced-motion:reduce) { #activity-calendar .snake-grow, #activity-calendar .snake-c, #activity-calendar .snake-s { animation:none } #activity-calendar .snake-body { display:none } }
</style>
<g id="activity-calendar" transform="translate(${776 - (width + left) * scale} ${y - top * scale}) scale(${scale})" role="img" aria-label="GitHub contribution snake">
<title>GitHub contributions · looping snake</title>
${grid}
<g class="snake-body">${snake.map(node => serializer.serializeToString(node)).join('\n')}</g>
</g>`
}
