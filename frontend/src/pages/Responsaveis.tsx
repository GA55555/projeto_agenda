import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import { normalizarBusca } from "../utils/format";
import { useAsync } from "../utils/useAsync";

type Ordem = "az" | "za";

export function Responsaveis() {
  const [params, setParams] = useSearchParams();
  // Nome do responsavel/crianca permanece local para nao vazar PII na URL.
  const [busca, setBusca] = useState("");
  const ordem: Ordem = params.get("ordem") === "za" ? "za" : "az";
  const { data: responsaveis, loading, error } = useAsync(() => api.responsaveis(), []);

  function mudarOrdem(valor: Ordem) {
    const proximos = new URLSearchParams(params);
    proximos.delete("q");
    if (valor === "za") proximos.set("ordem", valor);
    else proximos.delete("ordem");
    setParams(proximos, { replace: true });
  }

  const termo = normalizarBusca(busca);
  const visiveis = [...(responsaveis ?? [])]
    .filter((r) => {
      if (!termo) return true;
      const nomes = [r.nome, ...r.pacientes.map((p) => p.nome)].map(normalizarBusca);
      return nomes.some((nome) => nome.includes(termo));
    })
    .sort((a, b) => {
      const valor = a.nome.localeCompare(b.nome, "pt-BR", { sensitivity: "base" });
      return ordem === "az" ? valor : -valor;
    });

  return (
    <section>
      <div className="page-header">
        <div>
          <h2>Responsáveis</h2>
          <p className="muted">Busque pelo responsável ou pelo nome da criança vinculada.</p>
        </div>
        <Link className="botao" to="/responsaveis/novo">
          Novo responsável
        </Link>
      </div>

      <div className="filtros-lista">
        <label className="campo-busca">
          <span>Buscar responsável ou criança</span>
          <input
            type="search"
            value={busca}
            placeholder="Digite um nome"
            autoComplete="off"
            onChange={(e) => setBusca(e.target.value)}
          />
        </label>
        <label>
          <span>Ordenar</span>
          <select value={ordem} onChange={(e) => mudarOrdem(e.target.value as Ordem)}>
            <option value="az">Nome A–Z</option>
            <option value="za">Nome Z–A</option>
          </select>
        </label>
      </div>

      {loading && <p className="muted">Carregando…</p>}
      {error && <p className="erro">{error}</p>}
      {!loading && !error &&
        (visiveis.length === 0 ? (
          <p className="vazio">
            {termo ? `Nenhum responsável encontrado para “${busca.trim()}”.` : "Nenhum responsável cadastrado."}
          </p>
        ) : (
          <>
            <p className="resultado-contagem">
              {visiveis.length} {visiveis.length === 1 ? "responsável encontrado" : "responsáveis encontrados"}
            </p>
            <div className="card tabela-container">
              <table className="tabela">
                <thead>
                  <tr>
                    <th>Nome</th>
                    <th>Crianças vinculadas</th>
                    <th>Telefone</th>
                    <th>E-mail</th>
                  </tr>
                </thead>
                <tbody>
                  {visiveis.map((r) => (
                    <tr key={r.id}>
                      <td><Link to={`/responsaveis/${r.id}`}>{r.nome}</Link></td>
                      <td>
                        {r.pacientes.length === 0
                          ? "—"
                          : r.pacientes.map((p, i) => (
                              <span key={p.id}>
                                {i > 0 && ", "}
                                <Link className={p.ativo ? "" : "muted"} to={`/pacientes/${p.id}`}>
                                  {p.nome}{p.ativo ? "" : " (arquivado)"}
                                </Link>
                              </span>
                            ))}
                      </td>
                      <td>{r.telefone ?? "—"}</td>
                      <td>{r.email ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        ))}
    </section>
  );
}
