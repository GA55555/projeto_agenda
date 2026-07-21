import { useEffect, useState } from "react";
import { api } from "../api/client";
import { useAsync } from "../utils/useAsync";
import { fmtMesTitulo, hojeISO } from "../utils/format";

const DIAS_SEMANA = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"];

// Vizinho +/- n meses de um "YYYY-MM".
function deslocarMes(mesISO: string, n: number): string {
  const [a, m] = mesISO.split("-").map(Number);
  const d = new Date(a, m - 1 + n, 1);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

interface Props {
  diaSelecionado: string; // "YYYY-MM-DD"
  onSelecionar: (dia: string) => void;
}

// Calendário mensal (Fase 7f/7h): dias com atendimento ficam coloridos; o pai
// decide o destino do clique. No dashboard, clicar abre o novo agendamento já
// contextualizado naquela data.
export function Calendario({ diaSelecionado, onSelecionar }: Props) {
  const [mes, setMes] = useState(() => diaSelecionado.slice(0, 7));

  // Navegar meses (‹ ›) muda só `mes` (não mexe na seleção). Mas quando o PAI
  // troca o dia para outro mês (ex.: "Ir para hoje"), trazemos a grade junto —
  // senão o dia selecionado ficaria invisível.
  useEffect(() => {
    setMes(diaSelecionado.slice(0, 7));
  }, [diaSelecionado]);

  // Mapa dia->contagem do mês exibido (dias coloridos).
  const { data: contagens, error } = useAsync(() => api.calendario(mes), [mes]);

  const [ano, mesN] = mes.split("-").map(Number);
  const primeiro = new Date(ano, mesN - 1, 1);
  const diasNoMes = new Date(ano, mesN, 0).getDate();
  const deslocamento = primeiro.getDay(); // quantos vazios antes do dia 1
  const hoje = hojeISO();

  const celulas: (string | null)[] = [];
  for (let i = 0; i < deslocamento; i++) celulas.push(null);
  for (let d = 1; d <= diasNoMes; d++) {
    celulas.push(`${mes}-${String(d).padStart(2, "0")}`);
  }

  return (
    <div className="calendario">
      <div className="cal-nav">
        <button type="button" className="mini secundario" onClick={() => setMes(deslocarMes(mes, -1))} aria-label="Mês anterior">
          ‹
        </button>
        <span className="cal-titulo">{fmtMesTitulo(mes)}</span>
        <button type="button" className="mini secundario" onClick={() => setMes(deslocarMes(mes, 1))} aria-label="Próximo mês">
          ›
        </button>
      </div>
      {error && <p className="muted">Não foi possível carregar o calendário agora.</p>}
      <div className="cal-grade">
        {DIAS_SEMANA.map((d) => (
          <div key={d} className="cal-cab">
            {d}
          </div>
        ))}
        {celulas.map((diaISO, i) => {
          if (diaISO === null) return <div key={`v${i}`} className="cal-vazio" />;
          const n = contagens?.[diaISO] ?? 0;
          const classes = [
            "cal-dia",
            n > 0 ? "tem" : "",
            diaISO === diaSelecionado ? "selecionado" : "",
            diaISO === hoje ? "hoje" : "",
          ]
            .filter(Boolean)
            .join(" ");
          const dia = Number(diaISO.slice(-2));
          return (
            <button
              key={diaISO}
              type="button"
              className={classes}
              onClick={() => onSelecionar(diaISO)}
              title={n > 0 ? `${n} atendimento(s) — criar outro` : "Criar agendamento neste dia"}
            >
              <span className="cal-num">{dia}</span>
              {n > 0 && <span className="cal-badge">{n}</span>}
            </button>
          );
        })}
      </div>
    </div>
  );
}
