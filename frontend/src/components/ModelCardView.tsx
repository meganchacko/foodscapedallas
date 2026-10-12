import { useEffect, useState } from 'react'
import { fetchModelCard } from '../api'
import type { Metrics, ModelCard } from '../types'

function percent(value: number | undefined): string {
  return value === undefined ? '–' : `${Math.round(value * 100)}%`
}

function decimal(value: number | undefined): string {
  return value === undefined ? '–' : value.toFixed(2)
}

const GROUP_TITLES: Record<string, string> = { sex: 'By sex', age_band: 'By age' }

export function ModelCardView({ onBack }: { onBack: () => void }) {
  const [card, setCard] = useState<ModelCard | null>(null)
  const [error, setError] = useState(false)

  useEffect(() => {
    fetchModelCard()
      .then(setCard)
      .catch(() => setError(true))
  }, [])

  if (error) return <p className="error">Couldn't load the model card.</p>
  if (!card) return <p className="hint">Loading…</p>

  return (
    <article className="model-card">
      <button type="button" className="link-button" onClick={onBack}>
        ← Back to the health check
      </button>
      <h2>Model card</h2>
      <p className="hint">
        {card.name}, version {card.model_version}, trained {card.trained_on}
      </p>

      <h3>What it's for</h3>
      <p>{card.intended_use}</p>
      <p>Not for:</p>
      <ul>
        {card.not_intended_for.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>

      <h3>How well it works</h3>
      <p>
        Measured on people the model never saw during training. The second row only counts rows that
        look like real survey responses, which is closer to how it does for real people.
      </p>
      <MetricsTable
        rows={[
          ['Full test set', card.test_metrics],
          ['Real-looking responses only', card.test_metrics_survey_like_rows],
        ]}
      />
      {Object.entries(card.performance_by_group).map(([group, results]) => (
        <section key={group}>
          <h4>{GROUP_TITLES[group] ?? group}</h4>
          <MetricsTable rows={Object.entries(results)} />
        </section>
      ))}
      <p className="hint">
        Accuracy: how often the yes/no call (estimate of 50% or more) was right. ROC AUC: how well
        it ranks people with obesity above people without (0.5 is a coin flip, 1.0 is perfect).
        Small groups are noisy.
      </p>

      <h3>Effects of synthetic data</h3>
      <ul>
        {card.synthetic_data_effects.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>

      <h3>Limitations</h3>
      <ul>
        {card.limitations.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>

      <h3>Data and inputs</h3>
      <p>
        {card.training_data.source} ({card.training_data.license}, {card.training_data.citation}
        ). {card.training_data.notes}
      </p>
      <p>Target: {card.target}.</p>
      <p>Inputs: {card.features.map((feature) => feature.description).join('; ')}.</p>
      {card.excluded_features.map((feature) => (
        <p key={feature.name}>
          Not used: {feature.name}. {feature.reason}
        </p>
      ))}
      <p>
        Model: {card.model.type}. {card.model.selection}. Trained on {card.model.train_rows} rows.
      </p>
    </article>
  )
}

function MetricsTable({ rows }: { rows: [string, Metrics][] }) {
  return (
    <table className="metrics">
      <thead>
        <tr>
          <th scope="col">Group</th>
          <th scope="col">People</th>
          <th scope="col">Share with obesity</th>
          <th scope="col">Accuracy</th>
          <th scope="col">ROC AUC</th>
        </tr>
      </thead>
      <tbody>
        {rows.map(([label, metrics]) => (
          <tr key={label}>
            <th scope="row">{label}</th>
            <td>{metrics.n}</td>
            <td>{percent(metrics.obese_share)}</td>
            <td>{percent(metrics.accuracy)}</td>
            <td>{decimal(metrics.roc_auc)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
