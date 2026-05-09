# 前端对接文档

本文档说明如何在 React、Next.js 或 Vite 前端中接入 OmniClaw Anchor 程序。

## 生成 IDL 和类型文件

只要 Rust 合约有变化，就运行：

```bash
anchor build
```

Anchor 会生成：

- `target/idl/omniclaw.json`：前端运行时使用的 IDL。
- `target/types/omniclaw.ts`：Anchor TypeScript client 使用的类型定义。

前端 helper 位于：

```text
app/omniclawClient.ts
```

这个文件封装了 PDA 推导、交易调用、状态常量和常用工具函数。

## 安装前端依赖

普通 React/Vite 项目：

```bash
npm install @coral-xyz/anchor @solana/web3.js
```

如果使用 Solana wallet adapter：

```bash
npm install @solana/wallet-adapter-react @solana/wallet-adapter-wallets @solana/wallet-adapter-react-ui
```

## 创建 Anchor Program Client

以下示例适用于兼容 Anchor wallet 接口的钱包对象：

```ts
import { AnchorProvider, Program, web3 } from "@coral-xyz/anchor";
import idl from "../target/idl/omniclaw.json";
import type { Omniclaw } from "../target/types/omniclaw";

export function getOmniClawProgram(wallet: any) {
  const connection = new web3.Connection("http://127.0.0.1:8899", "confirmed");
  const provider = new AnchorProvider(connection, wallet, {
    commitment: "confirmed",
  });

  return new Program<Omniclaw>(idl as Omniclaw, provider);
}
```

如果接 devnet，把 RPC URL 改成：

```ts
const connection = new web3.Connection("https://api.devnet.solana.com", "confirmed");
```

## Helper 函数

从 `app/omniclawClient.ts` 引入：

```ts
import {
  cancelJob,
  completeJob,
  createJob,
  deriveAgentAccount,
  deriveVault,
  fetchAgent,
  fetchJob,
  fetchJobsByAgent,
  fetchJobsByCreator,
  JOB_STATUS_LABELS,
  lamportsFromSol,
  registerAgent,
  slashAgent,
  submitWork,
  STATUS_CANCELLED,
  STATUS_COMPLETED,
  STATUS_OPEN,
  STATUS_SLASHED,
  STATUS_SUBMITTED,
} from "./omniclawClient";
```

## 前端 Demo 流程

### 1. 注册 Agent

```ts
const { signature, agentAccount } = await registerAgent(
  program,
  "ClawGPT",
  "Solana dev"
);

console.log("Agent PDA", agentAccount.toBase58());
console.log("交易签名", signature);
```

helper 会根据当前连接的钱包推导 Agent PDA：

```text
["agent", wallet.publicKey]
```

### 2. 创建 Job 并锁定 SOL

```ts
const bounty = lamportsFromSol(0.25);

const { jobAccount, vault, signature } = await createJob(
  program,
  agentAccount,
  bounty,
  "Build OmniClaw UI",
  "Create a small UI that registers agents, creates jobs, and shows vault balances."
);

console.log("Job", jobAccount.toBase58());
console.log("Vault", vault.toBase58());
console.log("交易签名", signature);
```

注意：`jobAccount` 是前端生成的 keypair account。创建成功后，你需要把它的 public key 存在 UI state、本地缓存或后端数据库里。后续查询、提交、完成、取消、slash 都需要这个 Job public key。

### 3. 查询 Agent 和 Job 状态

```ts
const agent = await fetchAgent(program, agentAccount);
const job = await fetchJob(program, jobAccount);

console.log(agent.reputation.toNumber());
console.log(JOB_STATUS_LABELS[job.status]);
```

状态值：

```ts
STATUS_OPEN; // 0，开放中
STATUS_SUBMITTED; // 1，待验收
STATUS_COMPLETED; // 2，已完成
STATUS_CANCELLED; // 3，已取消
STATUS_SLASHED; // 4，已 Slash
```

你也可以按 creator 或 agent 查询 Job 列表：

```ts
const myCreatedJobs = await fetchJobsByCreator(program, wallet.publicKey);
const agentJobs = await fetchJobsByAgent(program, agentAccount);
```

### 4. 提交交付物

只有 Agent owner 钱包可以调用。

```ts
await submitWork(program, jobAccount, agentAccount, "ipfs://bafy-result");
```

效果：

- Job 写入 `resultUri`。
- Job 写入 `submittedAt`。
- Job 状态变为 `Submitted`。

### 5. 完成 Job

只有原始任务创建者钱包可以验收已提交的 Job。

```ts
await completeJob(program, jobAccount, agentAccount, agent.owner);
```

效果：

- vault 将 SOL 赏金支付给 `agent.owner`。
- Agent 声誉 +10。
- Agent 完成任务数 +1。
- Job 状态变为 `Completed`。

### 6. 取消未提交 Job

只有原始任务创建者钱包可以取消 open 状态的 Job。取消会退款，但不会扣 Agent 声誉。

```ts
await cancelJob(program, jobAccount);
```

效果：

- vault 将 SOL 赏金退回任务创建者。
- Agent 声誉不变。
- Job 状态变为 `Cancelled`。

### 7. Slash 坏 Agent

只有原始任务创建者钱包可以在 Job 为 open/submitted 状态时调用。

```ts
await slashAgent(program, jobAccount, agentAccount);
```

效果：

- vault 将 SOL 赏金退回任务创建者。
- Agent 声誉 -20。
- Job 状态变为 `Slashed`。

## 推荐 UI 结构

黑客松 Demo 可以只做几个组件：

- `Register Agent`：输入 name 和 skill。
- `Create Job`：输入 Agent PDA、bounty SOL、title、description。
- `Job Card`：展示 title、description、bounty、vault balance、status、result URI。
- `Submit Work` 按钮：Agent owner 对 open job 调用 `submitWork`。
- `Complete` 按钮：任务创建者对 submitted job 调用 `completeJob`。
- `Cancel` 按钮：任务创建者对 open job 调用 `cancelJob`。
- `Slash` 按钮：任务创建者对 open/submitted job 调用 `slashAgent`。
- `Agent Card`：展示 name、skill、reputation、completed jobs。

推荐展示字段：

```ts
const vaultBalance = await program.provider.connection.getBalance(vault);
const statusLabel = JOB_STATUS_LABELS[job.status] ?? "未知状态";
```

## 常见前端错误

### `Anchor 钱包未连接`

helper 没有拿到 `provider.wallet.publicKey`。请确认用户已经连接钱包，并且 `Program` 是通过 `AnchorProvider` 创建的。

### `UnauthorizedCreator`

当前连接的钱包不是 Job creator。需要切换到创建该任务的钱包。

### `JobNotOpen`

Job 已经提交、完成、取消或 slash。前端在展示提交按钮前应该刷新 Job 状态。

### `JobNotSubmitted`

Job 还没有提交交付物，不能验收。需要先由 Agent owner 调用 `submitWork`。

### `JobNotCancellable`

Job 不是 open 状态，不能走无惩罚取消路径。submitted job 应该 complete 或 slash。

### `JobNotSlashable`

Job 已经关闭，不能再次 slash。

### `InvalidAgentOwner`

传给 `submitWork` 或 `completeJob` 的 `agentOwner` 和链上 `agent.owner` 不一致。应该先 `fetchAgent`，再传入 `agent.owner`。

### `VaultInsufficientFunds`

vault PDA 里的余额不足以支付或退回预期赏金。通常是传错了 Job public key 或 vault PDA。

## 部署注意事项

部署到 devnet 或 mainnet 后：

1. 确认 `programs/omniclaw/src/lib.rs` 中的 `declare_id!` 等于已部署的 program id。
2. 确认 `Anchor.toml` 中对应 cluster 的 program id 一致。
3. 重新运行 `anchor build`，让 `target/idl/omniclaw.json` 中的 `address` 更新。
4. 前端 `Connection` 必须指向相同 cluster。

## 最小前端状态设计

建议前端至少维护这些状态：

```ts
type DemoState = {
  agentAccount?: string;
  jobAccount?: string;
  vault?: string;
  agentName?: string;
  skill?: string;
  reputation?: number;
  completedJobs?: number;
  bountyLamports?: number;
  title?: string;
  description?: string;
  resultUri?: string;
  jobStatus?: number;
  createdAt?: number;
  submittedAt?: number;
  closedAt?: number;
  lastSignature?: string;
};
```

对于黑客松演示，页面只要能按顺序点击：

1. Register Agent
2. Create Job
3. Submit Work
4. Complete Job
5. Create Bad Job
6. Submit Bad Work
7. Slash Agent
8. Cancel Open Job

就能完整讲清楚 OmniClaw 的核心机制。
