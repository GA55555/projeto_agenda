import { useState } from "react";
import { useAuth } from "../auth/AuthContext";
import { api } from "../api/client";
import { mensagemDeErro } from "../utils/erro";

// Configuração do próprio perfil (Fase 7c): editar nome/e-mail e trocar a senha.
// O backend escopa tudo ao usuário do JWT (usuarios é control-plane sem RLS).
export function Perfil() {
  const { user, refresh } = useAuth();

  // ---- Dados (nome / e-mail) ----
  const [nome, setNome] = useState(user?.nome ?? "");
  const [email, setEmail] = useState(user?.email ?? "");
  // Trocar o e-mail (login) exige re-autenticação: senha atual junto ao PATCH.
  const [senhaEmail, setSenhaEmail] = useState("");
  const [salvandoDados, setSalvandoDados] = useState(false);
  const [erroDados, setErroDados] = useState<string | null>(null);
  const [okDados, setOkDados] = useState(false);

  // ---- Senha ----
  const [senhaAtual, setSenhaAtual] = useState("");
  const [senhaNova, setSenhaNova] = useState("");
  const [senhaConfirma, setSenhaConfirma] = useState("");
  const [salvandoSenha, setSalvandoSenha] = useState(false);
  const [erroSenha, setErroSenha] = useState<string | null>(null);
  const [okSenha, setOkSenha] = useState(false);

  const trocandoEmail = email.trim().toLowerCase() !== (user?.email ?? "").toLowerCase();

  async function salvarDados(e: React.FormEvent) {
    e.preventDefault();
    setErroDados(null);
    setOkDados(false);
    setSalvandoDados(true);
    try {
      // Envia só o que mudou; se nada mudou, não chama.
      const patch: { nome?: string; email?: string; senha_atual?: string } = {};
      if (nome !== user?.nome) patch.nome = nome;
      if (trocandoEmail) {
        patch.email = email;
        patch.senha_atual = senhaEmail; // re-auth exigida pelo backend
      }
      if (Object.keys(patch).length > 0) {
        await api.atualizarPerfil(patch);
      }
      setOkDados(true);
      setSenhaEmail("");
    } catch (e) {
      setErroDados(
        mensagemDeErro(e, {
          409: "Já existe uma conta com este e-mail.",
          400: "Para trocar o e-mail, informe a senha atual correta.",
        }),
      );
      setSalvandoDados(false);
      return; // PATCH falhou de fato — não sincroniza nada
    }
    // O save JÁ deu certo: a falha do refresh (reidratar sidebar) não pode ser
    // reportada como falha do save. Sincroniza o form com o valor normalizado
    // pelo servidor (e-mail minúsculo) para o botão desabilitar corretamente.
    try {
      const me = await refresh();
      setNome(me.nome);
      setEmail(me.email);
    } catch {
      /* sidebar/form atualizam na próxima navegação; o dado está salvo */
    } finally {
      setSalvandoDados(false);
    }
  }

  async function salvarSenha(e: React.FormEvent) {
    e.preventDefault();
    setErroSenha(null);
    setOkSenha(false);
    if (senhaNova !== senhaConfirma) {
      setErroSenha("A confirmação não confere com a nova senha.");
      return;
    }
    if (senhaNova.length < 8) {
      setErroSenha("A nova senha deve ter ao menos 8 caracteres.");
      return;
    }
    // Limite real do bcrypt é 72 BYTES (acentos/emoji ocupam 2-4 em UTF-8);
    // o backend rejeita com 422 — barrar aqui dá mensagem clara.
    if (new TextEncoder().encode(senhaNova).length > 72) {
      setErroSenha("A nova senha é muito longa (máx. 72 bytes em UTF-8).");
      return;
    }
    setSalvandoSenha(true);
    try {
      await api.trocarSenha(senhaAtual, senhaNova);
      setOkSenha(true);
      setSenhaAtual("");
      setSenhaNova("");
      setSenhaConfirma("");
    } catch (e) {
      setErroSenha(mensagemDeErro(e, { 400: "Senha atual incorreta." }));
    } finally {
      setSalvandoSenha(false);
    }
  }

  // Compara contra o valor NORMALIZADO do servidor (e-mail é case-insensitive):
  // sem isso, salvar 'ana@CLINICA.com' deixaria o form "sujo" para sempre.
  const dadosInalterados = nome === user?.nome && !trocandoEmail;

  return (
    <section>
      <div className="page-header">
        <h2>Meu perfil</h2>
      </div>

      <form className="card" onSubmit={salvarDados}>
        <h3>Dados da conta</h3>
        <label className="campo">
          Nome
          <input value={nome} onChange={(e) => setNome(e.target.value)} required maxLength={200} />
        </label>
        <label className="campo">
          E-mail (usado para entrar)
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </label>
        {trocandoEmail && (
          <label className="campo">
            Senha atual (obrigatória para trocar o e-mail)
            <input
              type="password"
              value={senhaEmail}
              onChange={(e) => setSenhaEmail(e.target.value)}
              autoComplete="current-password"
              required
            />
          </label>
        )}
        {erroDados && <p className="erro">{erroDados}</p>}
        {okDados && <p className="sucesso">Dados salvos.</p>}
        <button
          type="submit"
          disabled={salvandoDados || dadosInalterados || (trocandoEmail && !senhaEmail)}
        >
          {salvandoDados ? "Salvando…" : "Salvar dados"}
        </button>
      </form>

      <form className="card" onSubmit={salvarSenha}>
        <h3>Trocar senha</h3>
        <label className="campo">
          Senha atual
          <input
            type="password"
            value={senhaAtual}
            onChange={(e) => setSenhaAtual(e.target.value)}
            autoComplete="current-password"
            required
          />
        </label>
        <label className="campo">
          Nova senha (mín. 8 caracteres)
          <input
            type="password"
            value={senhaNova}
            onChange={(e) => setSenhaNova(e.target.value)}
            autoComplete="new-password"
            required
            minLength={8}
          />
        </label>
        <label className="campo">
          Confirmar nova senha
          <input
            type="password"
            value={senhaConfirma}
            onChange={(e) => setSenhaConfirma(e.target.value)}
            autoComplete="new-password"
            required
          />
        </label>
        {erroSenha && <p className="erro">{erroSenha}</p>}
        {okSenha && <p className="sucesso">Senha alterada.</p>}
        <button type="submit" disabled={salvandoSenha}>
          {salvandoSenha ? "Alterando…" : "Alterar senha"}
        </button>
      </form>
    </section>
  );
}
