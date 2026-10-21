# Terminal 个人主页

由当前 README 的个人介绍与技术栈整理，复用 [RyMe.md](https://github.com/ryanpolasky/ryme.md) 的 Terminal 原版渲染器。

## 修改入口

- 根目录 `config.ts` 的 `config.profile`：姓名、介绍、技术栈、配色与段间停顿。账号统一读取 `config.github`，不再维护单独的 profile.json。
- `render.ts`：把 identity、about.md、skills、github.sh 纵向接入同一终端。正文节点、字体、22px 行距、标签与光标来自原模板；保留逐行淡入，改成一次播放后停留。
- `grouped-skills.ts`：按 `skillGroups` 顺序显示组名及技术栈，复用原版标签排版；指令、组名与技术栈统一为 14px，字体回退顺序与 identity/about 一致。组内自动换行，标题先出现，再依次出现标签，包含 `Try To Learn`。空组跳过。
- `terminal-layout.ts`：移除各模板标题栏和前三段的结尾提示符，按实际正文边界排版，相邻命令只留一个空行；最后保留一个光标。组合结果只保留原版圆角背景，不显示窗口圆点和标题，正文从顶部 44px 开始，与段间指令间距一致；背景圆角为 6px。
- `language-colors.json`：离线语言颜色表，来自 [GitHub Linguist](https://github.com/github-linguist/linguist/blob/main/lib/linguist/languages.yml)。优先采用 API 返回的颜色，缺失时按语言名补色；不改变真实语言比例。
- `generate.ts`：读取配置和 GitHub 快照，输出 `assets/profile/profile.svg`。
- `github.json`：最近一次成功取得的公开 GitHub 数据，仅含数据，不含 token。
- `contribution-snake.ts`：当前实际使用的贪吃蛇矩阵。从根目录 `github-snake-dark.svg` 提取原版格子、蛇身、路径与循环关键帧，隔离样式后内嵌进终端，不需要外部 SVG 加载。保留原版中性灰空格、等距正方形和配色，等比缩放至 60px 高，右边缘在 776px；不输出原版底部累计条。开场逐列长出，3.4 秒后启动吃格循环，不重复开场动画，完全独立于文字。减少动态效果模式显示静态矩阵。
- `vendor/`：原版四个 Terminal 模板及必要依赖；来源版本和文件 SHA256 在 `upstream.json`，保留上游 MIT 许可。`types.ts` 与 `terminal-about.ts` 增加了可选的自定义 tags 支持，其余模板保持原版；`upstream.json` 记录的是上游原始校验值。`github-client.ts` 提取自上游 Pages Function，移除 Cloudflare/KV 包装、增加请求超时，并将贡献查询起点明确设为当年 1 月 1 日，以匹配原 UI 的 ytd 标签。

## 生成

在项目根目录运行：

```sh
pnpm install --frozen-lockfile
pnpm profile:build
```

`profile:build` 使用已保存的数据和 `github-snake-dark.svg`，不联网。需要刷新 GitHub 统计时运行 `pnpm profile:refresh`；凭据从环境变量 `GITHUB_TOKEN` 或 `GH_TOKEN` 读取。贪吃蛇路径由 workflow 的 `Platane/snk@v3` 生成，先生成路径再构建终端；本地构建复用保存的原版路径快照。

`github.json` 是最近一次成功请求的数据快照，通常无需手改。workflow 的推送、定时或手动构建在通过默认分支检查后，都会先更新原版贪吃蛇 SVG，再执行 `profile:refresh`，重新请求 GitHub 数据、保存快照并生成 SVG。仅打开 README、刷新预览或运行 `profile:build` 不会拉取新数据。API 请求失败会报错；返回统计的即时性仍取决于 GitHub 自身的数据更新。README 下方不再重复展示独立贪吃蛇；当前终端仅使用原版蛇 SVG 中的矩阵快照，不再单独抓取或缓存贡献日历。

可在 `config.ts` 中修改：

| 配置 | 用途 |
| --- | --- |
| `config.github` | 查询 GitHub 统计的账号；改账号后需要执行 `profile:refresh`，旧账号缓存不能混用 |
| `config.profile.name / role / org / location` | 姓名、身份、组织、位置；组织和位置可留空 |
| `config.profile.tagline / bio` | 标语和个人介绍；长介绍受原模板换行及最多四行的限制 |
| `config.profile.tags` | 介绍中的独立标签数组，例如 `["Agents", "LLMs", "Infra"]`；按顺序显示，忽略空白标签，`[]` 隐藏整个 tags 区域。未配置时沿用身份、组织和位置；长标签沿用模板缩小字号及截断规则 |
| `config.profile.skillGroups` | 先显示类别名称，再在下方显示该组技术栈；组内自动换行，`Try To Learn` 同样展示 |
| `config.profile.theme` | `bg` 背景、`fg` 正文、`accent` 强调色、`muted` 次要文字色 |
| `config.profile.timing` | `templateSeconds` 调整原模板动画节奏，`sectionPauseSeconds` 控制段间等待，单位均为秒 |

修改这些展示配置后运行 `pnpm profile:build` 即可离线重新生成；`templateSeconds` 不是长图总时长，总时长由实际内容与段间停顿共同决定。

当前总画布 800×1007.5，约 17.68 秒完成文字显示，段间等待 0.4 秒。文字依次淡入后保留，最后一个光标持续闪烁；矩阵独立地从左至右逐列出现，随后贪吃蛇开始循环吃格与复原，循环时长沿用原版生成结果。刷新页面会重新开始各自的动画。画布从开始就预留全部高度，后续章节出现前暂时留白。各行沿用上游 12 秒模板中的淡入时长及 easing；原模板的淡出与重复播放改成一次显示后保持。

上游 `loopText: false` 会跳过文字淡入，直接显示最终结果，不能用于“动态播放一次”。因此保留 `loopText: true` 生成的逐行关键帧，在组合层去掉淡出阶段，将文字动画设为单次且保持最终状态；光标保留上游的独立 1Hz 闪烁。

直接用浏览器打开 `assets/profile/profile.svg` 即可离线查看，无需 JavaScript、外部字体、API 或服务器。README 与 README.template.md 都引用同一个 SVG，FindMe 和像素角色继续独立维护；项目列表、近期动态与收藏列表的生成逻辑已移除。

## GitHub 数据与 workflow

`.github/workflows/build.yml` 对应 `Retro README build`，支持 retro 推送、手动触发和每日 UTC 00:17（香港时间 08:17）定时运行。只有远程默认分支为 `retro` 且运行分支也为 `retro` 时才执行；其他情况跳过。时间为计划时间，实际执行可能延迟。它使用内置 `GITHUB_TOKEN` 刷新数据、生成 SVG 和 README，并将生成物一次性提交回 `retro`。检出和推送目标均明确指定为 `retro`，不会写入 `main`。需要仓库允许 workflow 写入内容；`permissions: contents: write` 已声明。

切换主页版本：

1. 先将本分支的源码、素材和 workflow 提交并推送到远程 `retro`。
2. 在 GitHub 仓库 Settings → General → Default branch 中，将默认分支从 `main` 改为 `retro`。主页随之使用 retro 的 README，后续定时更新使用 retro 的 workflow。
3. 更改默认分支本身不会立即触发构建。如需马上刷新统计，在 Actions 中选择 `Retro README build` → Run workflow，分支选 `retro`。
4. 恢复旧版时将默认分支改回 `main`，主页和定时更新改回 main 的版本。本分支的更新任务会跳过。

本地 `git switch` 和 GitHub 仓库页面的分支下拉框只切换查看/编辑版本，不改变线上主页。规则参见 [GitHub 定时任务](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule) 和 [手动运行 workflow](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow)。

- 有 token：沿用上游 GraphQL 查询，显示公开仓库、今年提交、PR、评审、贡献与语言分布。仓库统计最多取星标数排序的 100 个公开非 fork 仓库；语言按返回的源码字节数统计，每仓库最多 10 种语言。只代表该查询可见范围，非账户全部私有活动。
- 无 token：沿用上游公开 REST 模式，仓库最多 100 个，语言按仓库主语言数量估算；无法取得的提交、评审等值显示 `—`，不会填入演示数字或伪造为 0。
- 有 token 但 API 失败：构建报错，不把完整快照降级覆盖；旧 SVG 仍保留。当前本机无 token，随附的是 REST 快照，GraphQL 路径需 workflow 实际运行后验证。

无需部署 RyMe 服务，也不会把账户 token 放入 SVG。上游完整仓库仅放在忽略的 `.cache/ryme` 中供对照；正式维护只需要本目录。
