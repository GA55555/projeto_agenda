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
  nome: string;
  email: string;
}

export interface Tenant {
  id: string;
  nome: string;
  slug: string;
}

// ---- Dominio (espelham os schemas do backend) ----
export interface Paciente {
  id: string;
  nome: string;
  data_nascimento: string;
  sexo: string | null;
  observacoes_gerais: string | null;
  ativo: boolean;
  criado_em: string;
}

export interface Responsavel {
  id: string;
  nome: string;
  cpf: string;
  telefone: string | null;
  email: string | null;
}

export interface Vinculo {
  id: string;
  responsavel_id: string;
  tipo_vinculo: string;
  detem_guarda: boolean;
  principal: boolean;
  responsavel: Responsavel;
}

export interface PacienteDetalhado extends Paciente {
  vinculos: Vinculo[];
}

export interface Agendamento {
  id: string;
  paciente_id: string;
  inicio: string;
  fim: string;
  status: string;
  tipo: string | null;
  observacao: string | null;
  motivo_cancelamento: string | null;
  criado_em: string;
}

export interface Consentimento {
  id: string;
  paciente_id: string;
  responsavel_id: string;
  finalidade_clinica: string;
  limitacoes_acesso: string;
  termo_versao: string;
  concedido_em: string;
  revogado_em: string | null;
}

export interface Evolucao {
  id: string;
  paciente_id: string;
  autor_usuario_id: string;
  texto: string;
  criado_em: string;
  total_chunks: number;
  embeddings_pendentes: number;
}

export interface Rascunho {
  evolucao: string;
  destaques: string[];
  chunks_contexto: number;
}

function qs(params: Record<string, string | undefined>): string {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) if (v) p.set(k, v);
  const s = p.toString();
  return s ? `?${s}` : "";
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

  // ---- Dominio (7b) ----
  pacientes: () => request<Paciente[]>("/pacientes"),
  paciente: (id: string) => request<PacienteDetalhado>(`/pacientes/${id}`),
  agendamentos: (params: { de?: string; ate?: string; paciente_id?: string } = {}) =>
    request<Agendamento[]>(`/agendamentos${qs(params)}`),
  consentimentos: (pacienteId: string) =>
    request<Consentimento[]>(`/consentimentos${qs({ paciente_id: pacienteId })}`),
  evolucoes: (pacienteId: string) =>
    request<Evolucao[]>(`/evolucoes${qs({ paciente_id: pacienteId })}`),

  gerarRascunho: (pacienteId: string, notaDoDia: string) =>
    request<Rascunho>("/llm/evolucoes/rascunho", {
      method: "POST",
      body: JSON.stringify({ paciente_id: pacienteId, nota_do_dia: notaDoDia }),
    }),
  criarEvolucao: (pacienteId: string, texto: string) =>
    request<Evolucao>("/evolucoes", {
      method: "POST",
      body: JSON.stringify({ paciente_id: pacienteId, texto }),
    }),
};
