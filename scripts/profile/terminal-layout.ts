import { DOMParser, XMLSerializer } from '@xmldom/xmldom'
import type { Element } from '@xmldom/xmldom'

const serializer = new XMLSerializer()

function removePrompt(root: Element) {
  const cursor = Array.from(root.getElementsByTagName('rect')).find(node =>
    node.getAttribute('class') === 'cursor' || node.getAttribute('style')?.includes('blink'))
  if (!cursor) return
  const parent = cursor.parentNode!
  if (parent !== root) { root.removeChild(parent); return }
  // skills 的提示符没有包在组内，因此同时移除它单独的 $ 字符。
  const prompt = Array.from(root.getElementsByTagName('text')).at(-1)
  if (prompt?.textContent === '$') root.removeChild(prompt)
  root.removeChild(cursor)
}

function baseline(node: Element): number {
  if (node.hasAttribute('y')) return Number(node.getAttribute('y'))
  const position = node.getAttribute('transform')?.match(/translate\([\d.]+[ ,]+([\d.]+)\)/)
  return position ? Number(position[1]) : NaN
}

export function terminalBody(source: string, final: boolean) {
  const root = new DOMParser().parseFromString(source, 'image/svg+xml').documentElement!
  const css = root.getElementsByTagName('style')[0].textContent ?? ''
  const fontSize = root.getAttribute('font-size') || '16'
  const title = Array.from(root.getElementsByTagName('text')).find(node => node.getAttribute('text-anchor') === 'middle')
  if (!title) throw new Error('原模板缺少标题栏')
  while (root.firstChild && root.firstChild !== title) root.removeChild(root.firstChild)
  root.removeChild(title)
  if (!final) removePrompt(root)
  if (final) {
    const footer = Array.from(root.getElementsByTagName('text')).find(node => node.getAttribute('text-anchor') === 'end')
    footer?.parentNode?.removeChild(footer)
  }
  const children = Array.from(root.childNodes).filter(node => node.nodeType === 1) as Element[]
  const positions = children.map(baseline).filter(Number.isFinite)
  return {
    css, fontSize, top: Math.min(...positions), bottom: Math.max(...positions),
    body: children.map(node => serializer.serializeToString(node)).join('\n')
  }
}
