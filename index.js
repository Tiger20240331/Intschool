/**
 * Radar on Intschool — registers the packaged skill with the profile's skill registry.
 *
 * The skill body carries an absolute kit path so the agent can run the collector and
 * renderer from wherever the bundle was installed, including after an update.
 */
import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const here = dirname(fileURLToPath(import.meta.url))
const SKILL_FILE = join(here, 'skills', 'radar-on-intschool', 'SKILL.md')

function frontmatter(text) {
  const match = /^---\r?\n([\s\S]*?)\r?\n---\r?\n([\s\S]*)$/.exec(text)
  if (!match) throw new Error(`missing frontmatter in ${SKILL_FILE}`)
  const meta = {}
  for (const line of match[1].split(/\r?\n/)) {
    const at = line.indexOf(':')
    if (at <= 0) continue
    meta[line.slice(0, at).trim()] = line.slice(at + 1).trim().replace(/^["']|["']$/g, '')
  }
  return { meta, body: match[2] }
}

export const name = 'radar-on-intschool-skill'
export const inject = ['skills']

export function apply(ctx) {
  ctx.effect(() => {
    const { meta, body } = frontmatter(readFileSync(SKILL_FILE, 'utf8'))
    const content = body.split('{{KIT_DIR}}').join(join(here, 'kit'))
    const dispose = ctx.skills.register({
      name: meta.name,
      source: 'bundled',
      description: meta.description,
      whenToUse: meta.whenToUse,
      content,
      invocation: { modelInvocable: true, userInvocable: true },
    })
    return () => dispose()
  })
}
