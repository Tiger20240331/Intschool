---
name: radar-on-intschool
description: "Radar on Intschool v1.1 — build a one-page IntSchool student radar report card for any subject teacher, tutor, coordinator or administrator: course-level radar, task-level drill-down, weekly insight, triage queue, class heat map, communication coverage, parent drafts, student self-check and parent view."
whenToUse: "Use when someone asks for a radar report card, student profile, weekly follow-up list, class heat map, or parent-meeting material from IntSchool — for any subject, any grade, or an administrator's overview."
---

# Radar on Intschool · Skill v1.1

## 何时使用

老师、班主任、年级组长或管理员说：“帮我生成雷达报告卡 / 学生画像 / 本周跟进名单 /
班级热力图 / radar report / 家长会材料 / 汇报材料”，或要做家长会、导师谈话、学科组或年级汇报时。

## 这是什么

用**该账号自己的 IntSchool 权限**（系统控权，工具只读）抓取“任教课程 + 导师组”的
成绩册、Student Log、出勤与任务说明，生成一个**单文件 HTML**（可直接打印成 A4 单页 PDF）：

- **学生卡**：课程/学科雷达（高中按课程名出轴，初中按“学科 + 分层”），可切换 Q1P/Q1E/Q1F/
  Q2P/Q2F/S1P/S1M；每项显示分数 · 班级均分 · 同班百分位（≥5 人）；悬停课程名看逐次作业，
  悬停条形看任务名称/类型/说明/附件。
- **本周解读**：变化归因（近 7 天 vs 前 7 天，按 H10/IA15/Q15/PL20/Test40 加权）、
  稳定性 σ 与预测区间（区间不是承诺）、按任务类型的得分剖面——**可按课程下拉筛选**，
  类型按成绩册权重从高到低排列；在雷达图上**点击某科课名**，该面板会自动切到这门课。
- **Task highlights**：近 4 周 Top3 / Bottom3 + 近 1 周 Missing3，可一键展开本学期全部。
- **本周跟进队列**：按“可改变性”排序的 6 名学生 + 信号 + 下一步动作。
- **班级热力图**：课程 × 任务类型（HW/Class/Quiz/Test/Lab/Project）矩阵 + 优先补强清单。
- **沟通覆盖**：近 21 天正向反馈覆盖率、超过 21 天没有正向记录的学生。
- **家长草稿**：中英文，一键生成与复制（**永不自动发送**）。
- **学生自评页**：可打印，学生手写完成。
- **家长版**：隐藏同伴对比与教师工具。
- **数据质量提示**：成绩册缺分比例高时提示，缺交只按近 7 天计。

## 工具位置

本技能自带工具包，位于：

```
{{KIT_DIR}}
```

下文用 `$KIT` 指代该目录。工具包包含 `tools/collect.py`、`tools/render_radar.py`、
`config.json`、`README.md` 与《使用说明_图文版.pdf》。

## 适用于谁（同一套工具，不同用法）

| 角色 | 主视图 | 典型动作 |
|---|---|---|
| 学科老师（任意学科） | 学生卡 + 本周队列 | 每周 6 人跟进；家长草稿；学生自评页 |
| 班主任 / 导师 | 队列 + 沟通覆盖 | 找“3 周没有正向反馈”的学生；约谈前看画像 |
| 年级组长 / 教研组长 | 班级热力图 + 队列 | 找“整门课同一类任务偏低”→ 安排重讲/教研 |
| 管理员 / 教务 | 热力图 + 覆盖率 | 看覆盖与数据完整性，不逐生看分 |

> 工具不预设学科：Section 与课程名全部来自成绩册；中文、人文、艺术、体育、计算机等都会自动出轴。

## 前置条件

- 已在 Chrome 登录 `https://teacher.intschool.cn`；
- 本机有 Python 3；
- Agent 有终端/文件权限（没有则走“无终端模式”）。

## 先问 4 个确认问题（一次问完）

1. **账号与角色**：是否已登录 IntSchool？是学科老师、班主任、年级组长还是管理员？
   （非 macOS 请老师自行粘贴 token，**不要问密码**。）
2. **范围**：工具会自动识别“任教课程 + 导师组”，列出来让老师确认；duty/社团/会议是否排除？
3. **口径**：默认 Q1P（高中 S1P）；是否还要 Q1E/Q1F/Q2P/Q2F/S1M？
4. **给谁看**：家长 → 家长版 + 隐私模式；同事/组长 → 学生卡 + 热力图；自己 → 全部。

## 执行流程

1. **token**：macOS 运行 `"$KIT/1_get_token.command"`；其他系统请老师粘贴到 `"$KIT/token.txt"`。
2. **抓数据**（每次都要重跑）：
   ```bash
   cd "$KIT" && python3 tools/collect.py
   ```
   首次会为每个任务抓一次说明并缓存（约 2–3 分钟）；之后只抓新任务（约 1 分钟）。
   识别不对时改 `config.json` 的 `include_course_ids` / `exclude_course_ids` / `exclude_keywords`。
3. **生成**：
   ```bash
   python3 tools/render_radar.py
   ```
4. **打开**：`output/Radar_<姓名>.html`（静态快照），或 `python3 tools/serve.py` 后访问
   `http://127.0.0.1:8765/`（每次打开自动刷新）。
5. **按确认项调整**：左侧“班级 / 课程”默认选中 `config.json` 的 `default_class`（如 G7 Biology CPA），
   其余课程按人数排序；右上角可切家长版 / 隐私模式 / 打印。
6. **交付**：给出 HTML（与 PDF）路径，提醒 token 与学生数据的保密要求。

## 每周 10 分钟（老师）

1. 打开 `本周队列` → 6 人名单与下一步；
2. 逐个看 `本周解读`（变化归因 / 稳定性 / 预测区间）；
3. 看 `Task highlights` 的 Missing / Bottom；
4. `家长草稿` → 复制/邮件；必要时打印 `学生自评页`。

## 管理者视角

- 先看 `班级热力图`：哪门课、哪类任务系统性偏低（例：G7 Biology · Test 67% with 218 items）。
- 再看 `沟通覆盖`：哪些学生长期没有正向反馈（≥21 天）。
- 只在对个案做决定时打开学生卡；不要把个体分数用于公开排名。

## 数据口径与边界

- 成绩：Student Detail → Grade Book 的自定义列（初中 Q1P/Q1E/Q1F/Q2P/Q2F，高中 S1P/S1M）；
- 分层：G6–8 HF>ECP>CPA>CP；**仅 G9** A1>A2>Main>Basic；G10–12 AP>ECP>CP（英语 AP/ESL/EAL）；
- 高中出轴用课程名（同一门课跨年级共用一根轴，不同课程不混轴）；
- 缺交 = 已截止且近 7 天未录分；缺分比例过高视为数据问题，不当作缺交；
- 预测是**区间**，不是承诺；班级均分/百分位需 ≥5 名同伴；
- 家长信息只生成草稿，**发送键永远在老师手里**。

## 安全边界

- 只读 IntSchool，不写入任何学校数据；
- token 只留本机 `$KIT/token.txt`，绝不写入日志、截图或外发；
- 报告含学生姓名与成绩，只交老师本人或其指定对象；
- 不用自己的账号替别人抓数据；管理员也应遵循同样的最小披露原则。

## 无终端模式

把 `$KIT` 与《使用说明_图文版.pdf》发给老师，按 3 步手动运行（取 token → 2_run_radar →
打开页面）。Agent 负责解释与答疑，不接触 token。

## 修改与分享

- 工具包内所有脚本都是纯 Python 3（无第三方依赖），可直接改；
- 课程识别、默认班级、排除词在 `$KIT/config.json`；
- 版式与文案在 `$KIT/tools/render_radar.py`；采集口径在 `$KIT/tools/collect.py`；
- 许可证 MIT：可复制、修改、再分发，保留版权声明即可。

## 更新到最新版

- 作者发布新版本后，在 Plugins 里更新本插件（或重新安装同一包名）即可；技能正文与工具包一起更新。
- 更新后重新运行 `collect.py` + `render_radar.py`；`config.json` 与 `token.txt` 保留在工具包目录内，
  如被覆盖，用你自己的配置替换即可。
- 版本见插件标题与 `$KIT/README.md`。
