import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { Paciente } from "../api/client";
import { fmtData, fmtDataHora, idadeEmAnos, iniciais, rotuloSexo } from "../utils/format";
import { useAcao } from "../utils/useAcao";

const LIMITE_OBS = 1000;

export function PacienteCard({
  paciente,
  onReativar,
}: {
  paciente: Paciente;
  onReativar?: () => Promise<void>;
}) {
  const [obs, setObs] = useState(paciente.observacoes_gerais ?? "");
  const [editando, setEditando] = useState(false);
  const [rascunho, setRascunho] = useState(obs);
  const { ocupado, acaoErro, executar } = useAcao();
  const idade = idadeEmAnos(paciente.data_nascimento);
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
    <article className={`pac-card pac-card-compacto${paciente.ativo ? "" : " inativo"}`}>
      <div className="pac-topo">
        <span className="pac-avatar" aria-hidden="true">
          {iniciais(paciente.nome)}
        </span>
        <div className="pac-id">
          <div className="pac-nome">
            <Link to={`/pacientes/${paciente.id}`}>{paciente.nome}</Link>
          </div>
          <div className="pac-meta">{meta}</div>
          {!paciente.ativo && paciente.arquivado_em && (
            <div className="pac-arquivo-meta">Arquivado em {fmtDataHora(paciente.arquivado_em)}</div>
          )}
        </div>
        {!paciente.ativo && <span className="tag tag-inativo">Arquivado</span>}
        <div className="pac-acoes">
          <Link className="botao secundario mini" to={`/pacientes/${paciente.id}`}>
            Abrir ficha
          </Link>
          {onReativar && (
            <button
              type="button"
              className="mini"
              disabled={ocupado}
              onClick={() => void executar(onReativar)}
            >
              {ocupado ? "Reativando…" : "Reativar"}
            </button>
          )}
        </div>
      </div>

      {(obs || paciente.ativo || paciente.motivo_arquivamento) && (
        <details className="pac-obs">
          <summary>
            Observações{obs ? "" : " (vazio)"}
          </summary>
          {paciente.motivo_arquivamento && (
            <p className="pac-motivo"><strong>Motivo do arquivamento:</strong> {paciente.motivo_arquivamento}</p>
          )}
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
              <div className="acoes-linha">
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
          ) : (
            <div className="pac-obs-conteudo">
              <p className={obs ? "pac-obs-texto" : "pac-obs-vazio"}>
                {obs || "Sem observações."}
              </p>
              {paciente.ativo && (
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
          )}
        </details>
      )}
      {acaoErro && <p className="erro">{acaoErro}</p>}
    </article>
  );
}
