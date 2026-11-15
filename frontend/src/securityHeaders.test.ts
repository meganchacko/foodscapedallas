import { describe, expect, it } from 'vitest'
// The headers Azure Static Web Apps sends with every page
import config from '../public/staticwebapp.config.json'

const csp = config.globalHeaders['Content-Security-Policy']

describe('Content-Security-Policy', () => {
  it('only runs scripts from this site', () => {
    expect(csp).toContain("script-src 'self'")
    expect(csp).not.toContain('unsafe-inline')
    expect(csp).not.toContain('unsafe-eval')
  })

  it('stops other sites from framing the page', () => {
    expect(csp).toContain("frame-ancestors 'none'")
  })

  it('has a placeholder for the API address, filled in by the deploy job', () => {
    expect(csp).toMatch(/connect-src 'self' __API_ORIGIN__/)
  })
})
