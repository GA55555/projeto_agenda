import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { Agendamento, Paciente, Resumo } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { useAsync } from "../utils/useAsync";
import { fmtDataHora, janelaDeHoje } from "../utils/format";

const ROTULO_STATUS: Record<string, string> = {
  agendado: "Agendado",
  realizado: "Realizado",
  cancelado: "Cancelado",
  falta: "Falta",
};

function pct(taxa: number | null): string {
  return taxa === null ? "—" : `${Math.round(taxa * 100)}%`;
}

// Visão geral. Contadores agregados no backend (GET /dashboard/resumo, sem N+1)
// + a lista da agenda de hoje (com nomes dos pacientes). allSettled: uma falha
// transitória num dos GETs não apaga a tela inteira.
export function Dashboard() {
  const { user } = useAuth();
  const { data, loading, error } = useAsync(async () => {
    const { de, ate } = janelaDeHoje();
    const [r, a, p] = await Promise.allSettled([
      api.resumo(),
      api.agendamentos({ de, ate }),
      api.pacientes(),
    ]);
    return {
      resumo: r.status === "fulfilled" ? r.value : null,
      ags: a.status === "fulfilled" ? a.value : null,
      pacientes: p.status === "fulfilled" ? p.value : null,
    };
  }, []);

  if (loading) return <p className="muted">Carregando…</p>;
  if (error || !data) return <p className="erro">{error ?? "Erro ao carregar."}</p>;

  const { resumo, ags, pacientes } = data as {
    resumo: Resumo | null;
    ags: Agendamento[] | null;
    pacientes: Paciente[] | null;
  };
  const nomePorId = new Map((pacientes ?? []).map((p) => [p.id, p.nome]));
  const primeiroNome = user?.nome?.split(" ")[0];
  const n = (v: number | undefined) => v ?? "—";
  // "Atendimentos hoje" deriva da MESMA busca que renderiza a lista logo
  // abaixo (mesma janela/fuso do browser; exclui cancelados) — tile e lista
  // nunca se contradizem. O valor do resumo (fuso da clinica) fica de fallback
  // se a busca da agenda falhar.
  const atendimentosHoje =
    ags !== null
      ? ags.filter((a) => a.status !== "cancelado").length
      : resumo?.atendimentos_hoje;

  return (
    <section>
      <div className="page-header">
        <h2>{primeiroNome ? `Olá, ${primeiroNome}` : "Dashboard"}</h2>
      </div>

      {resumo === null && (
        <p className="aviso">Não foi possível carregar os indicadores agora.</p>
      )}

      {/* ---- Hoje ---- */}
      <div className="stats">
        <div className="stat">
          <span className="num">{n(atendimentosHoje)}</span>
          <span className="rot">Atendimentos hoje</span>
        </div>
        <div className="stat">
          <span className="num">{n(resumo?.pacientes_ativos)}</span>
          <span className="rot">Pacientes ativos</span>
        </div>
        <div className="stat">
          <span className="num">{n(resumo?.responsaveis)}</span>
          <span className="rot">Responsáveis</span>
        </div>
      </div>

      {/* ---- Este mês (gestão) ---- */}
      <h3 className="titulo-bloco">Este mês</h3>
      <div className="stats">
        <div className="stat">
          <span className="num">{n(resumo?.realizados_mes)}</span>
          <span className="rot">Atendimentos realizados</span>
        </div>
        <div className="stat">
          <span className="num">{n(resumo?.faltas_mes)}</span>
          <span className="rot">Faltas</span>
        </div>
        <div className="stat">
          <span className="num">{resumo ? pct(resumo.taxa_comparecimento_mes) : "—"}</span>
          <span className="rot">Comparecimento</span>
        </div>
        <div className="stat">
          <span className="num">{n(resumo?.dias_com_atendimento_mes)}</span>
          <span className="rot">Dias com atendimento</span>
        </div>
        <div className="stat">
          <span className="num">{n(resumo?.evolucoes_mes)}</span>
          <span className="rot">Evoluções registradas</span>
        </div>
      </div>

      {/* ---- Pendências / atenção ---- */}
      <h3 className="titulo-bloco">Pendências</h3>
      <div className="stats">
        <div className={`stat${resumo && resumo.pacientes_sem_tcle > 0 ? " alerta" : ""}`}>
          <span className="num">{n(resumo?.pacientes_sem_tcle)}</span>
          <span className="rot">Pacientes sem TCLE ativo</span>
        </div>
        <div
          className={`stat${resumo && resumo.pacientes_sem_agendamento_futuro > 0 ? " alerta" : ""}`}
        >
          <span className="num">{n(resumo?.pacientes_sem_agendamento_futuro)}</span>
          <span className="rot">Sem próximo atendimento</span>
        </div>
        <div className="stat">
          <span className="num">{n(resumo?.atendimentos_proxima_semana)}</span>
          <span className="rot">Atendimentos na próxima semana</span>
        </div>
      </div>

      {/* ---- Agenda de hoje ---- */}
      <div className="cabecalho-secao">
        <h3>Agenda de hoje</h3>
        <Link to="/agenda">Ver agenda →</Link>
      </div>
      <div className="card">
        {ags === null ? (
          <p className="muted">Não foi possível carregar a agenda agora.</p>
        ) : ags.length === 0 ? (
          <p className="vazio">Nenhum atendimento hoje.</p>
        ) : (
          <ul className="lista">
            {ags.map((a) => (
              <li key={a.id}>
                <span className="muted">{fmtDataHora(a.inicio)}</span> —{" "}
                <Link to={`/pacientes/${a.paciente_id}`}>{nomePorId.get(a.paciente_id) ?? "—"}</Link>{" "}
                <span className={`tag tag-${a.status}`}>{ROTULO_STATUS[a.status] ?? a.status}</span>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="acoes">
        <Link className="botao" to="/agenda/novo">
          Novo agendamento
        </Link>
        <Link className="botao secundario" to="/pacientes/novo">
          Novo paciente
        </Link>
      </div>
    </section>
  );
}
