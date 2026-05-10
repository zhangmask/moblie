from __future__ import annotations

import asyncio

from backend.cloud.demo_provider import DemoCloudProvider
from backend.cloud.orchestrators.hire import HireOrchestrator
from backend.cloud.orchestrators.lifecycle import InstanceLifecycleOrchestrator
from backend.cloud.registry import ProviderRegistry
from backend.config import Settings
from backend.models.schemas import (
    AgentOsUpsertRequest,
    PaymentOrderConfirmRequest,
    PaymentOrderCreateRequest,
    PaymentOrderFreezeRequest,
    PaymentOrderSettleRequest,
    ProtocolAutoHireRequest,
    ProtocolHireRequest,
)
from backend.models.database import UserImageRecord
from backend.models.schemas import (
    ImageMessageCreateRequest,
    ImageWorkflowConfirmRequest,
    ImageWorkflowCreateRequest,
)
from backend.services.image_workflow_service import ImageWorkflowService
from backend.services.instance_service import InstanceService
from backend.services.market_service import MarketService
from backend.services.message_service import MessageService
from backend.services.notification_service import NotificationService
from backend.services.payment_service import PaymentService
from backend.services.protocol_service import ProtocolService
from backend.services.review_service import ReviewService


def build_protocol_service(tmp_path) -> tuple[MarketService, PaymentService, ProtocolService]:
    notification_service = NotificationService()
    review_service = ReviewService()
    market_service = MarketService(review_service)
    payment_service = PaymentService(notification_service)
    registry = ProviderRegistry()
    registry.register("demo", DemoCloudProvider())
    settings = Settings(
        app_name="test",
        api_prefix="/api",
        storage_root=tmp_path,
        database_url="sqlite+pysqlite:///:memory:",
        solana_rpc_url="http://127.0.0.1:8899",
        solana_program_id="test-program",
        default_provider_name="demo",
        provider_options={},
    )
    instance_service = InstanceService(
        settings,
        notification_service,
        HireOrchestrator(registry),
        InstanceLifecycleOrchestrator(registry),
        review_service,
    )
    protocol_service = ProtocolService(
        market_service,
        instance_service,
        payment_service,
        review_service,
    )
    return market_service, payment_service, protocol_service


def test_image_workflow_confirm_creates_user_image(db_session) -> None:
    async def run_test():
        notification_service = NotificationService()
        service = ImageWorkflowService(notification_service)
        workflow = await service.create_request(
            db_session,
            "wallet-requester",
            ImageWorkflowCreateRequest(
                publisher_wallet="wallet-publisher",
                target_wallet="wallet-target",
                requested_image_name="agent-image-demo",
            ),
        )
        return await service.confirm_request(
            db_session,
            workflow.id,
            "wallet-publisher",
            ImageWorkflowConfirmRequest(approved=True),
        )

    confirmed = asyncio.run(run_test())
    assert confirmed.status == "completed"
    created_image = db_session.get(UserImageRecord, confirmed.created_image_id)
    assert created_image is not None
    assert created_image.owner_wallet == "wallet-target"


def test_payment_order_confirm_sets_signature(db_session) -> None:
    async def run_test():
        notification_service = NotificationService()
        service = PaymentService(notification_service)
        order = await service.create_order(
            db_session,
            "wallet-owner",
            PaymentOrderCreateRequest(
                agent_wallet="wallet-agent",
                amount="1.5",
            ),
        )
        return await service.confirm_order(
            db_session,
            order.id,
            "wallet-owner",
            PaymentOrderConfirmRequest(transaction_signature="tx-demo-123"),
        )

    confirmed = asyncio.run(run_test())
    assert confirmed.status == "confirmed"
    assert confirmed.transaction_signature == "tx-demo-123"


def test_send_image_message_returns_user_and_assistant_messages(db_session) -> None:
    image = UserImageRecord(
        owner_wallet="wallet-owner",
        provider_name="demo",
        image_ref="img-demo",
        image_name="demo-image",
        status="available",
        metadata_json={},
    )
    db_session.add(image)
    db_session.commit()
    db_session.refresh(image)

    async def run_test():
        notification_service = NotificationService()
        service = MessageService(notification_service)
        return await service.send_image_message(
            db_session,
            image,
            ImageMessageCreateRequest(content="帮我总结这个镜像的用途"),
        )

    messages = asyncio.run(run_test())
    assert [message.role for message in messages] == ["user", "assistant"]
    assert "demo-image" in messages[1].content


def test_market_dashboard_counts_settlements(db_session) -> None:
    async def run_test():
        notification_service = NotificationService()
        review_service = ReviewService()
        market_service = MarketService(review_service)
        payment_service = PaymentService(notification_service)
        agent_os = market_service.register_agent_os(
            db_session,
            "wallet-publisher",
            AgentOsUpsertRequest(
                name="研究员 Agent OS",
                description="用于行业研究",
                category="research",
                skill="research",
                price_amount="12",
                image_ref="img-research",
            ),
        )
        order = await payment_service.create_order(
            db_session,
            "wallet-owner",
            PaymentOrderCreateRequest(
                agent_wallet="wallet-publisher",
                agent_os_id=agent_os.id,
                amount="12",
            ),
        )
        await payment_service.freeze_order(
            db_session,
            order.id,
            PaymentOrderFreezeRequest(frozen_amount="12", note="发布者冻结"),
        )
        await payment_service.confirm_order(
            db_session,
            order.id,
            "wallet-owner",
            PaymentOrderConfirmRequest(transaction_signature="tx-market-1"),
        )
        await payment_service.settle_order(
            db_session,
            order.id,
            PaymentOrderSettleRequest(
                settled_amount="12",
                platform_fee="1.2000",
                publisher_amount="10.8000",
                refunded_amount="0",
                note="工作台结算",
            ),
        )
        return market_service.get_publisher_dashboard(
            db_session,
            "wallet-publisher",
        ), payment_service.list_settlements_for_publisher(db_session, "wallet-publisher")

    dashboard, settlements = asyncio.run(run_test())
    assert dashboard.total_agent_os == 1
    assert dashboard.settled_orders == 1
    assert dashboard.total_revenue == "10.8000"
    assert len(settlements) == 1
    assert settlements[0].publisher_amount == "10.8000"


def test_protocol_hire_and_fire_settles_order(db_session, tmp_path) -> None:
    async def run_test():
        market_service, _, protocol_service = build_protocol_service(tmp_path)
        agent_os = market_service.register_agent_os(
            db_session,
            "wallet-publisher",
            AgentOsUpsertRequest(
                name="数据搜集 Agent OS",
                description="自动搜集数据",
                category="research",
                skill="search,data",
                price_amount="8",
                image_ref="img-data",
            ),
        )
        hire_result = await protocol_service.hire_agent_os(
            db_session,
            ProtocolHireRequest(
                agent_os_id=agent_os.id,
                owner_wallet="wallet-owner",
                payment_method="web3_wallet",
                job_pubkey="job-hire-1",
            ),
        )
        fire_result = await protocol_service.fire_agent_os(
            db_session,
            hire_result.instance.id,
            "wallet-owner",
        )
        return hire_result, fire_result

    hire_result, fire_result = asyncio.run(run_test())
    assert hire_result.payment.status == "confirmed"
    assert hire_result.instance.agent_os_id == hire_result.agent_os.id
    assert fire_result.instance.status == "destroyed"
    assert fire_result.payment is not None
    assert fire_result.payment.status == "settled"
    assert fire_result.settlement is not None
    assert fire_result.final_cost == "8"


def test_protocol_auto_hire_dispatches_task(db_session, tmp_path) -> None:
    async def run_test():
        market_service, _, protocol_service = build_protocol_service(tmp_path)
        market_service.register_agent_os(
            db_session,
            "wallet-publisher",
            AgentOsUpsertRequest(
                name="行业分析 Agent OS",
                description="擅长新能源汽车调研",
                category="analysis",
                skill="analysis,research",
                price_amount="6",
                image_ref="img-analysis",
            ),
        )
        return await protocol_service.auto_hire(
            db_session,
            ProtocolAutoHireRequest(
                requester_agent_id="agent-master",
                owner_wallet="wallet-owner",
                query="新能源汽车行业调研",
                task="整理 2026 年行业规模和主要玩家",
                min_rating=0,
                max_price="10",
            ),
        )

    result = asyncio.run(run_test())
    assert result.match.name == "行业分析 Agent OS"
    assert result.hire.instance.owner_wallet == "wallet-owner"
    assert result.task.accepted is True
