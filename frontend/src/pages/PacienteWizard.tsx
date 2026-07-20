import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { useAsync } from "../utils/useAsync";
import { mensagemDeErro } from "../utils/erro";

const TIPOS_VINCULO = ["mae", "pai", "tutor", "avo", "outro"];
const ROTULO_VINCULO: Record<string, string> = {
  mae: "Mãe",
  pai: "Pai",
  tutor: "Tutor(a)",
  avo: "Avô/Avó",
  outro: "Outro",
};

// Assistente guiado: cria responsável (novo/existente) + paciente + TCLE. O POST
// /pacientes exige tudo junto (§2.2); o wizard conduz a psicóloga pelo invariante.
export function PacienteWizard() {
  const navigate = useNavigate();
  const { data: responsaveis } = useAsync(() => api.responsaveis(), []);

  const [passo, setPasso] = useState(1);
  const [erro, setErro] = useState<string | null>(null);
  const [salvando, setSalvando] = useState(false);
  // Se o responsável "novo" já foi criado numa tentativa anterior, reusa o id
  // no retry em vez de recriar (evitaria CPF duplicado). #2 do review.
  const [respCriadoId, setRespCriadoId] = useState<string | null>(null);

  // Passo 1 — responsável
  const [modo, setModo] = useState<"existente" | "novo">("existente");
  const [respId, setRespId] = useState("");
  const [respNovo, setRespNovo] = useState({ nome: "", cpf: "", telefone: "", email: "" });
  const [tipoVinculo, setTipoVinculo] = useState("mae");
  const [detemGuarda, setDetemGuarda] = useState(true);

  // Passo 2 — paciente
  const [pac, setPac] = useState({ nome: "", data_nascimento: "", sexo: "", observacoes_gerais: "" });

  // Passo 3 — consentimento
  const [tcle, setTcle] = useState({
    finalidade_clinica: "",
    limitacoes_acesso: "",
    termo_versao: "v1",
    termo_texto: "",
  });

  const passo1Ok =
    modo === "existente" ? Boolean(respId) : respNovo.nome.trim() !== "" && respNovo.cpf.trim() !== "";
  const passo2Ok = pac.nome.trim() !== "" && pac.data_nascimento !== "";
  const passo3Ok =
    tcle.finalidade_clinica.trim() !== "" &&
    tcle.limitacoes_acesso.trim() !== "" &&
    tcle.termo_versao.trim() !== "" &&
    tcle.termo_texto.trim() !== "";

  async function criar() {
    setErro(null);
    setSalvando(true);
    try {
      let responsavelId = respId;
      if (modo === "novo") {
        // Só cria uma vez: num retry após falha do paciente, reusa o id.
        if (respCriadoId) {
          responsavelId = respCriadoId;
        } else {
          const r = await api.criarResponsavel({
            nome: respNovo.nome,
            cpf: respNovo.cpf,
            telefone: respNovo.telefone || undefined,
            email: respNovo.email || undefined,
          });
          responsavelId = r.id;
          setRespCriadoId(r.id);
        }
      }
      const criado = await api.criarPaciente({
        nome: pac.nome,
        data_nascimento: pac.data_nascimento,
        sexo: pac.sexo || undefined,
        observacoes_gerais: pac.observacoes_gerais || undefined,
        vinculos: [
          { responsavel_id: responsavelId, tipo_vinculo: tipoVinculo, principal: true, detem_guarda: detemGuarda },
        ],
        consentimento: {
          responsavel_id: responsavelId,
          finalidade_clinica: tcle.finalidade_clinica,
          limitacoes_acesso: tcle.limitacoes_acesso,
          termo_versao: tcle.termo_versao,
          termo_texto: tcle.termo_texto,
        },
      });
      navigate(`/pacientes/${criado.id}`, { replace: true });
    } catch (e) {
      setErro(mensagemDeErro(e, { 409: "CPF do responsável já cadastrado." }));
    } finally {
      setSalvando(false);
    }
  }

  return (
    <section>
      <Link className="voltar muted" to="/pacientes">
        ← Pacientes
      </Link>
      <div className="page-header">
        <h2>Novo paciente</h2>
        <span className="muted">Passo {passo} de 3</span>
      </div>

      {passo === 1 && (
        <div className="card">
          <h3>Responsável legal</h3>
          <div className="opcoes">
            <label className="inline">
              <input type="radio" checked={modo === "existente"} onChange={() => setModo("existente")} />
              Usar existente
            </label>
            <label className="inline">
              <input type="radio" checked={modo === "novo"} onChange={() => setModo("novo")} />
              Cadastrar novo
            </label>
          </div>

          {modo === "existente" ? (
            <label className="campo">
              Responsável*
              <select value={respId} onChange={(e) => setRespId(e.target.value)}>
                <option value="">Selecione…</option>
                {responsaveis?.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.nome} — {r.cpf}
                  </option>
                ))}
              </select>
            </label>
          ) : (
            <>
              <label className="campo">
                Nome*
                <input value={respNovo.nome} onChange={(e) => setRespNovo({ ...respNovo, nome: e.target.value })} />
              </label>
              <label className="campo">
                CPF*
                <input value={respNovo.cpf} onChange={(e) => setRespNovo({ ...respNovo, cpf: e.target.value })} placeholder="apenas números" />
              </label>
              <label className="campo">
                Telefone
                <input value={respNovo.telefone} onChange={(e) => setRespNovo({ ...respNovo, telefone: e.target.value })} />
              </label>
              <label className="campo">
                E-mail
                <input type="email" value={respNovo.email} onChange={(e) => setRespNovo({ ...respNovo, email: e.target.value })} />
              </label>
            </>
          )}

          <label className="campo">
            Tipo de vínculo*
            <select value={tipoVinculo} onChange={(e) => setTipoVinculo(e.target.value)}>
              {TIPOS_VINCULO.map((t) => (
                <option key={t} value={t}>
                  {ROTULO_VINCULO[t]}
                </option>
              ))}
            </select>
          </label>
          <label className="inline">
            <input type="checkbox" checked={detemGuarda} onChange={(e) => setDetemGuarda(e.target.checked)} />
            Detém a guarda
          </label>

          <div className="acoes">
            <button disabled={!passo1Ok} onClick={() => setPasso(2)}>
              Próximo
            </button>
          </div>
        </div>
      )}

      {passo === 2 && (
        <div className="card">
          <h3>Dados do paciente</h3>
          <label className="campo">
            Nome*
            <input value={pac.nome} onChange={(e) => setPac({ ...pac, nome: e.target.value })} />
          </label>
          <label className="campo">
            Data de nascimento*
            <input type="date" value={pac.data_nascimento} onChange={(e) => setPac({ ...pac, data_nascimento: e.target.value })} />
          </label>
          <label className="campo">
            Sexo
            <input value={pac.sexo} onChange={(e) => setPac({ ...pac, sexo: e.target.value })} />
          </label>
          <label className="campo">
            Observações gerais
            <textarea rows={2} value={pac.observacoes_gerais} onChange={(e) => setPac({ ...pac, observacoes_gerais: e.target.value })} />
          </label>
          <div className="acoes">
            <button className="secundario" onClick={() => setPasso(1)}>
              Voltar
            </button>
            <button disabled={!passo2Ok} onClick={() => setPasso(3)}>
              Próximo
            </button>
          </div>
        </div>
      )}

      {passo === 3 && (
        <div className="card">
          <h3>Consentimento (TCLE)</h3>
          <p className="muted">Termo específico — sem cláusulas genéricas (§2.2).</p>
          <label className="campo">
            Finalidade clínica*
            <textarea rows={2} value={tcle.finalidade_clinica} onChange={(e) => setTcle({ ...tcle, finalidade_clinica: e.target.value })} />
          </label>
          <label className="campo">
            Limitações de acesso*
            <textarea rows={2} value={tcle.limitacoes_acesso} onChange={(e) => setTcle({ ...tcle, limitacoes_acesso: e.target.value })} placeholder="ex.: pais têm acesso apenas a informações gerais" />
          </label>
          <label className="campo">
            Versão do termo*
            <input value={tcle.termo_versao} onChange={(e) => setTcle({ ...tcle, termo_versao: e.target.value })} />
          </label>
          <label className="campo">
            Texto do termo*
            <textarea rows={4} value={tcle.termo_texto} onChange={(e) => setTcle({ ...tcle, termo_texto: e.target.value })} />
          </label>
          {erro && <p className="erro">{erro}</p>}
          <div className="acoes">
            <button className="secundario" onClick={() => setPasso(2)}>
              Voltar
            </button>
            <button disabled={!passo3Ok || salvando} onClick={() => void criar()}>
              {salvando ? "Criando…" : "Criar paciente"}
            </button>
          </div>
        </div>
      )}
    </section>
  );
}
