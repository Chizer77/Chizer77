import { DOMParser, XMLSerializer } from '@xmldom/xmldom'
import type { Element } from '@xmldom/xmldom'
import skillsTemplate from './vendor/templates/terminal-skills'
import { truncateToWidth } from './vendor/text-utils'
import type { ProfileInfo, TemplateTheme } from './vendor/types'

export type SkillGroup = { name: string; skills: string[] }
export type GroupedProfileInfo = ProfileInfo & { skillGroups?: SkillGroup[] }
const parse = (source: string) => new DOMParser().parseFromString(source, 'image/svg+xml')
const serializer = new XMLSerializer()
const textStyle = 'text { font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace; font-size: 14px; dominant-baseline: middle; }'

function groupLabels(info: ProfileInfo, group: SkillGroup, theme: TemplateTheme, seconds: number) {
  const source = skillsTemplate.renderSvg({ ...info, skills: group.skills }, theme, seconds, { loopText: true })
  return Array.from(parse(source).getElementsByTagName('text'))
    .filter(node => node.getAttribute('class')?.startsWith('tchip'))
}

function appendGroups(root: Element, info: ProfileInfo, groups: SkillGroup[], theme: TemplateTheme, seconds: number) {
  const nodes: Element[] = []
  let y = 138
  for (const group of groups) {
    const title = root.ownerDocument!.createElement('text')
    title.setAttribute('x', '62'); title.setAttribute('y', String(y))
    title.setAttribute('fill', theme.muted); title.setAttribute('font-size', '14')
    title.textContent = `# ${truncateToWidth(group.name, 680, 14, 'mono')}`
    nodes.push(title)
    const labels = groupLabels(info, group, theme, seconds)
    const firstY = Number(labels[0].getAttribute('y'))
    const bottom = Math.max(...labels.map(node => Number(node.getAttribute('y'))))
    for (const node of labels) {
      node.setAttribute('y', String(y + 22 + Number(node.getAttribute('y')) - firstY))
      nodes.push(node)
    }
    y += 22 + bottom - firstY + 44
  }
  nodes.forEach((node, index) => {
    node.setAttribute('class', `tchip${index}`)
    root.appendChild(root.ownerDocument!.importNode(node, true))
  })
  return { count: nodes.length, bottom: y - 44 }
}

function animationCss(count: number, seconds: number) {
  const stagger = Math.min(2.5, 60 / Math.max(1, count - 1))
  return Array.from({ length: count }, (_, index) => {
    const start = Number((4 + index * stagger).toFixed(4))
    return `@keyframes tchip${index} { 0%,${start}% { opacity: 0 } ${start + 2}%,92% { opacity: 1 } 97%,100% { opacity: 0 } }
.tchip${index} { animation: tchip${index} ${seconds}s ease-out infinite; }`
  }).join('\n')
}

export function renderGroupedSkills(info: GroupedProfileInfo, theme: TemplateTheme, seconds: number) {
  const groups = (info.skillGroups ?? [{ name: 'Skills', skills: info.skills }])
    .map(group => ({ ...group, skills: group.skills.filter(skill => skill.trim()) }))
    .filter(group => group.skills.length)
  const baseInfo = { ...info, skills: groups.flatMap(group => group.skills) }
  const source = skillsTemplate.renderSvg(baseInfo, theme, seconds, { loopText: true })
  const root = parse(source).documentElement!
  // 与 identity/about 共用字号和字体顺序，避免技能区命中不同字体后显得大小不一。
  root.setAttribute('font-size', '14')
  const sourceStyle = root.getElementsByTagName('style')[0]
  sourceStyle.textContent = sourceStyle.textContent!.replace(/text\s*\{[^}]+\}/, textStyle)
  if (!groups.length) {
    const empty = Array.from(root.getElementsByTagName('text')).find(node => node.getAttribute('font-style') === 'italic')!
    empty.setAttribute('class', 'tchip0')
    root.getElementsByTagName('style')[0].textContent += `\n${animationCss(1, seconds)}`
    return serializer.serializeToString(root)
  }
  const texts = Array.from(root.getElementsByTagName('text'))
  const chips = texts.filter(node => node.getAttribute('class')?.startsWith('tchip'))
  chips.forEach(node => root.removeChild(node))
  const prompt = texts.at(-1)!
  const cursor = Array.from(root.getElementsByTagName('rect')).find(node => node.getAttribute('class') === 'cursor')!
  root.removeChild(prompt); root.removeChild(cursor)
  const { count, bottom } = appendGroups(root, baseInfo, groups, theme, seconds)
  prompt.setAttribute('y', String(bottom + 44)); root.appendChild(prompt)
  cursor.setAttribute('y', String(bottom + 37)); root.appendChild(cursor)
  root.setAttribute('height', String(bottom + 80))
  root.setAttribute('viewBox', `0 0 800 ${bottom + 80}`)
  const style = root.getElementsByTagName('style')[0]
  const fontRule = style.textContent!.match(/text\s*\{[^}]+\}/)![0]
  style.textContent = `${fontRule}\n${animationCss(count, seconds)}`
  return serializer.serializeToString(root)
}
