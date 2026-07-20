import { useState } from "react";
import { mensagemDeErro } from "./erro";

// Ciclo comum das ações de mutação: ocupado/erro + try/catch/finally
// (antes copiado em FichaPaciente, AgendamentoDetalhe…). `executar(fn)` roda a
// ação, captura o erro em `acaoErro` e alterna `ocupado`.
export function useAcao() {
  const [ocupado, setOcupado] = useState(false);
  const [acaoErro, setAcaoErro] = useState<string | null>(null);

  async function executar(fn: () => Promise<unknown>): Promise<void> {
    setAcaoErro(null);
    setOcupado(true);
    try {
      await fn();
    } catch (e) {
      setAcaoErro(mensagemDeErro(e));
    } finally {
      setOcupado(false);
    }
  }

  return { ocupado, acaoErro, executar };
}
