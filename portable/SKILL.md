---
name: radar-on-intschool
description: "Radar on Intschool v1.1 — build a one-page IntSchool student radar report card for any subject teacher, tutor, coordinator or administrator: course-level radar, task-level drill-down, weekly insight, triage queue, class heat map, communication coverage, parent drafts, student self-check and parent view."
whenToUse: "Use when someone asks for a radar report card, student profile, weekly follow-up list, class heat map, or parent-meeting material from IntSchool — for any subject, any grade, or an administrator's overview."
---

# Radar on Intschool · portable skill (v1.1)

## 工具位置（不需要改任何占位符）

本技能自带工具包。先按顺序找，找到哪个用哪个：

1. 与本文件**同级**的 `kit/`（`portable/kit/`）
2. 本文件**上一级**的 `kit/`（仓库根 `kit/`）

两种情况的结构分别是：

```
<skills>/radar-on-intschool/SKILL.md      ← 把 portable/ 整个复制成这个目录
<skills>/radar-on-intschool/kit/tools/collect.py
```

或保持仓库原样：

```
<repo>/portable/SKILL.md
<repo>/kit/tools/collect.py
```

下文把找到的那个目录记作 `$KIT`。验证：`test -f "$KIT/tools/collect.py" && echo ok`。

## 这是什么

用**该账号自己的 IntSchool 权限**（只读）抓取“任教课程 + 导师组”的成绩册、Student Log、
出勤与任务说明，生成**单文件 HTML**（可打印 A4 单页 PDF）：课程/学科雷达与任务下钻、
本周归因与预测区间、Top/Bottom/缺交任务、6 人跟进队列、课程×任务类型热力图、沟通覆盖、
中英文家长草稿（不发送）、学生自评页、家长版、数据质量提示。

## 适用于谁

| 角色 | 主视图 | 典型动作 |
|---|---|---|
| 学科老师（任意学科） | 学生卡 + 本周队列 | 每周 6 人跟进；家长草稿；学生自评页 |
| 班主任 / 导师 | 队列 + 沟通覆盖 | 找“3 周没有正向反馈”的学生；约谈前看画像 |
| 年级组长 / 教研组长 | 热力图 + 队列 | 找“整门课同一类任务偏低”→ 安排重讲/教研 |
| 管理员 / 教务 | 热力图 + 覆盖率 | 看覆盖与数据完整性，不逐生看分 |

## 前置条件

- Chrome 已登录 `https://teacher.intschool.cn`（或老师把 token 粘贴到 `$KIT/token.txt`）；
- Python 3；
- 运行技能的 agent 能执行 shell 命令、读写文件。

## 先问 4 个问题（一次问完）

1. 账号与角色：学科老师 / 班主任 / 年级组长 / 管理员？是否已登录 IntSchool？**不要问密码**。
2. 范围：工具自动识别“任教课程 + 导师组”，列出来确认；duty/社团/会议是否排除？
3. 口径：默认 Q1P（高中 S1P）；是否还要 Q1E/Q1F/Q2P/Q2F/S1M？
4. 给谁看：家长 → 家长版 + 隐私模式；同事/组长 → 学生卡 + 热力图。

## 执行流程

1. **token**：macOS 运行 `"$KIT/1_get_token.command"`；其他系统让老师粘贴到 `"$KIT/token.txt"`。
2. **抓数据**（每次重跑）：
   ```bash
   cd "$KIT" && python3 tools/collect.py
   ```
   首次会缓存任务说明（约 2–3 分钟），之后只抓新任务（约 1 分钟）。
   课程识别不对：改 `$KIT/config.json` 的 `include_course_ids` / `exclude_course_ids` / `exclude_keywords`。
3. **生成**：`python3 tools/render_radar.py`
4. **打开**：`$KIT/output/Radar_<姓名>.html`，或 `python3 tools/serve.py` → `http://127.0.0.1:8765/`。
5. **调整**：左侧“班级 / 课程”默认取 `config.json` 的 `default_class`（为空则取人数最多的课程）；
   右上角有队列 / 热力图 / 沟通 / 自评 / 家长草稿 / 家长版 / 隐私 / 打印。
6. **交付**：给出 HTML（与 PDF）路径，提醒 token 与学生数据的保密要求。

## 每周 10 分钟

1. `本周队列` → 6 人名单与下一步；2. 逐个看 `本周解读`；3. 看 `Task highlights` 的 Missing / Bottom；
4. `家长草稿` → 复制/邮件；必要时打印 `学生自评页`。

## 数据口径与边界

- 成绩：Student Detail → Grade Book 自定义列（初中 Q1P/Q1E/Q1F/Q2P/Q2F，高中 S1P/S1M）；
- 分层：G6–8 HF>ECP>CPA>CP；仅 G9 A1>A2>Main>Basic；G10–12 AP>ECP>CP（英语 AP/ESL/EAL）；
- 高中用课程名出轴；跨年级同名课共用一根轴；
- 缺交 = 已截止且近 7 天未录分；缺分比例过高视为数据问题，不当作缺交；
- 预测是区间不是承诺；均分/百分位需 ≥5 名同伴；家长信息只生成草稿。

## 安全边界

- 只读 IntSchool；token 只留本机 `$KIT/token.txt`；报告含学生姓名与成绩，只交本人或指定对象；
- 不用自己的账号替别人抓数据。

## 修改

纯 Python 3、无第三方依赖；版式在 `tools/render_radar.py`，采集在 `tools/collect.py`，
配置在 `config.json`。MIT 许可，可复制、修改、再分发，保留版权声明。

## 更新

`git pull`（或重新下载仓库）后重跑 `collect.py` + `render_radar.py`；
`config.json` 与 `token.txt` 是你自己的，保留即可。

## 与 DSH 版的差别

DSH 版是一个 bundle（`index.js` + `cordis.patch.yml`），会注册到 Plugins / Discover，并能把
工具路径自动注入技能正文；本文件是**不含任何占位符**的可移植版本，任何读取 `SKILL.md`
并能执行命令的 agent 都可以直接使用。
