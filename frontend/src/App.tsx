import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider } from "./auth/AuthContext";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { Shell } from "./components/Shell";
import { Agenda } from "./pages/Agenda";
import { AgendamentoDetalhe } from "./pages/AgendamentoDetalhe";
import { AgendamentoForm } from "./pages/AgendamentoForm";
import { Dashboard } from "./pages/Dashboard";
import { EditorEvolucao } from "./pages/EditorEvolucao";
import { FichaPaciente } from "./pages/FichaPaciente";
import { Login } from "./pages/Login";
import { PacienteWizard } from "./pages/PacienteWizard";
import { Perfil } from "./pages/Perfil";
import { Pacientes } from "./pages/Pacientes";
import { Responsaveis } from "./pages/Responsaveis";
import { ResponsavelDetalhe } from "./pages/ResponsavelDetalhe";
import { ResponsavelForm } from "./pages/ResponsavelForm";

export function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          {/* Area autenticada: ProtectedRoute -> Shell (sidebar) -> telas (Outlet). */}
          <Route
            element={
              <ProtectedRoute>
                <Shell />
              </ProtectedRoute>
            }
          >
            <Route path="/" element={<Dashboard />} />
            <Route path="/agenda" element={<Agenda />} />
            <Route path="/agenda/novo" element={<AgendamentoForm />} />
            <Route path="/agenda/:id" element={<AgendamentoDetalhe />} />
            <Route path="/pacientes" element={<Pacientes />} />
            <Route path="/pacientes/arquivados" element={<Pacientes modo="arquivados" />} />
            <Route path="/pacientes/novo" element={<PacienteWizard />} />
            <Route path="/pacientes/:id" element={<FichaPaciente />} />
            <Route path="/pacientes/:id/evolucao/nova" element={<EditorEvolucao />} />
            <Route path="/responsaveis" element={<Responsaveis />} />
            <Route path="/responsaveis/novo" element={<ResponsavelForm />} />
            <Route path="/responsaveis/:id" element={<ResponsavelDetalhe />} />
            <Route path="/responsaveis/:id/editar" element={<ResponsavelForm />} />
            <Route path="/perfil" element={<Perfil />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
