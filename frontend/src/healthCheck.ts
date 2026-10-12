// Questions, wording, and helpers for the health check. Kept apart from the components so the
// wording lives in one place and the logic can be unit tested.
import type { HealthCheckAnswers, HealthCheckFactor } from './types'

export type Option = { label: string; value: string | number | boolean }

export type Question = {
  field: keyof HealthCheckAnswers
  prompt: string
  hint?: string
  options?: Option[] // omitted for free-number questions (age)
}

const YES_NO: Option[] = [
  { label: 'Yes', value: true },
  { label: 'No', value: false },
]

const FREQUENCY: Option[] = [
  { label: 'Never', value: 'no' },
  { label: 'Sometimes', value: 'Sometimes' },
  { label: 'Often', value: 'Frequently' },
  { label: 'Always', value: 'Always' },
]

// Plain, neutral wording. The values are what the API expects (see backend/app/schemas).
export const QUESTIONS: Question[] = [
  {
    field: 'sex',
    prompt: 'Sex',
    hint: 'The survey the model learned from only recorded female or male.',
    options: [
      { label: 'Female', value: 'Female' },
      { label: 'Male', value: 'Male' },
    ],
  },
  { field: 'age', prompt: 'Age', hint: 'For adults (18 and older).' },
  {
    field: 'family_history_overweight',
    prompt: 'Has anyone in your immediate family been overweight?',
    options: YES_NO,
  },
  {
    field: 'high_calorie_food_often',
    prompt: 'Do you often eat high-calorie foods, like fried food, fast food, or sweets?',
    options: YES_NO,
  },
  {
    field: 'vegetables',
    prompt: 'Do you usually eat vegetables with your meals?',
    options: [
      { label: 'Never', value: 1 },
      { label: 'Sometimes', value: 2 },
      { label: 'Always', value: 3 },
    ],
  },
  {
    field: 'main_meals_per_day',
    prompt: 'How many main meals do you eat a day?',
    options: [
      { label: '1', value: 1 },
      { label: '2', value: 2 },
      { label: '3', value: 3 },
      { label: '4 or more', value: 4 },
    ],
  },
  { field: 'snacking', prompt: 'Do you eat between meals?', options: FREQUENCY },
  { field: 'smokes', prompt: 'Do you smoke?', options: YES_NO },
  {
    field: 'water',
    prompt: 'How much water do you drink a day?',
    options: [
      { label: 'Less than 1 liter', value: 1 },
      { label: '1–2 liters', value: 2 },
      { label: 'More than 2 liters', value: 3 },
    ],
  },
  {
    field: 'tracks_calories',
    prompt: 'Do you keep track of the calories you eat?',
    options: YES_NO,
  },
  {
    field: 'physical_activity',
    prompt: 'How often are you physically active?',
    options: [
      { label: 'Not at all', value: 0 },
      { label: '1–2 days a week', value: 1 },
      { label: '2–4 days a week', value: 2 },
      { label: '4–5 days a week', value: 3 },
    ],
  },
  {
    field: 'screen_time',
    prompt: 'How much time do you spend on screens (phone, TV, computer) a day?',
    options: [
      { label: '0–2 hours', value: 0 },
      { label: '3–5 hours', value: 1 },
      { label: 'More than 5 hours', value: 2 },
    ],
  },
  { field: 'alcohol', prompt: 'How often do you drink alcohol?', options: FREQUENCY },
  {
    field: 'transportation',
    prompt: 'How do you usually get around?',
    options: [
      { label: 'Car', value: 'Automobile' },
      { label: 'Public transit', value: 'Public_Transportation' },
      { label: 'Walking', value: 'Walking' },
      { label: 'Bike', value: 'Bike' },
      { label: 'Motorbike', value: 'Motorbike' },
    ],
  },
]

export const MIN_AGE = 18
export const MAX_AGE = 100

export type Draft = Partial<Record<keyof HealthCheckAnswers, string | number | boolean>>

// Returns the complete answers, or the fields still missing
export function completeAnswers(
  draft: Draft,
): { answers: HealthCheckAnswers; missing: [] } | { answers: null; missing: string[] } {
  const missing = QUESTIONS.filter((question) => {
    const value = draft[question.field]
    if (question.field === 'age') {
      return typeof value !== 'number' || value < MIN_AGE || value > MAX_AGE
    }
    return value === undefined
  }).map((question) => question.prompt)
  if (missing.length > 0) return { answers: null, missing }
  return { answers: draft as HealthCheckAnswers, missing: [] }
}

// "34%": whole percent, but never "0%" or "100%", which would sound certain
export function formatLikelihood(probability: number): string {
  const percent = Math.round(probability * 100)
  if (percent < 1) return 'under 1%'
  if (percent > 99) return 'over 99%'
  return `${percent}%`
}

// The user's own answer to a question, in plain words
export function answerLabel(field: keyof HealthCheckAnswers, answers: HealthCheckAnswers): string {
  const value = answers[field]
  const question = QUESTIONS.find((q) => q.field === field)
  const option = question?.options?.find((o) => o.value === value)
  return option ? option.label : String(value)
}

// Describes a factor as an association in the data, never as a cause or an instruction
export function describeFactor(factor: HealthCheckFactor): string {
  const direction = factor.direction === 'raises' ? 'higher' : 'lower'
  return `In the survey data, answers like yours here went with a ${direction} estimate.`
}
