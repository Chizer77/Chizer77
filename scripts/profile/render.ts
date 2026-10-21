import { DOMParser, XMLSerializer } from '@xmldom/xmldom'
import boot from './vendor/templates/terminal-boot'
import about from './vendor/templates/terminal-about'
import skills from './vendor/templates/terminal-skills'
import github from './vendor/templates/terminal-github-stats'
import type { TemplateTheme } from './vendor/types'
import { renderGroupedSkills, type GroupedProfileInfo } from './grouped-skills'
import { terminalBody } from './terminal-layout'
import languageColors from './language-colors.json'
import { renderContributionSnake } from './contribution-snake'

const serializer = new XMLSerializer()
const parse = (source: string) => new DOMParser().parseFromString(source, 'image/svg+xml')
const templates = [boot, about, skills, github]
const sectionGap = 44

export type Timing = { templateSeconds: number; sectionPauseSeconds: number }
export type Section = { id: string; source: string; offset: number; end: number; y: number; height: number; top: number; body: string; css: string; fontSize: string }

function revealFrames(css: string) {
  return [...css.matchAll(/@keyframes (ln\d+|tchip\d+)\s*\{\s*0%,([\d.]+)%\s*\{ opacity: 0 \}\s*([\d.]+)%,[\d.]+%\s*\{ opacity: 1 \}\s*[\d.]+%,100%\s*\{ opacity: 0 \}\s*\}/g)]
}

export function prepareSections(info: GroupedProfileInfo, theme: TemplateTheme, timing: Timing): Section[] {
  let offset = 0
  let y = sectionGap
  return templates.map((template, index) => {
    const source = template === skills ? renderGroupedSkills(info, theme, timing.templateSeconds)
      : template.renderSvg(info, theme, timing.templateSeconds, { loopText: true })
    const layout = terminalBody(source, index === templates.length - 1)
    const frames = revealFrames(layout.css).filter(match => new RegExp(`class="${match[1]}"`).test(layout.body))
    if (!frames.length) throw new Error(`原模板动画结构改变：${template.id}`)
    const end = offset + Math.max(...frames.map(match => Number(match[3]))) / 100 * timing.templateSeconds
    const height = layout.bottom - layout.top + sectionGap
    const section = { id: template.id, source, offset, end, y, height, ...layout }
    offset = end + timing.sectionPauseSeconds
    y += height
    return section
  })
}

function sectionCss(css: string, section: Section, seconds: number, total: number) {
  for (const match of revealFrames(css)) {
    const start = (section.offset + Number(match[2]) / 100 * seconds) / total * 100
    const end = (section.offset + Number(match[3]) / 100 * seconds) / total * 100
    css = css.replace(match[0], `@keyframes ${match[1]} { 0%,${start.toFixed(6)}% { opacity: 0 } ${end.toFixed(6)}%,100% { opacity: 1 } }`)
  }
  css = css.replace(/animation: ((?:ln|tchip)\d+) [\d.]+s ([\w-]+) infinite/g,
    `animation: $1 ${total}s $2 both`)
  const names = [...css.matchAll(/@keyframes ([\w-]+)/g)].map(match => match[1])
  for (const name of names) css = css.replace(new RegExp(`\\b${name}\\b`, 'g'), `${section.id}-${name}`)
  css = css.replace(/(^|\n)(\s*)text\s*\{/g, `$1$2#${section.id} text {`)
  css = css.replace(/\.cursor\b/g, `#${section.id} .cursor`)
  const start = section.offset / total * 100
  css += `\n@keyframes ${section.id}-show { 0%,${start.toFixed(6)}% { opacity: 0 } ${(start + 0.000001).toFixed(6)}%,100% { opacity: 1 } }`
  css += `\n#${section.id} { animation: ${section.id}-show ${total}s steps(1,end) both }`
  return { css, names }
}

function renderSection(section: Section, seconds: number, total: number) {
  const { css, names } = sectionCss(section.css, section, seconds, total)
  let body = section.body
  if (section.id === boot.id) body = body.replaceAll('translate(60 ', 'translate(40 ').replaceAll('<text x="160"', '<text x="104"')
  for (const name of names) body = body.replace(new RegExp(`\\b${name}\\b`, 'g'), `${section.id}-${name}`)
  return `<style>${css}</style><g id="${section.id}" font-size="${section.fontSize}" transform="translate(0 ${section.y - section.top})">${body}</g>`
}

export function renderProfile(info: GroupedProfileInfo, theme: TemplateTheme, timing: Timing, snakeSource: string) {
  // GraphQL 的颜色优先；REST 缺失时使用随项目保存的 GitHub Linguist 色表。
  const stats = info.githubStats
  const coloredInfo = stats ? {
    ...info, githubStats: {
      ...stats, languages: stats.languages.map(language => ({
        ...language, color: language.color ?? (languageColors as Record<string, string>)[language.name] ?? null,
      }))
    }
  } : info
  const sections = prepareSections(coloredInfo, theme, timing)
  const total = Number((sections.at(-1)!.end + timing.sectionPauseSeconds).toFixed(6))
  const height = sections.at(-1)!.y + sections.at(-1)!.height - sectionGap + 18
  const original = parse(sections[0].source).documentElement!
  // 仅复用原版圆角背景，不输出窗口按钮和标题文字。
  const backgroundRect = original.getElementsByTagName('rect')[0]
  backgroundRect.setAttribute('rx', '6')
  backgroundRect.setAttribute('ry', '6')
  const background = serializer.serializeToString(backgroundRect)
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="800" height="${height}" viewBox="0 0 800 ${height}" role="img" aria-labelledby="title description">
<title id="title">Chizer — Terminal profile</title>
<desc id="description">Identity, about.md, skills and github.sh appear in order and remain visible. GitHub data is a build-time snapshot.</desc>
<style>text { font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace; dominant-baseline: middle; }</style>
${background}
${sections.map(section => renderSection(section, timing.templateSeconds, total)).join('\n')}
${renderContributionSnake(snakeSource, sections[0].y + 35)}
</svg>\n`
  return { svg, sections, seconds: total, height }
}
