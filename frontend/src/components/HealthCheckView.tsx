import { type FormEvent, useState } from 'react'
import { ApiError, checkHealth } from '../api'
import { getAnonymousId } from '../anonymousId'
import {
  MAX_AGE,
  MIN_AGE,
  QUESTIONS,
  answerLabel,
  completeAnswers,
  describeFactor,
  formatLikelihood,
  type Draft,
} from '../healthCheck'
import type { HealthCheckAnswers, HealthCheckResult, PlaceType } from '../types'

const NOT_ADVICE =
  'This is an educational estimate, not medical advice or a diagnosis. Talk to a doctor about ' +
  'your health.'

type Props = {
  onFindPlaces: (type: PlaceType) => void
  onShowModelCard: () => void
}

export function HealthCheckView({ onFindPlaces, onShowModelCard }: Props) {
  const [draft, setDraft] = useState<Draft>({})
  const [save, setSave] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<{ answers: HealthCheckAnswers; data: HealthCheckResult }>()

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    const { answers, missing } = completeAnswers(draft)
    if (!answers) {
      setError(`Please answer: ${missing.join('; ')}`)
      return
    }
    setError(null)
    setSubmitting(true)
    try {
      const data = await checkHealth(answers, save, save ? getAnonymousId() : null)
      setResult({ answers, data })
      window.scrollTo({ top: 0 })
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't reach the server.")
    } finally {
      setSubmitting(false)
    }
  }

  if (result) {
    return (
      <HealthCheckResultView
        answers={result.answers}
        result={result.data}
        onFindPlaces={onFindPlaces}
        onShowModelCard={onShowModelCard}
        onStartOver={() => setResult(undefined)}
      />
    )
  }

  return (
    <form className="health-form" onSubmit={onSubmit} noValidate>
      <h2>Health check</h2>
      <p>
        Answer a few questions about your habits to see an estimate of how likely obesity was for
        people with similar answers in a survey. It doesn't ask for your height or weight.
      </p>
      <p className="hint">{NOT_ADVICE}</p>

      {QUESTIONS.map((question) => (
        <fieldset key={question.field} className="question">
          <legend>{question.prompt}</legend>
          {question.hint && <p className="hint">{question.hint}</p>}
          {question.options ? (
            <div className="choices">
              {question.options.map((option) => (
                <label key={String(option.value)} className="choice">
                  <input
                    type="radio"
                    name={question.field}
                    checked={draft[question.field] === option.value}
                    onChange={() => setDraft({ ...draft, [question.field]: option.value })}
                  />
                  {option.label}
                </label>
              ))}
            </div>
          ) : (
            <input
              type="number"
              inputMode="numeric"
              min={MIN_AGE}
              max={MAX_AGE}
              aria-label={question.prompt}
              value={typeof draft.age === 'number' ? draft.age : ''}
              onChange={(event) =>
                setDraft({
                  ...draft,
                  age: event.target.value === '' ? undefined : Number(event.target.value),
                })
              }
              className="age-input"
            />
          )}
        </fieldset>
      ))}

      <label className="option save-option">
        <input type="checkbox" checked={save} onChange={(event) => setSave(event.target.checked)} />
        Save my answers anonymously to help improve this tool (optional). We never store your name,
        location, or anything that identifies you.
      </label>

      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      <button type="submit" className="primary" disabled={submitting}>
        {submitting ? 'Checking…' : 'See my estimate'}
      </button>
    </form>
  )
}

type ResultProps = {
  answers: HealthCheckAnswers
  result: HealthCheckResult
  onFindPlaces: (type: PlaceType) => void
  onShowModelCard: () => void
  onStartOver: () => void
}

const PLACE_BUTTON_LABELS: Record<'grocery' | 'farmers_market', string> = {
  grocery: 'Find grocery stores near you',
  farmers_market: 'Find farmers markets near you',
}

function HealthCheckResultView({
  answers,
  result,
  onFindPlaces,
  onShowModelCard,
  onStartOver,
}: ResultProps) {
  const likelihood = formatLikelihood(result.probability)
  return (
    <section className="health-result" aria-live="polite">
      <h2>Your estimate</h2>
      <p className="likelihood">{likelihood}</p>
      <p>
        Among people in the survey with answers like yours, an estimated {likelihood} had obesity
        (measured by BMI).
      </p>
      {result.notes.map((note) => (
        <p key={note} className="notice">
          {note}
        </p>
      ))}

      <h3>What moved this estimate</h3>
      <p className="hint">
        Compared with an average person in the survey. These are patterns in the data, not causes.
      </p>
      <ul className="factors">
        {result.factors.map((factor) => (
          <li key={factor.field}>
            <span className="factor-title">
              <span className={`factor-arrow ${factor.direction}`} aria-hidden="true">
                {factor.direction === 'raises' ? '▲' : '▼'}
              </span>
              {factor.label}: {answerLabel(factor.field, answers)}
              {factor.changeable && <span className="badge">habit</span>}
            </span>
            <span className="hint">{describeFactor(factor)}</span>
          </li>
        ))}
      </ul>

      {result.suggestion && (
        <div className="notice">
          <p>{result.suggestion.message}</p>
          {result.suggestion.place_type && (
            <button
              type="button"
              className="link-button"
              onClick={() => onFindPlaces(result.suggestion!.place_type!)}
            >
              {PLACE_BUTTON_LABELS[result.suggestion.place_type]}
            </button>
          )}
        </div>
      )}

      {result.saved && <p className="hint">Your answers were saved anonymously. Thank you.</p>}
      <p className="hint">{NOT_ADVICE}</p>
      <p className="hint">
        How the model works and where it falls short:{' '}
        <button type="button" className="link-button" onClick={onShowModelCard}>
          read the model card
        </button>
      </p>
      <button type="button" className="secondary" onClick={onStartOver}>
        Start over
      </button>
    </section>
  )
}
