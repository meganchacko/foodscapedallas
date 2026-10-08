import type { View } from '../types'

const TABS: { view: View; label: string }[] = [
  { view: 'explore', label: 'Map explorer' },
  { view: 'nearby', label: 'Find food near me' },
]

export function ViewTabs({ view, onChange }: { view: View; onChange: (view: View) => void }) {
  return (
    <div className="tabs" role="tablist" aria-label="View">
      {TABS.map((tab) => (
        <button
          key={tab.view}
          type="button"
          role="tab"
          aria-selected={view === tab.view}
          className={view === tab.view ? 'tab active' : 'tab'}
          onClick={() => onChange(tab.view)}
        >
          {tab.label}
        </button>
      ))}
    </div>
  )
}
