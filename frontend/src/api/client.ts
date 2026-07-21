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
  data_nascimento: string | null;
  telefone: string | null;
  email: string | null;
  endereco: string | null;
  criado_em: string;
}

// ---- Payloads de criação (7c.2) ----
export interface AgendamentoCreate {
  paciente_id: string;
  inicio: string; // ISO com timezone
  fim: string;
  tipo?: string;
  observacao?: string;
  recorrencia?: { frequencia: Frequencia };
}

export interface ResponsavelCreate {
  nome: string;
  cpf: string;
  data_nascimento?: string;
  telefone?: string;
  email?: string;
  endereco?: string;
}

// PATCH /responsaveis só aceita estes campos (ResponsavelUpdate no backend).
export interface ResponsavelUpdate {
  nome?: string;
  telefone?: string;
  email?: string;
}

export interface VinculoCreate {
  responsavel_id: string;
  tipo_vinculo: string;
  detem_guarda?: boolean;
  principal?: boolean;
}

export interface ConsentimentoCreate {
  responsavel_id: string;
  finalidade_clinica: string;
  limitacoes_acesso: string;
  termo_versao: string;
  termo_texto: string;
}

export interface PacienteCreate {
  nome: string;
  data_nascimento: string;
  sexo?: string;
  observacoes_gerais?: string;
  vinculos: VinculoCreate[];
  consentimento: ConsentimentoCreate;
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
  serie_id: string | null; // != null -> faz parte de uma recorrência (7f)
  criado_em: string;
}

// Resposta do POST /agendamentos: o criado + resumo da série (7f).
export interface AgendamentoCriado extends Agendamento {
  serie_criados: number;
  serie_pulados_datas: string[]; // ISO dos inícios pulados por conflito
}

export type Frequencia = "semanal" | "quinzenal" | "mensal";

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
  agendamento_id: string | null; // null nas legadas (antes da 7e)
  data_atendimento: string | null; // inicio do agendamento vinculado
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

// Dashboard dividido em DIA e MÊS (7f) — seletores independentes.
export interface ResumoDia {
  dia: string; // YYYY-MM-DD selecionado
  dia_inicio: string; // instante ISO — início do dia no fuso da clínica
  dia_fim: string; // instante ISO — fim do dia (exclusivo)
  atendimentos_dia: number;
  realizados_dia: number;
  faltas_dia: number;
  cancelados_dia: number;
}

export interface ResumoMes {
  mes: string; // YYYY-MM selecionado
  desde: string; // YYYY-MM da criação da conta (limite do seletor de mês)
  pacientes_ativos: number;
  responsaveis: number;
  realizados_mes: number;
  faltas_mes: number;
  cancelados_mes: number;
  taxa_comparecimento_mes: number | null;
  dias_com_atendimento_mes: number;
  evolucoes_mes: number;
  pacientes_sem_tcle: number;
  pacientes_sem_agendamento_futuro: number;
  atendimentos_proxima_semana: number;
}

// Edição do próprio perfil (PATCH /auth/me). Só o campo enviado muda.
// Trocar o e-mail (identificador de login) exige a senha atual (re-auth).
export interface PerfilUpdate {
  nome?: string;
  email?: string;
  senha_atual?: string;
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

  // ---- Perfil (7c) ----
  atualizarPerfil: (d: PerfilUpdate) =>
    request<Me>("/auth/me", { method: "PATCH", body: JSON.stringify(d) }),
  trocarSenha: (senha_atual: string, senha_nova: string) =>
    request<void>("/auth/me/senha", {
      method: "POST",
      body: JSON.stringify({ senha_atual, senha_nova }),
    }),

  // ---- Dashboard (7c/7e/7f) ----
  resumoDia: (dia: string) => request<ResumoDia>(`/dashboard/dia${qs({ dia })}`),
  resumoMes: (mes: string) => request<ResumoMes>(`/dashboard/mes${qs({ mes })}`),
  calendario: (mes: string) => request<Record<string, number>>(`/dashboard/calendario${qs({ mes })}`),

  // ---- Dominio (7b) ----
  pacientes: () => request<Paciente[]>("/pacientes"),
  paciente: (id: string) => request<PacienteDetalhado>(`/pacientes/${id}`),
  agendamentos: (params: { de?: string; ate?: string; paciente_id?: string } = {}) =>
    request<Agendamento[]>(`/agendamentos${qs(params)}`),
  agendamento: (id: string) => request<Agendamento>(`/agendamentos/${id}`),
  consentimentos: (pacienteId: string) =>
    request<Consentimento[]>(`/consentimentos${qs({ paciente_id: pacienteId })}`),
  evolucoes: (pacienteId: string) =>
    request<Evolucao[]>(`/evolucoes${qs({ paciente_id: pacienteId })}`),

  // ---- Cadastros (7c.2) ----
  responsaveis: () => request<Responsavel[]>("/responsaveis"),
  responsavel: (id: string) => request<Responsavel>(`/responsaveis/${id}`),
  criarResponsavel: (d: ResponsavelCreate) =>
    request<Responsavel>("/responsaveis", { method: "POST", body: JSON.stringify(d) }),
  atualizarResponsavel: (id: string, d: ResponsavelUpdate) =>
    request<Responsavel>(`/responsaveis/${id}`, { method: "PATCH", body: JSON.stringify(d) }),
  criarAgendamento: (d: AgendamentoCreate) =>
    request<AgendamentoCriado>("/agendamentos", { method: "POST", body: JSON.stringify(d) }),
  desfazerRecorrencia: (id: string) =>
    request<{ removidos: number }>(`/agendamentos/${id}/desfazer-recorrencia`, { method: "POST" }),
  // Ações na agenda (7c): PATCH muda status; cancelar é rota própria (soft, motivo).
  mudarStatusAgendamento: (id: string, status: string) =>
    request<Agendamento>(`/agendamentos/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    }),
  cancelarAgendamento: (id: string, motivo?: string) =>
    request<Agendamento>(`/agendamentos/${id}/cancelar`, {
      method: "POST",
      body: JSON.stringify({ motivo: motivo || null }),
    }),
  // Apagar corrige ERRO de lançamento (só status 'agendado'; auditado).
  apagarAgendamento: (id: string) =>
    request<void>(`/agendamentos/${id}`, { method: "DELETE" }),
  criarPaciente: (d: PacienteCreate) =>
    request<PacienteDetalhado>("/pacientes", { method: "POST", body: JSON.stringify(d) }),
  // Arquivar/reativar = PATCH ativo (auditado no backend). Apagar só é
  // possível SEM prontuário (CFP 5 anos) — 409 caso contrário.
  atualizarPaciente: (id: string, d: { ativo?: boolean; observacoes_gerais?: string }) =>
    request<Paciente>(`/pacientes/${id}`, { method: "PATCH", body: JSON.stringify(d) }),
  apagarPaciente: (id: string) => request<void>(`/pacientes/${id}`, { method: "DELETE" }),

  gerarRascunho: (pacienteId: string, notaDoDia: string) =>
    request<Rascunho>("/llm/evolucoes/rascunho", {
      method: "POST",
      body: JSON.stringify({ paciente_id: pacienteId, nota_do_dia: notaDoDia }),
    }),
  criarEvolucao: (pacienteId: string, agendamentoId: string, texto: string) =>
    request<Evolucao>("/evolucoes", {
      method: "POST",
      body: JSON.stringify({ paciente_id: pacienteId, agendamento_id: agendamentoId, texto }),
    }),
};
