from __future__ import annotations

import json
from typing import Any
from urllib import parse, request


class AgentMarket:
    """Agent 镜像市场协议客户端。"""

    def __init__(self, platform_url: str, auth_token: str | None = None):
        self.platform_url = platform_url.rstrip("/")
        self.auth_token = auth_token

    def search(
        self,
        query: str,
        category: str | None = None,
        skill: str | None = None,
        min_rating: float | None = None,
        max_price: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._request(
            "GET",
            "/api/market/agent-os",
            query={
                "q": query,
                "category": category,
                "skill": skill,
                "min_rating": min_rating,
                "max_price": max_price,
            },
        )

    def hire(
        self,
        agent_os_id: str,
        owner_wallet: str,
        job_pubkey: str,
        payment_method: str = "web3_wallet",
        instance_type: str = "standard.small",
        network_ref: str = "network-demo",
        security_groups: list[str] | None = None,
        user_data: str | None = None,
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            "/api/protocol/hire-agent-os",
            wallet_address=owner_wallet,
            body={
                "agent_os_id": agent_os_id,
                "payment_method": payment_method,
                "job_pubkey": job_pubkey,
                "owner_wallet": owner_wallet,
                "instance_type": instance_type,
                "network_ref": network_ref,
                "security_groups": security_groups or [],
                "user_data": user_data,
            },
        )

    def send_task(
        self,
        instance_id: str,
        owner_wallet: str,
        task: str,
        files: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            "/api/protocol/send-task",
            wallet_address=owner_wallet,
            body={
                "instance_id": instance_id,
                "task": task,
                "files": files or [],
                "metadata": metadata or {},
            },
        )

    def fire(self, instance_id: str, owner_wallet: str) -> dict[str, Any]:
        return self._request(
            "POST",
            f"/api/protocol/fire-agent-os/{instance_id}",
            wallet_address=owner_wallet,
        )

    def list_hired(self, owner_wallet: str) -> list[dict[str, Any]]:
        return self._request("GET", "/api/protocol/list-hired", wallet_address=owner_wallet)

    def rate_agent_os(
        self,
        owner_wallet: str,
        instance_id: str,
        rating: int,
        comment: str = "",
        dimensions: dict[str, int | float] | None = None,
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            "/api/protocol/rate-agent-os",
            wallet_address=owner_wallet,
            body={
                "instance_id": instance_id,
                "rating": rating,
                "comment": comment,
                "dimensions": dimensions or {},
            },
        )

    def rate_publisher(
        self,
        owner_wallet: str,
        instance_id: str,
        rating: int,
        comment: str = "",
        dimensions: dict[str, int | float] | None = None,
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            "/api/protocol/rate-publisher",
            wallet_address=owner_wallet,
            body={
                "instance_id": instance_id,
                "rating": rating,
                "comment": comment,
                "dimensions": dimensions or {},
            },
        )

    def get_reviews(self, target_type: str, target_id: str) -> dict[str, Any]:
        return self._request("GET", f"/api/protocol/reviews/{target_type}/{target_id}")

    def auto_hire(
        self,
        requester_agent_id: str,
        owner_wallet: str,
        query: str,
        task: str,
        min_rating: float | None = None,
        max_price: str | None = None,
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            "/api/protocol/auto-hire",
            wallet_address=owner_wallet,
            body={
                "requester_agent_id": requester_agent_id,
                "owner_wallet": owner_wallet,
                "query": query,
                "task": task,
                "min_rating": min_rating,
                "max_price": max_price,
            },
        )

    def _request(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
        query: dict[str, Any] | None = None,
        wallet_address: str | None = None,
    ) -> Any:
        url = f"{self.platform_url}{path}"
        if query:
            filtered_query = {key: value for key, value in query.items() if value not in (None, "")}
            if filtered_query:
                url = f"{url}?{parse.urlencode(filtered_query)}"
        data = None
        headers = {"Content-Type": "application/json"}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        if wallet_address:
            headers["X-Wallet-Address"] = wallet_address
        if body is not None:
            data = json.dumps(body).encode("utf-8")
        req = request.Request(url=url, data=data, headers=headers, method=method)
        with request.urlopen(req) as response:
            content = response.read().decode("utf-8")
            if not content:
                return None
            return json.loads(content)
