const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

class ApiError extends Error {
  constructor(
    public status: number,
    message: string
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token =
    typeof window !== "undefined" ? localStorage.getItem("token") : null;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, body.detail || res.statusText);
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}

// ── Auth ──
export const api = {
  auth: {
    register: (data: { email: string; name: string; password: string }) =>
      request<{ access_token: string; token_type: string }>(
        "/api/v1/auth/register",
        { method: "POST", body: JSON.stringify(data) }
      ),
    login: (data: { email: string; password: string }) =>
      request<{ access_token: string; token_type: string }>(
        "/api/v1/auth/login",
        { method: "POST", body: JSON.stringify(data) }
      ),
    google: (data: { credential: string }) =>
      request<{ access_token: string; token_type: string }>(
        "/api/v1/auth/google",
        { method: "POST", body: JSON.stringify(data) }
      ),
    me: () => request<User>("/api/v1/auth/me"),
  },

  // ── Organizations ──
  organizations: {
    list: () => request<Organization[]>("/api/v1/organizations"),
    get: (id: string) => request<Organization>(`/api/v1/organizations/${id}`),
    create: (data: { name: string }) =>
      request<Organization>("/api/v1/organizations", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    update: (id: string, data: { name: string }) =>
      request<Organization>(`/api/v1/organizations/${id}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
    delete: (id: string) =>
      request<void>(`/api/v1/organizations/${id}`, { method: "DELETE" }),
    members: (id: string) =>
      request<OrgMember[]>(`/api/v1/organizations/${id}/members`),
    addMember: (id: string, data: { email: string; role: string }) =>
      request<OrgMember>(`/api/v1/organizations/${id}/members`, {
        method: "POST",
        body: JSON.stringify(data),
      }),
    updateMember: (id: string, memberId: string, data: { role: string }) =>
      request<OrgMember>(`/api/v1/organizations/${id}/members/${memberId}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
    deleteMember: (id: string, memberId: string) =>
      request<void>(`/api/v1/organizations/${id}/members/${memberId}`, {
        method: "DELETE",
      }),
  },

  // ── Products ──
  products: {
    list: (orgId: string) =>
      request<Product[]>(`/api/v1/organizations/${orgId}/products`),
    get: (orgId: string, id: string) =>
      request<Product>(`/api/v1/organizations/${orgId}/products/${id}`),
    create: (orgId: string, data: { name: string; description?: string }) =>
      request<Product>(`/api/v1/organizations/${orgId}/products`, {
        method: "POST",
        body: JSON.stringify(data),
      }),
    update: (
      orgId: string,
      id: string,
      data: { name?: string; description?: string }
    ) =>
      request<Product>(`/api/v1/organizations/${orgId}/products/${id}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
    delete: (orgId: string, id: string) =>
      request<void>(`/api/v1/organizations/${orgId}/products/${id}`, {
        method: "DELETE",
      }),
  },

  // ── Configs ──
  configs: {
    list: (productId: string) =>
      request<Config[]>(`/api/v1/products/${productId}/configs`),
    get: (productId: string, id: string) =>
      request<Config>(`/api/v1/products/${productId}/configs/${id}`),
    create: (productId: string, data: { name: string; description?: string }) =>
      request<Config>(`/api/v1/products/${productId}/configs`, {
        method: "POST",
        body: JSON.stringify(data),
      }),
    update: (
      productId: string,
      id: string,
      data: { name?: string; description?: string }
    ) =>
      request<Config>(`/api/v1/products/${productId}/configs/${id}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
    delete: (productId: string, id: string) =>
      request<void>(`/api/v1/products/${productId}/configs/${id}`, {
        method: "DELETE",
      }),
  },

  // ── Environments ──
  environments: {
    list: (productId: string) =>
      request<Environment[]>(`/api/v1/products/${productId}/environments`),
    create: (productId: string, data: { name: string; color?: string }) =>
      request<Environment>(`/api/v1/products/${productId}/environments`, {
        method: "POST",
        body: JSON.stringify(data),
      }),
    update: (
      productId: string,
      id: string,
      data: { name?: string; color?: string }
    ) =>
      request<Environment>(`/api/v1/products/${productId}/environments/${id}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
    delete: (productId: string, id: string) =>
      request<void>(`/api/v1/products/${productId}/environments/${id}`, {
        method: "DELETE",
      }),
  },

  // ── Settings (Feature Flags) ──
  settings: {
    list: (configId: string) =>
      request<Setting[]>(`/api/v1/configs/${configId}/settings`),
    get: (configId: string, id: string) =>
      request<Setting>(`/api/v1/configs/${configId}/settings/${id}`),
    create: (
      configId: string,
      data: { name: string; key: string; setting_type: string; hint?: string }
    ) =>
      request<Setting>(`/api/v1/configs/${configId}/settings`, {
        method: "POST",
        body: JSON.stringify(data),
      }),
    update: (
      configId: string,
      id: string,
      data: { name?: string; hint?: string; order?: number }
    ) =>
      request<Setting>(`/api/v1/configs/${configId}/settings/${id}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
    delete: (configId: string, id: string) =>
      request<void>(`/api/v1/configs/${configId}/settings/${id}`, {
        method: "DELETE",
      }),
    getValue: (configId: string, settingId: string, envId: string) =>
      request<SettingValue>(
        `/api/v1/configs/${configId}/settings/${settingId}/values/${envId}`
      ),
    updateValue: (
      configId: string,
      settingId: string,
      envId: string,
      data: SettingValueUpdate
    ) =>
      request<SettingValue>(
        `/api/v1/configs/${configId}/settings/${settingId}/values/${envId}`,
        { method: "PUT", body: JSON.stringify(data) }
      ),
  },

  // ── Segments ──
  segments: {
    list: (productId: string) =>
      request<Segment[]>(`/api/v1/products/${productId}/segments`),
    create: (productId: string, data: SegmentCreate) =>
      request<Segment>(`/api/v1/products/${productId}/segments`, {
        method: "POST",
        body: JSON.stringify(data),
      }),
    update: (productId: string, id: string, data: SegmentCreate) =>
      request<Segment>(`/api/v1/products/${productId}/segments/${id}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
    delete: (productId: string, id: string) =>
      request<void>(`/api/v1/products/${productId}/segments/${id}`, {
        method: "DELETE",
      }),
  },

  // ── Tags ──
  tags: {
    list: (productId: string) =>
      request<Tag[]>(`/api/v1/products/${productId}/tags`),
    create: (productId: string, data: { name: string; color?: string }) =>
      request<Tag>(`/api/v1/products/${productId}/tags`, {
        method: "POST",
        body: JSON.stringify(data),
      }),
    delete: (productId: string, id: string) =>
      request<void>(`/api/v1/products/${productId}/tags/${id}`, {
        method: "DELETE",
      }),
  },

  // ── SDK Keys ──
  sdkKeys: {
    list: (productId: string, configId?: string) => {
      const q = new URLSearchParams();
      if (configId) q.set("config_id", configId);
      const qs = q.toString();
      return request<SDKKeySummary[]>(
        `/api/v1/products/${productId}/sdk-keys${qs ? `?${qs}` : ""}`
      );
    },
    create: (
      productId: string,
      data: { config_id: string; environment_id: string }
    ) =>
      request<SDKKeySecret>(`/api/v1/products/${productId}/sdk-keys`, {
        method: "POST",
        body: JSON.stringify(data),
      }),
    revoke: (productId: string, sdkKeyId: string) =>
      request<SDKKeySummary>(
        `/api/v1/products/${productId}/sdk-keys/${sdkKeyId}/revoke`,
        {
          method: "POST",
        }
      ),
    delete: (productId: string, sdkKeyId: string) =>
      request<void>(`/api/v1/products/${productId}/sdk-keys/${sdkKeyId}`, {
        method: "DELETE",
      }),
  },

  // ── Audit Log ──
  auditLog: {
    list: (
      orgId: string,
      params?: { entity_type?: string; limit?: number; offset?: number }
    ) => {
      const q = new URLSearchParams();
      if (params?.entity_type) q.set("entity_type", params.entity_type);
      if (params?.limit) q.set("limit", String(params.limit));
      if (params?.offset) q.set("offset", String(params.offset));
      const qs = q.toString();
      return request<AuditLogEntry[]>(
        `/api/v1/organizations/${orgId}/audit-log${qs ? `?${qs}` : ""}`
      );
    },
  },

  // ── Webhooks ──
  webhooks: {
    list: (productId: string) =>
      request<Webhook[]>(`/api/v1/products/${productId}/webhooks`),
    create: (
      productId: string,
      data: {
        url: string;
        config_id?: string;
        environment_id?: string;
        enabled?: boolean;
      }
    ) =>
      request<Webhook>(`/api/v1/products/${productId}/webhooks`, {
        method: "POST",
        body: JSON.stringify(data),
      }),
    delete: (productId: string, id: string) =>
      request<void>(`/api/v1/products/${productId}/webhooks/${id}`, {
        method: "DELETE",
      }),
  },
};

export { ApiError };
