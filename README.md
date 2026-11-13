# 实验室预约客服

一个用自然语言办理实验室预约的对话式客服系统。用户不用点表单，直接说「帮我约 LAB-301，明天下午两点到四点，学号 20230555」，机器人就会把日期和时段归一化、校验实验室状态与容量、写入数据库，并回一张预约条卡片。

整套业务逻辑由 YAML 流程描述，大模型只负责把一句话翻译成「开始哪个流程、填哪些槽位」，因此流程稳定可控，不会出现模型自由发挥、把预约写成散文的情况。

![聊天界面](docs/preview.png)

## 功能

| 能力 | 说明 |
|---|---|
| 实验室信息 | 报编号或点卡片即可查名称、容纳人数、位置、开放时间、当前预约状态 |
| 预约实验室 | 依次收集 学号 → 实验室编号 → 日期 → 时间段，缺哪个问哪个 |
| 查询预约 | 报预约号（如 `B20261114001`）返回实验室、时间、状态 |
| 取消预约 | 校验归属与状态，取消后状态置为「已取消」 |
| 业务对象卡片 | 用户发来实验室/预约条卡片时自动识别：没有进行中的业务就直接介绍，正在办理业务就自动填槽 |
| 知识咨询 | 预约规则、实验室使用规范、开放时间等 FAQ |
| 兜底 | 文本里出现 `LAB-xxx` 或 `B2026xxxxxxxx` 时强制路由到对应流程，不依赖模型判断 |

## 技术栈

- **Python 3.11+** / FastAPI / Uvicorn
- **LangChain** + OpenAI 兼容接口（默认对接 DeepSeek，换 `LLM_BASE_URL` 即可切换其他厂商）
- **MySQL 8** + SQLAlchemy 2.0（异步）+ aiomysql
- **Jinja2** 渲染提示词，**YAML** 描述业务流程

## 架构

```
用户消息
   │
   ├─ 对象消息（实验室/预约条）──→ 填槽 or 介绍
   │
   └─ 文本消息 ──→ TurnPlanner（LLM 输出 JSON 计划）
                        │
                   TurnPlanValidator（校验流程名、意图名是否合法）
                        │
                  命令：start_flow / set_slots
                        │
                  TaskHandler → FlowExecutor（读 YAML 步骤）
                        │
                  Action（查库 / 校验 / 写库）
                        │
                  ResponseRenderer（套模板 + 生成卡片）
                        │
                     BotMessage
```

对话状态（当前任务、已填槽位、历史轮次）按 `sender_id` 持久化在 `dialogue_states` 表，因此多轮补充信息、跨请求续接都能接得上。

## 项目结构

```
.
├── main.py                       # 启动入口
├── flow_config/user_flows.yml    # 业务流程与槽位定义（改这里就能加流程）
├── yoyo/
│   ├── app/                      # FastAPI 应用：路由、依赖、首页 index.html
│   ├── engine/                   # 对话引擎：分流、对象填槽、确定性兜底
│   ├── plan/                     # 轮次规划器与计划校验
│   ├── task/
│   │   ├── flow/                 # 流程加载、执行、条件、跳转
│   │   ├── action/custom/        # 三个业务动作：查实验室、查预约、建/取消预约
│   │   ├── command/              # start_flow / set_slots 命令
│   │   ├── lifecycle/            # 任务生命周期应答
│   │   └── response/             # 模板渲染与卡片
│   ├── knowledge/                # 意图定义、数据提供者、知识应答
│   ├── clarify/                  # 澄清与追问
│   ├── chitchat/                 # 闲聊
│   ├── models/                   # SQLAlchemy 模型（labs / bookings / dialogue_states）
│   ├── repository/               # 数据访问层
│   ├── prompts/jinja2/           # 提示词模板
│   ├── clients/                  # LLM、数据库、HTTP 客户端
│   └── conf/                     # 配置
└── test/
```

## 快速开始

### 1. 准备数据库

只用 MySQL，先建库和账号（表由程序启动时自动创建）：

```sql
CREATE DATABASE IF NOT EXISTS customer_service DEFAULT CHARSET utf8mb4;
CREATE USER IF NOT EXISTS 'yoyo'@'%' IDENTIFIED BY 'Yoyo.123';
GRANT ALL PRIVILEGES ON customer_service.* TO 'yoyo'@'%';
FLUSH PRIVILEGES;
```

### 2. 拉取并安装依赖

```bash
git clone https://github.com/Eurekaaaaaa21/service-agent.git
cd service-agent

# 用 uv（推荐，仓库自带 uv.lock）
uv sync

# 或者用普通虚拟环境
python -m venv .venv
.venv\Scripts\activate      # Windows
pip install -e .
```

### 3. 配置环境变量

```bash
cp .env.example .env
```

然后把 `.env` 里的 `LLM_API_KEY` 换成自己的 key。

### 4. 启动

```bash
python main.py
```

打开 http://127.0.0.1:18082/ 就能在浏览器里对话——左侧是实验室列表和我的预约，点一下相当于把那张卡片发给机器人。

## 环境变量

| 变量 | 示例 | 说明 |
|---|---|---|
| `LLM_MODEL` | `deepseek-chat` | 模型名，需与 `LLM_BASE_URL` 对应的服务商匹配 |
| `LLM_BASE_URL` | `https://api.deepseek.com/v1` | OpenAI 兼容端点，注意不要带 `/anthropic` 后缀 |
| `LLM_API_KEY` | `sk-...` | 大模型密钥 |
| `DATABASE_URL` | `mysql+aiomysql://yoyo:Yoyo.123@127.0.0.1:3306/customer_service?charset=utf8mb4` | SQLAlchemy 异步连接串 |
| `APP_HOST` | `127.0.0.1` | 监听地址 |
| `APP_PORT` | `18082` | 端口 |

## 数据模型

### `labs` 实验室

| 字段 | 类型 | 说明 |
|---|---|---|
| `lab_code` | varchar(32) | 实验室编号，唯一，如 `LAB-301` |
| `name` | varchar(128) | 名称 |
| `capacity` | int | 容纳人数 |
| `location` | varchar(128) | 位置 |
| `status` | varchar(32) | 预约状态：可预约 / 已满 / 维护中 |
| `open_hours` | varchar(128) | 开放时间 |
| `description` | varchar(512) | 用途与设备简介 |

### `bookings` 预约条

| 字段 | 类型 | 说明 |
|---|---|---|
| `booking_no` | varchar(32) | 预约号，唯一，如 `B20261114001` |
| `student_no` | varchar(32) | 学号 |
| `lab_code` | varchar(32) | 实验室编号 |
| `booking_date` | date | 预约日期 |
| `time_slot` | varchar(32) | 时间段，如 `14:00-16:00` |
| `status` | varchar(32) | 预约状态：待到馆 / 使用中 / 已完成 / 已取消 |
| `purpose` | varchar(255) | 使用用途 |
| `created_at` | datetime | 创建时间 |

### `dialogue_states` 对话状态

按 `sender_id` 存一份 JSON 状态，包含当前任务、槽位、多轮历史与聚焦对象。

启动时 `ensure_schema_and_seed()` 幂等建表，并在表为空时写入示例数据（重复启动不会重复插入）：

- 6 间实验室：`LAB-201` 电子电路、`LAB-301` 计算机基础、`LAB-302` 网络工程、`LAB-305` 人工智能（已满）、`LAB-401` 嵌入式、`LAB-402` 多媒体创作（维护中）
- 6 条预约：学号 `20230101` / `20230102` / `20230144` / `20220208`，覆盖待到馆、使用中、已完成、已取消四种状态

## 业务流程

定义在 `flow_config/user_flows.yml`，流程名会被写进提示词供模型选择：

| 流程 | 触发 | 收集的槽位 |
|---|---|---|
| `lab_info_query` | 查某间实验室 | `lab_code` |
| `lab_booking` | 预约实验室 | `student_no` → `lab_code` → `booking_date` → `time_slot` |
| `booking_status_query` | 查预约状态 | `booking_no` |
| `booking_cancel` | 取消预约 | `booking_no` |
| `human_handoff` | 要求人工 | — |
| `onboarding` | 打招呼/不知道怎么用 | — |

预约提交时会做这些校验（任一不通过就说明原因并让用户重来，不会静默失败）：

- 日期必须 `YYYY-MM-DD`，时间段必须 `HH:MM-HH:MM`（「明天下午两点到四点」这类说法由模型先归一化）
- 不能预约过去的日期
- 维护中的实验室不可预约，已满的实验室不可预约
- 同一实验室同一天同一时段，已约数量不能超过容纳人数

## 知识意图

| 意图 | 覆盖内容 |
|---|---|
| `lab_info` | 某间实验室的人数、位置、状态、开放时间 |
| `lab_list` | 有哪些实验室、哪些还能约 |
| `booking_info` | 某条预约的实验室、时间、状态 |
| `booking_rule` | 怎么预约、提前多久、单次时长、怎么取消、违约处理 |
| `lab_rule` | 进实验室要带什么、能不能饮食、设备损坏怎么办 |
| `open_hours` | 开放时间 |
| `general_lab_info` | 其他预约相关通用问题 |

## HTTP 接口

| 方法 | 路径 | 说明 |
|---|---|---|
| `GET` | `/` | 聊天页面 |
| `POST` | `/api/chat` | 对话主入口 |
| `GET` | `/api/labs` | 实验室列表，支持 `?status=可预约` |
| `GET` | `/api/labs/{lab_code}` | 单间实验室详情，不存在返回 404 |
| `GET` | `/api/users/{student_no}/bookings` | 某学号的预约条列表 |
| `GET` | `/api/chat/history?sender_id=xxx` | 历史对话（用户消息 + 机器人回复） |
| `GET` | `/health` | 健康检查 |
| `GET` | `/docs` | 自动生成的 OpenAPI 文档 |

`POST /api/chat` 请求体：

```jsonc
{
  "sender_id": "20230555",
  "text": "帮我约 LAB-301，明天下午两点到四点",   // 文本消息
  // 或者发对象卡片（二选一）：
  // "object": {"type": "lab", "id": "LAB-301", "title": "计算机基础实验室", "attributes": {}}
}
```

响应：

```jsonc
{
  "sender_id": "20230555",
  "message_id": "...",
  "messages": [
    {"text": "预约成功，预约号 B20261118007...", "object": {"type": "booking", "id": "B20261118007", "attributes": {"预约状态": "待到馆"}}}
  ]
}
```

`object` 字段可以直接拿去渲染卡片，`type` 为 `lab` 或 `booking`。

## 二次开发

- **加一个业务动作**：在 `yoyo/task/action/custom/` 下继承 `Action` 实现 `run()`，放进目录即自动注册，然后在 YAML 里用 `type: action`、`action: <name>` 引用。
- **加一个流程**：只改 `flow_config/user_flows.yml`，新增流程和槽位即可，提示词会自动带上。
- **加一类知识**：在 `yoyo/knowledge/intents.py` 加意图，在 `providers.py` 加数据来源（数据库 / FAQ / RAG）。
- **改业务字段**：`yoyo/models/lab_booking.py` 改表结构，`repository/lab_booking_repository.py` 同步查询与对象映射。

## 已知限制

- 单轮意图识别依赖大模型，弱模型可能把「查实验室」误判成闲聊；代码里对 `LAB-xxx` / `B2026xxxxxxxx` 做了确定性兜底，但更复杂的表述仍建议用能力较好的模型。
- 容量校验是「同时段已约数量 vs 容纳人数」，粒度为整间实验室，不是座位级分配。
- 接口没有鉴权，`sender_id` 由调用方传入；接入真实校园系统时需要替换为统一身份认证。
- `labs` / `bookings` 没有管理后台，维护开放时间、状态需要直接改库。
