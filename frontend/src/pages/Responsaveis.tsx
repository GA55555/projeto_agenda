import { Link } from "react-router-dom";
import { api } from "../api/client";
import { useAsync } from "../utils/useAsync";

// Lista dos responsáveis legais (cadastro dos pais). Clicar -> detalhe/contato.
export function Responsaveis() {
  const { data: responsaveis, loading, error } = useAsync(() => api.responsaveis(), []);

  return (
    <section>
      <div className="page-header">
        <h2>Responsáveis</h2>
        <Link className="botao" to="/responsaveis/novo">
          Novo responsável
        </Link>
      </div>

      {loading && <p className="muted">Carregando…</p>}
      {error && <p className="erro">{error}</p>}
      {responsaveis &&
        (responsaveis.length === 0 ? (
          <p className="vazio">Nenhum responsável cadastrado.</p>
        ) : (
          <div className="card">
            <table className="tabela">
              <thead>
                <tr>
                  <th>Nome</th>
                  <th>CPF</th>
                  <th>Telefone</th>
                  <th>E-mail</th>
                </tr>
              </thead>
              <tbody>
                {responsaveis.map((r) => (
                  <tr key={r.id}>
                    <td>
                      <Link to={`/responsaveis/${r.id}`}>{r.nome}</Link>
                    </td>
                    <td>{r.cpf}</td>
                    <td>{r.telefone ?? "—"}</td>
                    <td>{r.email ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ))}
    </section>
  );
}
