import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api/client";
import type {
  Agendamento,
  Consentimento,
  DocumentoPaciente,
  Evolucao,
  PacienteDetalhado,
} from "../api/client";
import { Stat } from "../components/Stat";
import { useAsync } from "../utils/useAsync";
import { fmtData, fmtDataHora, rotuloSexo } from "../utils/format";
import { useAcao } from "../utils/useAcao";
import { rotuloStatus } from "../utils/status";

const LIMITE_HISTORICO = 10;
const LIMITE_DOCUMENTOS = 20;

function fmtTamanho(bytes: number): string {
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function inicioDoDiaIso(dia: string): string | undefined {
  return dia ? new Date(`${dia}T00:00:00`).toISOString() : undefined;
}

function fimInclusivoDoDiaIso(dia: string): string | undefined {
  if (!dia) return undefined;
  const fim = new Date(`${dia}T00:00:00`);
  fim.setDate(fim.getDate() + 1);
  return fim.toISOString();
}

export function FichaPaciente() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const [statusHistorico, setStatusHistorico] = useState("");
  const [deHistorico, setDeHistorico] = useState("");
  const [ateHistorico, setAteHistorico] = useState("");
  const [offsetHistorico, setOffsetHistorico] = useState(0);
  const [offsetDocumentos, setOffsetDocumentos] = useState(0);
  const [arquivoDocumento, setArquivoDocumento] = useState<File | null>(null);
  const inputDocumento = useRef<HTMLInputElement>(null);

  useEffect(() => {
    setOffsetDocumentos(0);
    setArquivoDocumento(null);
    if (inputDocumento.current) inputDocumento.current.value = "";
  }, [id]);
  // O paciente e essencial; consentimentos/evolucoes/agenda sao secundarios -> uma
  // falha transitoria neles nao deve apagar a ficha (allSettled, #4 do review).
  const { data, loading, error, reload } = useAsync(async () => {
    const paciente = await api.paciente(id);
    const [c, e, a] = await Promise.allSettled([
      api.consentimentos(id),
      api.evolucoes(id),
      api.agendamentos({
        paciente_id: id,
        de: new Date().toISOString(),
        status: "agendado",
      }),
    ]);
    return {
      paciente,
      consentimentos: c.status === "fulfilled" ? c.value : null,
      evolucoes: e.status === "fulfilled" ? e.value : null,
      agendamentosFuturos: a.status === "fulfilled" ? a.value : null,
    };
  }, [id]);

  const {
    data: sessoes,
    loading: carregandoSessoes,
    error: erroSessoes,
    reload: reloadSessoes,
  } = useAsync(
    () =>
      api.sessoesPaciente(id, {
        de: inicioDoDiaIso(deHistorico),
        ate: fimInclusivoDoDiaIso(ateHistorico),
        status: statusHistorico || undefined,
        limite: LIMITE_HISTORICO,
        offset: offsetHistorico,
      }),
    [id, statusHistorico, deHistorico, ateHistorico, offsetHistorico],
  );

  const {
    data: documentos,
    loading: carregandoDocumentos,
    error: erroDocumentos,
    reload: reloadDocumentos,
  } = useAsync(
    () => api.documentosPaciente(id, LIMITE_DOCUMENTOS, offsetDocumentos),
    [id, offsetDocumentos],
  );

  const { ocupado, acaoErro, executar } = useAcao();
  const {
    ocupado: ocupadoAgenda,
    acaoErro: agendaErro,
    executar: executarAgenda,
  } = useAcao();
  const {
    ocupado: ocupadoDocumento,
    acaoErro: documentoAcaoErro,
    executar: executarDocumento,
  } = useAcao();

  function enviarDocumento() {
    if (!arquivoDocumento) return;
    void executarDocumento(async () => {
      await api.enviarDocumento(id, arquivoDocumento);
      setArquivoDocumento(null);
      if (inputDocumento.current) inputDocumento.current.value = "";
      setOffsetDocumentos(0);
      reloadDocumentos();
    });
  }

  function baixarDocumento(documento: DocumentoPaciente) {
    void executarDocumento(() => api.baixarDocumento(documento));
  }

  function arquivarOuReativar(paciente: PacienteDetalhado) {
    if (paciente.ativo) {
      const motivo = window.prompt(
        "Motivo do arquivamento (opcional). O arquivamento será bloqueado se houver agendamentos futuros:",
        "",
      );
      if (motivo === null) return;
      if (!window.confirm("Arquivar este paciente? Nada será apagado.")) return;
      void executar(async () => {
        await api.arquivarPaciente(paciente.id, motivo);
        reload();
        reloadSessoes();
      });
      return;
    }
    if (!window.confirm("Reativar este paciente?")) return;
    void executar(async () => {
      await api.reativarPaciente(paciente.id);
      reload();
      reloadSessoes();
    });
  }

  function apagar(paciente: PacienteDetalhado) {
    if (
      !window.confirm(
        `APAGAR o paciente "${paciente.nome}"?\n\nIsso exclui DEFINITIVAMENTE o cadastro, vínculos, TCLE e agendamentos. ` +
          "Só é possível para cadastro sem prontuário (evoluções) — com prontuário, use o arquivamento (guarda de 5 anos, CFP).",
      )
    ) {
      return;
    }
    void executar(async () => {
      await api.apagarPaciente(paciente.id);
      navigate("/pacientes", { replace: true });
    });
  }

  function cancelarAgendamentoFuturo(agendamento: Agendamento) {
    const motivo = window.prompt("Motivo do cancelamento (opcional):", "");
    if (motivo === null) return;
    if (!window.confirm(`Cancelar o agendamento de ${fmtDataHora(agendamento.inicio)}?`)) return;
    void executarAgenda(async () => {
      await api.cancelarAgendamento(agendamento.id, motivo);
      reload();
      reloadSessoes();
    });
  }

  function apagarSerieFutura(agendamento: Agendamento) {
    if (
      !window.confirm(
        "Apagar esta ocorrência e TODAS as ocorrências futuras ainda agendadas da série? " +
          "Atendimentos passados, realizados, faltas e cancelamentos serão preservados.",
      )
    ) {
      return;
    }
    void executarAgenda(async () => {
      const { removidos } = await api.apagarRecorrenciaFutura(agendamento.id);
      window.alert(`${removidos} ocorrência(s) futura(s) removida(s).`);
      reload();
      reloadSessoes();
    });
  }

  if (loading) return <p className="muted">Carregando ficha…</p>;
  if (error || !data) return <p className="erro">{error ?? "Erro ao carregar."}</p>;

  const { paciente, consentimentos, evolucoes, agendamentosFuturos } = data as {
    paciente: PacienteDetalhado;
    consentimentos: Consentimento[] | null;
    evolucoes: Evolucao[] | null;
    agendamentosFuturos: Agendamento[] | null;
  };
  // Sem a lista de consentimentos nao afirmamos "ativo" (fail-safe: bloqueia).
  const tcleAtivo = consentimentos !== null && consentimentos.some((c) => c.revogado_em === null);

  return (
    <section>
      <Link className="voltar muted" to="/pacientes">
        ← Pacientes
      </Link>
      <div className="page-header">
        <div>
          <h2>
            {paciente.nome}
            {!paciente.ativo && <span className="tag tag-inativo titulo-tag">Arquivado</span>}
          </h2>
        </div>
        {consentimentos === null ? (
          <span className="tag">TCLE: indisponível</span>
        ) : tcleAtivo ? (
          <span className="tag tag-ativo">TCLE ativo</span>
        ) : (
          <span className="tag tag-inativo">Sem TCLE ativo</span>
        )}
      </div>

      {/* ---- Cadastro completo (Fase 7e) ---- */}
      <div className="card">
        <h3>Dados cadastrais</h3>
        <dl className="dados">
          <div>
            <dt>Nascimento</dt>
            <dd>{fmtData(paciente.data_nascimento)}</dd>
          </div>
          <div>
            <dt>Sexo</dt>
            <dd>{paciente.sexo ? rotuloSexo(paciente.sexo) : "—"}</dd>
          </div>
          <div>
            <dt>Observações gerais</dt>
            <dd>{paciente.observacoes_gerais || "—"}</dd>
          </div>
          <div>
            <dt>Situação</dt>
            <dd>{paciente.ativo ? "Ativo" : "Arquivado"}</dd>
          </div>
          {!paciente.ativo && paciente.arquivado_em && (
            <div>
              <dt>Arquivado em</dt>
              <dd>{fmtDataHora(paciente.arquivado_em)}</dd>
            </div>
          )}
          {!paciente.ativo && paciente.motivo_arquivamento && (
            <div>
              <dt>Motivo do arquivamento</dt>
              <dd>{paciente.motivo_arquivamento}</dd>
            </div>
          )}
          <div>
            <dt>Cadastrado em</dt>
            <dd>{fmtDataHora(paciente.criado_em)}</dd>
          </div>
        </dl>
      </div>

      <div className="card">
        <h3>Responsáveis</h3>
        <ul className="lista">
          {paciente.vinculos.map((v) => (
            <li key={v.id}>
              <Link to={`/responsaveis/${v.responsavel_id}`}>{v.responsavel.nome}</Link>{" "}
              <span className="muted">
                ({v.tipo_vinculo}
                {v.principal && ", principal"}
                {v.detem_guarda && ", guarda"})
              </span>
              {(v.responsavel.telefone || v.responsavel.email) && (
                <span className="muted">
                  {" — "}
                  {[v.responsavel.telefone, v.responsavel.email].filter(Boolean).join(" · ")}
                </span>
              )}
            </li>
          ))}
        </ul>
      </div>

      <div className="cabecalho-secao">
        <div>
          <h3>Controle de sessões</h3>
          <p className="muted">Resumo administrativo da continuidade dos atendimentos.</p>
        </div>
      </div>
      {carregandoSessoes ? (
        <p className="muted">Carregando controle de sessões…</p>
      ) : erroSessoes || !sessoes ? (
        <p className="erro">{erroSessoes ?? "Não foi possível carregar as sessões."}</p>
      ) : (
        <>
          <div className="stats">
            <Stat
              valor={sessoes.total_realizadas}
              rotulo="Sessões realizadas"
              info="Total de agendamentos marcados como realizados neste cadastro."
            />
            <Stat
              valor={sessoes.realizadas_mes_atual}
              rotulo="Realizadas no mês"
              info="Sessões realizadas no mês atual, no fuso da clínica."
            />
            <Stat
              valor={sessoes.ultima_sessao ? fmtDataHora(sessoes.ultima_sessao.inicio) : "—"}
              rotulo="Última sessão"
              info={
                sessoes.dias_desde_ultima === null
                  ? "Nenhuma sessão realizada."
                  : `${sessoes.dias_desde_ultima} dia(s) desde a última sessão.`
              }
            />
            <Stat
              valor={sessoes.proxima_sessao ? fmtDataHora(sessoes.proxima_sessao.inicio) : "—"}
              rotulo="Próxima sessão"
              info="Primeiro agendamento futuro ainda pendente."
              alerta={paciente.ativo && !sessoes.proxima_sessao}
            />
            <Stat
              valor={sessoes.faltas_total}
              rotulo="Faltas"
              info="Total de atendimentos marcados como falta."
            />
            <Stat
              valor={
                sessoes.taxa_comparecimento === null
                  ? "—"
                  : `${Math.round(sessoes.taxa_comparecimento * 100)}%`
              }
              rotulo="Comparecimento"
              info="Realizadas ÷ (realizadas + faltas). Cancelamentos não entram no denominador."
            />
          </div>

          <div className="card resumo-sessoes-complementar">
            <span><strong>{sessoes.realizadas_ano_atual}</strong> realizadas no ano</span>
            <span><strong>{sessoes.cancelamentos_total}</strong> cancelamentos</span>
            <span>
              Intervalo mediano recente: <strong>
                {sessoes.intervalo_mediano_dias === null
                  ? "—"
                  : `${sessoes.intervalo_mediano_dias} dia(s)`}
              </strong>
            </span>
          </div>

          <div className="cabecalho-secao historico-sessoes-cabecalho">
            <h4>Histórico de agendamentos</h4>
            <span className="muted">{sessoes.historico_total} registro(s)</span>
          </div>
          <div className="filtros-lista filtros-historico-sessoes">
            <label>
              <span>De</span>
              <input
                type="date"
                value={deHistorico}
                onChange={(e) => {
                  const valor = e.target.value;
                  setDeHistorico(valor);
                  if (valor && ateHistorico && valor > ateHistorico) setAteHistorico(valor);
                  setOffsetHistorico(0);
                }}
              />
            </label>
            <label>
              <span>Até</span>
              <input
                type="date"
                value={ateHistorico}
                onChange={(e) => {
                  const valor = e.target.value;
                  setAteHistorico(valor);
                  if (valor && deHistorico && valor < deHistorico) setDeHistorico(valor);
                  setOffsetHistorico(0);
                }}
              />
            </label>
            <label>
              <span>Status</span>
              <select
                value={statusHistorico}
                onChange={(e) => {
                  setStatusHistorico(e.target.value);
                  setOffsetHistorico(0);
                }}
              >
                <option value="">Todos</option>
                <option value="agendado">Agendado</option>
                <option value="realizado">Realizado</option>
                <option value="falta">Falta</option>
                <option value="cancelado">Cancelado</option>
              </select>
            </label>
          </div>
          <div className="card tabela-container">
            {sessoes.historico.length === 0 ? (
              <p className="vazio">Nenhum agendamento encontrado neste filtro.</p>
            ) : (
              <table className="tabela">
                <thead>
                  <tr>
                    <th>Data</th>
                    <th>Status</th>
                    <th>Tipo</th>
                    <th>Registro</th>
                  </tr>
                </thead>
                <tbody>
                  {sessoes.historico.map((sessao) => (
                    <tr key={sessao.id}>
                      <td><Link to={`/agenda/${sessao.id}`}>{fmtDataHora(sessao.inicio)}</Link></td>
                      <td><span className={`tag tag-${sessao.status}`}>{rotuloStatus(sessao.status)}</span></td>
                      <td>{sessao.tipo || "—"}</td>
                      <td>
                        {sessao.evolucao_id ? (
                          <Link to={`#evolucao-${sessao.evolucao_id}`}>Ver evolução</Link>
                        ) : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
            <div className="paginacao-sessoes">
              <button
                type="button"
                className="mini secundario"
                disabled={offsetHistorico === 0 || carregandoSessoes}
                onClick={() => setOffsetHistorico(Math.max(0, offsetHistorico - LIMITE_HISTORICO))}
              >
                Anteriores
              </button>
              <span className="muted">
                {sessoes.historico_total === 0 ? 0 : offsetHistorico + 1}–{Math.min(
                  offsetHistorico + sessoes.historico.length,
                  sessoes.historico_total,
                )}
              </span>
              <button
                type="button"
                className="mini secundario"
                disabled={
                  offsetHistorico + sessoes.historico.length >= sessoes.historico_total ||
                  carregandoSessoes
                }
                onClick={() => setOffsetHistorico(offsetHistorico + LIMITE_HISTORICO)}
              >
                Próximos
              </button>
            </div>
          </div>
        </>
      )}

      <div className="cabecalho-secao">
        <div>
          <h3>Agendamentos futuros</h3>
          <p className="muted">Consultas ainda agendadas que precisam ser resolvidas antes de arquivar.</p>
        </div>
      </div>
      <div className="card tabela-container">
        {agendaErro && <p className="erro">{agendaErro}</p>}
        {agendamentosFuturos === null ? (
          <p className="muted">Não foi possível carregar os agendamentos futuros agora.</p>
        ) : agendamentosFuturos.length === 0 ? (
          <p className="vazio">Nenhum agendamento futuro pendente.</p>
        ) : (
          <table className="tabela">
            <thead>
              <tr>
                <th>Início</th>
                <th>Fim</th>
                <th>Tipo</th>
                <th aria-label="Ações"></th>
              </tr>
            </thead>
            <tbody>
              {agendamentosFuturos.map((a) => (
                <tr key={a.id}>
                  <td><Link to={`/agenda/${a.id}`}>{fmtDataHora(a.inicio)}</Link></td>
                  <td>{fmtDataHora(a.fim)}</td>
                  <td>{a.tipo || "—"}</td>
                  <td>
                    {a.serie_id ? (
                      <button
                        type="button"
                        className="mini erro-btn"
                        disabled={ocupadoAgenda}
                        onClick={() => apagarSerieFutura(a)}
                      >
                        Apagar série futura
                      </button>
                    ) : (
                      <button
                        type="button"
                        className="mini secundario"
                        disabled={ocupadoAgenda}
                        onClick={() => cancelarAgendamentoFuturo(a)}
                      >
                        Cancelar
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {!tcleAtivo && consentimentos !== null && (
        <p className="aviso">Sem TCLE ativo — novas evoluções ficam bloqueadas (§2.2).</p>
      )}

      <div className="cabecalho-secao">
        <h3>Evoluções</h3>
        {tcleAtivo && paciente.ativo && (
          <Link className="botao" to={`/pacientes/${id}/evolucao/nova`}>
            Nova evolução
          </Link>
        )}
      </div>
      <div className="card">
        {evolucoes === null ? (
          <p className="muted">Não foi possível carregar as evoluções agora.</p>
        ) : evolucoes.length === 0 ? (
          <p className="vazio">Nenhuma evolução registrada.</p>
        ) : (
          <ul className="lista">
            {evolucoes.map((e) => (
              <li key={e.id} id={`evolucao-${e.id}`}>
                <span className="muted">
                  {e.data_atendimento
                    ? `Atendimento: ${fmtDataHora(e.data_atendimento)}`
                    : fmtDataHora(e.criado_em)}
                </span>{" "}
                — {e.texto.length > 140 ? `${e.texto.slice(0, 140)}…` : e.texto}
                {e.embeddings_pendentes > 0 && (
                  <span className="muted"> (embeddings pendentes: {e.embeddings_pendentes})</span>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="cabecalho-secao">
        <div>
          <h3>Documentos clínicos</h3>
          <p className="muted">Testes e arquivos vinculados ao prontuário deste paciente.</p>
        </div>
      </div>
      <div className="card">
        <div className="upload-documento">
          <label>
            <span>Arquivo</span>
            <input
              ref={inputDocumento}
              type="file"
              accept=".pdf,.docx,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png"
              disabled={ocupadoDocumento}
              onChange={(e) => setArquivoDocumento(e.target.files?.[0] ?? null)}
            />
          </label>
          <button
            type="button"
            disabled={!arquivoDocumento || ocupadoDocumento}
            onClick={enviarDocumento}
          >
            {ocupadoDocumento ? "Processando…" : "Enviar documento"}
          </button>
        </div>
        <p className="muted ajuda-documento">
          PDF, DOCX, JPEG ou PNG, até 20 MB. O arquivo é validado e reconstruído antes de ser
          armazenado; arquivos ativos, protegidos ou inseguros são recusados.
        </p>
        {documentoAcaoErro && <p className="erro">{documentoAcaoErro}</p>}
        {carregandoDocumentos ? (
          <p className="muted">Carregando documentos…</p>
        ) : erroDocumentos || !documentos ? (
          <p className="erro">{erroDocumentos ?? "Não foi possível carregar os documentos."}</p>
        ) : documentos.itens.length === 0 ? (
          <p className="vazio">Nenhum documento armazenado.</p>
        ) : (
          <>
            <div className="tabela-container">
              <table className="tabela">
                <thead>
                  <tr>
                    <th>Arquivo</th>
                    <th>Formato</th>
                    <th>Tamanho</th>
                    <th>Enviado em</th>
                    <th aria-label="Ações"></th>
                  </tr>
                </thead>
                <tbody>
                  {documentos.itens.map((documento) => (
                    <tr key={documento.id}>
                      <td>{documento.nome_original}</td>
                      <td>{documento.extensao.slice(1).toUpperCase()}</td>
                      <td>{fmtTamanho(documento.tamanho_bytes)}</td>
                      <td>{fmtDataHora(documento.criado_em)}</td>
                      <td>
                        <button
                          type="button"
                          className="mini secundario"
                          disabled={ocupadoDocumento}
                          onClick={() => baixarDocumento(documento)}
                        >
                          Baixar
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="paginacao-sessoes">
              <button
                type="button"
                className="mini secundario"
                disabled={offsetDocumentos === 0 || ocupadoDocumento}
                onClick={() =>
                  setOffsetDocumentos(Math.max(0, offsetDocumentos - LIMITE_DOCUMENTOS))
                }
              >
                Anteriores
              </button>
              <span className="muted">
                {offsetDocumentos + 1}–{Math.min(
                  offsetDocumentos + documentos.itens.length,
                  documentos.total,
                )} de {documentos.total}
              </span>
              <button
                type="button"
                className="mini secundario"
                disabled={
                  offsetDocumentos + documentos.itens.length >= documentos.total ||
                  ocupadoDocumento
                }
                onClick={() => setOffsetDocumentos(offsetDocumentos + LIMITE_DOCUMENTOS)}
              >
                Próximos
              </button>
            </div>
          </>
        )}
      </div>

      {/* ---- Zona de administração do cadastro (Fase 7e) ---- */}
      <div className="card zona-perigo">
        <h3>Administração do cadastro</h3>
        <p className="muted">
          Arquivar preserva tudo (prontuário incluso) e tira o paciente das listas ativas. Apagar é
          definitivo e só é permitido para cadastro <strong>sem prontuário</strong> — com evoluções,
          a guarda de 5 anos (CFP 001/2009) exige manter o registro.
        </p>
        {paciente.ativo && (
          <p className="muted">
            Para evitar consultas órfãs, o arquivamento só é concluído depois que todos os
            agendamentos futuros forem cancelados ou resolvidos.
          </p>
        )}
        {acaoErro && <p className="erro">{acaoErro}</p>}
        <div className="acoes">
          <button
            className="secundario"
            disabled={ocupado}
            onClick={() => void arquivarOuReativar(paciente)}
          >
            {paciente.ativo ? "Arquivar paciente" : "Reativar paciente"}
          </button>
          <button className="perigo" disabled={ocupado} onClick={() => void apagar(paciente)}>
            Apagar paciente…
          </button>
        </div>
      </div>
    </section>
  );
}
