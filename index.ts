import { readFile, rm, writeFile } from 'fs/promises'
import axios from 'axios'
import * as reax from 'retry-axios'
import MarkdownIt from "markdown-it"
import { config, motto } from './config'
import { shuffle } from 'lodash-es'
import { InjectPoints } from './InjectPoints'
import { minify } from 'html-minifier'
import dayjs from 'dayjs'

const GITHUB_API_BASE_URL = 'https://api.github.com'

const userAgent = 'Mozilla / 5.0(Windows NT 10.0; Win64; x64) AppleWebKit / 537.36(KHTML, like Gecko) Chrome / 135.0.0.0 Safari / 537.36 Edg / 135.0.0.0'
axios.defaults.headers.common['User-Agent'] = userAgent
axios.defaults.raxConfig = {
    retry: 5,
    retryDelay: 4000,
    onRetryAttempt: (err) => {
        const cfg = reax.getConfig(err)
        console.log('Request: \n', err.request)
        console.log(`Retry attempt #${cfg?.currentRetryAttempt}`)
    },
}
const gh = axios.create({
    baseURL: GITHUB_API_BASE_URL,
    timeout: 4000,
})
gh.interceptors.response.use(undefined, (err) => {
    console.log(err.message)
    return Promise.reject(err)
})

function generateArtworksHtml(list: any[]) {
    const tbody = list.reduce((str, cur) => str +
        ` <tr>
            <td><a href="${cur.html_url}"><b>${cur.full_name}</b></a></td>
            <td><a href="${cur.html_url}"><img alt="Stars" src="https://img.shields.io/github/stars/${cur.full_name}?style=flat-square&labelColor=A99700&color=FCE100"/></a></td>
            <td><a href="${cur.html_url}"><img alt="Forks" src="https://img.shields.io/github/forks/${cur.full_name}?style=flat-square&labelColor=6F2C08&&color=84B61D"/></a></td>
            <td><a href="https://github.com/${cur.full_name}/issues"><img alt="Issues" src="https://img.shields.io/github/issues/${cur.full_name}?style=flat-square&labelColor=72D76F&color=0C630C"/></a></td>
            <td><a href="https://github.com/${cur.full_name}/pulls"><img alt="Pull Requests" src="https://img.shields.io/github/issues-pr/${cur.full_name}?style=flat-square&labelColor=7CBDEA&color=005395"/></a></td>
            <td><a href="https://github.com/${cur.full_name}/commits"><img alt="Last Commits" src="https://img.shields.io/github/last-commit/${cur.full_name}?style=flat-square&labelColor=F87C09&color=F7630C"/></a></td>
        </tr>`, ``)

    return minifyHTML
        `<table align="center">
            <thead align="center">
                <tr border: none;>
                    <td><b>🎉 Project</b></td>
                    <td><b>🌟 Stars</b></td>
                    <td><b>🌱 Forks</b></td>
                    <td><b>🧶 Issues</b></td>
                    <td><b>☄️ Pull Requests</b></td>
                    <td><b>🔥 Last Commit</b></td>
                </tr>
            </thead>
            <tbody>
            ${tbody}
            </tbody>
        </table>`
}

function generateToysHTML(list: any[]) {
    const tbody = list.reduce((str, cur) => str +
        ` <tr>
            <td><a href="${cur.html_url}"><b>${cur.full_name}</b></a></td>
            <td><a href="${cur.html_url}"><img alt="Stars" src="https://img.shields.io/github/stars/${cur.full_name}?style=flat-square&labelColor=A99700&color=FCE100"/></a></td>
            <td><a href="${cur.html_url}"><img alt="Forks" src="https://img.shields.io/github/forks/${cur.full_name}?style=flat-square&labelColor=6F2C08&&color=84B61D"/></a></td>
            <td align="center">${new Date(cur.pushed_at).toLocaleDateString()}</td>
        </tr>`, '')

    return minifyHTML
        `<table align="center">
            <thead align="center">
                <tr border: none;>
                    <td><b>🎉 Project</b></td>
                    <td><b>🌟 Stars</b></td>
                    <td><b>🌱 Forks</b></td>
                    <td><b>🔥 Last Commit</b></td>
                </tr>
            </thead>
            <tbody>
            ${tbody}
            </tbody>
        </table>`
}

function generateStarsHTML(list: any[], type: string, limit: number) {
    if (type === 'common') {
        list = list.slice(0, limit)
    } else if (type === 'random') {
        list = shuffle(list.slice(5)).slice(0, limit)
    }
    const recentStars = list.reduce((str, cur) => str +
        `<li>
            <a href="${cur.html_url}">${cur.full_name}</a>
            ${cur.description ? `<span>${cur.description}</span>` : ''}
        </li>`, '')

    return minifyHTML`<ul>${recentStars}</ul>`;
}

function generateFooterHTML() {
    const now = new Date()
    const next = dayjs().add(24, 'h').toDate()
    return minifyHTML
        `<p align="center"><b>
            24h Auto-Update
            </br>
            Last on: ${now.toLocaleString(undefined, {
            timeStyle: 'short',
            dateStyle: 'short',
            timeZone: config.timeZone,
        })}
            </br>
            Next on: ${next.toLocaleString(undefined, {
            timeStyle: 'short',
            dateStyle: 'short',
            timeZone: config.timeZone,
        })}
            </br>
            Power By <i>GitHub Action</i>
        </b></p>`
}

const md = new MarkdownIt({ html: true, })

/**
 * 根据键值获取注入点标记
 */
function gp(key: keyof typeof InjectPoints) {
    return `<!-- ${InjectPoints[key]} -->`
}

/**
 * 压缩 HTML 模板字符串
 */
function minifyHTML(html: TemplateStringsArray, ...args: any[]) {
    const str = html.reduce((s, h, i) => s + h + (args[i] ?? ''), '')
    return minify(str, {
        removeAttributeQuotes: true,
        removeEmptyAttributes: true,
        removeTagWhitespace: true,
        collapseWhitespace: true,
    }).trim()
}

async function main() {
    let newReadme = await readFile('./README.template.md', { encoding: 'utf-8' })

    // 获取代表项目详情
    const artworksDetail = await Promise.all(
        config.artworks.map((name) => {
            return gh.get('/repos/' + name).then((data) => data.data)
        }),
    )

    // 获取有趣项目详情
    const limit = config.toys.limit
    const toys = config.toys.random ? shuffle(config.toys.repos).slice(0, limit) : config.toys.repos.slice(0, limit)
    const toysDetail = await Promise.all(
        toys.map((name) => {
            return gh.get('/repos/' + name).then((data) => data.data)
        }),
    )

    // 获取 Stared 项目
    const star: any[] = await gh.get('/users/' + config.github + '/starred').then((data) => data.data)

    // TODO: 获取最近 tales
    const recentTales = minifyHTML`<p align=center>In progress...</p>`;

    // 注入HTML
    newReadme = newReadme.replace(gp('ARTWORKS'), generateArtworksHtml(artworksDetail))
        .replace(gp('TOYS'), generateToysHTML(toysDetail))
        .replace(gp('RECENT_STARS'), generateStarsHTML(star, 'common', 5))
        .replace(gp('RANDOM_STARS'), generateStarsHTML(star, 'random', 5))
        .replace(gp('RECENT_TALES'), recentTales)
        .replace(gp('MOTTO'), minifyHTML`<p align=center><b>${motto}</b></p>`)
        .replace(gp('FOOTER'), generateFooterHTML())

    await rm('./README.md', { force: true })
    await writeFile('./README.md', newReadme, { encoding: 'utf-8' })

    const newHtml = md.render(newReadme)
    await writeFile('./index.html', newHtml, { encoding: 'utf-8' })
}

main()

