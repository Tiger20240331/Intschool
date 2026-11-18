# Sharing the skill with colleagues

Three ways to get this skill onto a colleague's machine. They differ in who carries the updates.

| Route | Colleague does | Updates arrive | Needs |
|---|---|---|---|
| **A. git clone + link** (recommended) | run `share/radar_colleague.command` once, then point DSH at the folder | `git pull` — daily job or the same script | git; GitHub reachable |
| **B. npm package** | `Install from registry` in DSH | `npm update` / reinstall | npm account + registry access |
| **C. LAN market index** | install from the school index | reinstall from the index | a Mac/PC serving `plugins/market` |

## A. git clone + link — the one-command route

```bash
bash share/radar_colleague.command          # clones to ~/RadarSkill, prints the DSH step
bash share/radar_colleague.command --auto   # same, plus a daily 07:30 git pull
bash share/radar_colleague.command --check  # installed vs latest tag
```

The clone is ~7 MB, the daily job only pulls the diff, and because DSH links the folder, the new
files are already in place — a plugin reload (disable/enable) or a DSH restart applies them.

Why this over mailing a `.tgz`: no attachment, no "which version do you have", no re-download of
the 3 MB package each time, and `--check` answers the version question.

## B. npm

Publishing `radar-on-intschool-skill` to npm makes it installable through the Discover tab and
`npm update`-able. Costs: an npm account, registry reachability on the school network, and the
package (including `kit/使用说明_图文版.pdf`, ~3 MB) is public.

## C. LAN market index

Serve `plugins/market/` from a school machine (`serve-index.command`), then point each DSH profile
at `http://<server>:8787/index.json`. Installs stay on the LAN, but every update is still a fresh
download of the tarball.

## Keeping the versions honest

Every release tags `vX.Y.Z` and bumps `kit/…` version strings through `package.json`:

```bash
git -C ~/RadarSkill describe --tags --abbrev=0     # what the clone is at
bash share/radar_colleague.command --check         # compare with the newest tag
```
