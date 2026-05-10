import * as anchor from "@coral-xyz/anchor";
import { Program } from "@coral-xyz/anchor";
import { expect } from "chai";
import type { Omniclaw } from "../types/omniclaw";

describe("omniclaw", () => {
  const provider = anchor.AnchorProvider.env();
  anchor.setProvider(provider);

  const program = anchor.workspace.omniclaw as Program<Omniclaw>;
  const accounts = program.account as any;

  const STATUS_OPEN = 0;
  const STATUS_SUBMITTED = 1;
  const STATUS_COMPLETED = 2;
  const STATUS_CANCELLED = 3;
  const STATUS_SLASHED = 4;

  async function airdrop(
    publicKey: anchor.web3.PublicKey,
    lamports = anchor.web3.LAMPORTS_PER_SOL
  ) {
    const signature = await provider.connection.requestAirdrop(
      publicKey,
      lamports
    );
    const latestBlockhash = await provider.connection.getLatestBlockhash();

    await provider.connection.confirmTransaction(
      {
        signature,
        ...latestBlockhash,
      },
      "confirmed"
    );
  }

  function agentPda(owner: anchor.web3.PublicKey) {
    return anchor.web3.PublicKey.findProgramAddressSync(
      [Buffer.from("agent"), owner.toBuffer()],
      program.programId
    )[0];
  }

  function vaultPda(job: anchor.web3.PublicKey) {
    return anchor.web3.PublicKey.findProgramAddressSync(
      [Buffer.from("vault"), job.toBuffer()],
      program.programId
    )[0];
  }

  async function createJobForAgent(
    agentAccount: anchor.web3.PublicKey,
    bountyLamports: number,
    title = "Build a Solana demo",
    description = "Ship a concise end-to-end demo with clear acceptance notes."
  ) {
    const job = anchor.web3.Keypair.generate();
    const vault = vaultPda(job.publicKey);
    const bounty = new anchor.BN(bountyLamports);

    await program.methods
      .createJob(agentAccount, bounty, title, description)
      .accountsStrict({
        jobAccount: job.publicKey,
        creator: provider.wallet.publicKey,
        agentAccount,
        vault,
        systemProgram: anchor.web3.SystemProgram.programId,
      })
      .signers([job])
      .rpc();

    return { job, vault, bounty, title, description };
  }

  async function submitWorkForAgent(
    jobAccount: anchor.web3.PublicKey,
    agentAccount: anchor.web3.PublicKey,
    agentOwner: anchor.web3.Keypair,
    resultUri = "ipfs://bafy-good-result"
  ) {
    await program.methods
      .submitWork(resultUri)
      .accountsStrict({
        jobAccount,
        agentAccount,
        agentOwner: agentOwner.publicKey,
      })
      .signers([agentOwner])
      .rpc();

    return resultUri;
  }

  it("跑通 黑客松 Demo 流程", async () => {
    const agentOwner = anchor.web3.Keypair.generate();
    await airdrop(agentOwner.publicKey);

    const agentAccount = agentPda(agentOwner.publicKey);

    await program.methods
      .registerAgent("ClawGPT", "Solana dev")
      .accountsStrict({
        agentAccount,
        owner: agentOwner.publicKey,
        systemProgram: anchor.web3.SystemProgram.programId,
      })
      .signers([agentOwner])
      .rpc();

    const registeredAgent = await accounts.agentAccount.fetch(
      agentAccount
    );
    expect(registeredAgent.owner.equals(agentOwner.publicKey)).to.equal(true);
    expect(registeredAgent.name).to.equal("ClawGPT");
    expect(registeredAgent.skill).to.equal("Solana dev");
    expect(registeredAgent.reputation.toNumber()).to.equal(100);
    expect(registeredAgent.completedJobs.toNumber()).to.equal(0);
    console.log("1. Agent 已注册", {
      name: registeredAgent.name,
      skill: registeredAgent.skill,
      reputation: registeredAgent.reputation.toNumber(),
      completedJobs: registeredAgent.completedJobs.toNumber(),
    });

    const { job, vault, bounty, title, description } = await createJobForAgent(
      agentAccount,
      0.25 * anchor.web3.LAMPORTS_PER_SOL,
      "Build OmniClaw UI",
      "Create a small UI that registers agents, creates jobs, and shows vault balances."
    );

    const createdJob = await accounts.jobAccount.fetch(job.publicKey);
    expect(createdJob.creator.equals(provider.wallet.publicKey)).to.equal(true);
    expect(createdJob.agent.equals(agentAccount)).to.equal(true);
    expect(createdJob.bounty.toNumber()).to.equal(bounty.toNumber());
    expect(createdJob.status).to.equal(STATUS_OPEN);
    expect(createdJob.title).to.equal(title);
    expect(createdJob.description).to.equal(description);
    expect(createdJob.resultUri).to.equal("");
    expect(createdJob.createdAt.toNumber()).to.be.greaterThan(0);
    expect(createdJob.submittedAt.toNumber()).to.equal(0);
    expect(createdJob.closedAt.toNumber()).to.equal(0);
    expect(await provider.connection.getBalance(vault)).to.equal(
      bounty.toNumber()
    );
    console.log("2. Job 已创建，SOL 已锁定", {
      title: createdJob.title,
      bountyLamports: createdJob.bounty.toNumber(),
      vaultLamports: await provider.connection.getBalance(vault),
      status: createdJob.status,
    });

    const resultUri = await submitWorkForAgent(
      job.publicKey,
      agentAccount,
      agentOwner,
      "ipfs://bafy-omniclaw-ui"
    );
    const submittedJob = await accounts.jobAccount.fetch(job.publicKey);
    expect(submittedJob.status).to.equal(STATUS_SUBMITTED);
    expect(submittedJob.resultUri).to.equal(resultUri);
    expect(submittedJob.submittedAt.toNumber()).to.be.greaterThan(0);
    expect(submittedJob.closedAt.toNumber()).to.equal(0);
    console.log("3. Agent 已提交交付物，等待验收", {
      resultUri: submittedJob.resultUri,
      submittedAt: submittedJob.submittedAt.toNumber(),
      status: submittedJob.status,
    });

    const agentOwnerBalanceBefore = await provider.connection.getBalance(
      agentOwner.publicKey
    );

    await program.methods
      .completeJob()
      .accountsStrict({
        jobAccount: job.publicKey,
        creator: provider.wallet.publicKey,
        agentAccount,
        agentOwner: agentOwner.publicKey,
        vault,
        systemProgram: anchor.web3.SystemProgram.programId,
      })
      .rpc();

    const completedJob = await accounts.jobAccount.fetch(job.publicKey);
    const rewardedAgent = await accounts.agentAccount.fetch(
      agentAccount
    );
    const agentOwnerBalanceAfter = await provider.connection.getBalance(
      agentOwner.publicKey
    );

    expect(completedJob.status).to.equal(STATUS_COMPLETED);
    expect(completedJob.resultUri).to.equal(resultUri);
    expect(completedJob.closedAt.toNumber()).to.be.greaterThan(0);
    expect(rewardedAgent.reputation.toNumber()).to.equal(110);
    expect(rewardedAgent.completedJobs.toNumber()).to.equal(1);
    expect(agentOwnerBalanceAfter).to.equal(
      agentOwnerBalanceBefore + bounty.toNumber()
    );
    expect(await provider.connection.getBalance(vault)).to.equal(0);
    console.log("4. Job 已完成，赏金已自动支付", {
      paidLamports: agentOwnerBalanceAfter - agentOwnerBalanceBefore,
      vaultLamports: await provider.connection.getBalance(vault),
      reputation: rewardedAgent.reputation.toNumber(),
      completedJobs: rewardedAgent.completedJobs.toNumber(),
      status: completedJob.status,
    });

    const badJob = await createJobForAgent(
      agentAccount,
      0.1 * anchor.web3.LAMPORTS_PER_SOL,
      "Audit a risky prompt",
      "Return a short audit report with concrete vulnerabilities."
    );
    await submitWorkForAgent(
      badJob.job.publicKey,
      agentAccount,
      agentOwner,
      "ipfs://bafy-low-quality-result"
    );
    const badSubmittedJob = await accounts.jobAccount.fetch(
      badJob.job.publicKey
    );
    expect(badSubmittedJob.status).to.equal(STATUS_SUBMITTED);
    expect(await provider.connection.getBalance(badJob.vault)).to.equal(
      badJob.bounty.toNumber()
    );
    console.log("5. 坏 Agent 的 Job 已提交，赏金仍在 vault", {
      resultUri: badSubmittedJob.resultUri,
      bountyLamports: badSubmittedJob.bounty.toNumber(),
      vaultLamports: await provider.connection.getBalance(badJob.vault),
      status: badSubmittedJob.status,
    });

    await program.methods
      .slashAgent()
      .accountsStrict({
        jobAccount: badJob.job.publicKey,
        agentAccount,
        creator: provider.wallet.publicKey,
        vault: badJob.vault,
        systemProgram: anchor.web3.SystemProgram.programId,
      })
      .rpc();

    const slashedAgent = await accounts.agentAccount.fetch(agentAccount);
    const slashedJob = await accounts.jobAccount.fetch(
      badJob.job.publicKey
    );
    expect(slashedAgent.reputation.toNumber()).to.equal(90);
    expect(slashedJob.status).to.equal(STATUS_SLASHED);
    expect(slashedJob.resultUri).to.equal("ipfs://bafy-low-quality-result");
    expect(slashedJob.closedAt.toNumber()).to.be.greaterThan(0);
    expect(await provider.connection.getBalance(badJob.vault)).to.equal(0);
    console.log("6. 坏 Agent 已被 slash，赏金已退款", {
      reputation: slashedAgent.reputation.toNumber(),
      vaultLamports: await provider.connection.getBalance(badJob.vault),
      status: slashedJob.status,
    });

    const cancellableJob = await createJobForAgent(
      agentAccount,
      5_000_000,
      "Cancelled scope",
      "This task is cancelled before the agent starts work."
    );
    await program.methods
      .cancelJob()
      .accountsStrict({
        jobAccount: cancellableJob.job.publicKey,
        creator: provider.wallet.publicKey,
        vault: cancellableJob.vault,
        systemProgram: anchor.web3.SystemProgram.programId,
      })
      .rpc();

    const cancelledAgent = await accounts.agentAccount.fetch(
      agentAccount
    );
    const cancelledJob = await accounts.jobAccount.fetch(
      cancellableJob.job.publicKey
    );
    expect(cancelledJob.status).to.equal(STATUS_CANCELLED);
    expect(cancelledJob.closedAt.toNumber()).to.be.greaterThan(0);
    expect(cancelledAgent.reputation.toNumber()).to.equal(90);
    expect(await provider.connection.getBalance(cancellableJob.vault)).to.equal(
      0
    );
    console.log("7. 未提交 Job 已取消，Agent 声誉不变", {
      reputation: cancelledAgent.reputation.toNumber(),
      vaultLamports: await provider.connection.getBalance(cancellableJob.vault),
      status: cancelledJob.status,
    });

    for (let i = 0; i < 5; i += 1) {
      const floorJob = await createJobForAgent(agentAccount, 1_000_000);

      await program.methods
        .slashAgent()
        .accountsStrict({
          jobAccount: floorJob.job.publicKey,
          agentAccount,
          creator: provider.wallet.publicKey,
          vault: floorJob.vault,
          systemProgram: anchor.web3.SystemProgram.programId,
        })
        .rpc();
    }

    const flooredAgent = await accounts.agentAccount.fetch(agentAccount);
    expect(flooredAgent.reputation.toNumber()).to.equal(0);
    console.log("8. 声誉最低值检查完成", {
      reputation: flooredAgent.reputation.toNumber(),
    });
  });

  it("拒绝越权提交、complete 或 slash", async () => {
    const agentOwner = anchor.web3.Keypair.generate();
    const stranger = anchor.web3.Keypair.generate();
    await airdrop(agentOwner.publicKey);
    await airdrop(stranger.publicKey);

    const agentAccount = agentPda(agentOwner.publicKey);
    await program.methods
      .registerAgent("GuardedAI", "Verifier")
      .accountsStrict({
        agentAccount,
        owner: agentOwner.publicKey,
        systemProgram: anchor.web3.SystemProgram.programId,
      })
      .signers([agentOwner])
      .rpc();

    const guardedJob = await createJobForAgent(agentAccount, 10_000_000);

    try {
      await program.methods
        .submitWork("ipfs://bafy-stranger-result")
        .accountsStrict({
          jobAccount: guardedJob.job.publicKey,
          agentAccount,
          agentOwner: stranger.publicKey,
        })
        .signers([stranger])
        .rpc();

      expect.fail("非 Agent owner 不应该能提交交付物");
    } catch (error) {
      expect(`${error}`).to.include("InvalidAgentOwner");
    }

    await submitWorkForAgent(
      guardedJob.job.publicKey,
      agentAccount,
      agentOwner,
      "ipfs://bafy-guarded-result"
    );

    try {
      await program.methods
        .completeJob()
        .accountsStrict({
          jobAccount: guardedJob.job.publicKey,
          creator: stranger.publicKey,
          agentAccount,
          agentOwner: agentOwner.publicKey,
          vault: guardedJob.vault,
          systemProgram: anchor.web3.SystemProgram.programId,
        })
        .signers([stranger])
        .rpc();

      expect.fail("非创建者不应该能完成任务");
    } catch (error) {
      expect(`${error}`).to.include("UnauthorizedCreator");
    }

    try {
      await program.methods
        .slashAgent()
        .accountsStrict({
          jobAccount: guardedJob.job.publicKey,
          agentAccount,
          creator: stranger.publicKey,
          vault: guardedJob.vault,
          systemProgram: anchor.web3.SystemProgram.programId,
        })
        .signers([stranger])
        .rpc();

      expect.fail("非创建者不应该能 slash 任务");
    } catch (error) {
      expect(`${error}`).to.include("UnauthorizedCreator");
    }

    const stillSubmittedJob = await accounts.jobAccount.fetch(
      guardedJob.job.publicKey
    );
    expect(stillSubmittedJob.status).to.equal(STATUS_SUBMITTED);
    expect(await provider.connection.getBalance(guardedJob.vault)).to.equal(
      guardedJob.bounty.toNumber()
    );
  });

  it("拒绝未提交任务直接验收", async () => {
    const agentOwner = anchor.web3.Keypair.generate();
    await airdrop(agentOwner.publicKey);

    const agentAccount = agentPda(agentOwner.publicKey);
    await program.methods
      .registerAgent("StatefulAI", "Workflow QA")
      .accountsStrict({
        agentAccount,
        owner: agentOwner.publicKey,
        systemProgram: anchor.web3.SystemProgram.programId,
      })
      .signers([agentOwner])
      .rpc();

    const statefulJob = await createJobForAgent(agentAccount, 10_000_000);

    try {
      await program.methods
        .completeJob()
        .accountsStrict({
          jobAccount: statefulJob.job.publicKey,
          creator: provider.wallet.publicKey,
          agentAccount,
          agentOwner: agentOwner.publicKey,
          vault: statefulJob.vault,
          systemProgram: anchor.web3.SystemProgram.programId,
        })
        .rpc();

      expect.fail("未提交任务不应该能直接验收");
    } catch (error) {
      expect(`${error}`).to.include("JobNotSubmitted");
    }

    const stillOpenJob = await accounts.jobAccount.fetch(
      statefulJob.job.publicKey
    );
    expect(stillOpenJob.status).to.equal(STATUS_OPEN);
    expect(await provider.connection.getBalance(statefulJob.vault)).to.equal(
      statefulJob.bounty.toNumber()
    );
  });
});
