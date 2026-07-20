import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ApiError, api } from "../api/client";
import { useAsync } from "../utils/useAsync";
import { fmtDataHora } from "../utils/format";

// Coração da 7b: nota do dia -> rascunho da IA (túnel opaco, §3.4) -> revisão da
// psicóloga (texto DESANONIMIZADO) -> aprovar e gravar (POST /evolucoes).
// Fase 7e: a evolução nasce ATRELADA a um atendimento (agendamento) do paciente
// — a data do atendimento vem dele.
export function EditorEvolucao() {
  const { id = "" } = useParams();
  const navigate = useNavigate();

  // Atendimentos REALIZADOS do paciente (a evolução documenta uma sessão que
  // ocorreu — o backend exige status 'realizado'), mais recentes primeiro.
  const { data: atendimentos, loading: carregandoAg } = useAsync(async () => {
    const ags = await api.agendamentos({ paciente_id: id });
    return ags
      .filter((a) => a.status === "realizado")
      .sort((a, b) => b.inicio.localeCompare(a.inicio));
  }, [id]);

  const [agendamentoId, setAgendamentoId] = useState("");
  const [nota, setNota] = useState("");
  const [texto, setTexto] = useState(""); // rascunho editável (o que será gravado)
  const [destaques, setDestaques] = useState<string[]>([]);
  const [chunks, setChunks] = useState<number | null>(null);
  const [gerando, setGerando] = useState(false);
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  // Ao navegar entre pacientes o componente NÃO remonta (só o :id muda) — zera
  // a seleção/rascunho para não vazar dados de um paciente para outro.
  useEffect(() => {
    setAgendamentoId("");
    setNota("");
    setTexto("");
    setDestaques([]);
    setChunks(null);
    setErro(null);
  }, [id]);

  function traduzErro(e: unknown): string {
    if (e instanceof ApiError) {
      // 422 tem causas distintas (sem TCLE, paciente inexistente, guard-rail de
      // PII) — cada uma com seu `detail`. Mostramos a mensagem real do backend,
      // não uma suposição (não confundir um abort de PII §3.4 com consentimento).
      if (e.status === 503) return "Geração indisponível (IA/OpenAI). Tente novamente.";
      return e.message;
    }
    return "Falha de conexão. Tente novamente.";
  }

  async function gerar() {
    // Nao descartar silenciosamente um rascunho ja revisado (#5 do review).
    if (texto.trim().length > 0 && !window.confirm("Isso substitui o rascunho atual. Continuar?")) {
      return;
    }
    setErro(null);
    setGerando(true);
    try {
      const r = await api.gerarRascunho(id, nota);
      setTexto(r.evolucao);
      setDestaques(r.destaques);
      setChunks(r.chunks_contexto);
    } catch (e) {
      setErro(traduzErro(e));
    } finally {
      setGerando(false);
    }
  }

  async function aprovarEGravar() {
    setErro(null);
    setSalvando(true);
    try {
      await api.criarEvolucao(id, agendamentoId, texto);
      navigate(`/pacientes/${id}`, { replace: true });
    } catch (e) {
      setErro(traduzErro(e));
    } finally {
      setSalvando(false);
    }
  }

  return (
    <section>
      <Link className="voltar muted" to={`/pacientes/${id}`}>
        ← Ficha do paciente
      </Link>
      <div className="page-header">
        <h2>Nova evolução</h2>
      </div>

      <div className="card">
        <label className="campo">
          Atendimento (a evolução fica atrelada a ele)*
          {carregandoAg ? (
            <p className="muted">Carregando atendimentos…</p>
          ) : !atendimentos || atendimentos.length === 0 ? (
            <p className="aviso">
              Este paciente não tem atendimentos <strong>realizados</strong>. Marque o atendimento
              como “Realizado” na agenda primeiro — a evolução documenta uma sessão que ocorreu.
            </p>
          ) : (
            <select value={agendamentoId} onChange={(e) => setAgendamentoId(e.target.value)} required>
              <option value="">Selecione o atendimento…</option>
              {atendimentos.map((a) => (
                <option key={a.id} value={a.id}>
                  {fmtDataHora(a.inicio)}
                  {a.tipo ? ` — ${a.tipo}` : ""}
                </option>
              ))}
            </select>
          )}
        </label>
        <label className="campo">
          Nota do dia
          <textarea
            rows={4}
            value={nota}
            onChange={(e) => setNota(e.target.value)}
            placeholder="Descreva o atendimento de hoje…"
          />
        </label>
        <button onClick={() => void gerar()} disabled={gerando || nota.trim().length === 0}>
          {gerando ? "Gerando…" : "Gerar rascunho (IA)"}
        </button>
      </div>

      {erro && <p className="erro">{erro}</p>}

      {(texto || destaques.length > 0) && (
        <div className="card">
          <label className="campo">
            Evolução (revise antes de gravar)
            <textarea rows={10} value={texto} onChange={(e) => setTexto(e.target.value)} />
          </label>

          {destaques.length > 0 && (
            <div className="nota">
              <strong>Destaques (apoio à revisão — não são gravados)</strong>
              <ul className="lista">
                {destaques.map((d, i) => (
                  <li key={i}>{d}</li>
                ))}
              </ul>
            </div>
          )}
          {chunks !== null && (
            <p className="muted">Trechos do histórico usados pela IA: {chunks}</p>
          )}

          {!agendamentoId && (
            <p className="aviso">Selecione acima o atendimento ao qual esta evolução pertence.</p>
          )}
          <button
            onClick={() => void aprovarEGravar()}
            disabled={salvando || texto.trim().length === 0 || !agendamentoId}
          >
            {salvando ? "Gravando…" : "Aprovar e gravar"}
          </button>
        </div>
      )}
    </section>
  );
}
