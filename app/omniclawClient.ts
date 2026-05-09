import { AnchorProvider, BN, Program, web3 } from "@coral-xyz/anchor";
import type { Omniclaw } from "../target/types/omniclaw";

export const STATUS_OPEN = 0;
export const STATUS_SUBMITTED = 1;
export const STATUS_COMPLETED = 2;
export const STATUS_CANCELLED = 3;
export const STATUS_SLASHED = 4;

export const JOB_STATUS_LABELS: Record<number, string> = {
  [STATUS_OPEN]: "开放中",
  [STATUS_SUBMITTED]: "待验收",
  [STATUS_COMPLETED]: "已完成",
  [STATUS_CANCELLED]: "已取消",
  [STATUS_SLASHED]: "已 Slash",
};

export const JOB_CREATOR_MEMCMP_OFFSET = 8;
export const JOB_AGENT_MEMCMP_OFFSET = 40;

export function lamportsFromSol(sol: number) {
  return new BN(Math.round(sol * web3.LAMPORTS_PER_SOL));
}

export function deriveAgentAccount(
  owner: web3.PublicKey,
  programId: web3.PublicKey
) {
  return web3.PublicKey.findProgramAddressSync(
    [Buffer.from("agent"), owner.toBuffer()],
    programId
  )[0];
}

export function deriveVault(job: web3.PublicKey, programId: web3.PublicKey) {
  return web3.PublicKey.findProgramAddressSync(
    [Buffer.from("vault"), job.toBuffer()],
    programId
  )[0];
}

export function walletPublicKey(program: Program<Omniclaw>) {
  const provider = program.provider as AnchorProvider;
  const publicKey = provider.wallet?.publicKey;

  if (!publicKey) {
    throw new Error("Anchor 钱包未连接");
  }

  return publicKey;
}

export async function registerAgent(
  program: Program<Omniclaw>,
  name: string,
  skill: string,
  owner = walletPublicKey(program)
) {
  // 每个 owner 钱包只对应一个 Agent PDA：["agent", owner]。
  const agentAccount = deriveAgentAccount(owner, program.programId);
  const signature = await program.methods
    .registerAgent(name, skill)
    .accountsStrict({
      agentAccount,
      owner,
      systemProgram: web3.SystemProgram.programId,
    })
    .rpc();

  return { signature, agentAccount };
}

export async function createJob(
  program: Program<Omniclaw>,
  agentAccount: web3.PublicKey,
  bountyLamports: number | BN,
  title: string,
  description: string,
  creator = walletPublicKey(program)
) {
  // Job 本身是普通 keypair 账户；它的 public key 会作为 vault PDA 的 seed。
  const job = web3.Keypair.generate();
  const vault = deriveVault(job.publicKey, program.programId);
  const bounty = BN.isBN(bountyLamports)
    ? bountyLamports
    : new BN(bountyLamports);

  const signature = await program.methods
    .createJob(agentAccount, bounty, title, description)
    .accountsStrict({
      jobAccount: job.publicKey,
      creator,
      agentAccount,
      vault,
      systemProgram: web3.SystemProgram.programId,
    })
    .signers([job])
    .rpc();

  return {
    signature,
    jobAccount: job.publicKey,
    jobKeypair: job,
    vault,
  };
}

export async function submitWork(
  program: Program<Omniclaw>,
  jobAccount: web3.PublicKey,
  agentAccount: web3.PublicKey,
  resultUri: string,
  agentOwner = walletPublicKey(program)
) {
  const signature = await program.methods
    .submitWork(resultUri)
    .accountsStrict({
      jobAccount,
      agentAccount,
      agentOwner,
    })
    .rpc();

  return { signature };
}

export async function completeJob(
  program: Program<Omniclaw>,
  jobAccount: web3.PublicKey,
  agentAccount: web3.PublicKey,
  agentOwner: web3.PublicKey,
  creator = walletPublicKey(program)
) {
  const vault = deriveVault(jobAccount, program.programId);
  const signature = await program.methods
    .completeJob()
    .accountsStrict({
      jobAccount,
      creator,
      agentAccount,
      agentOwner,
      vault,
      systemProgram: web3.SystemProgram.programId,
    })
    .rpc();

  return { signature, vault };
}

export async function cancelJob(
  program: Program<Omniclaw>,
  jobAccount: web3.PublicKey,
  creator = walletPublicKey(program)
) {
  const vault = deriveVault(jobAccount, program.programId);
  const signature = await program.methods
    .cancelJob()
    .accountsStrict({
      jobAccount,
      creator,
      vault,
      systemProgram: web3.SystemProgram.programId,
    })
    .rpc();

  return { signature, vault };
}

export async function slashAgent(
  program: Program<Omniclaw>,
  jobAccount: web3.PublicKey,
  agentAccount: web3.PublicKey,
  creator = walletPublicKey(program)
) {
  const vault = deriveVault(jobAccount, program.programId);
  const signature = await program.methods
    .slashAgent()
    .accountsStrict({
      jobAccount,
      agentAccount,
      creator,
      vault,
      systemProgram: web3.SystemProgram.programId,
    })
    .rpc();

  return { signature, vault };
}

export async function fetchAgent(
  program: Program<Omniclaw>,
  agentAccount: web3.PublicKey
) {
  return program.account.agentAccount.fetch(agentAccount);
}

export async function fetchJob(
  program: Program<Omniclaw>,
  jobAccount: web3.PublicKey
) {
  return program.account.jobAccount.fetch(jobAccount);
}

export async function fetchJobsByCreator(
  program: Program<Omniclaw>,
  creator: web3.PublicKey
) {
  return program.account.jobAccount.all([
    {
      memcmp: {
        offset: JOB_CREATOR_MEMCMP_OFFSET,
        bytes: creator.toBase58(),
      },
    },
  ]);
}

export async function fetchJobsByAgent(
  program: Program<Omniclaw>,
  agentAccount: web3.PublicKey
) {
  return program.account.jobAccount.all([
    {
      memcmp: {
        offset: JOB_AGENT_MEMCMP_OFFSET,
        bytes: agentAccount.toBase58(),
      },
    },
  ]);
}
