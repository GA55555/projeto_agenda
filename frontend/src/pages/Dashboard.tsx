import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { Agendamento, Paciente, Responsavel } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { useAsync } from "../utils/useAsync";
import { fmtDataHora, janelaDeHoje } from "../utils/format";

const ROTULO_STATUS: Record<string, string> = {
  agendado: "Agendado",
  realizado: "Realizado",
  cancelado: "Cancelado",
  falta: "Falta",
};

// Visão geral. Compõe 3 GETs existentes (agenda de hoje, pacientes,
// responsáveis) — sem N+1. Primeiro nome do usuário para a saudação.
export function Dashboard() {
  const { user } = useAuth();
  // Landing: uma falha transitória num dos GETs não deve apagar a tela inteira
  // (#1 do review). allSettled -> renderiza o que carregou; o que falhou vira
  // vazio/indisponível.
  const { data, loading, error } = useAsync(async () => {
    const { de, ate } = janelaDeHoje();
    const [a, p, r] = await Promise.allSettled([
      api.agendamentos({ de, ate }),
      api.pacientes(),
      api.responsaveis(),
    ]);
    return {
      ags: a.status === "fulfilled" ? a.value : null,
      pacientes: p.status === "fulfilled" ? p.value : null,
      responsaveis: r.status === "fulfilled" ? r.value : null,
    };
  }, []);

  if (loading) return <p className="muted">Carregando…</p>;
  if (error || !data) return <p className="erro">{error ?? "Erro ao carregar."}</p>;

  const { ags, pacientes, responsaveis } = data as {
    ags: Agendamento[] | null;
    pacientes: Paciente[] | null;
    responsaveis: Responsavel[] | null;
  };
  const nomePorId = new Map((pacientes ?? []).map((p) => [p.id, p.nome]));
  const ativos = pacientes?.filter((p) => p.ativo).length ?? null;
  const primeiroNome = user?.nome?.split(" ")[0];

  return (
    <section>
      <div className="page-header">
        <h2>{primeiroNome ? `Olá, ${primeiroNome}` : "Dashboard"}</h2>
      </div>

      <div className="stats">
        <div className="stat">
          <span className="num">{ags?.length ?? "—"}</span>
          <span className="rot">Atendimentos hoje</span>
        </div>
        <div className="stat">
          <span className="num">{ativos ?? "—"}</span>
          <span className="rot">Pacientes ativos</span>
        </div>
        <div className="stat">
          <span className="num">{responsaveis?.length ?? "—"}</span>
          <span className="rot">Responsáveis</span>
        </div>
      </div>

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
