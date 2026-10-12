import { describe, expect, it } from 'vitest'
import { apiUrl } from './api'

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
