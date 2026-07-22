import { useState } from "react";
import { Link, NavLink, useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import { PacienteCard } from "../components/PacienteCard";
import { normalizarBusca } from "../utils/format";
import { useAsync } from "../utils/useAsync";

type Modo = "ativos" | "arquivados";
type Ordem = "az" | "za";

export function Pacientes({ modo = "ativos" }: { modo?: Modo }) {
  const [params, setParams] = useSearchParams();
  // Nome clinico fica somente na memoria da tela: nunca entra em URL, logs ou Referer.
  const [busca, setBusca] = useState("");
  const ordem: Ordem = params.get("ordem") === "za" ? "za" : "az";
  const { data: pacientes, loading, error, reload } = useAsync(
    () => api.pacientes(modo === "ativos"),
    [modo],
  );

  function mudarOrdem(valor: Ordem) {
    const proximos = new URLSearchParams(params);
    proximos.delete("q"); // defesa para links gerados durante o desenvolvimento da 7i
    if (valor === "za") proximos.set("ordem", valor);
    else proximos.delete("ordem");
    setParams(proximos, { replace: true });
  }

  const termo = normalizarBusca(busca);
  const visiveis = [...(pacientes ?? [])]
    .filter((p) => !termo || normalizarBusca(p.nome).includes(termo))
    .sort((a, b) => {
      const valor = a.nome.localeCompare(b.nome, "pt-BR", { sensitivity: "base" });
      return ordem === "az" ? valor : -valor;
    });

  return (
    <section>
      <div className="page-header">
        <div>
          <h2>{modo === "ativos" ? "Pacientes" : "Pacientes arquivados"}</h2>
          <p className="muted">
            {modo === "ativos"
              ? "Localize rapidamente um cadastro ativo."
              : "Cadastros preservados fora das listas de atendimento ativo."}
          </p>
        </div>
        {modo === "ativos" && (
          <Link className="botao" to="/pacientes/novo">
            Novo paciente
          </Link>
        )}
      </div>

      <nav className="abas-lista" aria-label="Situação dos pacientes">
        <NavLink to="/pacientes" end>
          Ativos
        </NavLink>
        <NavLink to="/pacientes/arquivados">Arquivados</NavLink>
      </nav>

      <div className="filtros-lista">
        <label className="campo-busca">
          <span>Buscar pelo nome</span>
          <input
            type="search"
            value={busca}
            placeholder="Digite o nome da criança"
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

      {loading ? (
        <p className="muted">Carregando pacientes…</p>
      ) : error ? (
        <p className="erro">{error}</p>
      ) : visiveis.length === 0 ? (
        <p className="vazio">
          {termo
            ? `Nenhum paciente encontrado para “${busca.trim()}”.`
            : modo === "ativos"
              ? "Nenhum paciente ativo cadastrado."
              : "Nenhum paciente arquivado."}
        </p>
      ) : (
        <>
          <p className="resultado-contagem">
            {visiveis.length} {visiveis.length === 1 ? "paciente encontrado" : "pacientes encontrados"}
          </p>
          <div className="pac-lista">
            {visiveis.map((p) => (
              <PacienteCard
                key={p.id}
                paciente={p}
                onReativar={
                  modo === "arquivados"
                    ? async () => {
                        await api.reativarPaciente(p.id);
                        reload();
                      }
                    : undefined
                }
              />
            ))}
          </div>
        </>
      )}
    </section>
  );
}
