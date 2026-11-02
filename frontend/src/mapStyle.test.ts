import { describe, expect, it } from 'vitest'
import { tractName } from './mapStyle'

describe('tractName', () => {
  it('turns the last 6 GEOID digits into a tract number and adds the county', () => {
    expect(tractName({ geoid: '48113000101', county: 'Dallas' })).toBe('Tract 1.01, Dallas County')
    expect(tractName({ geoid: '48439101100', county: 'Tarrant' })).toBe(
      'Tract 1011, Tarrant County',
    )
  })
})
