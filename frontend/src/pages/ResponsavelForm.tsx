import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api/client";
import type { ResponsavelCreate } from "../api/client";
import { mensagemDeErro } from "../utils/erro";

const VAZIO: ResponsavelCreate = {
  nome: "",
  cpf: "",
  data_nascimento: "",
  telefone: "",
  email: "",
  endereco: "",
};

// Criar (sem id) ou editar (com id). Na edição o backend (ResponsavelUpdate) só
// aceita nome/telefone/e-mail — CPF/nascimento/endereço ficam somente-leitura.
export function ResponsavelForm() {
  const { id } = useParams();
  const editando = Boolean(id);
  const navigate = useNavigate();

  const [f, setF] = useState<ResponsavelCreate>(VAZIO);
  const [erro, setErro] = useState<string | null>(null);
  const [salvando, setSalvando] = useState(false);
  const [carregando, setCarregando] = useState(editando);

  useEffect(() => {
    if (!id) return;
    api
      .responsavel(id)
      .then((r) =>
        setF({
          nome: r.nome,
          cpf: r.cpf,
          data_nascimento: r.data_nascimento ?? "",
          telefone: r.telefone ?? "",
          email: r.email ?? "",
          endereco: r.endereco ?? "",
        }),
      )
      .catch((e) => setErro(mensagemDeErro(e)))
      .finally(() => setCarregando(false));
  }, [id]);

  function set<K extends keyof ResponsavelCreate>(k: K, v: string) {
    setF((prev) => ({ ...prev, [k]: v }));
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setErro(null);
    setSalvando(true);
    try {
      if (editando && id) {
        // PATCH só aceita nome/telefone/email.
        await api.atualizarResponsavel(id, {
          nome: f.nome,
          telefone: f.telefone || undefined,
          email: f.email || undefined,
        });
        navigate(`/responsaveis/${id}`, { replace: true });
      } else {
        // Campos vazios opcionais viram undefined (não enviar string vazia).
        const criado = await api.criarResponsavel({
          nome: f.nome,
          cpf: f.cpf,
          data_nascimento: f.data_nascimento || undefined,
          telefone: f.telefone || undefined,
          email: f.email || undefined,
          endereco: f.endereco || undefined,
        });
        navigate(`/responsaveis/${criado.id}`, { replace: true });
      }
    } catch (e) {
      setErro(mensagemDeErro(e, { 409: "Já existe um responsável com este CPF." }));
    } finally {
      setSalvando(false);
    }
  }

  if (carregando) return <p className="muted">Carregando…</p>;

  return (
    <section>
      <Link className="voltar muted" to={editando ? `/responsaveis/${id}` : "/responsaveis"}>
        ← Voltar
      </Link>
      <div className="page-header">
        <h2>{editando ? "Editar responsável" : "Novo responsável"}</h2>
      </div>
      <form className="card" onSubmit={onSubmit}>
        <label className="campo">
          Nome*
          <input value={f.nome} onChange={(e) => set("nome", e.target.value)} required />
        </label>
        <label className="campo">
          CPF{editando ? " (não editável)" : "*"}
          <input
            value={f.cpf}
            onChange={(e) => set("cpf", e.target.value)}
            required={!editando}
            disabled={editando}
            placeholder="apenas números"
          />
        </label>
        <label className="campo">
          Data de nascimento{editando ? " (não editável)" : ""}
          <input
            type="date"
            value={f.data_nascimento}
            onChange={(e) => set("data_nascimento", e.target.value)}
            disabled={editando}
          />
        </label>
        <label className="campo">
          Telefone
          <input value={f.telefone} onChange={(e) => set("telefone", e.target.value)} />
        </label>
        <label className="campo">
          E-mail
          <input type="email" value={f.email} onChange={(e) => set("email", e.target.value)} />
        </label>
        <label className="campo">
          Endereço{editando ? " (não editável)" : ""}
          <input
            value={f.endereco}
            onChange={(e) => set("endereco", e.target.value)}
            disabled={editando}
          />
        </label>
        {erro && <p className="erro">{erro}</p>}
        <button type="submit" disabled={salvando}>
          {salvando ? "Salvando…" : editando ? "Salvar" : "Criar responsável"}
        </button>
      </form>
    </section>
  );
}
