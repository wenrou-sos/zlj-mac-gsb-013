import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { StoreProvider } from '../store'
import ConflictList from '../components/ConflictList'

const conflicts = [
  {
    id: 'SEP-1-2',
    type: 'SEPARATION',
    severity: 'SOFT',
    runway: '09L',
    taxiway: null,
    flight_ids: [1, 2],
    flights: ['CA1001', 'CA2002'],
    message: '跑道 09L：CA1001 → CA2002 间隔 20s，小于要求的 90s',
    start: '2026-09-18T08:00:00.000Z',
    end: '2026-09-18T08:01:00.000Z',
    suggestions: [
      {
        action: 'DELAY',
        flight_id: 2,
        callsign: 'CA2002',
        delay_seconds: 70,
        new_scheduled: '2026-09-18T08:02:00.000Z',
        note: '推迟 70s',
      },
    ],
  },
  {
    id: 'CLO-3-1',
    type: 'CLOSURE',
    severity: 'HARD',
    runway: '09R',
    taxiway: null,
    flight_ids: [3],
    flights: ['CA3003'],
    message: '跑道 09R 关闭，CA3003 占用窗口落入关闭区间',
    start: '2026-09-18T08:10:00.000Z',
    end: '2026-09-18T08:12:00.000Z',
    suggestions: [
      {
        action: 'CHANGE_RUNWAY',
        flight_id: 3,
        callsign: 'CA3003',
        to_runway: '18L',
        note: '改用 18L',
      },
    ],
  },
]

function mockFetch(route) {
  let adjusted = false
  return vi.fn(async (url, opts = {}) => {
    if (url.endsWith('/api/rehearse/adjust')) {
      adjusted = true
      return {
        ok: true,
        status: 200,
        json: async () => ({
          conflicts: route,
          windows: [],
          closures: [],
          conflict_count: route.length,
          hard_count: route.length,
        }),
      }
    }
    return {
      ok: true,
      status: 200,
      json: async () => {
        if (url.endsWith('/api/flights')) return []
        if (url.endsWith('/api/closures')) return []
        if (url.endsWith('/api/config')) return { runways: ['09L'] }
        const shown = adjusted ? route : conflicts
        return {
          conflicts: shown,
          windows: [],
          closures: [],
          conflict_count: shown.length,
          hard_count: shown.filter((c) => c.severity === 'HARD').length,
        }
      },
    }
  })
}

function renderList(route) {
  global.fetch = mockFetch(route)
  return render(
    <StoreProvider>
      <ConflictList />
    </StoreProvider>,
  )
}

describe('ConflictList', () => {
  beforeEach(() => vi.clearAllMocks())

  it('renders conflict cards with severity badges and suggestions', async () => {
    renderList()
    expect(
      await screen.findByText((_, el) => el?.textContent === 'CA1001 × CA2002'),
    ).toBeInTheDocument()
    expect(screen.getByText('1 严重')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /推迟 CA2002 70s/ })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /CA3003 改用跑道 18L/ })).toBeInTheDocument()
  })

  it('posts the adjustment and refreshes to the returned rehearsal', async () => {
    renderList([]) // after adjustment no conflicts remain
    await screen.findByRole('button', { name: /推迟 CA2002 70s/ })
    fireEvent.click(screen.getByRole('button', { name: /推迟 CA2002 70s/ }))
    await waitFor(() =>
      expect(screen.getByText('✓ 当前调度方案无冲突')).toBeInTheDocument(),
    )
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/rehearse/adjust'),
      expect.objectContaining({ method: 'POST' }),
    )
  })
})
