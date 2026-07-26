/**
 * Locale parity.
 *
 * A key present in one file and missing from another falls back to English
 * mid-sentence, which is the kind of thing nobody notices until a user reports
 * it. `en.json` is the source of truth; every other locale must declare exactly
 * the same key set.
 *
 * The stage labels are checked too: `generation.progress.*` keys are built at
 * runtime from `stages.ts`, so they are invisible to grep and were the one
 * place where dead keys accumulated (three of them, one still promising
 * "Generating JBeam code" after that module was deleted).
 */

import { describe, expect, it } from 'vitest'

import en from './locales/en.json'
import ru from './locales/ru.json'
import { AI_STAGES, BASE_STAGES } from '../lib/stages'

type Tree = { [key: string]: string | Tree }

/** Flatten a nested translation object into dotted paths. */
function flatten(tree: Tree, prefix = ''): string[] {
  return Object.entries(tree).flatMap(([key, value]) => {
    const path = prefix ? `${prefix}.${key}` : key
    return typeof value === 'object' && value !== null ? flatten(value, path) : [path]
  })
}

/** Placeholder names used by an interpolated string, e.g. `{{count}}`. */
function placeholders(value: string): string[] {
  return [...value.matchAll(/\{\{\s*(\w+)\s*\}\}/g)].map((match) => match[1]).sort()
}

function lookup(tree: Tree, path: string): string {
  return path.split('.').reduce<string | Tree>((node, part) => (node as Tree)[part], tree) as string
}

const source = en as unknown as Tree
const locales: Record<string, Tree> = { ru: ru as unknown as Tree }

const sourceKeys = flatten(source)

describe('translations', () => {
  it.each(Object.keys(locales))('%s declares exactly the keys en declares', (code) => {
    const keys = flatten(locales[code])

    expect(sourceKeys.filter((key) => !keys.includes(key))).toEqual([])
    expect(keys.filter((key) => !sourceKeys.includes(key))).toEqual([])
  })

  it.each(Object.keys(locales))('%s keeps the same interpolation variables', (code) => {
    const mismatched = sourceKeys
      .map((key) => ({
        key,
        en: placeholders(lookup(source, key)),
        translated: placeholders(lookup(locales[code], key)),
      }))
      .filter((entry) => entry.en.join() !== entry.translated.join())

    expect(mismatched).toEqual([])
  })

  it('has no empty strings', () => {
    for (const [code, tree] of Object.entries({ en: source, ...locales })) {
      for (const key of flatten(tree)) {
        expect(lookup(tree, key).trim(), `${code}: ${key} is empty`).not.toBe('')
      }
    }
  })
})

describe('pipeline stage labels', () => {
  const stageLabelKeys = [...BASE_STAGES, ...AI_STAGES].map(
    (stage) => `generation.progress.${stage.labelKey}`,
  )

  it('every stage in stages.ts has a label in every locale', () => {
    for (const [code, tree] of Object.entries({ en: source, ...locales })) {
      for (const key of stageLabelKeys) {
        expect(flatten(tree), `${code} is missing ${key}`).toContain(key)
      }
    }
  })

  it('no stage label is left over from a removed stage', () => {
    const declared = sourceKeys.filter((key) => key.startsWith('generation.progress.'))

    expect(declared.filter((key) => !stageLabelKeys.includes(key))).toEqual([])
  })
})
