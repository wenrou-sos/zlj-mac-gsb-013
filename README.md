# 机场跑道占用冲突预演平台

面向塔台/机坪调度的跑道占用预演系统：配置航班进离场时刻、滑行路线、跑道
关闭区间与安全间隔（含尾流间隔矩阵），系统自动推演跑道与滑行道占用时间窗，
**识别三类调度冲突**并给出可一键执行的调整方案。

## 功能

- **航班计划管理**：进/离港时刻、跑道、尾流等级（L/M/H）、机位、滑行路线
  （有序节点列表）及路线耗时。
- **跑道关闭区间**：按跑道配置维护时段，落入窗口的运行自动标红。
- **安全间隔配置**：离/进港跑道占用时长、基础跑道间隔、尾流追加间隔矩阵、
  自动调整可接受最大延误。
- **冲突自动识别**：
  - `SEPARATION` 同跑道前后机间隔不足（尾流矩阵加权），占用直接重叠判为严重；
  - `CLOSURE` 跑道占用窗口与关闭区间重叠；
  - `TAXIWAY` 两航班在同一滑行道节点的占用时间重叠（地面冲突风险）。
- **调整方案**：每个冲突给出「推迟 N 秒」或「改用跑道 X」建议，支持
  单条执行，或 **一键自动调整**（按时刻顺序贪心排程：跑道间隔 → 关闭区间
  → 滑行道冲突，延误超限时自动改派空闲跑道），并输出完整推演日志。
- **可视化时间线**：按跑道分泳道展示占用条、滑行段、关闭斜纹带，冲突航班
  红色高亮。

## 技术栈

| 层 | 技术 |
|---|---|
| 前端 | React 18 + Vite，原生 CSS，Vitest + Testing Library |
| 后端 | FastAPI + SQLAlchemy 2 + Pydantic v2，pytest + httpx |
| 数据库 | PostgreSQL 16（本地开发/测试可回退 SQLite，零配置） |
| 部署 | Dockerfile × 2 + docker-compose（db/backend/frontend + nginx 反代） |

## 快速开始

### 方式一：Docker Compose（推荐）

```bash
./start.sh
```

启动后：

- 前端控制台：<http://localhost:8080>
- API 文档（Swagger）：<http://localhost:8000/docs>

其他命令：

```bash
./start.sh --stop     # 停止
./start.sh --reset    # 清空数据库卷并重建
./start.sh --test     # 运行全部后端 + 前端测试
```

### 方式二：本机直接运行（无需 Docker）

需要 Python 3.11+ 与 Node 18+，后端自动使用 SQLite：

```bash
./start.sh --local
```

- 前端：<http://localhost:5173>（Vite 代理 `/api` 到 8000）
- 后端：<http://localhost:8000>

### 手动运行（不使用脚本）

```bash
# 后端
cd backend
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload            # 默认连 postgres://db:5432
# 无 PostgreSQL 时：
DATABASE_URL="sqlite:///./dev.db" uvicorn app.main:app --reload

# 前端
cd frontend
npm install
npm run dev

# 测试
cd backend && pytest -q
cd frontend && npm test
```

首次启动自动建表并写入内置演示场景（早高峰 7 个航班 + 09L 道面检查关闭
窗口），包含间隔不足、关闭冲突与滑行道抢占三类问题；页面点击
**「一键自动调整」**可观察完整消解过程，**「重置演示场景」**可随时还原。

## API 概览

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/rehearse` | 执行冲突预演，返回冲突、占用窗口、关闭区间 |
| POST | `/api/rehearse/adjust` | 执行单条建议（DELAY / CHANGE_RUNWAY）并重新预演 |
| POST | `/api/rehearse/auto-resolve` | 自动排程，返回延误表、跑道改派表与推演日志 |
| POST | `/api/rehearse/reset-demo` | 重置为演示场景 |
| GET/POST/PUT/DELETE | `/api/flights` | 航班 CRUD |
| GET/POST/PUT/DELETE | `/api/closures` | 关闭区间 CRUD |
| GET/PUT | `/api/config` | 安全间隔参数与尾流矩阵 |

## 占用模型说明

- 离港跑道占用：`[起飞时刻, +dep_occupy]`；
  进港跑道占用：`[落地时刻 - arr_occupy, 落地时刻]`。
- 所需跑道间隔 = `min_sep + wake_sep[前机尾流][后机尾流]`。
- 滑行路线为有序节点列表，路线总耗时（离港 `eta_to_runway` /
  进港 `vacate_to_gate`）按路段均摊，得到每个节点的占用时间窗；
  离港占用发生在计划时刻之前，进港发生在之后。

## 目录结构

```
.
├── start.sh                # 一键启动 / 测试 / 停止
├── docker-compose.yml
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   │   ├── engine/         # 占用建模 + 冲突检测 + 自动排程（纯函数核心）
│   │   ├── routers/        # flights / closures / config / rehearse
│   │   ├── models.py       # SQLAlchemy 模型
│   │   ├── schemas.py      # Pydantic 模型
│   │   ├── service.py      # ORM ↔ 引擎编排
│   │   └── seed.py         # 内置演示场景
│   └── tests/              # 引擎单测 + API 端到端测试
└── frontend/
    ├── Dockerfile          # 多阶段构建 + nginx
    ├── nginx.conf
    └── src/
        ├── components/     # Timeline / ConflictList / FlightPanel ...
        └── test/           # Vitest 组件测试
```
