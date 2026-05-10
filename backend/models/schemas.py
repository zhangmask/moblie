from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import AliasChoices, BaseModel, Field


class WalletVerifyRequest(BaseModel):
    wallet_address: str
    message: str
    signature: str


class WalletVerifyResponse(BaseModel):
    verified: bool
    verification_mode: str
    reason: str


class AgentSummary(BaseModel):
    agent_account: str
    owner_wallet: str
    name: str
    skill: str
    reputation: int
    completed_jobs: int
    average_rating: float = 0.0
    review_count: int = 0
    publisher_average_rating: float = 0.0
    publisher_review_count: int = 0
    source: str = "demo_stub"


class AgentOsUpsertRequest(BaseModel):
    agent_account: str | None = None
    name: str
    description: str = ""
    category: str | None = None
    skill: str
    pricing_model: str = "hourly"
    price_amount: str = "0"
    currency: str = "SOL"
    region: str | None = None
    cpu_cores: int | None = None
    memory_gb: int | None = None
    disk_gb: int | None = None
    image_ref: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentOsResponse(BaseModel):
    id: str
    publisher_wallet: str
    agent_account: str | None = None
    name: str
    description: str
    category: str | None = None
    skill: str
    pricing_model: str
    price_amount: str
    currency: str
    region: str | None = None
    cpu_cores: int | None = None
    memory_gb: int | None = None
    disk_gb: int | None = None
    image_ref: str | None = None
    status: str
    metadata: dict[str, Any]
    average_rating: float = 0.0
    review_count: int = 0
    publisher_average_rating: float = 0.0
    publisher_review_count: int = 0
    created_at: datetime
    updated_at: datetime


class PublisherDashboardResponse(BaseModel):
    publisher_wallet: str
    total_agent_os: int
    published_agent_os: int
    pending_image_requests: int
    total_orders: int
    frozen_orders: int
    settled_orders: int
    total_revenue: str
    recent_agent_os: list[AgentOsResponse]


class InstanceCreateRequest(BaseModel):
    job_pubkey: str
    provider_name: str = Field(default="demo", validation_alias=AliasChoices("provider_name", "provider"))
    image_ref: str = Field(validation_alias=AliasChoices("image_ref", "image_id"))
    owner_wallet: str
    agent_wallet: str
    agent_os_id: str | None = None
    instance_type: str = "standard.small"
    security_groups: list[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("security_groups", "security_group_ids"),
    )
    network_ref: str = Field(default="network-demo", validation_alias=AliasChoices("network_ref", "subnet_id"))
    user_data: str | None = None
    provider_config: dict[str, Any] = Field(default_factory=dict)


class InstanceResponse(BaseModel):
    id: str
    job_pubkey: str
    provider_name: str
    provider_instance_id: str | None = None
    image_ref: str
    agent_os_id: str | None = None
    status: str
    public_ip: str | None = None
    private_ip: str | None = None
    owner_wallet: str
    agent_wallet: str
    instance_type: str
    network_ref: str | None = None
    created_at: datetime
    destroyed_at: datetime | None = None


class TaskDispatchRequest(BaseModel):
    task: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class TaskDispatchResponse(BaseModel):
    instance_id: str
    accepted: bool
    message: str


class FileUploadResponse(BaseModel):
    instance_id: str
    filename: str
    direction: str
    size_bytes: int


class NotificationEvent(BaseModel):
    id: str
    wallet: str
    type: str
    payload: dict[str, Any]
    read: bool
    created_at: datetime


class ImageWorkflowCreateRequest(BaseModel):
    publisher_wallet: str
    target_wallet: str
    provider_name: str = "demo"
    requested_image_name: str
    source_instance_id: str | None = None
    source_image_ref: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ImageWorkflowConfirmRequest(BaseModel):
    approved: bool = True
    created_image_ref: str | None = None
    note: str | None = None


class ImageWorkflowResponse(BaseModel):
    id: str
    requester_wallet: str
    publisher_wallet: str
    target_wallet: str
    provider_name: str
    requested_image_name: str
    source_instance_id: str | None = None
    source_image_ref: str | None = None
    status: str
    created_image_id: str | None = None
    note: str | None = None
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class UserImageResponse(BaseModel):
    id: str
    owner_wallet: str
    provider_name: str
    image_ref: str
    image_name: str
    source_workflow_id: str | None = None
    source_instance_id: str | None = None
    source_image_ref: str | None = None
    status: str
    metadata: dict[str, Any]
    created_at: datetime


class PaymentOrderCreateRequest(BaseModel):
    agent_wallet: str
    agent_os_id: str | None = None
    job_pubkey: str | None = None
    payment_type: str = "hire_image_copy"
    amount: str
    currency: str = "SOL"
    chain_name: str = "solana"
    metadata: dict[str, Any] = Field(default_factory=dict)


class PaymentOrderFreezeRequest(BaseModel):
    frozen_amount: str | None = None
    note: str | None = None


class PaymentOrderConfirmRequest(BaseModel):
    transaction_signature: str
    note: str | None = None


class PaymentOrderSettleRequest(BaseModel):
    instance_id: str | None = None
    settled_amount: str | None = None
    platform_fee: str = "0"
    publisher_amount: str = "0"
    refunded_amount: str = "0"
    note: str | None = None


class PaymentOrderResponse(BaseModel):
    id: str
    owner_wallet: str
    agent_wallet: str
    agent_os_id: str | None = None
    instance_id: str | None = None
    job_pubkey: str | None = None
    payment_type: str
    amount: str
    frozen_amount: str | None = None
    settled_amount: str | None = None
    currency: str
    chain_name: str
    status: str
    transaction_signature: str | None = None
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class SettlementResponse(BaseModel):
    id: str
    order_id: str
    instance_id: str | None = None
    owner_wallet: str
    publisher_wallet: str
    platform_fee: str
    publisher_amount: str
    refunded_amount: str
    status: str
    metadata: dict[str, Any]
    created_at: datetime


class ImageMessageCreateRequest(BaseModel):
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class MessageResponse(BaseModel):
    id: str
    owner_wallet: str
    target_type: str
    target_id: str
    role: str
    content: str
    metadata: dict[str, Any]
    created_at: datetime


class AssetFileResponse(BaseModel):
    target_type: str
    target_id: str
    filename: str
    direction: str
    size_bytes: int


class ReviewCreateRequest(BaseModel):
    instance_id: str
    rating: int = Field(ge=1, le=5)
    comment: str = ""
    dimensions: dict[str, int | float] = Field(default_factory=dict)


class ReviewResponse(BaseModel):
    id: str
    target_type: str
    target_id: str
    instance_id: str
    reviewer_wallet: str
    rating: int
    comment: str
    dimensions: dict[str, int | float]
    created_at: datetime


class ReviewSummaryResponse(BaseModel):
    target_type: str
    target_id: str
    average_rating: float
    review_count: int
    dimension_averages: dict[str, float]
    reviews: list[ReviewResponse]


class HiredInstanceResponse(InstanceResponse):
    agent_os_reviewed: bool = False
    publisher_reviewed: bool = False


class FireAgentOsResponse(BaseModel):
    instance: HiredInstanceResponse
    payment: PaymentOrderResponse | None = None
    settlement: SettlementResponse | None = None
    final_cost: str
    refunded_amount: str
    message: str


class ProtocolHireRequest(BaseModel):
    agent_os_id: str
    payment_method: str = "web3_wallet"
    job_pubkey: str
    owner_wallet: str
    instance_type: str = "standard.small"
    network_ref: str = "network-demo"
    security_groups: list[str] = Field(default_factory=list)
    user_data: str | None = None


class ProtocolSendTaskRequest(BaseModel):
    instance_id: str
    task: str
    files: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProtocolAutoHireRequest(BaseModel):
    requester_agent_id: str
    owner_wallet: str
    query: str
    task: str
    min_rating: float | None = None
    max_price: str | None = None


class ProtocolHireResponse(BaseModel):
    agent_os: AgentOsResponse
    instance: InstanceResponse
    payment: PaymentOrderResponse


class ProtocolAutoHireResponse(BaseModel):
    match: AgentOsResponse
    hire: ProtocolHireResponse
    task: TaskDispatchResponse
