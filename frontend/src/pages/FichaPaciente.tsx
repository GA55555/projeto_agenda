import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import type { Consentimento, Evolucao, PacienteDetalhado } from "../api/client";
import { useAsync } from "../utils/useAsync";
import { fmtData, fmtDataHora } from "../utils/format";

export function FichaPaciente() {
  const { id = "" } = useParams();
  // O paciente e essencial; consentimentos/evolucoes sao secundarios -> uma
  // falha transitoria neles nao deve apagar a ficha (allSettled, #4 do review).
  const { data, loading, error } = useAsync(async () => {
    const paciente = await api.paciente(id);
    const [c, e] = await Promise.allSettled([api.consentimentos(id), api.evolucoes(id)]);
    return {
      paciente,
      consentimentos: c.status === "fulfilled" ? c.value : null,
      evolucoes: e.status === "fulfilled" ? e.value : null,
    };
  }, [id]);

  if (loading) return <p className="muted">Carregando ficha…</p>;
  if (error || !data) return <p className="erro">{error ?? "Erro ao carregar."}</p>;

  const { paciente, consentimentos, evolucoes } = data as {
    paciente: PacienteDetalhado;
    consentimentos: Consentimento[] | null;
    evolucoes: Evolucao[] | null;
  };
  // Sem a lista de consentimentos nao afirmamos "ativo" (fail-safe: bloqueia).
  const tcleAtivo = consentimentos !== null && consentimentos.some((c) => c.revogado_em === null);

  return (
    <section>
      <p className="muted">
        <Link to="/pacientes">← Pacientes</Link>
      </p>
      <h2>{paciente.nome}</h2>
      <p className="muted">Nascimento: {fmtData(paciente.data_nascimento)}</p>

      <h3>Consentimento (TCLE)</h3>
      {consentimentos === null ? (
        <p className="muted">Não foi possível carregar o consentimento agora.</p>
      ) : tcleAtivo ? (
        <p className="tag tag-realizado">Ativo</p>
      ) : (
        <p className="tag tag-cancelado">Sem TCLE ativo — evoluções bloqueadas (§2.2)</p>
      )}

      <h3>Responsáveis</h3>
      <ul className="lista">
        {paciente.vinculos.map((v) => (
          <li key={v.id}>
            {v.responsavel.nome} <span className="muted">({v.tipo_vinculo}</span>
            {v.principal && <span className="muted">, principal</span>}
            {v.detem_guarda && <span className="muted">, guarda</span>}
            <span className="muted">)</span>
          </li>
        ))}
      </ul>

      <div className="cabecalho-secao">
        <h3>Evoluções</h3>
        {tcleAtivo && (
          <Link className="botao" to={`/pacientes/${id}/evolucao/nova`}>
            Nova evolução
          </Link>
        )}
      </div>
      {evolucoes === null ? (
        <p className="muted">Não foi possível carregar as evoluções agora.</p>
      ) : evolucoes.length === 0 ? (
        <p className="muted">Nenhuma evolução registrada.</p>
      ) : (
        <ul className="lista">
          {evolucoes.map((e) => (
            <li key={e.id}>
              <span className="muted">{fmtDataHora(e.criado_em)}</span> —{" "}
              {e.texto.length > 140 ? `${e.texto.slice(0, 140)}…` : e.texto}
              {e.embeddings_pendentes > 0 && (
                <span className="muted"> (embeddings pendentes: {e.embeddings_pendentes})</span>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
