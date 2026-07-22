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

// "YYYY-MM-DD" de uma Date no fuso LOCAL (sem o shift de UTC do toISOString).
export function toISODate(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

// "YYYY-MM-DD" e "YYYY-MM" de hoje (fuso local).
export function hojeISO(): string {
  return toISODate(new Date());
}
export function mesAtualISO(): string {
  return hojeISO().slice(0, 7);
}

// HH:MM pt-BR de um instante.
export function fmtHora(iso: string | Date): string {
  return new Date(iso).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
}

// "julho de 2026" a partir de "YYYY-MM".
export function fmtMesTitulo(mesISO: string): string {
  return new Date(`${mesISO}-01T00:00:00`).toLocaleDateString("pt-BR", {
    month: "long",
    year: "numeric",
  });
}

// Rótulo pt-BR do sexo (fonte única — antes duplicado em telas).
export function rotuloSexo(sexo: string): string {
  return ({ masculino: "Masculino", feminino: "Feminino" } as Record<string, string>)[sexo] ?? sexo;
}

// Idade em anos completos a partir de "YYYY-MM-DD". null se vazio/inválido.
export function idadeEmAnos(iso: string): number | null {
  if (!iso) return null;
  const [y, m, d] = iso.slice(0, 10).split("-").map(Number);
  if (!y || !m || !d) return null;
  // Rejeita datas fora de faixa (ex.: 2020-13-45): se o Date normalizar para
  // outro mês/dia, não bate com o informado -> inválida.
  const nasc = new Date(y, m - 1, d);
  if (nasc.getFullYear() !== y || nasc.getMonth() !== m - 1 || nasc.getDate() !== d) return null;
  const hoje = new Date();
  let idade = hoje.getFullYear() - y;
  const aindaNaoFez = hoje.getMonth() + 1 < m || (hoje.getMonth() + 1 === m && hoje.getDate() < d);
  if (aindaNaoFez) idade--;
  return idade >= 0 ? idade : null;
}

// Iniciais (1ª e última palavra) para o avatar. "Ana Clara Souza" -> "AS".
export function iniciais(nome: string): string {
  const partes = nome.trim().split(/\s+/).filter(Boolean);
  if (partes.length === 0) return "?";
  const a = partes[0][0];
  const b = partes.length > 1 ? partes[partes.length - 1][0] : "";
  return (a + b).toUpperCase();
}

// Busca de nomes tolerante a maiusculas e acentos, sem enviar PII ao backend.
export function normalizarBusca(valor: string): string {
  return valor
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLocaleLowerCase("pt-BR")
    .trim();
}
