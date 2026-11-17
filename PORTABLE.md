# Use this skill outside DSH (WorkBuddy, Claude-style agents, plain shell)

The repository ships two ways to load the same skill:

| Entry point | For | Registration |
|---|---|---|
| `skills/radar-on-intschool/SKILL.md` + `index.js` + `cordis.patch.yml` | DeepSeek Harness | Bundle: Plugins / Discover, kit path injected at load |
| `portable/SKILL.md` | Any agent that reads `SKILL.md` and can run commands | None — no placeholders, no editing |

## Drop-in layout

The portable skill finds its tool kit without any substitution. It looks for `kit/` beside the
skill file first, then one level up. Both of these work:

```
# A. self-contained folder (copy portable/ and kit/ together)
radar-on-intschool/
├── SKILL.md
└── kit/tools/collect.py

# B. straight from the repository
Intschool/
├── portable/SKILL.md
└── kit/tools/collect.py
```

Layout A: copy `portable/` into your agent's skills directory, rename it `radar-on-intschool/`,
then copy the repository's `kit/` into that folder. Layout B: point the agent at the repository
as it is.

Verify before running anything:

```bash
test -f radar-on-intschool/kit/tools/collect.py && echo ok
```

## Requirements

- Python 3 (standard library only — no pip installs)
- A browser session on `https://teacher.intschool.cn`, or a pasted token in `kit/token.txt`
- An agent or shell that can read/write files and run commands

## First run

```bash
cd radar-on-intschool/kit
python3 tools/collect.py        # 2–3 min first time (caches task descriptions), ~1 min after
python3 tools/render_radar.py   # writes output/Radar_<teacher>.html
python3 tools/serve.py          # optional: live page at http://127.0.0.1:8765/
```

macOS can double-click `kit/2_run_radar.command` instead.

## What it does

One-page IntSchool radar report card for any subject, grade or role: course-level radar with
task drill-down, weekly attribution and forecast interval, Top/Bottom/Missing tasks, a six-student
triage queue, a class × task-type heat map, communication coverage, bilingual parent drafts
(never sent), a printable student self-check and a parent view without peer comparison.

## Limits and privacy

- Read-only IntSchool access; nothing is written back to the school system.
- The token stays in `kit/token.txt` on the teacher's machine — never share or log it.
- Reports contain student names and grades; share only with the teacher or their named audience.
- Missing work counts only for tasks due in the last seven days; a sparsely marked gradebook is
  treated as a data problem, not as missing work.
- Forecasts are intervals, not promises; class averages and percentiles need at least five peers.

## Updating a portable copy

Pull the repository (or download the new tag) and replace the `kit/` folder and `SKILL.md`;
keep your own `kit/config.json` and `kit/token.txt`.

## Licence

MIT — copy, change and re-share, keeping the copyright notice.
