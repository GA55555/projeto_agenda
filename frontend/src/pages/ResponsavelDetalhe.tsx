import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import { useAsync } from "../utils/useAsync";
import { fmtData } from "../utils/format";

export function ResponsavelDetalhe() {
  const { id = "" } = useParams();
  const { data: r, loading, error } = useAsync(() => api.responsavel(id), [id]);

  if (loading) return <p className="muted">Carregando…</p>;
  if (error || !r) return <p className="erro">{error ?? "Não encontrado."}</p>;

  const linhas: [string, string][] = [
    ["CPF", r.cpf],
    ["Nascimento", r.data_nascimento ? fmtData(r.data_nascimento) : "—"],
    ["Telefone", r.telefone ?? "—"],
    ["E-mail", r.email ?? "—"],
    ["Endereço", r.endereco ?? "—"],
  ];

  return (
    <section>
      <Link className="voltar muted" to="/responsaveis">
        ← Responsáveis
      </Link>
      <div className="page-header">
        <h2>{r.nome}</h2>
        <Link className="botao secundario" to={`/responsaveis/${id}/editar`}>
          Editar
        </Link>
      </div>
      <div className="card">
        <dl className="dados">
          {linhas.map(([rotulo, valor]) => (
            <div key={rotulo}>
              <dt>{rotulo}</dt>
              <dd>{valor}</dd>
            </div>
          ))}
        </dl>
      </div>
    </section>
  );
}
