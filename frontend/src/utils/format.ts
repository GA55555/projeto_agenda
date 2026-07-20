// Formatacao pt-BR de datas/horas vindas do backend (ISO 8601 com timezone).
const dataHora = new Intl.DateTimeFormat("pt-BR", {
  dateStyle: "short",
  timeStyle: "short",
});
const data = new Intl.DateTimeFormat("pt-BR", { dateStyle: "short" });

export function fmtDataHora(iso: string): string {
  return dataHora.format(new Date(iso));
}

export function fmtData(iso: string): string {
  // data_nascimento vem como "YYYY-MM-DD" (sem hora) -> evita shift de fuso.
  const d = iso.length === 10 ? new Date(iso + "T00:00:00") : new Date(iso);
  return data.format(d);
}

// Janela [início de hoje, início de amanhã) no fuso local, como instantes ISO —
// para filtrar a agenda do dia no backend (`de`/`ate`).
export function janelaDeHoje(): { de: string; ate: string } {
  const h = new Date();
  const de = new Date(h.getFullYear(), h.getMonth(), h.getDate()).toISOString();
  const ate = new Date(h.getFullYear(), h.getMonth(), h.getDate() + 1).toISOString();
  return { de, ate };
}
