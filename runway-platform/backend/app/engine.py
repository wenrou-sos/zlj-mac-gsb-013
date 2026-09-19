"""跑道占用冲突识别与调整方案引擎。

时间约定：
- 所有时刻均为带时区偏移的 ISO-8601 字符串（如 2026-09-19T08:00:00Z）。
- 跑道占用窗口：
  * 离场航班 [takeoff_time - enter_offset, takeoff_time + vacate_offset]
  * 进场航班 [landing_time - enter_offset, landing_time + vacate_offset]
- 滑行路线：有序节点列表； runway 类型节点代表穿越/使用跑道，
  crossing_duration 秒为该节点处占用跑道的时长。
- 安全间隔：以前一航班的跑道基准时刻(起飞/落地)为基准，
  按 前机/后机 的运行类型矩阵校验（单位秒）。

冲突类型：
- SEPARATION  同跑道前后机安全间隔不足
- OCCUPANCY   同跑道占用窗口重叠
- CROSSING    后机滑行穿越跑道时，前机仍占用跑道
- CLOSURE     跑道关闭区间内存在占用/穿越
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

RUNWAY_NODE = "runway"
TAXIWAY_NODE = "taxiway"

ARRIVAL = "arrival"
DEPARTURE = "departure"

SEPARATION_DEFAULT = 90  # 同跑道前后机默认最小间隔（秒）
MAX_DELAY_SECONDS = 7200  # 自动调整时允许的最大延误
CROSSING_SCAN_WINDOW = 1800  # 穿越冲突扫描窗口（秒）


def parse_ts(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        return value
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def fmt_ts(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def route_runway_steps(route: list[dict]) -> list[dict]:
    """路线中所有跑道节点（使用跑道或穿越跑道）。"""
    return [s for s in (route or []) if s.get("type") == RUNWAY_NODE]


def base_time(flight: dict) -> datetime:
    """跑道基准时刻：离场=起飞时刻，进场=落地时刻。"""
    key = "takeoff_time" if flight["operation"] == DEPARTURE else "landing_time"
    return parse_ts(flight[key])


def runway_id_of_flight(flight: dict) -> str | None:
    for step in route_runway_steps(flight.get("route", [])):
        rid = step.get("runway_id") or flight.get("runway_id")
        if rid:
            return rid
    return flight.get("runway_id")


def runway_intervals(flight: dict) -> list[tuple[str, datetime, datetime, str]]:
    """返回 (runway_id, start, end, role) 列表。

    role: 'use' 表示航班自身使用跑道（起降），'cross' 表示滑行穿越。
    """
    op = flight["operation"]
    ref_key = "takeoff_time" if op == DEPARTURE else "landing_time"
    ref = parse_ts(flight[ref_key])
    primary = flight.get("runway_id")
    intervals: list[tuple[str, datetime, datetime, str]] = []
    found_primary = False

    steps = route_runway_steps(flight.get("route", []))
    if not steps and primary:
        enter = int(flight.get("enter_offset", 60))
        vacate = int(flight.get("vacate_offset", 40))
        intervals.append(
            (primary, ref - timedelta(seconds=enter),
             ref + timedelta(seconds=vacate), "use")
        )
        return intervals

    for i, step in enumerate(steps):
        rid = step.get("runway_id") or primary
        if rid is None:
            continue
        duration = int(step.get("crossing_duration", 30))
        if not found_primary and rid == primary:
            enter = int(step.get("enter_offset", flight.get("enter_offset", 60)))
            vacate = int(step.get("vacate_offset", flight.get("vacate_offset", 40)))
            intervals.append(
                (rid, ref - timedelta(seconds=enter),
                 ref + timedelta(seconds=vacate), "use")
            )
            found_primary = True
        else:
            # 穿越节点：以路线顺序用固定滑行速度推断穿越时刻
            cross_at = _crossing_time(flight, steps, i, ref)
            intervals.append(
                (rid, cross_at, cross_at + timedelta(seconds=duration), "cross")
            )
    return intervals


def _crossing_time(
    flight: dict, steps: list[dict], index: int, ref: datetime
) -> datetime:
    """根据路线节点 taxi_seconds 推断第 index 个跑道节点的进入时刻。

    主使用跑道节点的时刻锚定为基准时刻，其余节点按相对步长推算：
    离场沿路线向后，进场沿路线向前。
    """
    op = flight["operation"]
    primary_idx = next(
        (i for i, s in enumerate(steps)
         if (s.get("runway_id") or flight.get("runway_id")) == flight.get("runway_id")),
        0,
    )
    t = ref
    if op == DEPARTURE:
        # 穿越点在主跑道之前：沿路线回推
        for j in range(index, primary_idx):
            t -= timedelta(seconds=int(steps[j].get("taxi_seconds", 45)))
    else:
        # 进场：穿越点在主跑道之后：沿路线延后
        for j in range(primary_idx, index):
            t += timedelta(seconds=int(steps[j].get("taxi_seconds", 45)))
    return t


def separation_required(
    leader_op: str, follower_op: str, matrix: dict | None
) -> int:
    if not matrix:
        return SEPARATION_DEFAULT
    rows = matrix.get(leader_op) or {}
    return int(rows.get(follower_op, SEPARATION_DEFAULT))


def overlaps(a: tuple[datetime, datetime], b: tuple[datetime, datetime]) -> bool:
    return a[0] < b[1] and b[0] < a[1]


def conflict_id(kind: str, a: str, b: str | None = None) -> str:
    return f"{kind}:{a}:{b or '-'}"


def detect_conflicts(
    flights: list[dict],
    closures: list[dict] | None = None,
    separation_matrix: dict | None = None,
) -> list[dict]:
    """识别全部调度冲突。"""
    conflicts: list[dict] = []
    flights = [f for f in flights if f.get("runway_id") or f.get("route")]
    closures = closures or []

    # 预计算每架航班的跑道占用区间
    intervals_by_flight = {f["id"]: runway_intervals(f) for f in flights}

    # 1. 航班两两比对（同跑道）
    for i, leader in enumerate(flights):
        for follower in flights[i + 1 :]:
            conflicts.extend(
                _pair_conflicts(
                    leader, follower, intervals_by_flight, separation_matrix
                )
            )

    # 2. 跑道关闭区间
    closure_windows = [
        (c["runway_id"], parse_ts(c["start_time"]), parse_ts(c["end_time"]), c)
        for c in closures
    ]
    for f in flights:
        for rid, start, end, closure in closure_windows:
            for fr_id, istart, iend, role in intervals_by_flight[f["id"]]:
                if fr_id == rid and overlaps((istart, iend), (start, end)):
                    conflicts.append(
                        {
                            "id": conflict_id("CLOSURE", f["id"], closure.get("id")),
                            "type": "CLOSURE",
                            "runway_id": rid,
                            "flight_ids": [f["id"]],
                            "message": (
                                f"航班 {f['callsign']} {role == 'cross' and '穿越' or '占用'}"
                                f"跑道 {rid} 的窗口与关闭区间 "
                                f"{fmt_ts(start)} ~ {fmt_ts(end)} 冲突"
                            ),
                            "time": fmt_ts(istart),
                            "severity": "high",
                            "closure_id": closure.get("id"),
                            "window_start": fmt_ts(max(istart, start)),
                            "window_end": fmt_ts(min(iend, end)),
                        }
                    )
    conflicts.sort(key=lambda c: (c["time"], c["id"]))
    return conflicts


def _ordered_pair(leader: dict, follower: dict) -> tuple[dict, dict]:
    if base_time(leader) <= base_time(follower):
        return leader, follower
    return follower, leader


def _pair_conflicts(
    fa: dict,
    fb: dict,
    intervals: dict[str, list],
    matrix: dict | None,
) -> list[dict]:
    out: list[dict] = []
    leader, follower = _ordered_pair(fa, fb)
    ta, tb = base_time(leader), base_time(follower)
    gap = (tb - ta).total_seconds()

    for ra, sa, ea, role_a in intervals[leader["id"]]:
        for rb, sb, eb, role_b in intervals[follower["id"]]:
            if ra != rb:
                continue

            # 安全间隔（仅对两架航班“使用”同一条跑道的基准时刻校验）
            if role_a == "use" and role_b == "use":
                required = separation_required(
                    leader["operation"], follower["operation"], matrix
                )
                if 0 <= gap < required:
                    out.append(
                        {
                            "id": conflict_id("SEPARATION", leader["id"], follower["id"]),
                            "type": "SEPARATION",
                            "runway_id": ra,
                            "flight_ids": [leader["id"], follower["id"]],
                            "message": (
                                f"跑道 {ra}：{leader['callsign']} 与 "
                                f"{follower['callsign']} 间隔 {int(gap)}s < "
                                f"规定 {required}s"
                            ),
                            "time": fmt_ts(tb),
                            "severity": "high" if gap < required * 0.6 else "medium",
                            "actual_gap_seconds": int(gap),
                            "required_gap_seconds": required,
                        }
                    )

            # 占用窗口重叠
            if overlaps((sa, ea), (sb, eb)):
                conflict_type = (
                    "OCCUPANCY" if role_a == "use" and role_b == "use" else "CROSSING"
                )
                out.append(
                    {
                        "id": conflict_id(
                            conflict_type,
                            f"{leader['id']}|{follower['id']}|{ra}",
                        ),
                        "type": conflict_type,
                        "runway_id": ra,
                        "flight_ids": [leader["id"], follower["id"]],
                        "message": (
                            f"跑道 {ra}：{leader['callsign']} 占用窗口 "
                            f"({fmt_ts(sa)}~{fmt_ts(ea)}) 与 "
                            f"{follower['callsign']} ({fmt_ts(sb)}~{fmt_ts(eb)}) 重叠"
                        ),
                        "time": fmt_ts(max(sa, sb)),
                        "severity": "high",
                    }
                )
    return _dedupe(out)


def _dedupe(conflicts: list[dict]) -> list[dict]:
    seen: dict[str, dict] = {}
    for c in conflicts:
        seen.setdefault(c["id"], c)
    return list(seen.values())


# ---------------------------------------------------------------------------
# 调整方案
# ---------------------------------------------------------------------------

def shift_flight(flight: dict, delta_seconds: int) -> dict:
    """将航班整体（起降时刻、路线节点时刻随之平移）顺延 delta 秒。"""
    f = {**flight, "route": [dict(s) for s in flight.get("route", [])]}
    delta = timedelta(seconds=delta_seconds)
    for key in ("scheduled_time", "takeoff_time", "landing_time"):
        if f.get(key):
            f[key] = fmt_ts(parse_ts(f[key]) + delta)
    return f


def retime_flight(flight: dict, new_ref_time: datetime) -> dict:
    """把航班的跑道基准时刻调整到指定时刻（其余字段整体平移）。"""
    delta = int((new_ref_time - base_time(flight)).total_seconds())
    return shift_flight(flight, delta)


def assign_runway(flight: dict, new_runway_id: str) -> dict:
    """改派跑道：替换路线中的跑道节点。"""
    f = {**flight, "route": [dict(s) for s in flight.get("route", [])]}
    f["runway_id"] = new_runway_id
    for step in f["route"]:
        if step.get("type") == RUNWAY_NODE and step.get("primary"):
            step["runway_id"] = new_runway_id
    return f


def suggest_resolutions(
    flights: list[dict],
    closures: list[dict] | None = None,
    separation_matrix: dict | None = None,
    runways: list[dict] | None = None,
) -> list[dict]:
    """为每个冲突航班生成调整方案：顺延 / 改派跑道。"""
    by_id = {f["id"]: f for f in flights}
    conflicts = detect_conflicts(flights, closures, separation_matrix)
    suggestions: list[dict] = []

    for f in flights:
        related = [c for c in conflicts if f["id"] in c["flight_ids"]]
        if not related:
            continue

        # 方案 A：最小顺延
        min_delay = _minimum_delay(f, flights, closures, separation_matrix)
        options: list[dict] = []
        if min_delay is not None:
            options.append(
                {
                    "kind": "DELAY",
                    "delta_seconds": min_delay,
                    "description": f"顺延 {min_delay // 60} 分 {min_delay % 60} 秒",
                }
            )

        # 方案 B：改派其他可用跑道
        current = runway_id_of_flight(f)
        for rw in runways or []:
            if rw["id"] != current and rw.get("active", True):
                candidate = assign_runway(f, rw["id"])
                others = [x for x in flights if x["id"] != f["id"]]
                residual = detect_conflicts(
                    others + [candidate], closures, separation_matrix
                )
                options.append(
                    {
                        "kind": "CHANGE_RUNWAY",
                        "new_runway_id": rw["id"],
                        "description": f"改派跑道 {rw['id']}"
                        + ("（仍有残余冲突）" if residual else ""),
                        "residual_conflicts": len(residual),
                    }
                )

        suggestions.append(
            {
                "flight_id": f["id"],
                "callsign": f["callsign"],
                "conflict_ids": [c["id"] for c in related],
                "options": options,
            }
        )
    return suggestions


def _minimum_delay(
    target: dict,
    flights: list[dict],
    closures: list[dict] | None,
    matrix: dict | None,
) -> int | None:
    others = [x for x in flights if x["id"] != target["id"]]
    for minute in range(0, MAX_DELAY_SECONDS + 1, 30):
        moved = shift_flight(target, minute)
        if not detect_conflicts(others + [moved], closures, matrix):
            return minute
    return None


def auto_resolve(
    flights: list[dict],
    closures: list[dict] | None = None,
    separation_matrix: dict | None = None,
) -> dict:
    """贪心自动排程：按基准时刻顺序逐架顺延至无冲突。"""
    resolved = sorted(flights, key=base_time)
    total_delay = 0
    adjustments: list[dict] = []
    for idx, f in enumerate(resolved):
        delay = _minimum_delay(f, resolved[:idx], closures, separation_matrix) or 0
        if delay:
            resolved[idx] = shift_flight(f, delay)
            total_delay += delay
            adjustments.append(
                {
                    "flight_id": f["id"],
                    "callsign": f["callsign"],
                    "delta_seconds": delay,
                }
            )
    remaining = detect_conflicts(resolved, closures, separation_matrix)
    return {
        "flights": resolved,
        "adjustments": adjustments,
        "total_delay_seconds": total_delay,
        "remaining_conflicts": remaining,
    }
