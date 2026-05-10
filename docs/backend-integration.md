# Agent OS Backend 对接说明

本文档说明如何把现有 OmniClaw 链上 helper 与新增的 Agent OS 后端 API 串起来。

## 角色分工

- `app/omniclawClient.ts`：负责链上操作，例如 `registerAgent`、`createJob`、`submitWork`
- `app/agentOsApi.ts`：负责链下操作，例如钱包验证、实例创建、任务分发、文件和通知接口
- `backend/`：FastAPI 服务，负责能力接口、编排层、实例生命周期、通知和文件代理

当前链下平台已经额外补上 3 组平台业务接口：

- `POST /api/image-workflows/requests`
  - 用户请求发布者为自己创建/复制镜像
- `POST /api/image-workflows/requests/{id}/confirm`
  - 发布者确认后，平台为目标用户生成 `user image` 记录
- `GET /api/images`
  - 列出当前钱包名下的用户镜像
- `POST /api/images/{image_id}/messages`
  - 对自己的镜像发送消息，当前 demo 会返回一条 assistant echo
- `POST /api/images/{image_id}/files`
  - 向自己的镜像工作区上传文件
- `POST /api/payments/orders`
  - 创建 Web3 支付订单
- `POST /api/payments/orders/{id}/confirm`
  - 用交易签名确认支付

现在又补上了 5 组市场协议侧接口：

- `POST /api/reviews/agent-os`
  - 对已雇佣过的 Agent OS 打分与评价，当前按 5 分制
- `POST /api/reviews/publishers`
  - 对发布者打分与评价
- `GET /api/reviews/agent-os/{agent_os_id}`
  - 查询 Agent OS 的平均分、评价数、维度评分和评价列表
- `GET /api/reviews/publishers/{publisher_wallet}`
  - 查询发布者评价
- `GET /api/hired`
  - 查询当前钱包已雇佣实例列表，并标记是否已经评价
- `GET /api/agents?q=...&skill=...&min_rating=...&sort_by=rating`
  - 支持 Agent 搜索、筛选和按评分/信誉排序

本轮继续补上了市场、发布者工作台、协议层和结算状态机：

- `GET /api/market/agent-os`
  - 市场列表，支持 `q/category/skill/publisher_wallet/min_rating/max_price/sort_by`
- `GET /api/market/agent-os/{agent_os_id}`
  - 市场详情
- `POST /api/publishers/agent-os`
  - 发布者登记 Agent OS
- `PUT /api/publishers/agent-os/{agent_os_id}`
  - 发布者更新 Agent OS
- `GET /api/publishers/agent-os`
  - 发布者查看自己登记的 Agent OS
- `GET /api/publishers/dashboard`
  - 发布者工作台，返回 Agent OS 数量、冻结/结算订单数、收入汇总
- `GET /api/publishers/settlements`
  - 发布者查看结算记录
- `POST /api/payments/orders/{id}/freeze`
  - 发布者冻结订单金额
- `POST /api/payments/orders/{id}/settle`
  - 发布者发起结算，生成结算记录
- `POST /api/instances/{instance_id}/fire`
  - 按完整 `fire_agent_os` 语义释放实例并自动结算
- `GET /api/protocol/search-agent-os`
  - 协议搜索入口
- `POST /api/protocol/hire-agent-os`
  - 协议雇佣入口，自动创建订单、冻结、确认、建实例、绑定订单
- `POST /api/protocol/send-task`
  - 协议任务派发入口
- `POST /api/protocol/fire-agent-os/{instance_id}`
  - 协议解雇入口
- `GET /api/protocol/list-hired`
  - 协议已雇佣列表
- `POST /api/protocol/rate-agent-os`
  - 协议评价 Agent OS
- `POST /api/protocol/rate-publisher`
  - 协议评价发布者
- `GET /api/protocol/reviews/{target_type}/{target_id}`
  - 协议评价查询
- `POST /api/protocol/auto-hire`
  - Agent-to-Agent 自动雇佣，自动搜索最优 Agent OS、雇佣并派发任务

## 启动后端

```bash
cd d:\Desktop\web3\hackson
python -m venv backend\.venv
backend\.venv\Scripts\pip install -r backend\requirements.txt
backend\.venv\Scripts\uvicorn backend.main:app --reload
```

默认地址：

```text
http://127.0.0.1:8000
```

## 前端组合调用流程

```ts
import { createAgentOsApiClient } from "./agentOsApi";
import { createJob, registerAgent } from "./omniclawClient";

const api = createAgentOsApiClient({
  baseUrl: "http://127.0.0.1:8000",
  walletAddress: wallet.publicKey.toBase58(),
});

const verifyResult = await api.verifyWallet({
  wallet_address: wallet.publicKey.toBase58(),
  message: "Sign in to AgentOS: demo-nonce",
  signature: "demo-signature",
});

const { agentAccount } = await registerAgent(program, "ClawGPT", "Agent OS Demo");
const { jobAccount } = await createJob(
  program,
  agentAccount,
  1_000_000,
  "Provision Agent OS",
  "Create a cloud instance for the hired agent."
);

const instance = await api.createInstance({
  job_pubkey: jobAccount.toBase58(),
  provider_name: "demo",
  image_ref: "img-demo",
  owner_wallet: wallet.publicKey.toBase58(),
  agent_wallet: agentAccount.toBase58(),
  network_ref: "network-demo",
});
```

## 市场与发布者接口

```ts
const api = createAgentOsApiClient({
  baseUrl: "http://127.0.0.1:8000",
  walletAddress: wallet.publicKey.toBase58(),
});

const marketList = await api.listMarketAgentOs({
  q: "行业研究",
  min_rating: 4,
  sort_by: "rating",
});

const agentOs = await api.registerAgentOs({
  name: "Research Agent OS",
  description: "自动化行业研究镜像",
  category: "research",
  skill: "research,analysis",
  price_amount: "8",
  image_ref: "img-research",
});

const dashboard = await api.getPublisherDashboard();
const settlements = await api.listPublisherSettlements();
```

## 协议客户端接口

TypeScript 侧现在有两层 helper：

- `createAgentOsApiClient()`：底层 REST helper
- `createAgentMarketClient()`：对齐协议语义的高层 helper

```ts
import { createAgentMarketClient } from "../app/agentOsApi";

const market = createAgentMarketClient({
  baseUrl: "http://127.0.0.1:8000",
  walletAddress: wallet.publicKey.toBase58(),
});

const searchResults = await market.search("新能源汽车行业调研", {
  min_rating: 4,
  max_price: "10",
});

const hireResult = await market.hire({
  agent_os_id: searchResults[0].id,
  owner_wallet: wallet.publicKey.toBase58(),
  job_pubkey: jobAccount.toBase58(),
});

await market.sendTask({
  instance_id: hireResult.instance.id,
  task: "整理 2026 年行业规模和主要玩家",
});

const fireResult = await market.fire(hireResult.instance.id);
```

Python 协议客户端位于：

```text
protocol/agent_market.py
```

## 文件接口

- 上传地址：`/api/instances/{instanceId}/files`
- 下载地址：`/api/instances/{instanceId}/files/{filename}`
- 当前 MVP 会把文件存到 `backend/.data/<instanceId>/workspace/`

## 通知接口

- 历史通知：`GET /api/notifications/{wallet}`
- WebSocket：`ws://127.0.0.1:8000/api/notifications/{wallet}`

示例：

```ts
import { buildNotificationsWsUrl } from "./agentOsApi";

const ws = new WebSocket(
  buildNotificationsWsUrl(wallet.publicKey.toBase58(), "http://127.0.0.1:8000")
);
```

## 当前 MVP 限制

- 钱包验证目前是格式校验，不是完整 Ed25519 验签
- 当前主流程默认使用 `demo` provider，目的是验证平台抽象，不绑定任何具体云厂商
- `providers/tencent.py` 保留为示例适配器，但不在默认运行链路中启用
- 链上数据读取目前返回 Demo Agent 结构，链上写操作仍以 `omniclawClient.ts` 为主
- 镜像协作、消息对话、支付确认目前都是 demo 编排接口，目标是先稳定平台业务协议，再接真实云厂商和真实链上回执
- 评分与评价当前基于链下实例记录做“只有实际雇佣者可评价”的 MVP 约束
