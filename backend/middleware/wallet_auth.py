from __future__ import annotations

from dataclasses import dataclass

from fastapi import Header, HTTPException, status


@dataclass(frozen=True)
class WalletIdentity:
    wallet_address: str


async def require_wallet_identity(
    x_wallet_address: str | None = Header(default=None, alias="X-Wallet-Address"),
) -> WalletIdentity:
    if not x_wallet_address:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="缺少 X-Wallet-Address 请求头",
        )
    return WalletIdentity(wallet_address=x_wallet_address.strip())
