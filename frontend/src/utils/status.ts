// Rótulos pt-BR dos status de agendamento (fonte única — antes duplicado em
// Agenda.tsx e Dashboard.tsx). As cores vivem nas classes .tag-<status> do CSS.
export const ROTULO_STATUS: Record<string, string> = {
  agendado: "Agendado",
  realizado: "Realizado",
  cancelado: "Cancelado",
  falta: "Falta",
};

export function rotuloStatus(status: string): string {
  return ROTULO_STATUS[status] ?? status;
}
