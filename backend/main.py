from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.cloud.channels.websocket_channel import WebSocketNotificationChannel
from backend.cloud.demo_provider import DemoCloudProvider
from backend.cloud.orchestrators.file_exchange import FileExchangeOrchestrator
from backend.cloud.orchestrators.hire import HireOrchestrator
from backend.cloud.orchestrators.lifecycle import InstanceLifecycleOrchestrator
from backend.cloud.registry import ProviderRegistry
from backend.config import get_settings
from backend.models.database import init_db
from backend.routers import (
    agents,
    files,
    hired,
    image_workflows,
    images,
    instances,
    market,
    notifications,
    payments,
    protocol,
    publishers,
    reviews,
    wallet,
)
from backend.services.agent_service import AgentService
from backend.services.file_service import FileService
from backend.services.image_asset_service import ImageAssetService
from backend.services.image_workflow_service import ImageWorkflowService
from backend.services.instance_service import InstanceService
from backend.services.market_service import MarketService
from backend.services.message_service import MessageService
from backend.services.notification_service import NotificationService
from backend.services.payment_service import PaymentService
from backend.services.protocol_service import ProtocolService
from backend.services.review_service import ReviewService
from backend.services.solana_service import SolanaService


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    settings.storage_root.mkdir(parents=True, exist_ok=True)
    init_db()

    provider_registry = ProviderRegistry()
    provider_registry.register("demo", DemoCloudProvider())

    websocket_channel = WebSocketNotificationChannel()
    notification_service = NotificationService({"websocket": websocket_channel})
    review_service = ReviewService()
    solana_service = SolanaService(settings)
    agent_service = AgentService(solana_service, review_service)
    hire_orchestrator = HireOrchestrator(provider_registry)
    lifecycle_orchestrator = InstanceLifecycleOrchestrator(provider_registry)
    file_exchange = FileExchangeOrchestrator(provider_registry)
    instance_service = InstanceService(
        settings,
        notification_service,
        hire_orchestrator,
        lifecycle_orchestrator,
        review_service,
    )
    file_service = FileService(settings.storage_root, file_exchange)
    image_workflow_service = ImageWorkflowService(notification_service)
    payment_service = PaymentService(notification_service)
    message_service = MessageService(notification_service)
    image_asset_service = ImageAssetService(settings.storage_root, notification_service)
    market_service = MarketService(review_service)
    protocol_service = ProtocolService(
        market_service,
        instance_service,
        payment_service,
        review_service,
    )

    app.state.settings = settings
    app.state.provider_registry = provider_registry
    app.state.websocket_channel = websocket_channel
    app.state.notification_service = notification_service
    app.state.solana_service = solana_service
    app.state.agent_service = agent_service
    app.state.instance_service = instance_service
    app.state.file_service = file_service
    app.state.image_workflow_service = image_workflow_service
    app.state.payment_service = payment_service
    app.state.message_service = message_service
    app.state.image_asset_service = image_asset_service
    app.state.review_service = review_service
    app.state.market_service = market_service
    app.state.protocol_service = protocol_service
    yield


settings = get_settings()
app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(wallet.router, prefix=settings.api_prefix)
app.include_router(agents.router, prefix=settings.api_prefix)
app.include_router(instances.router, prefix=settings.api_prefix)
app.include_router(files.router, prefix=settings.api_prefix)
app.include_router(hired.router, prefix=settings.api_prefix)
app.include_router(image_workflows.router, prefix=settings.api_prefix)
app.include_router(images.router, prefix=settings.api_prefix)
app.include_router(market.router, prefix=settings.api_prefix)
app.include_router(notifications.router, prefix=settings.api_prefix)
app.include_router(payments.router, prefix=settings.api_prefix)
app.include_router(protocol.router, prefix=settings.api_prefix)
app.include_router(publishers.router, prefix=settings.api_prefix)
app.include_router(reviews.router, prefix=settings.api_prefix)


@app.get("/healthz")
async def healthcheck() -> dict[str, object]:
    return {
        "status": "ok",
        "service": settings.app_name,
        "api_prefix": settings.api_prefix,
        "default_provider_name": settings.default_provider_name,
    }
