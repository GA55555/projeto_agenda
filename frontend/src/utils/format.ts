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
