import { useEffect, useState } from "react";

// Carrega dados de forma assincrona com estados {data, loading, error} e um
// `reload()`. Evita repetir o mesmo try/loading em cada tela. 401 e tratado
// globalmente no cliente de API (redireciona ao login).
export function useAsync<T>(loader: () => Promise<T>, deps: unknown[]) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let vivo = true;
    setLoading(true);
    setError(null);
    loader()
      .then((d) => vivo && setData(d))
      .catch((e: unknown) => vivo && setError(e instanceof Error ? e.message : "Erro ao carregar"))
      .finally(() => vivo && setLoading(false));
    return () => {
      vivo = false;
    };
    // deps controladas pelo chamador; `tick` forca o reload.
  }, [...deps, tick]);

  return { data, loading, error, reload: () => setTick((t) => t + 1) };
}
