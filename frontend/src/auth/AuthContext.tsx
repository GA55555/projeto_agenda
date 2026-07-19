// Estado de autenticacao da SPA. Como o token esta num cookie httpOnly (JS nao
// le), a fonte da verdade e o proprio backend: ao montar, chamamos /auth/me —
// 200 = sessao valida, 401 = anonimo. (Fase 7, §2.2/§4.1)
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { api, setUnauthorizedHandler } from "../api/client";
import type { Me } from "../api/client";

interface AuthState {
  user: Me | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthState | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<Me | null>(null);
  const [loading, setLoading] = useState(true);

  const carregarSessao = useCallback(async () => {
    try {
      setUser(await api.me());
    } catch {
      // 401 (anonimo) ou falha de infra -> sem sessao valida agora.
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  // Qualquer 401 durante a navegacao (sessao expirada) zera o usuario -> a
  // ProtectedRoute redireciona ao login (#2 do review).
  useEffect(() => {
    setUnauthorizedHandler(() => setUser(null));
    void carregarSessao();
    return () => setUnauthorizedHandler(null);
  }, [carregarSessao]);

  const login = useCallback(async (username: string, password: string) => {
    await api.login(username, password);
    setUser(await api.me());
  }, []);

  const logout = useCallback(async () => {
    await api.logout();
    setUser(null);
  }, []);

  const value = useMemo(() => ({ user, loading, login, logout }), [user, loading, login, logout]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth deve ser usado dentro de <AuthProvider>");
  return ctx;
}
