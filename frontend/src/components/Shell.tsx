// Layout autenticado: sidebar (navegação + perfil) + área de conteúdo (Outlet).
import { useEffect, useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { api } from "../api/client";
import type { Tenant } from "../api/client";
import { useAuth } from "../auth/AuthContext";

const ITENS = [
  { to: "/", rotulo: "Dashboard", end: true },
  { to: "/agenda", rotulo: "Agenda", end: false },
  { to: "/pacientes", rotulo: "Pacientes", end: false },
  { to: "/responsaveis", rotulo: "Responsáveis", end: false },
];

const PAPEL_ROTULO: Record<string, string> = {
  psicologa: "Psicóloga",
  admin: "Administração",
};

export function Shell() {
  const { user, logout } = useAuth();
  const [tenant, setTenant] = useState<Tenant | null>(null);

  useEffect(() => {
    api.tenantAtual().then(setTenant).catch(() => setTenant(null));
  }, []);

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="marca">{tenant?.nome ?? "Agenda"}</div>
        <nav className="sidebar-nav">
          {ITENS.map((i) => (
            <NavLink key={i.to} to={i.to} end={i.end}>
              {i.rotulo}
            </NavLink>
          ))}
        </nav>
        <div className="perfil">
          <div>
            <div className="nome">{user?.nome ?? "—"}</div>
            <div className="email">{user?.email}</div>
          </div>
          <span className="papel">{PAPEL_ROTULO[user?.papel ?? ""] ?? user?.papel}</span>
          <div className="perfil-acoes">
            <NavLink className="botao secundario mini" to="/perfil">
              Meu perfil
            </NavLink>
            <button className="secundario mini" onClick={() => void logout()}>
              Sair
            </button>
          </div>
        </div>
      </aside>
      <main className="main">
        <Outlet />
      </main>
    </div>
  );
}
