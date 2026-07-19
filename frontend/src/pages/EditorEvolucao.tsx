import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ApiError, api } from "../api/client";

// Coração da 7b: nota do dia -> rascunho da IA (túnel opaco, §3.4) -> revisão da
// psicóloga (texto DESANONIMIZADO) -> aprovar e gravar (POST /evolucoes).
export function EditorEvolucao() {
  const { id = "" } = useParams();
  const navigate = useNavigate();

  const [nota, setNota] = useState("");
  const [texto, setTexto] = useState(""); // rascunho editável (o que será gravado)
  const [destaques, setDestaques] = useState<string[]>([]);
  const [chunks, setChunks] = useState<number | null>(null);
  const [gerando, setGerando] = useState(false);
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

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
      await api.criarEvolucao(id, texto);
      navigate(`/pacientes/${id}`, { replace: true });
    } catch (e) {
      setErro(traduzErro(e));
    } finally {
      setSalvando(false);
    }
  }

  return (
    <section>
      <p className="muted">
        <Link to={`/pacientes/${id}`}>← Ficha do paciente</Link>
      </p>
      <h2>Nova evolução</h2>

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

      {erro && <p className="erro">{erro}</p>}

      {(texto || destaques.length > 0) && (
        <>
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

          <button onClick={() => void aprovarEGravar()} disabled={salvando || texto.trim().length === 0}>
            {salvando ? "Gravando…" : "Aprovar e gravar"}
          </button>
        </>
      )}
    </section>
  );
}
