import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { Paciente } from "../api/client";
import { fmtData, idadeEmAnos, iniciais, rotuloSexo } from "../utils/format";
import { useAcao } from "../utils/useAcao";

// Limite de caracteres da observação (igual ao do backend: observacoes_gerais
// é String(1000)). A caixa tem altura fixa; o cap evita texto sem fim.
const LIMITE_OBS = 1000;

// Cartão de paciente (redesenho 7g): avatar de iniciais, nome, idade·sexo·nasc.
// e um espaço para as OBSERVAÇÕES da psicóloga — editável inline (ela anota
// direto no cartão; grava via PATCH /pacientes).
export function PacienteCard({ paciente }: { paciente: Paciente }) {
  const [obs, setObs] = useState(paciente.observacoes_gerais ?? "");
  const [editando, setEditando] = useState(false);
  const [rascunho, setRascunho] = useState(obs);
  const { ocupado, acaoErro, executar } = useAcao();

  const idade = idadeEmAnos(paciente.data_nascimento);
  // Idade · sexo · nascimento — preenche o cartão e permite desambiguar homônimos.
  const meta = [
    idade != null ? `${idade} ${idade === 1 ? "ano" : "anos"}` : "idade —",
    paciente.sexo ? rotuloSexo(paciente.sexo) : null,
    `nasc. ${fmtData(paciente.data_nascimento)}`,
  ]
    .filter(Boolean)
    .join(" · ");

  function salvar() {
    void executar(async () => {
      await api.atualizarPaciente(paciente.id, { observacoes_gerais: rascunho });
      setObs(rascunho);
      setEditando(false);
    });
  }

  return (
    <div className={`pac-card${paciente.ativo ? "" : " inativo"}`}>
      <div className="pac-topo">
        <span className="pac-avatar" aria-hidden="true">
          {iniciais(paciente.nome)}
        </span>
        <div className="pac-id">
          <div className="pac-nome">
            <Link to={`/pacientes/${paciente.id}`}>{paciente.nome}</Link>
          </div>
          <div className="pac-meta">{meta}</div>
        </div>
        {!paciente.ativo && <span className="tag tag-inativo">Arquivado</span>}
      </div>

      <div className="pac-obs">
        <div className="pac-obs-label">
          <span>Observações</span>
          {!editando && (
            <button
              type="button"
              className="pac-obs-editar"
              onClick={() => {
                setRascunho(obs);
                setEditando(true);
              }}
            >
              {obs ? "Editar" : "Adicionar"}
            </button>
          )}
        </div>
        {editando ? (
          <>
            <textarea
              value={rascunho}
              maxLength={LIMITE_OBS}
              autoFocus
              placeholder="Anotações rápidas sobre o paciente…"
              onChange={(e) => setRascunho(e.target.value)}
            />
            <p className={`pac-obs-contador${rascunho.length >= LIMITE_OBS ? " no-limite" : ""}`}>
              {rascunho.length}/{LIMITE_OBS}
            </p>
            {acaoErro && <p className="erro">{acaoErro}</p>}
            <div className="acoes-linha" style={{ marginTop: "0.45rem" }}>
              <button type="button" className="mini" disabled={ocupado} onClick={salvar}>
                {ocupado ? "Salvando…" : "Salvar"}
              </button>
              <button
                type="button"
                className="mini secundario"
                disabled={ocupado}
                onClick={() => setEditando(false)}
              >
                Cancelar
              </button>
            </div>
          </>
        ) : obs ? (
          <p className="pac-obs-texto">{obs}</p>
        ) : (
          <p className="pac-obs-vazio">Sem observações.</p>
        )}
      </div>
    </div>
  );
}
