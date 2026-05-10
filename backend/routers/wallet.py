from __future__ import annotations

from fastapi import APIRouter

from backend.models.schemas import WalletVerifyRequest, WalletVerifyResponse


router = APIRouter(prefix="/wallet", tags=["wallet"])


def verify_wallet_signature(wallet_address: str, message: str, signature: str) -> WalletVerifyResponse:
    if not wallet_address.strip():
        return WalletVerifyResponse(
            verified=False,
            verification_mode="format_only",
            reason="钱包地址不能为空",
        )
    if not message.startswith("Sign in to AgentOS:"):
        return WalletVerifyResponse(
            verified=False,
            verification_mode="format_only",
            reason="message 必须以 `Sign in to AgentOS:` 开头",
        )
    if not signature.strip():
        return WalletVerifyResponse(
            verified=False,
            verification_mode="format_only",
            reason="签名不能为空",
        )
    return WalletVerifyResponse(
        verified=True,
        verification_mode="format_only",
        reason="当前为黑客松 MVP，仅完成签名格式校验，未接真实 Ed25519 验签",
    )


@router.post("/verify", response_model=WalletVerifyResponse)
async def verify_wallet(payload: WalletVerifyRequest) -> WalletVerifyResponse:
    return verify_wallet_signature(
        wallet_address=payload.wallet_address,
        message=payload.message,
        signature=payload.signature,
    )
