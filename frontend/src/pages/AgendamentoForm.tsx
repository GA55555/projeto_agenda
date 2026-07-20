import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { useAsync } from "../utils/useAsync";
import { mensagemDeErro } from "../utils/erro";


export function AgendamentoForm() {
  const navigate = useNavigate();
  const { data: pacientes, loading, error } = useAsync(() => api.pacientes(), []);

  const [pacienteId, setPacienteId] = useState("");
  const [inicio, setInicio] = useState("");
  const [fim, setFim] = useState("");
  const [tipo, setTipo] = useState("");
  const [observacao, setObservacao] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [salvando, setSalvando] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setErro(null);
    // datetime-local ("2026-08-01T14:00", hora local) -> instante ISO.
    const di = new Date(inicio);
    const df = new Date(fim);
    if (Number.isNaN(di.getTime()) || Number.isNaN(df.getTime())) {
      setErro("Informe início e fim válidos.");
      return;
    }
    if (df <= di) {
      setErro("O fim deve ser depois do início.");
      return;
    }
    setSalvando(true);
    try {
      await api.criarAgendamento({
        paciente_id: pacienteId,
        inicio: di.toISOString(),
        fim: df.toISOString(),
        tipo: tipo || undefined,
        observacao: observacao || undefined,
      });
      navigate("/agenda", { replace: true });
    } catch (e) {
      setErro(
        mensagemDeErro(e, {
          409: "Conflito de horário: sobrepõe outro atendimento.",
          422: "Paciente inválido ou horário incoerente.",
        }),
      );
    } finally {
      setSalvando(false);
    }
  }

  if (loading) return <p className="muted">Carregando…</p>;
  if (error) return <p className="erro">{error}</p>;

  return (
    <section>
      <Link className="voltar muted" to="/agenda">
        ← Agenda
      </Link>
      <div className="page-header">
        <h2>Novo agendamento</h2>
      </div>
      <form className="card" onSubmit={onSubmit}>
        <label className="campo">
          Paciente*
          <select value={pacienteId} onChange={(e) => setPacienteId(e.target.value)} required>
            <option value="">Selecione…</option>
            {pacientes?.map((p) => (
              <option key={p.id} value={p.id}>
                {p.nome}
              </option>
            ))}
          </select>
        </label>
        <label className="campo">
          Início*
          <input type="datetime-local" value={inicio} onChange={(e) => setInicio(e.target.value)} required />
        </label>
        <label className="campo">
          Fim*
          <input type="datetime-local" value={fim} onChange={(e) => setFim(e.target.value)} required />
        </label>
        <label className="campo">
          Tipo
          <input value={tipo} onChange={(e) => setTipo(e.target.value)} placeholder="ex.: sessão, avaliação" />
        </label>
        <label className="campo">
          Observação
          <textarea rows={2} value={observacao} onChange={(e) => setObservacao(e.target.value)} />
        </label>
        {erro && <p className="erro">{erro}</p>}
        <button type="submit" disabled={salvando || !pacienteId}>
          {salvando ? "Agendando…" : "Agendar"}
        </button>
      </form>
    </section>
  );
}
