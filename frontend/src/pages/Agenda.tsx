import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { Agendamento, Paciente } from "../api/client";
import { useAsync } from "../utils/useAsync";
import { fmtDataHora } from "../utils/format";

const ROTULO_STATUS: Record<string, string> = {
  agendado: "Agendado",
  realizado: "Realizado",
  cancelado: "Cancelado",
  falta: "Falta",
};

// Janela [inicio de hoje, inicio de amanha) no fuso local, como instantes ISO.
function janelaDeHoje(): { de: string; ate: string } {
  const h = new Date();
  const de = new Date(h.getFullYear(), h.getMonth(), h.getDate()).toISOString();
  const ate = new Date(h.getFullYear(), h.getMonth(), h.getDate() + 1).toISOString();
  return { de, ate };
}

// Landing: AGENDA DO DIA (read-only). O backend filtra por [de, ate) e ja ordena
// por `inicio`. Clicar num paciente -> ficha.
export function Agenda() {
  const { data, loading, error } = useAsync(() => {
    const { de, ate } = janelaDeHoje();
    return Promise.all([api.agendamentos({ de, ate }), api.pacientes()]);
  }, []);

  if (loading) return <p className="muted">Carregando agenda…</p>;
  if (error) return <p className="erro">{error}</p>;

  const [ags, pacientes] = data as [Agendamento[], Paciente[]];
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
            </tr>
          </thead>
          <tbody>
            {ags.map((a) => (
              <tr key={a.id} className={a.status === "cancelado" ? "linha-inativa" : undefined}>
                <td>{fmtDataHora(a.inicio)}</td>
                <td>{fmtDataHora(a.fim)}</td>
                <td>
                  <Link to={`/pacientes/${a.paciente_id}`}>
                    {nomePorId.get(a.paciente_id) ?? "—"}
                  </Link>
                </td>
                <td>
                  <span className={`tag tag-${a.status}`}>
                    {ROTULO_STATUS[a.status] ?? a.status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        </div>
      )}
    </section>
  );
}
