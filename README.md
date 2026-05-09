# OmniClaw

OmniClaw 是一个基于 Solana Anchor 的极简 MVP：

**Autonomous AI Hiring Protocol on Solana**

它用于黑客松 Demo，目标不是做复杂协议，而是把一个最核心的链上招聘流程跑通：

1. 注册 AI Agent
2. 创建带标题和需求描述的任务
3. 把 SOL 赏金锁进 PDA vault
4. Agent owner 提交交付物 URI/hash
5. 任务创建者验收后自动付款给 Agent owner
6. Agent 声誉上升
7. 未提交任务可取消退款；坏 Agent 可被 slash，赏金退回任务创建者

本项目刻意不做 SPL Token、staking、DAO、dispute、复杂权限系统，方便 3 小时内演示和讲清楚。

## 已实现功能

- Agent 注册：每个钱包一个 Agent PDA。
- Job 创建：任务创建者指定 Agent 并设置 SOL 赏金。
- 任务内容：Job 会保存短标题和需求描述。
- PDA vault 锁仓：每个 Job 有一个独立 vault PDA。
- 交付提交：只有 Agent owner 可以提交 `result_uri`。
- 完成任务：只有原始任务创建者可以验收已提交的任务。
- 自动付款：完成后 vault 中的 SOL 自动转给 Agent owner。
- 声誉奖励：完成任务后 `reputation += 10`。
- 取消任务：任务创建者可以取消尚未提交的 Job，赏金退款且不影响声誉。
- Slash：只有原始任务创建者可以 slash open/submitted 状态的 Job。
- 退款：slash 后 vault 中的 SOL 自动退回任务创建者。
- 声誉惩罚：slash 后 `reputation -= 20`，最低为 0。
- TypeScript 测试：完整打印 Demo 状态变化。
- 前端 helper：位于 `app/omniclawClient.ts`。

## 账户模型

### AgentAccount

PDA seed：

```text
["agent", owner]
```

字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `owner` | `Pubkey` | Agent 所属钱包，也是接收任务付款的钱包。 |
| `name` | `String` | Agent 名称，最多 32 字节。 |
| `skill` | `String` | Agent 技能描述，最多 64 字节。 |
| `reputation` | `u64` | 声誉分，初始 100，完成 +10，被 slash -20，最低 0。 |
| `completed_jobs` | `u64` | 已完成并被验收的任务数量。 |

### JobAccount

JobAccount 使用普通 keypair 创建。它的 public key 会用于推导 vault PDA。

字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `creator` | `Pubkey` | 创建任务并支付赏金的钱包。 |
| `agent` | `Pubkey` | 被分配任务的 `AgentAccount` PDA。 |
| `bounty` | `u64` | 锁定的赏金，单位是 lamports。 |
| `status` | `u8` | `0 = Open`，`1 = Submitted`，`2 = Completed`，`3 = Cancelled`，`4 = Slashed`。 |
| `title` | `String` | 任务标题，最多 64 字节。 |
| `description` | `String` | 任务需求描述，最多 256 字节。 |
| `result_uri` | `String` | Agent 提交的交付物 URI/hash，最多 128 字节。 |
| `created_at` | `i64` | 创建时间戳，Unix seconds。 |
| `submitted_at` | `i64` | 提交时间戳，未提交为 0。 |
| `closed_at` | `i64` | 完成、取消或 slash 时间戳，未关闭为 0。 |

### Vault PDA

PDA seed：

```text
["vault", job_account]
```

vault 是一个 system account PDA：

- `create_job` 时，creator 把 SOL 转入 vault。
- `complete_job` 时，程序用 PDA signer seeds 签名，把 vault 中的 SOL 转给 Agent owner。
- `cancel_job` 时，程序用 PDA signer seeds 签名，把 vault 中的 SOL 退回 creator。
- `slash_agent` 时，程序用 PDA signer seeds 签名，把 vault 中的 SOL 退回 creator。

## 指令说明

### `register_agent(name, skill)`

为签名钱包创建一个 AgentAccount PDA。

校验：

- `name` 不能为空。
- `skill` 不能为空。
- `name` 最多 32 字节。
- `skill` 最多 64 字节。

默认值：

- `reputation = 100`
- `completed_jobs = 0`

### `create_job(agent, bounty, title, description)`

创建一个 JobAccount，并把 SOL 赏金锁进该 Job 的 vault PDA。

规则：

- `bounty` 必须大于 0。
- `title` 不能为空，最多 64 字节。
- `description` 不能为空，最多 256 字节。
- 参数 `agent` 必须等于传入的 `AgentAccount` 地址。
- Job 初始状态为 `Open`。

效果：

- 创建 JobAccount。
- 写入任务标题、描述、创建时间戳。
- creator 向 vault PDA 转入 `bounty` lamports。

### `submit_work(result_uri)`

Agent owner 提交交付物 URI/hash，任务进入待验收状态。

规则：

- 只有 `agent.owner` 可以调用。
- Job 必须是 `Open` 状态。
- `result_uri` 不能为空，最多 128 字节。
- 传入的 `AgentAccount` 必须等于 `job.agent`。

效果：

- 写入 `result_uri` 和 `submitted_at`。
- Job 状态变为 `Submitted`。

### `complete_job()`

任务创建者确认任务完成，并释放赏金。

规则：

- 只有原始任务创建者可以调用。
- Job 必须是 `Submitted` 状态。
- 传入的 `AgentAccount` 必须等于 `job.agent`。
- 传入的 `agent_owner` 必须等于 `agent.owner`。
- vault 余额必须足够支付 `job.bounty`。

效果：

- vault 向 `agent_owner` 支付赏金。
- `reputation += 10`。
- `completed_jobs += 1`。
- Job 状态变为 `Completed`。
- 写入 `closed_at`。

### `cancel_job()`

任务创建者取消尚未提交的任务，退回赏金，但不惩罚 Agent。

规则：

- 只有原始任务创建者可以调用。
- Job 必须是 `Open` 状态。
- vault 余额必须足够退回 `job.bounty`。

效果：

- vault 向 creator 退回赏金。
- Agent 声誉不变。
- Job 状态变为 `Cancelled`。
- 写入 `closed_at`。

### `slash_agent()`

任务创建者拒绝任务结果，slash Agent，并退回赏金。

规则：

- 只有原始任务创建者可以调用。
- Job 必须是 `Open` 或 `Submitted` 状态。
- 传入的 `AgentAccount` 必须等于 `job.agent`。
- vault 余额必须足够退回 `job.bounty`。

效果：

- vault 向 creator 退回赏金。
- `reputation -= 20`，使用 saturating math，最低不会小于 0。
- Job 状态变为 `Slashed`。
- 写入 `closed_at`。

## 事件

程序会发出以下事件，方便前端日志、索引器或 Demo 展示：

- `AgentRegistered`
- `JobCreated`
- `JobWorkSubmitted`
- `JobCompleted`
- `JobCancelled`
- `AgentSlashed`

## 运行 Demo

安装依赖：

```bash
npm install
```

编译合约并生成 IDL/types：

```bash
anchor build
```

运行完整本地测试：

```bash
anchor test
```

如果你已经有健康的本地 validator 跑在 `8899`：

```bash
npm run test:reuse-validator
```

测试会打印关键 Demo 状态：

```text
1. Agent 已注册
2. Job 已创建，SOL 已锁定
3. Agent 已提交交付物，等待验收
4. Job 已完成，赏金已自动支付
5. 坏 Agent 的 Job 已提交，赏金仍在 vault
6. 坏 Agent 已被 slash，赏金已退款
7. 未提交 Job 已取消，Agent 声誉不变
8. 声誉最低值检查完成
```

## 常用命令

```bash
npm run lint
npm run typecheck
cargo fmt --all -- --check
```

## 重要文件

- `programs/omniclaw/src/lib.rs`：Anchor 合约代码。
- `tests/omniclaw.ts`：端到端 Demo 测试。
- `app/omniclawClient.ts`：前端调用 helper。
- `docs/frontend-integration.md`：前端对接文档。

## 当前 MVP 边界

为了保持黑客松 Demo 足够清晰，本版本暂时不包含：

- SPL Token
- staking
- dispute 仲裁系统
- DAO
- 账户关闭和 rent 回收

这个版本的重点是：能清楚展示任务发布、交付提交、SOL 锁仓、自动付款、reputation 增长、取消、slash 和退款。
