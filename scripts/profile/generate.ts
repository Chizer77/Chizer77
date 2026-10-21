import { mkdir, readFile, writeFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { join } from 'node:path'
import { renderProfile } from './render'
import { fetchViaGraphQL, fetchViaRestUnauth } from './vendor/github-client'
import type { GitHubStats } from './vendor/github-types'
import type { GroupedProfileInfo } from './grouped-skills'
import { config } from '../../config'

const root = fileURLToPath(new URL('../../', import.meta.url))
const folder = join(root, 'scripts/profile')

async function loadStats(username: string, refresh: boolean): Promise<GitHubStats> {
  const path = join(folder, 'github.json')
  if (!refresh) {
    const cached = JSON.parse(await readFile(path, 'utf8')) as GitHubStats
    if (cached.username.toLowerCase() !== username.toLowerCase()) throw new Error('缓存账号不匹配，请运行 profile:refresh')
    return cached
  }
  const token = process.env.GITHUB_TOKEN || process.env.GH_TOKEN
  // 有凭据时失败即报错，避免把完整统计悄悄覆盖成缺失数据。
  const stats = token ? await fetchViaGraphQL(username, token) : await fetchViaRestUnauth(username)
  await writeFile(path, JSON.stringify(stats, null, 2) + '\n', 'utf8')
  console.log(`GitHub: @${stats.username}, source=${stats.source}`)
  if (!token) console.warn('未配置 GITHUB_TOKEN：当前为公开 REST 数据，无法取得的统计显示 —。')
  return stats
}

async function main() {
  const profile = config.profile
  const refresh = process.argv.includes('--refresh')
  const stats = await loadStats(config.github, refresh)
  const info: GroupedProfileInfo = {
    name: profile.name, role: profile.role, org: profile.org, location: profile.location,
    tagline: profile.tagline, bio: profile.bio, tags: profile.tags, socials: [], githubUsername: config.github,
    githubStats: stats,
    skillGroups: profile.skillGroups,
    skills: profile.skillGroups.flatMap(group => group.skills),
  }
  const snakeSource = await readFile(join(root, 'github-snake-dark.svg'), 'utf8')
  const result = renderProfile(info, profile.theme, profile.timing, snakeSource)
  const assets = join(root, 'assets/profile')
  await mkdir(assets, { recursive: true })
  await writeFile(join(assets, 'profile.svg'), result.svg, 'utf8')
  console.log(JSON.stringify({ output: 'assets/profile/profile.svg', height: result.height,
    revealSeconds: result.seconds, stages: result.sections.map(({ id, offset, end }) => ({ id, offset, end })) }, null, 2))
}

main().catch(error => { console.error(error instanceof Error ? error.message : String(error)); process.exitCode = 1 })
