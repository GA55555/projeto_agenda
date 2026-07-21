import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { PacienteCard } from "../components/PacienteCard";
import { useAsync } from "../utils/useAsync";

export function Pacientes() {
  const { data: pacientes, loading, error } = useAsync(() => api.pacientes(), []);
  // Arquivados (ativo=false) ficam fora da vista padrão, mas acessíveis (7e).
  const [mostrarArquivados, setMostrarArquivados] = useState(false);

  if (loading) return <p className="muted">Carregando pacientes…</p>;
  if (error) return <p className="erro">{error}</p>;

  const visiveis = (pacientes ?? []).filter((p) => mostrarArquivados || p.ativo);
  const arquivados = (pacientes ?? []).filter((p) => !p.ativo).length;

  return (
    <section>
      <div className="page-header">
        <h2>Pacientes</h2>
        <Link className="botao" to="/pacientes/novo">
          Novo paciente
        </Link>
      </div>
      {arquivados > 0 && (
        <label className="inline">
          <input
            type="checkbox"
            checked={mostrarArquivados}
            onChange={(e) => setMostrarArquivados(e.target.checked)}
          />
          Mostrar arquivados ({arquivados})
        </label>
      )}
      {visiveis.length === 0 ? (
        <p className="vazio">
          {pacientes && pacientes.length > 0
            ? "Nenhum paciente ativo — veja os arquivados acima."
            : "Nenhum paciente cadastrado."}
        </p>
      ) : (
        <div className="pac-grid">
          {visiveis.map((p) => (
            <PacienteCard key={p.id} paciente={p} />
          ))}
        </div>
      )}
    </section>
  );
}
