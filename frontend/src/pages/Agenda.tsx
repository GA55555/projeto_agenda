import { useState } from "react";
import { Link } from "react-router-dom";
import { api, ApiError } from "../api/client";
import type { Agendamento, Paciente } from "../api/client";
import { useAsync } from "../utils/useAsync";
import { fmtDataHora, janelaDeHoje } from "../utils/format";
import { rotuloStatus } from "../utils/status";

// AGENDA DO DIA. O backend filtra por [de, ate) e ja ordena por `inicio`.
// Atendimentos `agendado` podem ser concluidos (realizado), marcados como
// falta ou cancelados (soft, com motivo opcional). Os demais status sao
// terminais e nao exibem acoes.
export function Agenda() {
  const { data, loading, error } = useAsync(() => {
    const { de, ate } = janelaDeHoje();
    return Promise.all([api.agendamentos({ de, ate }), api.pacientes()]);
  }, []);

  // Estado das acoes por linha: qual esta ocupada, qual esta em modo cancelar.
  const [ocupadoId, setOcupadoId] = useState<string | null>(null);
  const [cancelandoId, setCancelandoId] = useState<string | null>(null);
  const [motivo, setMotivo] = useState("");
  const [acaoErro, setAcaoErro] = useState<string | null>(null);
  // As mutacoes (PATCH/cancelar) DEVOLVEM o agendamento atualizado: aplicamos
  // por cima da lista carregada, sem refetch. Elimina a janela em que a linha
  // stale reabilitava os botoes (double-click enviaria PATCH conflitante) e o
  // caso em que uma falha do refetch apagava a tabela inteira.
  const [overrides, setOverrides] = useState<Map<string, Agendamento>>(new Map());
  // Apagados nesta sessão de tela (DELETE devolve 204 — sem objeto p/ override).
  const [removidos, setRemovidos] = useState<Set<string>>(new Set());

  async function executar(fn: () => Promise<Agendamento>, id: string) {
    setOcupadoId(id);
    setAcaoErro(null);
    try {
      const atualizado = await fn();
      setOverrides((prev) => new Map(prev).set(id, atualizado));
      setCancelandoId(null);
      setMotivo("");
    } catch (e) {
      setAcaoErro(e instanceof ApiError ? e.message : "Não foi possível concluir a ação.");
    } finally {
      setOcupadoId(null);
    }
  }

  async function apagar(a: Agendamento) {
    // Apagar corrige ERRO de lançamento (só 'agendado'; auditado no backend).
    if (!window.confirm("Apagar este agendamento? Use para corrigir um lançamento errado.")) {
      return;
    }
    setOcupadoId(a.id);
    setAcaoErro(null);
    try {
      await api.apagarAgendamento(a.id);
      setRemovidos((prev) => new Set(prev).add(a.id));
    } catch (e) {
      setAcaoErro(e instanceof ApiError ? e.message : "Não foi possível apagar.");
    } finally {
      setOcupadoId(null);
    }
  }

  if (loading) return <p className="muted">Carregando agenda…</p>;
  if (error) return <p className="erro">{error}</p>;

  const [agsBase, pacientes] = data as [Agendamento[], Paciente[]];
  const ags = agsBase.filter((a) => !removidos.has(a.id)).map((a) => overrides.get(a.id) ?? a);
  const nomePorId = new Map(pacientes.map((p) => [p.id, p.nome]));

  return (
    <section>
      <div className="page-header">
        <div>
          <h2>Agenda de hoje</h2>
          <p className="muted">{new Date().toLocaleDateString("pt-BR", { dateStyle: "full" })}</p>
        </div>
        <Link className="botao" to="/agenda/novo">
          Novo agendamento
        </Link>
      </div>
      {acaoErro && <p className="erro">{acaoErro}</p>}
      {ags.length === 0 ? (
        <p className="vazio">Nenhum atendimento hoje.</p>
      ) : (
        <div className="card">
          <table className="tabela">
            <thead>
              <tr>
                <th>Início</th>
                <th>Fim</th>
                <th>Paciente</th>
                <th>Status</th>
                <th aria-label="Ações"></th>
              </tr>
            </thead>
            <tbody>
              {ags.map((a) => {
                const ocupado = ocupadoId === a.id;
                return (
                  <tr key={a.id} className={a.status === "cancelado" ? "linha-inativa" : undefined}>
                    <td>
                      <Link to={`/agenda/${a.id}`}>{fmtDataHora(a.inicio)}</Link>
                      {a.serie_id && (
                        <span className="serie-tag" title="Faz parte de uma recorrência">
                          {" "}
                          🔁
                        </span>
                      )}
                    </td>
                    <td>{fmtDataHora(a.fim)}</td>
                    <td>
                      <Link to={`/pacientes/${a.paciente_id}`}>
                        {nomePorId.get(a.paciente_id) ?? "—"}
                      </Link>
                    </td>
                    <td>
                      <span className={`tag tag-${a.status}`}>{rotuloStatus(a.status)}</span>
                    </td>
                    <td>
                      {a.status !== "agendado" ? null : cancelandoId === a.id ? (
                        <div className="cancelar-inline">
                          <input
                            value={motivo}
                            onChange={(e) => setMotivo(e.target.value)}
                            placeholder="Motivo (opcional)"
                            aria-label="Motivo do cancelamento"
                          />
                          <button
                            className="mini erro-btn"
                            disabled={ocupado}
                            onClick={() => executar(() => api.cancelarAgendamento(a.id, motivo), a.id)}
                          >
                            Confirmar
                          </button>
                          <button
                            className="mini secundario"
                            disabled={ocupado}
                            onClick={() => {
                              setCancelandoId(null);
                              setMotivo("");
                            }}
                          >
                            Voltar
                          </button>
                        </div>
                      ) : (
                        <div className="acoes-linha">
                          <button
                            className="mini"
                            disabled={ocupado}
                            onClick={() =>
                              executar(() => api.mudarStatusAgendamento(a.id, "realizado"), a.id)
                            }
                          >
                            Realizado
                          </button>
                          <button
                            className="mini secundario"
                            disabled={ocupado}
                            onClick={() =>
                              executar(() => api.mudarStatusAgendamento(a.id, "falta"), a.id)
                            }
                          >
                            Falta
                          </button>
                          <button
                            className="mini secundario"
                            disabled={ocupado}
                            onClick={() => {
                              setAcaoErro(null);
                              setCancelandoId(a.id);
                              setMotivo("");
                            }}
                          >
                            Cancelar
                          </button>
                          <button
                            className="mini erro-btn"
                            disabled={ocupado}
                            onClick={() => void apagar(a)}
                            title="Apagar lançamento errado (auditado)"
                          >
                            Apagar
                          </button>
                        </div>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
