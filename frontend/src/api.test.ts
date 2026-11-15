import { afterEach, describe, expect, it, vi } from 'vitest'
import { apiUrl, deleteSavedHealthChecks } from './api'

describe('apiUrl', () => {
  it('goes through the dev proxy by default', () => {
    expect(apiUrl('/tracts')).toBe('/api/tracts')
  })

  it('encodes query parameters', () => {
    expect(apiUrl('/geocode', { q: '1500 Marilla St & Main' })).toBe(
      '/api/geocode?q=1500+Marilla+St+%26+Main',
    )
  })
})

describe('deleteSavedHealthChecks', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('sends the anonymous ID in a header, never in the URL', async () => {
    const fetchMock = vi.fn().mockResolvedValue(Response.json({ deleted: 2 }))
    vi.stubGlobal('fetch', fetchMock)
    const id = '3f2b8c1e-0000-4000-8000-000000000000'

    await expect(deleteSavedHealthChecks(id)).resolves.toEqual({ deleted: 2 })

    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/health-checks')
    expect(url).not.toContain(id)
    expect(init).toMatchObject({ method: 'DELETE', headers: { 'X-Anonymous-ID': id } })
  })
})
