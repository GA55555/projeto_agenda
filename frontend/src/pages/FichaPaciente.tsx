import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api/client";
import type { Agendamento, Consentimento, Evolucao, PacienteDetalhado } from "../api/client";
import { useAsync } from "../utils/useAsync";
import { fmtData, fmtDataHora, rotuloSexo } from "../utils/format";
import { useAcao } from "../utils/useAcao";

export function FichaPaciente() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
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

  const { ocupado, acaoErro, executar } = useAcao();
  const {
    ocupado: ocupadoAgenda,
    acaoErro: agendaErro,
    executar: executarAgenda,
  } = useAcao();

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
      });
      return;
    }
    if (!window.confirm("Reativar este paciente?")) return;
    void executar(async () => {
      await api.reativarPaciente(paciente.id);
      reload();
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
                    <button
                      type="button"
                      className="mini secundario"
                      disabled={ocupadoAgenda}
                      onClick={() => cancelarAgendamentoFuturo(a)}
                    >
                      Cancelar
                    </button>
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
              <li key={e.id}>
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
