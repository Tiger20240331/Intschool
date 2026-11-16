# Radar Report Card Kit（macOS 版）

用**你自己的 IntSchool 教师账号**，生成**你任教班级 + 导师组**的雷达报告卡：
按 Section 展开、FLG 标注、多口径切换、班级均分、Student Log 趋势、100–300 词总评，A4 单页，可打印/分享。

> 本工具**只读** IntSchool，不写入任何数据。

## 前提

- macOS + Chrome；
- Python 3（终端执行 `python3 --version` 检查；没有就安装 python.org 版本，或让 IT 装一次）；
- 第一次运行时，macOS 可能提示“终端/命令要控制 Google Chrome”，点**允许**。

> 图文版说明：双击 `使用说明_图文版.pdf`（含截图与操作示意）。

## 三步

1. Chrome 登录 `https://teacher.intschool.cn`，保持该标签页打开；
2. 双击 **`1_get_token.command`**：自动读取你的登录 token（失败会提示手动粘贴方法）；
3. 双击 **`2_run_radar.command`**：自动识别你的课程与导师组 → 抓数据 → 生成
   `output/Radar_<你的名字>.html` 并自动打开。

`2_run_radar.command` 会启动本地小服务并打开实时页面：**每次打开页面会自动重新抓取**
成绩册/日志/出勤并重绘（约 1–2 分钟，页面会显示“正在刷新数据”）。关闭终端窗口即停止服务；
之后可双击 **`3_start_live_report.command`** 再次打开。

## 自动识别规则

- **教学课程**：`/dropDown/teach/courses` 中排除
  `Advisory / Meeting / Study Hall / Table Tennis / Club / CCA / Conference / Life Block / Department`；
- **导师组**：课程名含 `Advisory` 的课程名单（自动并入报告范围）；
- 需要调整：编辑 `config.json` 的 `exclude_keywords`、`include_course_ids`、`exclude_course_ids`。

## 报告功能

- 雷达按 Section 展开：初中（G6–8）用「学科 + HF/ECP/CPA/CP」；**G9 用 A1/A2/Main/Basic**；**G10–12 直接用课程名**（AP > ECP > CP，英语 AP/ESL/EAL）——跨年级同名课（如 AP Precalculus 同时有 G10/G11）不再混成一根轴；同名科目只保留在读的一条（Out of class 自动排除）；
- 多口径切换（Q1P/Q1E/Q1F/Q2P/Q2F、S1P/S1M）；表格显示分数 · 班级均分 · **同班百分位（P）**；
- 鼠标悬停**课程名**：弹出该课程最近 14 次作业条形图（分数 ÷ 满分；缺交为淡红虚框 + `?`）；再悬停**任一条形**显示任务名称、类型、日期、得分与**任务说明/附件**；悬停图例：单口径全科明细；
- 雷达下方 **Task highlights**：近 4 周 Top3 / Bottom3 + 近 1 周 Missing3；点「展开本学期全部」查看整学期全部任务，可再收起；
- **本周解读**：变化归因（近 7 天 vs 前 7 天，按 H10/IA15/Q15/PL20/Test40 加权）、稳定性与预测（σ + 区间 + 距 A 线）、按任务类型得分剖面；
- **本周跟进队列**：按“可改变性”排序的 6 名学生（信号 + 下一步动作），点行跳转；
- **家长草稿**：一键生成中英文草稿（学生画像 + 优势/待改进 + 缺分提醒），只复制/发邮件，不自动发送；
- Student Log 全宽趋势图（日/周/月/年、15/30/60 天），悬停柱显示金钥匙/违规的**类型与描述**；
- 总评含 Student Log 类型 Top3、出勤摘要（无记录时明确标注）、FLG 说明、数据时间戳与来源；
- **本周队列 / 班级热力图 / 沟通覆盖 / 学生自评页 / 家长版**：右上角按钮；队列每周 6 人，热力图看课程×任务类型，沟通覆盖看 21 天无正向反馈的学生；
- **隐私模式**：一键把姓名换成 initials + 班级，适合发家长群；页面打开时自动刷新数据；
- **班级 / 课程下拉**：默认选中 config.json 的 default_class（如 G7 Biology CPA），其余课程按人数排序；
- **数据质量提示**：成绩册缺分比例过高（转班/未回传）时顶部提示，缺交统计只按近 7 天计，避免误报；
- 分享（系统分享/复制摘要/邮件）、打印/PDF（A4 单页）。

## 夜间预警与学期报告

- `5_run_early_warning.command`：重抓数据后扫描三项风险指标（学术/参与/行为），输出
  `early_warning_<date>.md/.json`，并为预警/庆祝学生生成家长邮件草稿（`.eml`，不发送）。
- `6_semester_report.command`：生成每位学生的学期报告草稿（HTML，≤500 词，含画像、洞察、
  学习计划、路径与 how-to 步骤）。每年 **1 月 10 日（S1）** 与 **6 月 10 日（S2）** 运行；
  也可随时手动执行。
- 夜间自动：把 `cd "<Radar_Kit路径>" && python3 tools/early_warning.py` 加入 cron/launchd
  （例如每天 21:00）。Agent 也可代为设置定时任务。

## 学生画像与学习计划

雷达页在总评下方新增：学生画像（入学年份、走读/住宿、学院、Life Block、任务完成、出勤、
Student Log）、2–5 条学习体验洞察，以及 100–300 词个性化学习计划与升学路径建议。

## 数据口径

- **成绩**：Student Detail → Grade Book 的 Section 分数（初中 Q1P/Q1E/Q1F/Q2P/Q2F；高中 S1P/S1M）；
- **分层**：G6–8 为 HF > ECP > CPA > CP；**仅 G9** 为 A1 > A2 > Main > Basic；G10–12 为 AP > ECP > CP（英语 AP/ESL/EAL）；
- **班级均分**：Teaching → Gradebook 的本课程均分；缺失时用本班同 Section 均值；
- **Student Log**：本学期（学年开始至今天）的金钥匙与违规记录，按日/周/月/年趋势；
- **出勤**：逐日记录（多数学生为 `noRecords`，属正常，报告会注明）。

## 隐私与合规

- `token.txt` 等价于你的账号，只保存在本机；**不要发给任何人**；
- 报告含学生姓名与成绩，只发给直接相关的同事/家长；
- 数据只在本机与 IntSchool 之间流动，不经过第三方服务器。

## 常见问题

| 问题 | 解决 |
|---|---|
| token 过期（默认约 1 年，以脚本显示的到期日为准） | 重新执行第 1 步 |
| 自动读取 token 失败 | Chrome 菜单 View → Developer → 勾选 *Allow JavaScript from Apple Events*；或按提示 F12 手动复制 |
| 双击没反应 / 被系统拦截 | 右键 → 打开；系统设置 → 隐私与安全性 → 仍要打开 |
| 没有 python3 | 安装 Python 3；或让 IT 装一次 |
| 课程识别不全 | 在 `config.json` 的 `include_course_ids` 手动加入课程 ID；也可用 `exclude_course_ids` 排除 |
| Windows 电脑 | 本包为 macOS 版；Windows 同事请用校内服务版（方式 C） |

## 更新

替换 `tools/collect.py` 与 `tools/render_radar.py` 即可，`config.json` 与 token 不受影响。
