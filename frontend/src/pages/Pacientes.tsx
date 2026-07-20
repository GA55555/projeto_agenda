import { Link } from "react-router-dom";
import { api } from "../api/client";
import { useAsync } from "../utils/useAsync";
import { fmtData } from "../utils/format";

export function Pacientes() {
  const { data: pacientes, loading, error } = useAsync(() => api.pacientes(), []);

  if (loading) return <p className="muted">Carregando pacientes…</p>;
  if (error) return <p className="erro">{error}</p>;

  return (
    <section>
      <div className="page-header">
        <h2>Pacientes</h2>
        <Link className="botao" to="/pacientes/novo">
          Novo paciente
        </Link>
      </div>
      {!pacientes || pacientes.length === 0 ? (
        <p className="vazio">Nenhum paciente cadastrado.</p>
      ) : (
        <div className="card">
          <ul className="lista">
            {pacientes.map((p) => (
              <li key={p.id}>
                <Link to={`/pacientes/${p.id}`}>{p.nome}</Link>
                <span className="muted"> · nasc. {fmtData(p.data_nascimento)}</span>
                {!p.ativo && <span className="tag tag-inativo"> inativo</span>}
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
