import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api/client";
import type { Agendamento, Paciente } from "../api/client";
import { useAsync } from "../utils/useAsync";
import { fmtDataHora } from "../utils/format";
import { useAcao } from "../utils/useAcao";
import { rotuloStatus } from "../utils/status";

function paraDatetimeLocal(iso: string): string {
  const data = new Date(iso);
  const local = new Date(data.getTime() - data.getTimezoneOffset() * 60_000);
  return local.toISOString().slice(0, 16);
}

// Detalhe de um atendimento — o "abrir o agendamento" para desfazer a
// recorrência (Fase 7f). Acessível a partir da agenda.
export function AgendamentoDetalhe() {
  const { id = "" } = useParams();
  const navigate = useNavigate();

  const { data, loading, error, reload } = useAsync(async () => {
    const ag = await api.agendamento(id);
    const pac = await api.paciente(ag.paciente_id).catch(() => null);
    return { ag, pac };
  }, [id]);

  const {
    ocupado: ocupadoRecorrencia,
    acaoErro: erroRecorrencia,
    executar: executarRecorrencia,
  } = useAcao();
  const {
    ocupado: salvandoEdicao,
    acaoErro: erroEdicao,
    executar: executarEdicao,
  } = useAcao();
  const [editando, setEditando] = useState(false);
  const [inicio, setInicio] = useState("");
  const [fim, setFim] = useState("");
  const [tipo, setTipo] = useState("");
  const [observacao, setObservacao] = useState("");
  const [validacaoEdicao, setValidacaoEdicao] = useState<string | null>(null);

  function desfazer(ag: Agendamento) {
    if (
      !window.confirm(
        "Desfazer a recorrência mantém ESTE atendimento e remove as demais repetições futuras " +
          "ainda agendadas. Os já realizados permanecem. Continuar?",
      )
    ) {
      return;
    }
    void executarRecorrencia(async () => {
      const { removidos } = await api.desfazerRecorrencia(ag.id);
      window.alert(`Recorrência desfeita: ${removidos} repetição(ões) futura(s) removida(s).`);
      navigate("/agenda", { replace: true });
    });
  }

  function iniciarEdicao(ag: Agendamento) {
    setInicio(paraDatetimeLocal(ag.inicio));
    setFim(paraDatetimeLocal(ag.fim));
    setTipo(ag.tipo ?? "");
    setObservacao(ag.observacao ?? "");
    setValidacaoEdicao(null);
    setEditando(true);
  }

  function salvarEdicao(ag: Agendamento) {
    const novoInicio = new Date(inicio);
    const novoFim = new Date(fim);
    if (
      !inicio ||
      !fim ||
      Number.isNaN(novoInicio.getTime()) ||
      Number.isNaN(novoFim.getTime()) ||
      novoFim <= novoInicio
    ) {
      setValidacaoEdicao("Informe início e fim válidos; o fim deve ser posterior ao início.");
      return;
    }
    setValidacaoEdicao(null);
    void executarEdicao(async () => {
      await api.atualizarAgendamento(ag.id, {
        inicio: novoInicio.toISOString(),
        fim: novoFim.toISOString(),
        tipo: tipo.trim() || null,
        observacao: observacao.trim() || null,
      });
      setEditando(false);
      reload();
    });
  }

  function apagarSerieFutura(ag: Agendamento) {
    if (
      !window.confirm(
        "Apagar esta ocorrência e todas as ocorrências futuras ainda agendadas? " +
          "O histórico passado será preservado.",
      )
    ) {
      return;
    }
    void executarRecorrencia(async () => {
      const { removidos } = await api.apagarRecorrenciaFutura(ag.id);
      window.alert(`${removidos} ocorrência(s) futura(s) removida(s).`);
      navigate(`/pacientes/${ag.paciente_id}`, { replace: true });
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

      {ag.status === "agendado" && (
        <div className="card">
          <div className="cabecalho-secao">
            <div>
              <h3>Editar agendamento</h3>
              {ag.serie_id && (
                <p className="muted">A edição altera somente esta ocorrência da série.</p>
              )}
            </div>
            {!editando && (
              <button type="button" className="secundario" onClick={() => iniciarEdicao(ag)}>
                Editar
              </button>
            )}
          </div>
          {editando && (
            <form
              onSubmit={(e) => {
                e.preventDefault();
                salvarEdicao(ag);
              }}
            >
              <div className="form-grid">
                <label className="campo">
                  Início
                  <input
                    type="datetime-local"
                    value={inicio}
                    onChange={(e) => setInicio(e.target.value)}
                    required
                  />
                </label>
                <label className="campo">
                  Fim
                  <input
                    type="datetime-local"
                    value={fim}
                    onChange={(e) => setFim(e.target.value)}
                    required
                  />
                </label>
              </div>
              <label className="campo">
                Tipo
                <input value={tipo} maxLength={40} onChange={(e) => setTipo(e.target.value)} />
              </label>
              <label className="campo">
                Observação
                <textarea
                  rows={3}
                  value={observacao}
                  maxLength={1000}
                  onChange={(e) => setObservacao(e.target.value)}
                />
              </label>
              {(validacaoEdicao || erroEdicao) && (
                <p className="erro">{validacaoEdicao ?? erroEdicao}</p>
              )}
              <div className="acoes-linha">
                <button type="submit" disabled={salvandoEdicao}>
                  {salvandoEdicao ? "Salvando…" : "Salvar alterações"}
                </button>
                <button
                  type="button"
                  className="secundario"
                  disabled={salvandoEdicao}
                  onClick={() => setEditando(false)}
                >
                  Cancelar edição
                </button>
              </div>
            </form>
          )}
        </div>
      )}

      {ag.serie_id && (
        <div className="card">
          <h3>Recorrência</h3>
          <p className="muted">
            Este atendimento se repete automaticamente. Desfazer remove as ocorrências futuras ainda
            agendadas (as já realizadas ficam no histórico).
          </p>
          {erroRecorrencia && <p className="erro">{erroRecorrencia}</p>}
          <div className="acoes-linha">
            <button
              className="secundario"
              disabled={ocupadoRecorrencia}
              onClick={() => void desfazer(ag)}
            >
              Desfazer recorrência
            </button>
            {ag.status === "agendado" && new Date(ag.inicio) >= new Date() && (
              <button
                className="erro-btn"
                disabled={ocupadoRecorrencia}
                onClick={() => void apagarSerieFutura(ag)}
              >
                Apagar série futura
              </button>
            )}
          </div>
        </div>
      )}
    </section>
  );
}
