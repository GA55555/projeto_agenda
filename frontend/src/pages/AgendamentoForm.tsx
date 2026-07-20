import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api/client";
import type { Agendamento, Frequencia } from "../api/client";
import { useAsync } from "../utils/useAsync";
import { mensagemDeErro } from "../utils/erro";
import { fmtHora, hojeISO } from "../utils/format";

const FREQ_ROTULO: Record<Frequencia, string> = {
  semanal: "Toda semana (mesmo dia da semana)",
  quinzenal: "A cada 15 dias",
  mensal: "Todo mês (mesma data)",
};

// Novo agendamento por CLIQUES (Fase 7e): escolhe o dia -> vê a ocupação ->
// clica num horário livre -> escolhe a duração (presets ou valor livre).
// Conflitos ficam visíveis por construção (slots ocupados) e um aviso aparece
// ao vivo se a duração invadir o próximo atendimento (o EXCLUDE do BD é a
// autoridade final — o aviso é só UX).

const DURACOES = [30, 45, 50, 60, 90] as const;
const HORA_INICIO = 7; // grade 07:00–20:00
const HORA_FIM = 20;
const PASSO_MIN = 30;

// Predicado ÚNICO de sobreposição [início, fim) — usado para marcar slots e
// para o aviso de conflito (mesma regra do EXCLUDE no backend).
function sobrepoe(a: Agendamento, inicio: Date, fim: Date): boolean {
  return new Date(a.inicio) < fim && new Date(a.fim) > inicio;
}

export function AgendamentoForm() {
  const navigate = useNavigate();

  const [pacienteId, setPacienteId] = useState("");
  const [dia, setDia] = useState(hojeISO());
  const [horaInicio, setHoraInicio] = useState<string>(""); // "HH:MM"
  const [duracao, setDuracao] = useState<number>(50);
  const [tipo, setTipo] = useState("");
  const [observacao, setObservacao] = useState("");
  const [repetir, setRepetir] = useState(false);
  const [frequencia, setFrequencia] = useState<Frequencia>("semanal");
  const [erro, setErro] = useState<string | null>(null);
  const [salvando, setSalvando] = useState(false);

  // Pacientes (roster invariante) buscado UMA vez; a agenda do dia recarrega
  // só quando o dia muda.
  const { data: pacientes } = useAsync(async () => {
    const ps = await api.pacientes();
    return ps.filter((p) => p.ativo);
  }, []);
  const { data: ags, loading: carregandoAgenda } = useAsync(async () => {
    const de = new Date(`${dia}T00:00:00`);
    const ate = new Date(de.getTime() + 24 * 3600 * 1000);
    return api.agendamentos({ de: de.toISOString(), ate: ate.toISOString() });
  }, [dia]);

  const ocupados = (ags ?? []).filter((a) => a.status !== "cancelado");

  // Slots da grade: blocos de PASSO_MIN, marcados como livres/ocupados.
  const slots: { hora: string; inicio: Date; ocupadoPor: Agendamento | null }[] = [];
  for (let h = HORA_INICIO; h < HORA_FIM; h++) {
    for (let m = 0; m < 60; m += PASSO_MIN) {
      const inicio = new Date(`${dia}T${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:00`);
      const fim = new Date(inicio.getTime() + PASSO_MIN * 60000);
      const dono = ocupados.find((a) => sobrepoe(a, inicio, fim));
      slots.push({ hora: fmtHora(inicio), inicio, ocupadoPor: dono ?? null });
    }
  }

  // Conflito ao vivo: o intervalo escolhido invade algum atendimento?
  const inicioSel = horaInicio ? new Date(`${dia}T${horaInicio}:00`) : null;
  const fimSel = inicioSel ? new Date(inicioSel.getTime() + duracao * 60000) : null;
  const conflito =
    inicioSel && fimSel ? ocupados.find((a) => sobrepoe(a, inicioSel, fimSel)) ?? null : null;

  const nomePaciente = (id: string) => pacientes?.find((p) => p.id === id)?.nome ?? "ocupado";

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!inicioSel || !fimSel) {
      setErro("Escolha um horário na grade (ou digite no ajuste fino).");
      return;
    }
    setErro(null);
    setSalvando(true);
    try {
      const criado = await api.criarAgendamento({
        paciente_id: pacienteId,
        inicio: inicioSel.toISOString(),
        fim: fimSel.toISOString(),
        tipo: tipo || undefined,
        observacao: observacao || undefined,
        recorrencia: repetir ? { frequencia } : undefined,
      });
      if (repetir) {
        let msg = `Recorrência criada: ${criado.serie_criados} atendimento(s) futuro(s).`;
        if (criado.serie_pulados_datas.length > 0) {
          const datas = criado.serie_pulados_datas
            .map((d) => new Date(d).toLocaleDateString("pt-BR"))
            .join(", ");
          msg += `\n\nPuladas por conflito (${criado.serie_pulados_datas.length}): ${datas}.`;
        }
        window.alert(msg);
      }
      navigate("/agenda", { replace: true });
    } catch (e) {
      setErro(
        mensagemDeErro(e, {
          409: "Conflito de horário: sobrepõe outro atendimento.",
          422: "Paciente inválido ou horário incoerente.",
        }),
      );
    } finally {
      setSalvando(false);
    }
  }

  if (!pacientes) return <p className="muted">Carregando…</p>;

  return (
    <section>
      <Link className="voltar muted" to="/agenda">
        ← Agenda
      </Link>
      <div className="page-header">
        <h2>Novo agendamento</h2>
      </div>
      <form className="card" onSubmit={onSubmit}>
        <label className="campo">
          Paciente*
          <select value={pacienteId} onChange={(e) => setPacienteId(e.target.value)} required>
            <option value="">Selecione…</option>
            {pacientes.map((p) => (
              <option key={p.id} value={p.id}>
                {p.nome}
              </option>
            ))}
          </select>
        </label>

        <label className="campo">
          Dia*
          <input
            type="date"
            value={dia}
            onChange={(e) => {
              setDia(e.target.value);
              setHoraInicio("");
            }}
            required
          />
        </label>

        <div className="campo">
          <span className="rotulo-grade">Horário* (clique num horário livre)</span>
          {carregandoAgenda ? (
            <p className="muted">Carregando ocupação do dia…</p>
          ) : (
            <div className="grade-horarios">
              {slots.map((s) => {
                const selecionado =
                  inicioSel !== null && fimSel !== null && s.inicio >= inicioSel && s.inicio < fimSel;
                return (
                  <button
                    key={s.hora}
                    type="button"
                    className={`slot${s.ocupadoPor ? " ocupado" : ""}${selecionado ? " selecionado" : ""}`}
                    disabled={Boolean(s.ocupadoPor)}
                    title={
                      s.ocupadoPor ? `Ocupado — ${nomePaciente(s.ocupadoPor.paciente_id)}` : s.hora
                    }
                    onClick={() => setHoraInicio(s.hora)}
                  >
                    {s.hora}
                  </button>
                );
              })}
            </div>
          )}
          <label className="ajuste-fino">
            Ajuste fino (opcional)
            <input type="time" value={horaInicio} onChange={(e) => setHoraInicio(e.target.value)} />
          </label>
        </div>

        <div className="campo">
          <span className="rotulo-grade">Duração*</span>
          <div className="chips">
            {DURACOES.map((d) => (
              <button
                key={d}
                type="button"
                className={`chip${duracao === d ? " ativo" : ""}`}
                onClick={() => setDuracao(d)}
              >
                {d} min
              </button>
            ))}
            <label className="ajuste-fino" style={{ marginTop: 0 }}>
              Outra (min)
              <input
                type="number"
                min={15}
                max={480}
                step={5}
                value={duracao}
                onChange={(e) => setDuracao(Math.max(1, Number(e.target.value) || 0))}
              />
            </label>
          </div>
        </div>

        {inicioSel && fimSel && (
          <p className={conflito ? "aviso" : "muted"}>
            {conflito
              ? `⚠️ Conflito: ${fmtHora(inicioSel)}–${fmtHora(fimSel)} sobrepõe o atendimento de ` +
                `${nomePaciente(conflito.paciente_id)} (${fmtHora(conflito.inicio)}–${fmtHora(conflito.fim)}).`
              : `Agendar ${fmtHora(inicioSel)}–${fmtHora(fimSel)}.`}
          </p>
        )}

        <div className="campo">
          <label className="inline">
            <input type="checkbox" checked={repetir} onChange={(e) => setRepetir(e.target.checked)} />
            Repetir neste mesmo dia e horário (recorrência)
          </label>
          {repetir && (
            <>
              <select
                value={frequencia}
                onChange={(e) => setFrequencia(e.target.value as Frequencia)}
                style={{ marginTop: "0.4rem", maxWidth: "16rem" }}
              >
                {(Object.keys(FREQ_ROTULO) as Frequencia[]).map((f) => (
                  <option key={f} value={f}>
                    {FREQ_ROTULO[f]}
                  </option>
                ))}
              </select>
              <p className="muted" style={{ fontSize: "0.82rem", marginTop: "0.3rem" }}>
                Cria os atendimentos futuros por ~6 meses. Para desfazer, abra um atendimento da
                série na agenda e clique em “Desfazer recorrência”.
              </p>
            </>
          )}
        </div>

        <label className="campo">
          Tipo
          <input value={tipo} onChange={(e) => setTipo(e.target.value)} placeholder="ex.: sessão, avaliação" />
        </label>
        <label className="campo">
          Observação
          <textarea rows={2} value={observacao} onChange={(e) => setObservacao(e.target.value)} />
        </label>
        {erro && <p className="erro">{erro}</p>}
        <button type="submit" disabled={salvando || !pacienteId || !horaInicio || Boolean(conflito)}>
          {salvando ? "Agendando…" : "Agendar"}
        </button>
      </form>
    </section>
  );
}
