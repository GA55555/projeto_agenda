// Cliente de API central. Mesma origem (Nginx faz proxy de /api), entao os
// cookies httpOnly vao automaticamente com `credentials: "include"`. O JS NUNCA
// le o token (esta no cookie httpOnly) — resistente a XSS (Fase 7, §2.2/§4.1).

const BASE = "/api/v1";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

// Handler global de sessao expirada: qualquer 401 (JWT de 30 min vence enquanto
// navega) avisa a app p/ voltar ao login, em vez de deixar a tela quebrada.
let onUnauthorized: (() => void) | null = null;
export function setUnauthorizedHandler(fn: (() => void) | null): void {
  onUnauthorized = fn;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(BASE + path, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    ...init,
  });
  if (!resp.ok) {
    if (resp.status === 401) onUnauthorized?.();
    let detail = resp.statusText;
    try {
      const body = await resp.json();
      if (typeof body?.detail === "string") detail = body.detail;
    } catch {
      /* corpo nao-JSON */
    }
    throw new ApiError(resp.status, detail);
  }
  if (resp.status === 204) return undefined as T;
  return (await resp.json()) as T;
}

export interface Me {
  id: string;
  tenant_id: string;
  papel: string;
}

export interface Tenant {
  id: string;
  nome: string;
  slug: string;
}

export const api = {
  async login(username: string, password: string): Promise<void> {
    // OAuth2PasswordRequestForm exige form-urlencoded (nao JSON).
    const body = new URLSearchParams({ username, password });
    const resp = await fetch(BASE + "/auth/login", {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body,
    });
    if (!resp.ok) {
      throw new ApiError(resp.status, resp.status === 401 ? "Credenciais invalidas" : "Falha no login");
    }
    // Ignoramos o corpo (token) de proposito: a sessao vive no cookie httpOnly.
  },

  logout: () => request<{ detail: string }>("/auth/logout", { method: "POST" }),
  me: () => request<Me>("/auth/me"),
  tenantAtual: () => request<Tenant>("/tenants/atual"),
};
