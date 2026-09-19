import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import Timeline from '../components/Timeline'

const windows = [
  {
    flight_id: 1,
    callsign: 'CA1001',
    operation: 'DEP',
    runway: '09L',
    runway_start: '2026-09-18T08:00:00.000Z',
    runway_end: '2026-09-18T08:01:00.000Z',
    taxi: [
      { taxiway: 'A', start: '2026-09-18T07:58:00.000Z', end: '2026-09-18T07:59:00.000Z' },
    ],
  },
  {
    flight_id: 2,
    callsign: 'CA2002',
    operation: 'ARR',
    runway: '09R',
    runway_start: '2026-09-18T08:05:00.000Z',
    runway_end: '2026-09-18T08:05:50.000Z',
    taxi: [],
  },
]

const closures = [
  {
    id: 1,
    runway: '09L',
    start: '2026-09-18T08:10:00.000Z',
    end: '2026-09-18T08:40:00.000Z',
    reason: '道面检查',
  },
]

const conflicts = [
  {
    id: 'SEP-1-9',
    type: 'SEPARATION',
    severity: 'SOFT',
    runway: '09L',
    taxiway: null,
    flight_ids: [1, 9],
    flights: ['CA1001', 'CA9009'],
    message: '间隔不足',
    start: '2026-09-18T08:00:00.000Z',
    end: '2026-09-18T08:01:00.000Z',
    suggestions: [],
  },
]

describe('Timeline', () => {
  it('renders one lane per runway with flight bars', () => {
    render(
      <Timeline windows={windows} closures={closures} conflicts={conflicts} />,
    )
    expect(screen.getByText('09L')).toBeInTheDocument()
    expect(screen.getByText('09R')).toBeInTheDocument()
    expect(screen.getByText('CA1001')).toBeInTheDocument()
    expect(screen.getByText('CA2002')).toBeInTheDocument()
  })

  it('draws closure bands and taxiway segments', () => {
    const { container } = render(
      <Timeline windows={windows} closures={closures} conflicts={[]} />,
    )
    expect(container.querySelectorAll('.closure-band').length).toBe(1)
    expect(container.querySelectorAll('.taxi-bar').length).toBe(1)
  })

  it('marks flights participating in a conflict', () => {
    const { container } = render(
      <Timeline windows={windows} closures={[]} conflicts={conflicts} />,
    )
    expect(container.querySelectorAll('.runway-bar.conflict').length).toBe(1)
  })
})
