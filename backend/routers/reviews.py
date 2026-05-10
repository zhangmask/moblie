from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.dependencies import get_db, get_review_service
from backend.middleware.wallet_auth import WalletIdentity, require_wallet_identity
from backend.models.schemas import ReviewCreateRequest, ReviewResponse, ReviewSummaryResponse
from backend.services.review_service import ReviewService


router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.post("/agent-os", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
async def create_agent_os_review(
    payload: ReviewCreateRequest,
    db: Session = Depends(get_db),
    review_service: ReviewService = Depends(get_review_service),
    identity: WalletIdentity = Depends(require_wallet_identity),
) -> ReviewResponse:
    return review_service.create_agent_os_review(db, identity.wallet_address, payload)


@router.post("/publishers", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
async def create_publisher_review(
    payload: ReviewCreateRequest,
    db: Session = Depends(get_db),
    review_service: ReviewService = Depends(get_review_service),
    identity: WalletIdentity = Depends(require_wallet_identity),
) -> ReviewResponse:
    return review_service.create_publisher_review(db, identity.wallet_address, payload)


@router.get("/agent-os/{agent_os_id}", response_model=ReviewSummaryResponse)
async def get_agent_os_reviews(
    agent_os_id: str,
    db: Session = Depends(get_db),
    review_service: ReviewService = Depends(get_review_service),
) -> ReviewSummaryResponse:
    return review_service.get_summary(db, "agent_os", agent_os_id)


@router.get("/publishers/{publisher_wallet}", response_model=ReviewSummaryResponse)
async def get_publisher_reviews(
    publisher_wallet: str,
    db: Session = Depends(get_db),
    review_service: ReviewService = Depends(get_review_service),
) -> ReviewSummaryResponse:
    return review_service.get_summary(db, "publisher", publisher_wallet)
