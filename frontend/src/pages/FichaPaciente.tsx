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
      <Link className="voltar muted" to="/pacientes">
        ← Pacientes
      </Link>
      <div className="page-header">
        <div>
          <h2>{paciente.nome}</h2>
          <p className="muted">Nascimento: {fmtData(paciente.data_nascimento)}</p>
        </div>
        {consentimentos === null ? (
          <span className="tag">TCLE: indisponível</span>
        ) : tcleAtivo ? (
          <span className="tag tag-ativo">TCLE ativo</span>
        ) : (
          <span className="tag tag-inativo">Sem TCLE ativo</span>
        )}
      </div>

      <div className="card">
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
      </div>

      {!tcleAtivo && consentimentos !== null && (
        <p className="aviso">Sem TCLE ativo — novas evoluções ficam bloqueadas (§2.2).</p>
      )}

      <div className="cabecalho-secao">
        <h3>Evoluções</h3>
        {tcleAtivo && (
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
                <span className="muted">{fmtDataHora(e.criado_em)}</span> —{" "}
                {e.texto.length > 140 ? `${e.texto.slice(0, 140)}…` : e.texto}
                {e.embeddings_pendentes > 0 && (
                  <span className="muted"> (embeddings pendentes: {e.embeddings_pendentes})</span>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
