use anchor_lang::prelude::*;
use anchor_lang::system_program;

declare_id!("5FrcPFSPgzE78u93i9qMG28G9Rpa6NgpbMcyjeqevTwE");

/// 新 Agent 默认从一个中性分数开始，方便 Demo 解释。
pub const DEFAULT_REPUTATION: u64 = 100;
/// 任务成功完成后的声誉奖励。
pub const REPUTATION_REWARD: u64 = 10;
/// 任务创建者拒绝结果并 slash Agent 时的声誉惩罚。
pub const REPUTATION_SLASH: u64 = 20;

/// 任务已创建并锁定赏金，等待提交、取消或 slash。
pub const STATUS_OPEN: u8 = 0;
/// Agent owner 已提交交付物，等待任务创建者验收或 slash。
pub const STATUS_SUBMITTED: u8 = 1;
/// 任务已被创建者验收，赏金已支付给 Agent owner，并关闭。
pub const STATUS_COMPLETED: u8 = 2;
/// 任务创建者取消了尚未提交的任务，赏金已退回，并关闭。
pub const STATUS_CANCELLED: u8 = 3;
/// 任务被拒绝并触发 slash，赏金已退回创建者，并关闭。
pub const STATUS_SLASHED: u8 = 4;

#[program]
pub mod omniclaw {
    use super::*;

    /// 为签名钱包注册唯一的 Agent 档案。
    ///
    /// AgentAccount PDA 由 `["agent", owner]` 推导，因此同一个钱包不会重复注册多个 Agent。
    pub fn register_agent(ctx: Context<RegisterAgent>, name: String, skill: String) -> Result<()> {
        require!(!name.trim().is_empty(), OmniClawError::NameRequired);
        require!(!skill.trim().is_empty(), OmniClawError::SkillRequired);
        require!(
            name.as_bytes().len() <= AgentAccount::MAX_NAME_LEN,
            OmniClawError::NameTooLong
        );
        require!(
            skill.as_bytes().len() <= AgentAccount::MAX_SKILL_LEN,
            OmniClawError::SkillTooLong
        );

        let agent_account = &mut ctx.accounts.agent_account;
        agent_account.owner = ctx.accounts.owner.key();
        agent_account.name = name;
        agent_account.skill = skill;
        agent_account.reputation = DEFAULT_REPUTATION;
        agent_account.completed_jobs = 0;

        emit!(AgentRegistered {
            agent: agent_account.key(),
            owner: agent_account.owner,
            name: agent_account.name.clone(),
            skill: agent_account.skill.clone(),
        });

        Ok(())
    }

    /// 为已有 Agent 创建任务，并把赏金锁进该任务的 vault PDA。
    ///
    /// vault PDA 由 `["vault", job_account]` 推导。它是 system account，
    /// 程序通过 PDA signer seeds 控制里面的 lamports。
    pub fn create_job(
        ctx: Context<CreateJob>,
        agent: Pubkey,
        bounty: u64,
        title: String,
        description: String,
    ) -> Result<()> {
        require!(bounty > 0, OmniClawError::InvalidBounty);
        require!(!title.trim().is_empty(), OmniClawError::TitleRequired);
        require!(
            !description.trim().is_empty(),
            OmniClawError::DescriptionRequired
        );
        require!(
            title.as_bytes().len() <= JobAccount::MAX_TITLE_LEN,
            OmniClawError::TitleTooLong
        );
        require!(
            description.as_bytes().len() <= JobAccount::MAX_DESCRIPTION_LEN,
            OmniClawError::DescriptionTooLong
        );

        let job_account = &mut ctx.accounts.job_account;
        job_account.creator = ctx.accounts.creator.key();
        job_account.agent = agent;
        job_account.bounty = bounty;
        job_account.status = STATUS_OPEN;
        job_account.title = title;
        job_account.description = description;
        job_account.result_uri = String::new();
        job_account.created_at = Clock::get()?.unix_timestamp;
        job_account.submitted_at = 0;
        job_account.closed_at = 0;

        let transfer_accounts = system_program::Transfer {
            from: ctx.accounts.creator.to_account_info(),
            to: ctx.accounts.vault.to_account_info(),
        };
        let transfer_ctx = CpiContext::new(
            ctx.accounts.system_program.to_account_info(),
            transfer_accounts,
        );
        system_program::transfer(transfer_ctx, bounty)?;

        emit!(JobCreated {
            job: job_account.key(),
            creator: job_account.creator,
            agent: job_account.agent,
            bounty,
            title: job_account.title.clone(),
            created_at: job_account.created_at,
        });

        Ok(())
    }

    /// Agent owner 提交交付物 URI，任务进入待验收状态。
    ///
    /// 这里不强行校验 URI 格式，前端可以传 URL、IPFS CID、Arweave tx id 或 hash。
    pub fn submit_work(ctx: Context<SubmitWork>, result_uri: String) -> Result<()> {
        require!(
            !result_uri.trim().is_empty(),
            OmniClawError::ResultUriRequired
        );
        require!(
            result_uri.as_bytes().len() <= JobAccount::MAX_RESULT_URI_LEN,
            OmniClawError::ResultUriTooLong
        );

        let submitted_at = Clock::get()?.unix_timestamp;
        let job_account = &mut ctx.accounts.job_account;
        job_account.result_uri = result_uri;
        job_account.submitted_at = submitted_at;
        job_account.status = STATUS_SUBMITTED;

        emit!(JobWorkSubmitted {
            job: job_account.key(),
            agent: job_account.agent,
            agent_owner: ctx.accounts.agent_owner.key(),
            result_uri: job_account.result_uri.clone(),
            submitted_at,
        });

        Ok(())
    }

    /// 任务创建者验收工作，从 vault 释放 SOL，并奖励 Agent。
    ///
    /// creator 必须签名，避免任意钱包替别人完成任务并强制付款。
    pub fn complete_job(ctx: Context<CompleteJob>) -> Result<()> {
        let bounty = ctx.accounts.job_account.bounty;
        let job_key = ctx.accounts.job_account.key();
        let vault_bump = [ctx.bumps.vault];
        let signer_seeds: &[&[&[u8]]] = &[&[b"vault", job_key.as_ref(), &vault_bump]];

        let transfer_accounts = system_program::Transfer {
            from: ctx.accounts.vault.to_account_info(),
            to: ctx.accounts.agent_owner.to_account_info(),
        };
        let transfer_ctx = CpiContext::new_with_signer(
            ctx.accounts.system_program.to_account_info(),
            transfer_accounts,
            signer_seeds,
        );
        system_program::transfer(transfer_ctx, bounty)?;

        let agent_key = ctx.accounts.agent_account.key();
        let (reputation, completed_jobs) = {
            let agent_account = &mut ctx.accounts.agent_account;
            agent_account.reputation = agent_account.reputation.saturating_add(REPUTATION_REWARD);
            agent_account.completed_jobs = agent_account.completed_jobs.saturating_add(1);
            (agent_account.reputation, agent_account.completed_jobs)
        };

        let closed_at = Clock::get()?.unix_timestamp;
        ctx.accounts.job_account.status = STATUS_COMPLETED;
        ctx.accounts.job_account.closed_at = closed_at;

        emit!(JobCompleted {
            job: job_key,
            creator: ctx.accounts.creator.key(),
            agent: agent_key,
            agent_owner: ctx.accounts.agent_owner.key(),
            bounty,
            result_uri: ctx.accounts.job_account.result_uri.clone(),
            reputation,
            completed_jobs,
            closed_at,
        });

        Ok(())
    }

    /// 任务创建者取消尚未提交的任务，退回赏金，但不惩罚 Agent。
    pub fn cancel_job(ctx: Context<CancelJob>) -> Result<()> {
        let bounty = ctx.accounts.job_account.bounty;
        let job_key = ctx.accounts.job_account.key();
        let vault_bump = [ctx.bumps.vault];
        let signer_seeds: &[&[&[u8]]] = &[&[b"vault", job_key.as_ref(), &vault_bump]];

        let transfer_accounts = system_program::Transfer {
            from: ctx.accounts.vault.to_account_info(),
            to: ctx.accounts.creator.to_account_info(),
        };
        let transfer_ctx = CpiContext::new_with_signer(
            ctx.accounts.system_program.to_account_info(),
            transfer_accounts,
            signer_seeds,
        );
        system_program::transfer(transfer_ctx, bounty)?;

        let closed_at = Clock::get()?.unix_timestamp;
        ctx.accounts.job_account.status = STATUS_CANCELLED;
        ctx.accounts.job_account.closed_at = closed_at;

        emit!(JobCancelled {
            job: job_key,
            creator: ctx.accounts.creator.key(),
            agent: ctx.accounts.job_account.agent,
            bounty_refunded: bounty,
            closed_at,
        });

        Ok(())
    }

    /// 任务创建者拒绝 open/submitted 状态的任务，退回赏金，并惩罚 Agent。
    ///
    /// 这里刻意保持简单：没有 dispute、DAO、staking。
    /// 它只是 Demo 中“坏 Agent 被 slash，同时资金不会卡住”的路径。
    pub fn slash_agent(ctx: Context<SlashAgent>) -> Result<()> {
        require!(
            ctx.accounts.job_account.status == STATUS_OPEN
                || ctx.accounts.job_account.status == STATUS_SUBMITTED,
            OmniClawError::JobNotSlashable
        );

        let bounty = ctx.accounts.job_account.bounty;
        let job_key = ctx.accounts.job_account.key();
        let vault_bump = [ctx.bumps.vault];
        let signer_seeds: &[&[&[u8]]] = &[&[b"vault", job_key.as_ref(), &vault_bump]];

        let transfer_accounts = system_program::Transfer {
            from: ctx.accounts.vault.to_account_info(),
            to: ctx.accounts.creator.to_account_info(),
        };
        let transfer_ctx = CpiContext::new_with_signer(
            ctx.accounts.system_program.to_account_info(),
            transfer_accounts,
            signer_seeds,
        );
        system_program::transfer(transfer_ctx, bounty)?;

        let agent_key = ctx.accounts.agent_account.key();
        let agent_account = &mut ctx.accounts.agent_account;
        agent_account.reputation = agent_account.reputation.saturating_sub(REPUTATION_SLASH);
        let reputation = agent_account.reputation;
        let closed_at = Clock::get()?.unix_timestamp;
        ctx.accounts.job_account.status = STATUS_SLASHED;
        ctx.accounts.job_account.closed_at = closed_at;

        emit!(AgentSlashed {
            job: job_key,
            creator: ctx.accounts.creator.key(),
            agent: agent_key,
            bounty_refunded: bounty,
            result_uri: ctx.accounts.job_account.result_uri.clone(),
            reputation,
            closed_at,
        });

        Ok(())
    }
}

#[derive(Accounts)]
pub struct RegisterAgent<'info> {
    /// Agent 档案 PDA。一个钱包一个档案，MVP 查询更简单。
    #[account(
        init,
        payer = owner,
        space = 8 + AgentAccount::LEN,
        seeds = [b"agent", owner.key().as_ref()],
        bump
    )]
    pub agent_account: Account<'info, AgentAccount>,
    /// 拥有该 Agent 档案并支付租金的钱包。
    #[account(mut)]
    pub owner: Signer<'info>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
#[instruction(agent: Pubkey)]
pub struct CreateJob<'info> {
    /// 任务账户，使用随机 keypair 创建。前端需要保存它的 public key。
    #[account(init, payer = creator, space = 8 + JobAccount::LEN)]
    pub job_account: Account<'info, JobAccount>,
    /// 发布任务并支付赏金的钱包。
    #[account(mut)]
    pub creator: Signer<'info>,
    /// 分配给该任务的已有 AgentAccount。
    #[account(constraint = agent_account.key() == agent @ OmniClawError::InvalidAgent)]
    pub agent_account: Account<'info, AgentAccount>,
    /// 接收赏金 lamports 的 PDA vault。
    #[account(mut, seeds = [b"vault", job_account.key().as_ref()], bump)]
    pub vault: SystemAccount<'info>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct SubmitWork<'info> {
    #[account(
        mut,
        constraint = job_account.status == STATUS_OPEN @ OmniClawError::JobNotOpen,
        constraint = job_account.agent == agent_account.key() @ OmniClawError::InvalidAgent
    )]
    pub job_account: Account<'info, JobAccount>,
    pub agent_account: Account<'info, AgentAccount>,
    /// Agent owner 必须签名，避免第三方替 Agent 提交伪造交付物。
    #[account(constraint = agent_owner.key() == agent_account.owner @ OmniClawError::InvalidAgentOwner)]
    pub agent_owner: Signer<'info>,
}

#[derive(Accounts)]
pub struct CompleteJob<'info> {
    #[account(
        mut,
        constraint = job_account.status == STATUS_SUBMITTED @ OmniClawError::JobNotSubmitted,
        constraint = job_account.agent == agent_account.key() @ OmniClawError::InvalidAgent,
        constraint = job_account.creator == creator.key() @ OmniClawError::UnauthorizedCreator
    )]
    pub job_account: Account<'info, JobAccount>,
    /// 原始任务创建者必须签名确认付款。
    pub creator: Signer<'info>,
    #[account(mut)]
    pub agent_account: Account<'info, AgentAccount>,
    /// Agent owner 接收 SOL 赏金。
    #[account(
        mut,
        constraint = agent_owner.key() == agent_account.owner @ OmniClawError::InvalidAgentOwner
    )]
    pub agent_owner: SystemAccount<'info>,
    #[account(
        mut,
        seeds = [b"vault", job_account.key().as_ref()],
        bump,
        constraint = vault.lamports() >= job_account.bounty @ OmniClawError::VaultInsufficientFunds
    )]
    pub vault: SystemAccount<'info>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct CancelJob<'info> {
    #[account(
        mut,
        constraint = job_account.status == STATUS_OPEN @ OmniClawError::JobNotCancellable,
        constraint = job_account.creator == creator.key() @ OmniClawError::UnauthorizedCreator
    )]
    pub job_account: Account<'info, JobAccount>,
    /// 原始任务创建者可以取消尚未提交的任务，并收到退回的赏金。
    #[account(mut)]
    pub creator: Signer<'info>,
    #[account(
        mut,
        seeds = [b"vault", job_account.key().as_ref()],
        bump,
        constraint = vault.lamports() >= job_account.bounty @ OmniClawError::VaultInsufficientFunds
    )]
    pub vault: SystemAccount<'info>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct SlashAgent<'info> {
    #[account(
        mut,
        constraint = job_account.agent == agent_account.key() @ OmniClawError::InvalidAgent,
        constraint = job_account.creator == creator.key() @ OmniClawError::UnauthorizedCreator
    )]
    pub job_account: Account<'info, JobAccount>,
    #[account(mut)]
    pub agent_account: Account<'info, AgentAccount>,
    /// 原始任务创建者可以 slash，并收到退回的赏金。
    #[account(mut)]
    pub creator: Signer<'info>,
    #[account(
        mut,
        seeds = [b"vault", job_account.key().as_ref()],
        bump,
        constraint = vault.lamports() >= job_account.bounty @ OmniClawError::VaultInsufficientFunds
    )]
    pub vault: SystemAccount<'info>,
    pub system_program: Program<'info, System>,
}

#[account]
pub struct AgentAccount {
    /// 拥有该 Agent 档案并接收成功任务付款的钱包。
    pub owner: Pubkey,
    /// 短名称。为了黑客松 Demo，直接存到链上账户里。
    pub name: String,
    /// 人类可读的能力描述，例如 "Solana dev" 或 "Prompt engineer"。
    pub skill: String,
    /// Demo 声誉分：初始 100，完成任务 +10，被 slash -20，最低为 0。
    pub reputation: u64,
    /// 被任务创建者验收通过的任务数量。
    pub completed_jobs: u64,
}

impl AgentAccount {
    /// 字符串最大长度按字节计算，不是按字符数量计算。
    pub const MAX_NAME_LEN: usize = 32;
    pub const MAX_SKILL_LEN: usize = 64;
    pub const LEN: usize = 32 + 4 + Self::MAX_NAME_LEN + 4 + Self::MAX_SKILL_LEN + 8 + 8;
}

#[account]
pub struct JobAccount {
    /// 创建任务并向 vault 付款的钱包。
    pub creator: Pubkey,
    /// 分配到该任务的 AgentAccount PDA。
    pub agent: Pubkey,
    /// 锁定的 SOL 赏金，单位是 lamports。
    pub bounty: u64,
    /// 0 = Open，1 = Submitted，2 = Completed，3 = Cancelled，4 = Slashed。
    pub status: u8,
    /// 任务标题，方便前端和索引器直接展示。
    pub title: String,
    /// 任务需求说明。MVP 直接存短文本，复杂版本可以换成 URI/hash。
    pub description: String,
    /// Agent 提交的交付物 URI/hash，未提交时为空字符串。
    pub result_uri: String,
    /// 创建时间戳，Unix seconds。
    pub created_at: i64,
    /// 提交时间戳，未提交时为 0。
    pub submitted_at: i64,
    /// 完成、取消或 slash 时间戳，任务未关闭时为 0。
    pub closed_at: i64,
}

impl JobAccount {
    pub const MAX_TITLE_LEN: usize = 64;
    pub const MAX_DESCRIPTION_LEN: usize = 256;
    pub const MAX_RESULT_URI_LEN: usize = 128;
    pub const LEN: usize = 32
        + 32
        + 8
        + 1
        + 4
        + Self::MAX_TITLE_LEN
        + 4
        + Self::MAX_DESCRIPTION_LEN
        + 4
        + Self::MAX_RESULT_URI_LEN
        + 8
        + 8
        + 8;
}

#[event]
pub struct AgentRegistered {
    pub agent: Pubkey,
    pub owner: Pubkey,
    pub name: String,
    pub skill: String,
}

#[event]
pub struct JobCreated {
    pub job: Pubkey,
    pub creator: Pubkey,
    pub agent: Pubkey,
    pub bounty: u64,
    pub title: String,
    pub created_at: i64,
}

#[event]
pub struct JobWorkSubmitted {
    pub job: Pubkey,
    pub agent: Pubkey,
    pub agent_owner: Pubkey,
    pub result_uri: String,
    pub submitted_at: i64,
}

#[event]
pub struct JobCompleted {
    pub job: Pubkey,
    pub creator: Pubkey,
    pub agent: Pubkey,
    pub agent_owner: Pubkey,
    pub bounty: u64,
    pub result_uri: String,
    pub reputation: u64,
    pub completed_jobs: u64,
    pub closed_at: i64,
}

#[event]
pub struct JobCancelled {
    pub job: Pubkey,
    pub creator: Pubkey,
    pub agent: Pubkey,
    pub bounty_refunded: u64,
    pub closed_at: i64,
}

#[event]
pub struct AgentSlashed {
    pub job: Pubkey,
    pub creator: Pubkey,
    pub agent: Pubkey,
    pub bounty_refunded: u64,
    pub result_uri: String,
    pub reputation: u64,
    pub closed_at: i64,
}

#[error_code]
pub enum OmniClawError {
    #[msg("Agent 名称不能为空")]
    NameRequired,
    #[msg("Agent 技能不能为空")]
    SkillRequired,
    #[msg("Agent 名称过长")]
    NameTooLong,
    #[msg("Agent 技能描述过长")]
    SkillTooLong,
    #[msg("赏金必须大于 0")]
    InvalidBounty,
    #[msg("任务标题不能为空")]
    TitleRequired,
    #[msg("任务描述不能为空")]
    DescriptionRequired,
    #[msg("任务标题过长")]
    TitleTooLong,
    #[msg("任务描述过长")]
    DescriptionTooLong,
    #[msg("交付物 URI 不能为空")]
    ResultUriRequired,
    #[msg("交付物 URI 过长")]
    ResultUriTooLong,
    #[msg("无效的 Agent 账户")]
    InvalidAgent,
    #[msg("无效的 Agent owner")]
    InvalidAgentOwner,
    #[msg("任务不是 Open 状态")]
    JobNotOpen,
    #[msg("任务尚未提交，不能验收")]
    JobNotSubmitted,
    #[msg("任务不是可取消状态")]
    JobNotCancellable,
    #[msg("任务不是可 slash 状态")]
    JobNotSlashable,
    #[msg("只有任务创建者可以执行该操作")]
    UnauthorizedCreator,
    #[msg("Vault 中的余额不足以支付预期赏金")]
    VaultInsufficientFunds,
}
