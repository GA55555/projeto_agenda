import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { Tenant } from "../api/client";
import { useAuth } from "../auth/AuthContext";

// Home da 7a: prova o loop de auth (sessao via cookie) e uma chamada autenticada
// a API atraves do proxy (/api). As telas de dominio entram na 7b.
export function Home() {
  const { user, logout } = useAuth();
  const [tenant, setTenant] = useState<Tenant | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    api
      .tenantAtual()
      .then(setTenant)
      .catch(() => setErro("Nao foi possivel carregar a clinica."));
  }, []);

  return (
    <div className="app">
      <header className="topo">
        <strong>{tenant ? tenant.nome : "Agenda de Atendimentos"}</strong>
        <button className="link" onClick={() => void logout()}>
          Sair
        </button>
      </header>
      <main className="conteudo">
        <h2>Sessão ativa</h2>
        {erro && <p className="erro">{erro}</p>}
        <p className="muted">Papel: {user?.papel}</p>
        <p className="muted">
          Clínica (RLS): {tenant ? `${tenant.nome} (${tenant.slug})` : "…"}
        </p>
        <p className="nota">
          Próximo (Fase 7b): agenda, ficha do paciente e o editor de evolução com
          geração assistida por IA e fluxo de aprovação.
        </p>
      </main>
    </div>
  );
}
