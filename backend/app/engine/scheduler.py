"""Conflict detection and resolution engine.

Three kinds of conflicts are detected:

* SEPARATION - two operations on the same runway are closer than the wake
  turbulence / safety separation.
* CLOSURE    - an operation occupies a runway inside a published closure.
* TAXIWAY    - two flights occupy the same taxiway node at the same time.

Suggestions are produced for every conflict; ``auto_resolve`` greedily delays
flights until the schedule is conflict free (within the configured maximum
delay).
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta
from itertools import combinations

from .windows import flight_windows
from .types import (
    ClosureInput,
    ConfigInput,
    Conflict,
    FlightInput,
    FlightWindows,
)

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _callsigns(flights: list[FlightInput], ids: list[int]) -> list[str]:
    by_id = {f.id: f for f in flights}
    return [by_id[i].callsign for i in ids if i in by_id]


def _overlaps(a_start: datetime, a_end: datetime,
              b_start: datetime, b_end: datetime) -> bool:
    return a_start < b_end and b_start < a_end


def required_separation(leader: FlightInput, follower: FlightInput,
                        cfg: ConfigInput) -> int:
    """Required runway separation in seconds when ``leader`` goes first."""
    extra = cfg.wake_sep.get(f"{leader.wake}{follower.wake}", 0)
    return cfg.min_sep + int(extra or 0)


def _shifted(flight: FlightInput, delay: int) -> FlightInput:
    f = deepcopy(flight)
    f.scheduled = f.scheduled + timedelta(seconds=delay)
    return f


def _all_windows(flights: list[FlightInput],
                 cfg: ConfigInput) -> list[FlightWindows]:
    return [flight_windows(f, cfg) for f in flights]


# ---------------------------------------------------------------------------
# feasibility: can a (optionally delayed / re-runwayed) flight join a plan?
# ---------------------------------------------------------------------------


def _runway_gap_ok(candidate: FlightInput, others: list[FlightInput],
                   cfg: ConfigInput) -> int:
    """Smallest non-negative delay so the candidate clears every other flight
    on the same runway, ignoring closures.

    ``others`` are treated as flights that have already been fixed earlier in
    the processing order: the candidate is only pushed *after* them. Other
    flights that (still) sit later in time are ignored here — they will be
    pushed when their own turn comes.
    """
    delay = 0
    for _ in range(len(others) + 2):
        cw = flight_windows(_shifted(candidate, delay), cfg).runway_window
        extra = 0
        for other in others:
            if other.runway != candidate.runway:
                continue
            ow = flight_windows(other, cfg).runway_window
            if cw.start >= ow.end:
                # candidate follows other: need follower gap
                have = (cw.start - ow.end).total_seconds()
                need = required_separation(other, candidate, cfg)
                if have < need:
                    extra = max(extra, int(round(need - have)))
            elif ow.start >= cw.end:
                # candidate still sits before other but too close; the other
                # will be shifted on its own turn -> nothing to do here
                continue
            else:
                # windows overlap -> move fully behind the other flight
                need = required_separation(other, candidate, cfg)
                target_start = ow.end + timedelta(seconds=need)
                extra = max(
                    extra,
                    int(round((target_start - cw.start).total_seconds())),
                )
        if extra <= 0:
            return delay
        delay += extra
    return delay


def earliest_feasible_delay(flight: FlightInput,
                            others: list[FlightInput],
                            closures: list[ClosureInput],
                            cfg: ConfigInput,
                            max_delay: int) -> int | None:
    """Earliest delay (seconds) so runway separation and closures are clear.

    Uses the runway-gap solver which accounts for every other flight on the
    runway, then verifies the closure windows of that result.
    """
    delay = _runway_gap_ok(flight, others, cfg)
    if delay > max_delay:
        return None
    candidate = _shifted(flight, delay)
    cw = flight_windows(candidate, cfg).runway_window
    blocked_by = next(
        (c for c in closures
         if c.runway == candidate.runway
         and _overlaps(cw.start, cw.end, c.start, c.end)),
        None,
    )
    if blocked_by is None:
        return delay
    # hop over the blocking closure and re-check separation
    if flight.operation == "DEP":
        hop = int(round((blocked_by.end - candidate.scheduled).total_seconds()))
    else:
        hop = int(round(
            (blocked_by.start - timedelta(seconds=cfg.arr_occupy)
             - candidate.scheduled).total_seconds()
        ))
    total = delay + max(0, hop)
    if total > max_delay:
        return None
    recheck = earliest_feasible_delay(
        _shifted(flight, total), others, [], cfg, max_delay - total
    )
    if recheck is None or total + recheck > max_delay:
        return None
    return total + recheck


# ---------------------------------------------------------------------------
# conflict detection
# ---------------------------------------------------------------------------


def _alt_runway_clear(flight: FlightInput, alt: str,
                      flights: list[FlightInput],
                      closures: list[ClosureInput],
                      cfg: ConfigInput) -> bool:
    trial = deepcopy(flight)
    trial.runway = alt
    if _runway_gap_ok(trial, [x for x in flights if x.id != flight.id], cfg):
        return False
    rw = flight_windows(trial, cfg).runway_window
    return not any(
        c.runway == alt and _overlaps(rw.start, rw.end, c.start, c.end)
        for c in closures
    )


def _separation_conflicts(flights, closures, cfg, windows) -> list[Conflict]:
    out: list[Conflict] = []
    by_runway: dict[str, list[FlightWindows]] = {}
    for w in windows:
        by_runway.setdefault(w.runway, []).append(w)
    fmap = {f.id: f for f in flights}

    for runway, group in by_runway.items():
        group.sort(key=lambda w: w.runway_window.start)
        for wa_w, wb_w in combinations(group, 2):
            if wa_w.runway_window.start > wb_w.runway_window.start:
                wa_w, wb_w = wb_w, wa_w
            wa, wb = wa_w.runway_window, wb_w.runway_window
            leader = fmap[wa_w.flight_id]
            follower = fmap[wb_w.flight_id]
            need = required_separation(leader, follower, cfg)
            gap = (wb.start - wa.end).total_seconds()
            if gap >= need:
                continue
            ids = [leader.id, follower.id]
            if gap < 0:
                msg = (f"跑道 {runway}：{leader.callsign} 与 "
                       f"{follower.callsign} 跑道占用时间重叠"
                       f"（{int(round(-gap))}s）")
            else:
                msg = (f"跑道 {runway}：{leader.callsign} → "
                       f"{follower.callsign} 间隔 {int(round(gap))}s，"
                       f"小于要求的 {need}s")
            delay_s = max(5, int(round(need - gap)))
            feasible = earliest_feasible_delay(
                follower,
                [x for x in flights if x.id != follower.id],
                closures, cfg, cfg.max_delay,
            )
            suggestions: list[dict] = []
            if feasible is not None:
                delay_s = max(delay_s, feasible)
                suggestions.append({
                    "action": "DELAY",
                    "flight_id": follower.id,
                    "callsign": follower.callsign,
                    "delay_seconds": delay_s,
                    "new_scheduled": (
                        follower.scheduled + timedelta(seconds=delay_s)
                    ).isoformat(),
                    "note": f"推迟 {delay_s}s 以满足 {need}s 安全间隔",
                })
            else:
                suggestions.append({
                    "action": "DELAY",
                    "flight_id": follower.id,
                    "callsign": follower.callsign,
                    "delay_seconds": None,
                    "note": "在最大可接受延误内无法仅靠推迟解决，建议更换跑道",
                })
            for alt in cfg.runways:
                if alt != runway and _alt_runway_clear(
                    follower, alt, flights, closures, cfg
                ):
                    suggestions.append({
                        "action": "CHANGE_RUNWAY",
                        "flight_id": follower.id,
                        "callsign": follower.callsign,
                        "from_runway": runway,
                        "to_runway": alt,
                        "note": f"改用空闲跑道 {alt}",
                    })
            out.append(Conflict(
                id=f"SEP-{leader.id}-{follower.id}",
                type="SEPARATION",
                severity="HARD" if gap < 0 else "SOFT",
                runway=runway,
                taxiway=None,
                flight_ids=ids,
                flights=_callsigns(flights, ids),
                message=msg,
                start=max(wa.start, wb.start),
                end=min(wa.end, wb.end) if gap < 0 else wb.start,
                suggestions=suggestions,
            ))
    return out


def _closure_conflicts(flights, closures, cfg, windows) -> list[Conflict]:
    out: list[Conflict] = []
    fmap = {f.id: f for f in flights}
    for w in windows:
        rw = w.runway_window
        for c in closures:
            if c.runway != w.runway:
                continue
            if _overlaps(rw.start, rw.end, c.start, c.end):
                f = fmap[w.flight_id]
                # DEP must move to after the closure; ARR window must clear
                # the closure start (window ends at the landing time).
                if f.operation == "DEP":
                    delay = int(round((c.end - f.scheduled).total_seconds()))
                else:
                    delay = int(round(
                        (c.start - timedelta(seconds=cfg.arr_occupy)
                         - f.scheduled).total_seconds()
                    ))
                suggestions: list[dict] = [{
                    "action": "DELAY",
                    "flight_id": f.id,
                    "callsign": f.callsign,
                    "delay_seconds": max(5, delay),
                    "new_scheduled": (
                        f.scheduled + timedelta(seconds=max(5, delay))
                    ).isoformat(),
                    "note": f"推迟到跑道 {c.runway} 关闭结束（{c.end:%H:%M:%S}）之后",
                }]
                for alt in cfg.runways:
                    if alt != c.runway and _alt_runway_clear(
                        f, alt, flights, closures, cfg
                    ):
                        suggestions.append({
                            "action": "CHANGE_RUNWAY",
                            "flight_id": f.id,
                            "callsign": f.callsign,
                            "from_runway": c.runway,
                            "to_runway": alt,
                            "note": f"改用未关闭跑道 {alt}",
                        })
                out.append(Conflict(
                    id=f"CLO-{f.id}-{c.id}",
                    type="CLOSURE",
                    severity="HARD",
                    runway=c.runway,
                    taxiway=None,
                    flight_ids=[f.id],
                    flights=[f.callsign],
                    message=(f"跑道 {c.runway} 于 {c.start:%H:%M}-{c.end:%H:%M}"
                             f" 关闭（{c.reason or '未注明原因'}），"
                             f"{f.callsign} 占用窗口落入关闭区间"),
                    start=max(rw.start, c.start),
                    end=min(rw.end, c.end),
                    suggestions=suggestions,
                ))
    return out


def _taxi_clear_delay(target: FlightInput, node: str,
                      others: list[FlightInput], cfg: ConfigInput) -> int:
    """Smallest delay so ``target`` no longer shares ``node`` with any other
    flight (every flight's whole schedule is shifted by its delay)."""
    delay = 0
    for _ in range(len(others) + 1):
        shifted = _shifted(target, delay)
        tws = {t.taxiway: t for t in flight_windows(shifted, cfg).taxi_windows}
        mine = tws.get(node)
        extra = 0
        if mine is not None:
            for other in others:
                for t in flight_windows(other, cfg).taxi_windows:
                    if t.taxiway != node:
                        continue
                    if _overlaps(mine.start, mine.end, t.start, t.end):
                        need = int(round(
                            (t.end - mine.start).total_seconds())) + 5
                        extra = max(extra, need)
        if extra <= 0:
            return delay
        delay += extra
    return delay


def _taxiway_conflicts(flights, cfg, windows) -> list[Conflict]:
    out: list[Conflict] = []
    fmap = {f.id: f for f in flights}
    # taxiway node -> list of (flight_id, window)
    occupancy: dict[str, list[tuple[int, object]]] = {}
    for w in windows:
        for tw in w.taxi_windows:
            occupancy.setdefault(tw.taxiway, []).append((w.flight_id, tw))

    for node, uses in occupancy.items():
        uses.sort(key=lambda u: u[1].start)
        for (ida, wa), (idb, wb) in combinations(uses, 2):
            if ida == idb:
                continue
            if _overlaps(wa.start, wa.end, wb.start, wb.end):
                fa, fb = fmap[ida], fmap[idb]
                ids = sorted([ida, idb])
                # delay the flight that reaches the node later in absolute
                # time; compute a delay that clears *every* user of the node
                if wa.start <= wb.start:
                    target = fb
                else:
                    target = fa
                delay = _taxi_clear_delay(
                    target, node,
                    [x for x in flights if x.id != target.id], cfg,
                )
                out.append(Conflict(
                    id=f"TAX-{ids[0]}-{ids[1]}-{node}",
                    type="TAXIWAY",
                    severity="SOFT",
                    runway=None,
                    taxiway=node,
                    flight_ids=ids,
                    flights=_callsigns(flights, ids),
                    message=(f"滑行道节点 {node}：{fa.callsign} 与 "
                             f"{fb.callsign} 同时占用（地面冲突风险）"),
                    start=max(wa.start, wb.start),
                    end=min(wa.end, wb.end),
                    suggestions=[{
                        "action": "DELAY",
                        "flight_id": target.id,
                        "callsign": target.callsign,
                        "delay_seconds": max(5, delay),
                        "new_scheduled": (
                            target.scheduled
                            + timedelta(seconds=max(5, delay))
                        ).isoformat(),
                        "note": f"推迟 {target.callsign}，让出节点 {node}",
                    }],
                ))
    return out


def detect_conflicts(flights: list[FlightInput],
                     closures: list[ClosureInput],
                     cfg: ConfigInput) -> tuple[list[Conflict], list[FlightWindows]]:
    windows = _all_windows(flights, cfg)
    conflicts: list[Conflict] = []
    conflicts += _closure_conflicts(flights, closures, cfg, windows)
    conflicts += _separation_conflicts(flights, closures, cfg, windows)
    conflicts += _taxiway_conflicts(flights, cfg, windows)
    return conflicts, windows


# ---------------------------------------------------------------------------
# automatic resolver
# ---------------------------------------------------------------------------


def _signature(conflicts: list[Conflict]) -> set[str]:
    return {
        (c.type + "|"
         + (c.taxiway or c.runway or "")
         + "|" + "-".join(map(str, c.flight_ids)))
        for c in conflicts
    }


def _taxi_clear_delay_against(target: FlightInput,
                              placed: list[FlightInput],
                              cfg: ConfigInput) -> int:
    """Delay so every taxiway node of ``target`` is clear of ``placed``.

    Only pushes the target past a *later* occupancy; if the target reaches a
    node before an already-placed flight, that flight cannot move anymore and
    the target has to move past it too (ground movement has no wake order).
    """
    delay = 0
    for _ in range(max(1, len(placed)) + 2):
        shifted = _shifted(target, delay)
        mine = {t.taxiway: t for t
                in flight_windows(shifted, cfg).taxi_windows}
        extra = 0
        for other in placed:
            for t in flight_windows(other, cfg).taxi_windows:
                m = mine.get(t.taxiway)
                if m and _overlaps(m.start, m.end, t.start, t.end):
                    extra = max(
                        extra,
                        int(round((t.end - m.start).total_seconds())) + 5,
                    )
        if extra <= 0:
            return delay
        delay += extra
    return delay


def auto_resolve(flights: list[FlightInput],
                 closures: list[ClosureInput],
                 cfg: ConfigInput,
                 max_passes: int = 3
                 ) -> tuple[dict[int, int], dict[int, str],
                            list[Conflict], list[str]]:
    """Construct a conflict-free plan.

    Flights are processed in scheduled order and each one is delayed only as
    much as needed to clear the flights already placed: runway separation,
    closures and taxiway occupancy. If the required delay exceeds the
    configured maximum, a free alternative runway is tried first.
    Returns (delay map, runway-change map, remaining conflicts, log).
    """
    work = {f.id: deepcopy(f) for f in flights}
    delays = {fid: 0 for fid in work}
    runway_changes: dict[int, str] = {}
    log: list[str] = []

    order_ids = [f.id for f in
                 sorted(flights, key=lambda x: x.scheduled)]

    def required_delay(fid: int) -> int:
        flight = work[fid]
        idx = order_ids.index(fid)
        placed = [work[o] for o in order_ids[:idx]]
        need = _runway_gap_ok(flight, placed, cfg)
        candidate = _shifted(flight, need)
        rw = flight_windows(candidate, cfg).runway_window
        closure = next(
            (c for c in closures
             if c.runway == candidate.runway
             and _overlaps(rw.start, rw.end, c.start, c.end)),
            None,
        )
        if closure is not None:
            if flight.operation == "DEP":
                hop = int(round(
                    (closure.end - candidate.scheduled).total_seconds()))
            else:
                hop = int(round((
                    closure.start - timedelta(seconds=cfg.arr_occupy)
                    - candidate.scheduled).total_seconds()))
            need += max(0, hop)
        candidate = _shifted(flight, need)
        need += _taxi_clear_delay_against(candidate, placed, cfg)
        return need

    for pass_no in range(1, max_passes + 2):
        moved_any = False
        for fid in order_ids:
            flight = work[fid]
            need = required_delay(fid)
            headroom = cfg.max_delay - delays[fid]

            # try alternative runways if this one cannot be held in time
            if need > headroom:
                best = None
                for alt in cfg.runways:
                    if alt == flight.runway:
                        continue
                    trial = deepcopy(flight)
                    trial.runway = alt
                    rw = flight_windows(trial, cfg).runway_window
                    if any(c.runway == alt
                           and _overlaps(rw.start, rw.end, c.start, c.end)
                           for c in closures):
                        continue
                    idx = order_ids.index(fid)
                    placed = [work[o] for o in order_ids[:idx]]
                    alt_need = _runway_gap_ok(trial, placed, cfg)
                    alt_trial = _shifted(trial, alt_need)
                    alt_need += _taxi_clear_delay_against(
                        alt_trial, placed, cfg)
                    if alt_need <= headroom and (
                            best is None or alt_need < best[1]):
                        best = (alt, alt_need)
                if best is not None:
                    alt, alt_need = best
                    old_runway = flight.runway
                    flight.runway = alt
                    runway_changes[fid] = alt
                    if alt_need > 0:
                        flight.scheduled += timedelta(seconds=alt_need)
                        delays[fid] += alt_need
                    moved_any = True
                    log.append(
                        f"第 {pass_no} 轮：{flight.callsign} 由跑道 "
                        f"{old_runway} 改派 {alt}"
                        + (f"，并推迟 {alt_need}s" if alt_need else "")
                    )
                    continue

            if need <= 0:
                continue
            add = min(need, max(0, headroom))
            if add <= 0:
                log.append(
                    f"第 {pass_no} 轮：{flight.callsign} 已达最大延误 "
                    f"{cfg.max_delay}s，保持现状"
                )
                continue
            flight.scheduled += timedelta(seconds=add)
            delays[fid] += add
            moved_any = True
            log.append(
                f"第 {pass_no} 轮：{flight.callsign} 推迟 {add}s"
                f"（累计 {delays[fid]}s）"
            )
        if not moved_any:
            break

    result = [work[fid] for fid in order_ids]
    remaining, _ = detect_conflicts(result, closures, cfg)
    if remaining:
        log.append(f"调度结束，仍有 {len(remaining)} 个冲突需人工调整")
    else:
        log.append("调度完成：跑道间隔、关闭区间与滑行道均无冲突")
    return delays, runway_changes, remaining, log
