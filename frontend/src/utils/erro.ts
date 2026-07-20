import { ApiError } from "../api/client";

// Traduz um erro de API para mensagem ao usuário. `porStatus` permite sobrepor
// mensagens específicas (ex.: 409 -> "horário ocupado"); caso contrário usa o
// `detail` que o backend já devolve (mensagens em pt, específicas por caso).
export function mensagemDeErro(e: unknown, porStatus?: Record<number, string>): string {
  if (e instanceof ApiError) {
    return porStatus?.[e.status] ?? e.message;
  }
  return "Falha de conexão. Tente novamente.";
}
