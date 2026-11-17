# Radar on Intschool_Skill_v1.1

A DeepSeek Harness **skill bundle** that builds a one-page IntSchool radar report card for any
subject teacher, tutor, coordinator or administrator — plus the read-only collector, renderer,
illustrated guide and configurable defaults it needs.

- **Students.** Course-level radar (high school axes are course names, so AP Precalculus for G10 and G11
  are separate axes; middle school uses subject + level), score-metric switch, class average and
  percentile (only with ≥5 peers), per-task drill-down with task name, type, description and attachments.
- **Weekly reading.** Attribution of the last two weeks, stability σ, a forecast interval (a range,
  not a promise), and the score profile by task type.
- **Evidence.** Top 3 / Bottom 3 over four weeks and Missing 3 over the last week, expandable to the
  whole term.
- **Teacher views.** A weekly triage queue of six students, a class × task-type heat map, and
  communication coverage (who has had no positive note for three weeks).
- **Communication.** Bilingual parent drafts (copy or mail only — never sent), a printable
  student self-check, and a parent view without peer comparison.

## Live demo

An anonymised copy of the report the kit produces — same layout, names removed:
<https://tiger20240331.github.io/Intschool/>

## Install

- **From the plugin market:** add the index that lists this bundle, then install it from **Discover**.
- **From a local directory:** **Plugins → Add plugin** and choose this folder.
- **From npm:** `npm install radar-on-intschool-skill` in the profile (the bundle is a normal DSH bundle).

The bundle registers the skill `radar-on-intschool` and its kit. No DSH dependency is declared:
the plugin only reads its own files at activation.

## Use

Ask the agent for a radar report card, a weekly follow-up list, a class heat map or parent-meeting
material. The skill asks four questions (account and role, scope, score metric, audience), then runs
`kit/tools/collect.py` and `kit/tools/render_radar.py` and opens `kit/output/Radar_<name>.html`.

## Configure

`kit/config.json` ships with an empty `default_class`, so the class dropdown opens on the teacher's
largest course. Set it to a course name (for example `"G7 Biology CPA"`) to pin the default.
`exclude_keywords`, `include_course_ids` and `exclude_course_ids` adjust what the collector treats
as a teaching course.

## Update

Install the newer version of `radar-on-intschool-skill` (same package name); the skill body and kit
update together. Keep your `kit/config.json` and `kit/token.txt` — they are yours, not the author's.

## Privacy and limits

- Read-only IntSchool access; nothing is written back to the school system.
- The token stays in `kit/token.txt` on the teacher's machine; never share or log it.
- Reports contain student names and grades: share only with the teacher or their named audience.
- Missing work is counted only for tasks due in the last seven days; a gradebook with many unmarked
  tasks is treated as a data problem, not as missing work.
- Predictions are intervals; class averages and percentiles require at least five peers.
- Parent messages are drafts only; the send button stays with the teacher.

## Licence

MIT. Copy, change and re-share — keep the copyright notice.
