// A random ID for saved health checks, so saved results aren't linked to a person.
// It's created only when someone opts in to saving, and kept in this browser so their saved
// checks share one ID. Browser storage can be unavailable (private windows, blocked storage),
// so failures fall back to a fresh ID instead of breaking the page.
const STORAGE_KEY = 'foodscape-anonymous-id'

export function getAnonymousId(): string {
  try {
    const existing = localStorage.getItem(STORAGE_KEY)
    if (existing) return existing
    const created = crypto.randomUUID()
    localStorage.setItem(STORAGE_KEY, created)
    return created
  } catch {
    return crypto.randomUUID()
  }
}
