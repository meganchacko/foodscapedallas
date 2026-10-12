import { describe, expect, it } from 'vitest'
import {
  QUESTIONS,
  answerLabel,
  completeAnswers,
  describeFactor,
  formatLikelihood,
  type Draft,
} from './healthCheck'
import type { HealthCheckAnswers, HealthCheckFactor } from './types'

const ANSWERS: HealthCheckAnswers = {
  sex: 'Female',
  age: 30,
  family_history_overweight: true,
  high_calorie_food_often: true,
  vegetables: 2,
  main_meals_per_day: 3,
  snacking: 'Sometimes',
  smokes: false,
  water: 2,
  tracks_calories: false,
  physical_activity: 1,
  screen_time: 1,
  alcohol: 'Sometimes',
  transportation: 'Public_Transportation',
}

function factor(direction: 'raises' | 'lowers'): HealthCheckFactor {
  return {
    field: 'snacking',
    label: 'Eating between meals',
    effect: 0.5,
    direction,
    changeable: true,
    actionable: true,
  }
}

describe('questions', () => {
  it('asks every question the API needs, once each', () => {
    const fields = QUESTIONS.map((question) => question.field).sort()
    expect(fields).toEqual(Object.keys(ANSWERS).sort())
  })

  it('never asks for height or weight', () => {
    const text = QUESTIONS.map((q) => `${q.field} ${q.prompt}`)
      .join(' ')
      .toLowerCase()
    // whole words only: "overweight" (family history question) is fine
    expect(text).not.toMatch(/\b(height|weight)\b/)
  })

  it('uses the exact values the API accepts for multiple-choice answers', () => {
    const snacking = QUESTIONS.find((q) => q.field === 'snacking')!
    expect(snacking.options!.map((o) => o.value)).toEqual([
      'no',
      'Sometimes',
      'Frequently',
      'Always',
    ])
  })
})

describe('completeAnswers', () => {
  it('returns the answers when everything is filled in', () => {
    expect(completeAnswers(ANSWERS as Draft).answers).toEqual(ANSWERS)
  })

  it('lists unanswered questions', () => {
    const { answers, missing } = completeAnswers({ ...ANSWERS, smokes: undefined })
    expect(answers).toBeNull()
    expect(missing).toEqual(['Do you smoke?'])
  })

  it('treats an age under 18 as unanswered', () => {
    expect(completeAnswers({ ...ANSWERS, age: 15 }).answers).toBeNull()
  })

  it('accepts false as an answer (it is not missing)', () => {
    expect(completeAnswers({ ...ANSWERS, smokes: false }).answers).not.toBeNull()
  })
})

describe('wording', () => {
  it('shows whole percents but never sounds certain', () => {
    expect(formatLikelihood(0.342)).toBe('34%')
    expect(formatLikelihood(0.001)).toBe('under 1%')
    expect(formatLikelihood(0.999)).toBe('over 99%')
  })

  it('shows the answer as the user saw it', () => {
    expect(answerLabel('snacking', ANSWERS)).toBe('Sometimes')
    expect(answerLabel('transportation', ANSWERS)).toBe('Public transit')
    expect(answerLabel('age', ANSWERS)).toBe('30')
  })

  it('describes factors as patterns in the data, not causes or instructions', () => {
    for (const direction of ['raises', 'lowers'] as const) {
      const text = describeFactor(factor(direction))
      expect(text).toMatch(/in the survey data/i)
      expect(text).not.toMatch(/\b(cause|causes|should|must)\b/i)
    }
  })
})
