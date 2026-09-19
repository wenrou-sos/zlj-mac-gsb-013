# 机场跑道占用冲突预演平台

配置航班进离场时刻、滑行路线、跑道关闭区间和安全间隔，自动识别调度冲突并给出调整方案。

- **前端**：React 18 + TypeScript + Vite（时间轴可视化 + 配置表单）
- **后端**：FastAPI + SQLAlchemy 2（冲突检测/自动排程引擎）
- **数据库**：PostgreSQL 16（本地开发可零配置使用 SQLite）

## 一键启动（Docker）

```bash
./start.sh
```

启动后：

| 地址 | 说明 |
| --- | --- |
| http://localhost:8000 | 平台界面（后端同时托管前端静态产物） |
| http://localhost:8000/docs | Swagger API 文档 |
| localhost:5432 | PostgreSQL（runway/runway/runway_platform） |

首次启动自动写入演示场景：3 条跑道、6 个航班、1 个关闭区间，覆盖全部四类冲突。

停止：`docker compose down`（清除数据加 `-v`）。

## 本地开发模式

无 Docker 时 `./start.sh` 会自动回退到开发模式，或手动执行：

```bash
./scripts/dev.sh        # 后端 :8000 (SQLite) + Vite 前端 :5173
```

前端 5173 已配置 `/api`、`/health` 代理到 8000。

## 运行测试

```bash
./scripts/test.sh
```

- 后端 21 个 pytest（引擎单元测试 + API 集成测试，内存 SQLite）
- 前端 10 个 vitest（时间工具、占用区间计算、App 集成渲染）
- 前端 TypeScript 类型检查与生产构建

## 冲突模型

每架航班按滑行路线生成跑道占用窗口：

- 离场：`[起飞时刻 - 进入提前量, 起飞时刻 + 脱离延后量]`
- 进场：`[落地时刻 - 进入提前量, 落地时刻 + 脱离延后量]`
- 路线中可配置穿越其他跑道的节点，穿越时刻按节点间 `taxi_seconds` 推算

检测四类冲突：

| 类型 | 含义 |
| --- | --- |
| `SEPARATION` | 同跑道前/后机基准时刻间隔小于安全间隔矩阵（按 离场/进场 2×2 配置，秒） |
| `OCCUPANCY` | 同跑道两架航班占用窗口重叠 |
| `CROSSING` | 航班滑行穿越跑道时与该跑道占用窗口重叠 |
| `CLOSURE` | 占用/穿越窗口落入跑道关闭区间 |

## 调整方案

- **顺延建议**：对每个涉冲突航班以 30 秒为步长搜索最小顺延量（上限 2 小时），顺延至无冲突
- **改派跑道**：枚举其他可用跑道，校验改派后残余冲突数
- **一键自动排程**：按基准时刻贪心逐架顺延，返回调整明细、累计延误和剩余冲突；前端将结果写回并重新预演

## 主要 API

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET/POST/PUT/DELETE | `/api/runways` | 跑道配置 |
| GET/POST/PUT/DELETE | `/api/flights` | 航班与滑行路线 |
| GET/POST/PUT/DELETE | `/api/closures` | 跑道关闭区间 |
| GET/PUT | `/api/separation` | 安全间隔矩阵 |
| POST | `/api/analyze` | 冲突识别 + 调整方案 |
| POST | `/api/auto-resolve` | 贪心自动排程 |
| GET | `/health` | 健康检查 |

### 航班对象示例

```json
{
  "id": "HU7801",
  "callsign": "CHH7801",
  "operation": "departure",
  "runway_id": "09R",
  "takeoff_time": "2026-09-19T08:05:00Z",
  "enter_offset": 60,
  "vacate_offset": 40,
  "route": [
    {"name": "A5", "type": "taxiway", "taxi_seconds": 50},
    {"name": "穿越18", "type": "runway", "runway_id": "18",
     "crossing_duration": 30, "taxi_seconds": 40},
    {"name": "RWY09R", "type": "runway", "runway_id": "09R", "primary": true}
  ]
}
```

## 目录结构

```
runway-platform/
├── backend/
│   ├── app/
│   │   ├── engine.py        # 冲突识别与调整方案引擎（纯函数，可独立测试）
│   │   ├── models.py        # SQLAlchemy 模型
│   │   ├── schemas.py       # Pydantic 校验
│   │   ├── routers/         # runways / flights / closures / simulation
│   │   ├── seed.py          # 演示数据
│   │   └── main.py
│   ├── tests/               # pytest（引擎 11 + API 10）
│   └── Dockerfile           # 多阶段：构建前端并打入后端镜像
├── frontend/
│   ├── src/
│   │   ├── lib/             # api client、类型、时间/占用区间计算
│   │   ├── components/      # Timeline / FlightForm / ConflictPanel 等
│   │   └── test/            # vitest
├── docker-compose.yml       # postgres + api
├── start.sh                 # 一键启动（Docker，无 Docker 时回退开发模式）
└── scripts/
    ├── dev.sh               # 本地开发
    └── test.sh              # 全部测试 + 构建
```
