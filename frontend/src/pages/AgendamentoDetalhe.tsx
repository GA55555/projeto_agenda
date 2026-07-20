import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api/client";
import type { Agendamento, Paciente } from "../api/client";
import { useAsync } from "../utils/useAsync";
import { fmtDataHora } from "../utils/format";
import { useAcao } from "../utils/useAcao";
import { rotuloStatus } from "../utils/status";

// Detalhe de um atendimento — o "abrir o agendamento" para desfazer a
// recorrência (Fase 7f). Acessível a partir da agenda.
export function AgendamentoDetalhe() {
  const { id = "" } = useParams();
  const navigate = useNavigate();

  const { data, loading, error } = useAsync(async () => {
    const ag = await api.agendamento(id);
    const pac = await api.paciente(ag.paciente_id).catch(() => null);
    return { ag, pac };
  }, [id]);

  const { ocupado, acaoErro, executar } = useAcao();

  function desfazer(ag: Agendamento) {
    if (
      !window.confirm(
        "Desfazer a recorrência mantém ESTE atendimento e remove as demais repetições futuras " +
          "ainda agendadas. Os já realizados permanecem. Continuar?",
      )
    ) {
      return;
    }
    void executar(async () => {
      const { removidos } = await api.desfazerRecorrencia(ag.id);
      window.alert(`Recorrência desfeita: ${removidos} repetição(ões) futura(s) removida(s).`);
      navigate("/agenda", { replace: true });
    });
  }

  if (loading) return <p className="muted">Carregando…</p>;
  if (error || !data) return <p className="erro">{error ?? "Erro ao carregar."}</p>;

  const { ag, pac } = data as { ag: Agendamento; pac: Paciente | null };

  return (
    <section>
      <Link className="voltar muted" to="/agenda">
        ← Agenda
      </Link>
      <div className="page-header">
        <h2>Atendimento</h2>
        <span className={`tag tag-${ag.status}`}>{rotuloStatus(ag.status)}</span>
      </div>

      <div className="card">
        <dl className="dados">
          <div>
            <dt>Paciente</dt>
            <dd>
              <Link to={`/pacientes/${ag.paciente_id}`}>{pac?.nome ?? "—"}</Link>
            </dd>
          </div>
          <div>
            <dt>Início</dt>
            <dd>{fmtDataHora(ag.inicio)}</dd>
          </div>
          <div>
            <dt>Fim</dt>
            <dd>{fmtDataHora(ag.fim)}</dd>
          </div>
          <div>
            <dt>Tipo</dt>
            <dd>{ag.tipo || "—"}</dd>
          </div>
          <div>
            <dt>Observação</dt>
            <dd>{ag.observacao || "—"}</dd>
          </div>
          <div>
            <dt>Recorrência</dt>
            <dd>{ag.serie_id ? "Faz parte de uma série" : "Atendimento avulso"}</dd>
          </div>
          {ag.status === "cancelado" && ag.motivo_cancelamento && (
            <div>
              <dt>Motivo do cancelamento</dt>
              <dd>{ag.motivo_cancelamento}</dd>
            </div>
          )}
        </dl>
      </div>

      {ag.serie_id && (
        <div className="card">
          <h3>Recorrência</h3>
          <p className="muted">
            Este atendimento se repete automaticamente. Desfazer remove as ocorrências futuras ainda
            agendadas (as já realizadas ficam no histórico).
          </p>
          {acaoErro && <p className="erro">{acaoErro}</p>}
          <button className="secundario" disabled={ocupado} onClick={() => void desfazer(ag)}>
            Desfazer recorrência
          </button>
        </div>
      )}
    </section>
  );
}
