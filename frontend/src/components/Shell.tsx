// Layout das telas autenticadas: barra de navegacao + area de conteudo (Outlet).
import { useEffect, useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { api } from "../api/client";
import type { Tenant } from "../api/client";
import { useAuth } from "../auth/AuthContext";

export function Shell() {
  const { logout } = useAuth();
  const [tenant, setTenant] = useState<Tenant | null>(null);

  useEffect(() => {
    api.tenantAtual().then(setTenant).catch(() => setTenant(null));
  }, []);

  return (
    <div className="app">
      <header className="topo">
        <strong>{tenant?.nome ?? "Agenda de Atendimentos"}</strong>
        <nav className="nav">
          <NavLink to="/" end>
            Agenda
          </NavLink>
          <NavLink to="/pacientes">Pacientes</NavLink>
        </nav>
        <button className="link" onClick={() => void logout()}>
          Sair
        </button>
      </header>
      <main className="conteudo">
        <Outlet />
      </main>
    </div>
  );
}
