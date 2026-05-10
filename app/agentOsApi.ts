export type JsonPrimitive = string | number | boolean | null;
export type JsonValue = JsonPrimitive | JsonObject | JsonValue[];
export type JsonObject = { [key: string]: JsonValue };

type FetchLike = (
  input: string,
  init?: {
    method?: string;
    headers?: Record<string, string>;
    body?: any;
  }
) => Promise<{
  ok: boolean;
  status: number;
  json(): Promise<any>;
  text(): Promise<string>;
}>;

export type WalletVerifyPayload = {
  wallet_address: string;
  message: string;
  signature: string;
};

export type InstanceCreatePayload = {
  job_pubkey: string;
  provider_name: string;
  image_ref: string;
  owner_wallet: string;
  agent_wallet: string;
  instance_type?: string;
  security_groups?: string[];
  network_ref?: string;
  user_data?: string;
  provider_config?: JsonObject;
};

export type TaskDispatchPayload = {
  task: string;
  metadata?: JsonObject;
};

export type ImageWorkflowCreatePayload = {
  publisher_wallet: string;
  target_wallet: string;
  provider_name?: string;
  requested_image_name: string;
  source_instance_id?: string;
  source_image_ref?: string;
  metadata?: JsonObject;
};

export type ImageWorkflowConfirmPayload = {
  approved?: boolean;
  created_image_ref?: string;
  note?: string;
};

export type AgentOsUpsertPayload = {
  agent_account?: string;
  name: string;
  description?: string;
  category?: string;
  skill: string;
  pricing_model?: string;
  price_amount?: string;
  currency?: string;
  region?: string;
  cpu_cores?: number;
  memory_gb?: number;
  disk_gb?: number;
  image_ref?: string;
  metadata?: JsonObject;
};

export type MarketSearchOptions = {
  q?: string;
  category?: string;
  skill?: string;
  publisher_wallet?: string;
  min_rating?: number;
  max_price?: string;
  sort_by?: "rating" | "price" | "reviews" | "newest";
};

export type PaymentOrderCreatePayload = {
  agent_wallet: string;
  agent_os_id?: string;
  job_pubkey?: string;
  payment_type?: string;
  amount: string;
  currency?: string;
  chain_name?: string;
  metadata?: JsonObject;
};

export type PaymentOrderFreezePayload = {
  frozen_amount?: string;
  note?: string;
};

export type PaymentOrderConfirmPayload = {
  transaction_signature: string;
  note?: string;
};

export type PaymentOrderSettlePayload = {
  instance_id?: string;
  settled_amount?: string;
  platform_fee?: string;
  publisher_amount?: string;
  refunded_amount?: string;
  note?: string;
};

export type ImageMessagePayload = {
  content: string;
  metadata?: JsonObject;
};

export type AgentSearchOptions = {
  q?: string;
  skill?: string;
  publisher_wallet?: string;
  min_rating?: number;
  sort_by?: "reputation" | "rating" | "jobs" | "publisher_rating";
};

export type ReviewCreatePayload = {
  instance_id: string;
  rating: number;
  comment?: string;
  dimensions?: JsonObject;
};

export type ProtocolHirePayload = {
  agent_os_id: string;
  payment_method?: string;
  job_pubkey: string;
  owner_wallet: string;
  instance_type?: string;
  network_ref?: string;
  security_groups?: string[];
  user_data?: string;
};

export type ProtocolSendTaskPayload = {
  instance_id: string;
  task: string;
  files?: string[];
  metadata?: JsonObject;
};

export type ProtocolAutoHirePayload = {
  requester_agent_id: string;
  owner_wallet: string;
  query: string;
  task: string;
  min_rating?: number;
  max_price?: string;
};

export type AgentOsApiClientOptions = {
  baseUrl?: string;
  fetchImpl?: FetchLike;
  walletAddress?: string;
};

export const DEFAULT_BACKEND_URL = "http://127.0.0.1:8000";

function getFetch(fetchImpl?: FetchLike): FetchLike {
  const resolved = fetchImpl ?? ((globalThis as any).fetch as FetchLike | undefined);
  if (!resolved) {
    throw new Error("当前环境没有可用的 fetch，请显式传入 fetchImpl");
  }
  return resolved;
}

export function buildApiUrl(path: string, baseUrl = DEFAULT_BACKEND_URL) {
  const normalizedBase = baseUrl.replace(/\/$/, "");
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${normalizedBase}${normalizedPath}`;
}

export function buildNotificationsWsUrl(wallet: string, baseUrl = DEFAULT_BACKEND_URL) {
  const httpUrl = buildApiUrl(`/api/notifications/${wallet}`, baseUrl);
  if (httpUrl.startsWith("https://")) {
    return `wss://${httpUrl.slice("https://".length)}`;
  }
  if (httpUrl.startsWith("http://")) {
    return `ws://${httpUrl.slice("http://".length)}`;
  }
  return httpUrl;
}

export function buildFileUploadUrl(instanceId: string, baseUrl = DEFAULT_BACKEND_URL) {
  return buildApiUrl(`/api/instances/${instanceId}/files`, baseUrl);
}

export function buildImageFileUploadUrl(imageId: string, baseUrl = DEFAULT_BACKEND_URL) {
  return buildApiUrl(`/api/images/${imageId}/files`, baseUrl);
}

export function buildFileDownloadUrl(
  instanceId: string,
  filename: string,
  baseUrl = DEFAULT_BACKEND_URL
) {
  return buildApiUrl(
    `/api/instances/${instanceId}/files/${encodeURIComponent(filename)}`,
    baseUrl
  );
}

export function buildImageFileDownloadUrl(
  imageId: string,
  filename: string,
  baseUrl = DEFAULT_BACKEND_URL
) {
  return buildApiUrl(`/api/images/${imageId}/files/${encodeURIComponent(filename)}`, baseUrl);
}

async function requestJson<T>(
  path: string,
  options: AgentOsApiClientOptions & {
    method?: string;
    body?: JsonObject | JsonValue[] | string;
    headers?: Record<string, string>;
  } = {}
): Promise<T> {
  const fetchImpl = getFetch(options.fetchImpl);
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers ?? {}),
  };

  if (options.walletAddress) {
    headers["X-Wallet-Address"] = options.walletAddress;
  }

  const response = await fetchImpl(buildApiUrl(path, options.baseUrl), {
    method: options.method ?? "GET",
    headers,
    body:
      typeof options.body === "string" || options.body === undefined
        ? options.body
        : JSON.stringify(options.body),
  });

  if (!response.ok) {
    throw new Error(`Agent OS API 请求失败: ${response.status} ${await response.text()}`);
  }

  return response.json() as Promise<T>;
}

function appendQuery(path: string, query?: Record<string, string | number | undefined>) {
  if (!query) {
    return path;
  }
  const searchParams = new URLSearchParams();
  Object.entries(query).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      searchParams.set(key, String(value));
    }
  });
  const queryString = searchParams.toString();
  return queryString ? `${path}?${queryString}` : path;
}

export function createAgentOsApiClient(options: AgentOsApiClientOptions = {}) {
  return {
    verifyWallet(payload: WalletVerifyPayload) {
      return requestJson("/api/wallet/verify", {
        ...options,
        method: "POST",
        body: payload,
      });
    },
    listAgents(search?: AgentSearchOptions) {
      return requestJson(
        appendQuery("/api/agents", {
          q: search?.q,
          skill: search?.skill,
          publisher_wallet: search?.publisher_wallet,
          min_rating: search?.min_rating,
          sort_by: search?.sort_by,
        }),
        options
      );
    },
    getAgent(agentPubkey: string) {
      return requestJson(`/api/agents/${agentPubkey}`, options);
    },
    createInstance(payload: InstanceCreatePayload) {
      return requestJson("/api/instances", {
        ...options,
        method: "POST",
        walletAddress: payload.owner_wallet,
        body: payload,
      });
    },
    getInstance(instanceId: string) {
      return requestJson(`/api/instances/${instanceId}`, options);
    },
    destroyInstance(instanceId: string) {
      return requestJson(`/api/instances/${instanceId}`, {
        ...options,
        method: "DELETE",
      });
    },
    sendTask(instanceId: string, payload: TaskDispatchPayload) {
      return requestJson(`/api/instances/${instanceId}/task`, {
        ...options,
        method: "POST",
        body: payload,
      });
    },
    listNotifications(wallet: string) {
      return requestJson(`/api/notifications/${wallet}`, options);
    },
    listHired() {
      return requestJson("/api/hired", options);
    },
    createImageWorkflowRequest(payload: ImageWorkflowCreatePayload) {
      return requestJson("/api/image-workflows/requests", {
        ...options,
        method: "POST",
        body: payload,
      });
    },
    confirmImageWorkflowRequest(workflowId: string, payload: ImageWorkflowConfirmPayload) {
      return requestJson(`/api/image-workflows/requests/${workflowId}/confirm`, {
        ...options,
        method: "POST",
        body: payload,
      });
    },
    getImageWorkflowRequest(workflowId: string) {
      return requestJson(`/api/image-workflows/requests/${workflowId}`, options);
    },
    listMarketAgentOs(search?: MarketSearchOptions) {
      return requestJson(
        appendQuery("/api/market/agent-os", {
          q: search?.q,
          category: search?.category,
          skill: search?.skill,
          publisher_wallet: search?.publisher_wallet,
          min_rating: search?.min_rating,
          max_price: search?.max_price,
          sort_by: search?.sort_by,
        }),
        options
      );
    },
    getMarketAgentOs(agentOsId: string) {
      return requestJson(`/api/market/agent-os/${agentOsId}`, options);
    },
    registerAgentOs(payload: AgentOsUpsertPayload) {
      return requestJson("/api/publishers/agent-os", {
        ...options,
        method: "POST",
        body: payload,
      });
    },
    updateAgentOs(agentOsId: string, payload: AgentOsUpsertPayload) {
      return requestJson(`/api/publishers/agent-os/${agentOsId}`, {
        ...options,
        method: "PUT",
        body: payload,
      });
    },
    listMyAgentOs() {
      return requestJson("/api/publishers/agent-os", options);
    },
    getPublisherDashboard() {
      return requestJson("/api/publishers/dashboard", options);
    },
    listPublisherSettlements() {
      return requestJson("/api/publishers/settlements", options);
    },
    listMyImages() {
      return requestJson("/api/images", options);
    },
    getMyImage(imageId: string) {
      return requestJson(`/api/images/${imageId}`, options);
    },
    sendImageMessage(imageId: string, payload: ImageMessagePayload) {
      return requestJson(`/api/images/${imageId}/messages`, {
        ...options,
        method: "POST",
        body: payload,
      });
    },
    listImageMessages(imageId: string) {
      return requestJson(`/api/images/${imageId}/messages`, options);
    },
    createPaymentOrder(payload: PaymentOrderCreatePayload) {
      return requestJson("/api/payments/orders", {
        ...options,
        method: "POST",
        body: payload,
      });
    },
    confirmPaymentOrder(orderId: string, payload: PaymentOrderConfirmPayload) {
      return requestJson(`/api/payments/orders/${orderId}/confirm`, {
        ...options,
        method: "POST",
        body: payload,
      });
    },
    freezePaymentOrder(orderId: string, payload: PaymentOrderFreezePayload) {
      return requestJson(`/api/payments/orders/${orderId}/freeze`, {
        ...options,
        method: "POST",
        body: payload,
      });
    },
    settlePaymentOrder(orderId: string, payload: PaymentOrderSettlePayload) {
      return requestJson(`/api/payments/orders/${orderId}/settle`, {
        ...options,
        method: "POST",
        body: payload,
      });
    },
    getPaymentOrder(orderId: string) {
      return requestJson(`/api/payments/orders/${orderId}`, options);
    },
    fireAgentOs(instanceId: string) {
      return requestJson(`/api/instances/${instanceId}/fire`, {
        ...options,
        method: "POST",
      });
    },
    createAgentOsReview(payload: ReviewCreatePayload) {
      return requestJson("/api/reviews/agent-os", {
        ...options,
        method: "POST",
        body: payload,
      });
    },
    createPublisherReview(payload: ReviewCreatePayload) {
      return requestJson("/api/reviews/publishers", {
        ...options,
        method: "POST",
        body: payload,
      });
    },
    getAgentOsReviews(agentOsId: string) {
      return requestJson(`/api/reviews/agent-os/${agentOsId}`, options);
    },
    getPublisherReviews(publisherWallet: string) {
      return requestJson(`/api/reviews/publishers/${publisherWallet}`, options);
    },
    protocolSearchAgentOs(
      search?: Pick<MarketSearchOptions, "category" | "skill" | "min_rating" | "max_price"> & {
        query?: string;
      }
    ) {
      return requestJson(
        appendQuery("/api/protocol/search-agent-os", {
          query: search?.query,
          category: search?.category,
          skill: search?.skill,
          min_rating: search?.min_rating,
          max_price: search?.max_price,
        }),
        options
      );
    },
    protocolHireAgentOs(payload: ProtocolHirePayload) {
      return requestJson("/api/protocol/hire-agent-os", {
        ...options,
        method: "POST",
        walletAddress: payload.owner_wallet,
        body: payload,
      });
    },
    protocolSendTask(payload: ProtocolSendTaskPayload) {
      return requestJson("/api/protocol/send-task", {
        ...options,
        method: "POST",
        body: payload,
      });
    },
    protocolFireAgentOs(instanceId: string) {
      return requestJson(`/api/protocol/fire-agent-os/${instanceId}`, {
        ...options,
        method: "POST",
      });
    },
    protocolListHired() {
      return requestJson("/api/protocol/list-hired", options);
    },
    protocolRateAgentOs(payload: ReviewCreatePayload) {
      return requestJson("/api/protocol/rate-agent-os", {
        ...options,
        method: "POST",
        body: payload,
      });
    },
    protocolRatePublisher(payload: ReviewCreatePayload) {
      return requestJson("/api/protocol/rate-publisher", {
        ...options,
        method: "POST",
        body: payload,
      });
    },
    protocolGetReviews(targetType: "agent_os" | "publisher", targetId: string) {
      return requestJson(`/api/protocol/reviews/${targetType}/${targetId}`, options);
    },
    protocolAutoHire(payload: ProtocolAutoHirePayload) {
      return requestJson("/api/protocol/auto-hire", {
        ...options,
        method: "POST",
        walletAddress: payload.owner_wallet,
        body: payload,
      });
    },
  };
}

export function createAgentMarketClient(options: AgentOsApiClientOptions = {}) {
  const api = createAgentOsApiClient(options);
  return {
    search(query: string, search: Omit<MarketSearchOptions, "q"> = {}) {
      return api.protocolSearchAgentOs({
        query,
        category: search.category,
        skill: search.skill,
        min_rating: search.min_rating,
        max_price: search.max_price,
      });
    },
    hire(payload: ProtocolHirePayload) {
      return api.protocolHireAgentOs(payload);
    },
    sendTask(payload: ProtocolSendTaskPayload) {
      return api.protocolSendTask(payload);
    },
    fire(instanceId: string) {
      return api.protocolFireAgentOs(instanceId);
    },
    listHired() {
      return api.protocolListHired();
    },
    rateAgentOs(payload: ReviewCreatePayload) {
      return api.protocolRateAgentOs(payload);
    },
    ratePublisher(payload: ReviewCreatePayload) {
      return api.protocolRatePublisher(payload);
    },
    getReviews(targetType: "agent_os" | "publisher", targetId: string) {
      return api.protocolGetReviews(targetType, targetId);
    },
    autoHire(payload: ProtocolAutoHirePayload) {
      return api.protocolAutoHire(payload);
    },
  };
}
