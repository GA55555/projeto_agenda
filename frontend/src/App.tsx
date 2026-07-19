import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider } from "./auth/AuthContext";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { Shell } from "./components/Shell";
import { Agenda } from "./pages/Agenda";
import { EditorEvolucao } from "./pages/EditorEvolucao";
import { FichaPaciente } from "./pages/FichaPaciente";
import { Login } from "./pages/Login";
import { Pacientes } from "./pages/Pacientes";

export function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          {/* Area autenticada: ProtectedRoute -> Shell (nav) -> telas (Outlet). */}
          <Route
            element={
              <ProtectedRoute>
                <Shell />
              </ProtectedRoute>
            }
          >
            <Route path="/" element={<Agenda />} />
            <Route path="/pacientes" element={<Pacientes />} />
            <Route path="/pacientes/:id" element={<FichaPaciente />} />
            <Route path="/pacientes/:id/evolucao/nova" element={<EditorEvolucao />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
