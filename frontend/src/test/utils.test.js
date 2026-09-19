import { describe, it, expect } from 'vitest'
import { fmtTime, fmtSec, toLocalInput, fromLocalInput } from '../utils'

describe('utils', () => {
  it('formats seconds as compact durations', () => {
    expect(fmtSec(0)).toBe('0s')
    expect(fmtSec(45)).toBe('45s')
    expect(fmtSec(120)).toBe('2m')
    expect(fmtSec(150)).toBe('2m30s')
    expect(fmtSec(null)).toBe('—')
  })

  it('formats ISO timestamps as HH:MM:SS', () => {
    expect(fmtTime('2026-09-18T08:00:00')).toMatch(/^08:00:00$/)
  })

  it('round-trips datetime-local inputs', () => {
    const iso = '2026-09-18T08:30:00.000Z'
    const local = toLocalInput(iso)
    expect(local).toMatch(/2026-09-18 \d{2}:\d{2}:\d{2}/)
    const back = new Date(fromLocalInput(local)).toISOString()
    expect(back).toBe(iso)
  })
})
