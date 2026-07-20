import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { Calendario } from "../components/Calendario";
import { Stat } from "../components/Stat";
import { useAsync } from "../utils/useAsync";
import { fmtDataHora, fmtMesTitulo, hojeISO, mesAtualISO } from "../utils/format";
import { rotuloStatus } from "../utils/status";

function pct(taxa: number | null | undefined): string {
  return taxa == null ? "—" : `${Math.round(taxa * 100)}%`;
}

function fmtDiaTitulo(diaISO: string): string {
  return new Date(`${diaISO}T00:00:00`).toLocaleDateString("pt-BR", { dateStyle: "full" });
}

// Visão geral com HISTÓRICO. Dia (calendário) e mês são seletores INDEPENDENTES:
// buscados em hooks separados (mudar o dia não recomputa as agregações do mês).
// Cada tile explica no ⓘ como o número é construído.
export function Dashboard() {
  const { user } = useAuth();
  const [dia, setDia] = useState(hojeISO()); // sempre nasce no dia atual
  const [mes, setMes] = useState(mesAtualISO());

  // Roster de pacientes (só nomes p/ a lista) — buscado UMA vez.
  const { data: pacientes } = useAsync(() => api.pacientes(), []);
  // Mês: estado atual + estatísticas + pendências — recarrega só ao mudar o mês.
  const { data: mesData } = useAsync(() => api.resumoMes(mes).catch(() => null), [mes]);
  // Dia: contadores do dia + a agenda daquele dia (mesma janela do backend,
  // fuso da clínica → tile e lista nunca divergem).
  const { data: diaData, loading: carregandoDia } = useAsync(async () => {
    const rd = await api.resumoDia(dia).catch(() => null);
    const janela = rd
      ? { de: rd.dia_inicio, ate: rd.dia_fim }
      : (() => {
          const de = new Date(`${dia}T00:00:00`);
          return { de: de.toISOString(), ate: new Date(de.getTime() + 864e5).toISOString() };
        })();
    const ags = await api.agendamentos(janela).catch(() => null);
    return { rd, ags };
  }, [dia]);

  const rd = diaData?.rd ?? null;
  const ags = diaData?.ags ?? null;
  const nomePorId = new Map((pacientes ?? []).map((p) => [p.id, p.nome]));
  const primeiroNome = user?.nome?.split(" ")[0];
  const n = (v: number | undefined) => v ?? "—";
  const desdeMes = mesData?.desde;
  const ehHoje = dia === hojeISO();

  return (
    <section>
      <div className="page-header">
        <h2>{primeiroNome ? `Olá, ${primeiroNome}` : "Dashboard"}</h2>
      </div>

      {/* ---- Estado atual ---- */}
      <div className="stats">
        <Stat
          valor={n(mesData?.pacientes_ativos)}
          rotulo="Pacientes ativos"
          info="Pacientes com cadastro ativo (não arquivados), independente do período selecionado."
        />
        <Stat
          valor={n(mesData?.responsaveis)}
          rotulo="Responsáveis"
          info="Total de responsáveis legais cadastrados."
        />
      </div>

      {/* ---- Calendário: escolher o dia (inclui meses futuros) ---- */}
      <div className="cabecalho-secao">
        <h3 className="titulo-bloco">Calendário</h3>
        {!ehHoje && (
          <button className="mini secundario" onClick={() => setDia(hojeISO())}>
            Ir para hoje
          </button>
        )}
      </div>
      <Calendario diaSelecionado={dia} onSelecionar={setDia} />

      {/* ---- Dia selecionado ---- */}
      <h3 className="titulo-bloco">{ehHoje ? "Hoje" : fmtDiaTitulo(dia)}</h3>
      <div className="stats">
        <Stat
          valor={n(rd?.atendimentos_dia)}
          rotulo="Atendimentos no dia"
          info="Agendamentos com início neste dia, excluindo os cancelados (agendados + realizados + faltas)."
        />
        <Stat
          valor={n(rd?.realizados_dia)}
          rotulo="Realizados"
          info="Atendimentos deste dia marcados como realizados."
        />
        <Stat
          valor={n(rd?.faltas_dia)}
          rotulo="Faltas"
          info="Atendimentos deste dia marcados como falta."
        />
        <Stat
          valor={n(rd?.cancelados_dia)}
          rotulo="Cancelados"
          info="Atendimentos deste dia que foram cancelados (não contam como atendimento)."
        />
      </div>

      {/* ---- Mês selecionado ---- */}
      <div className="cabecalho-secao">
        <h3 className="titulo-bloco">{fmtMesTitulo(mes)}</h3>
        <div className="seletor-periodo">
          <input
            type="month"
            value={mes}
            min={desdeMes}
            max={mesAtualISO()}
            onChange={(e) => e.target.value && setMes(e.target.value)}
            aria-label="Escolher mês"
          />
          {mes !== mesAtualISO() && (
            <button className="mini secundario" onClick={() => setMes(mesAtualISO())}>
              Mês atual
            </button>
          )}
        </div>
      </div>
      <div className="stats">
        <Stat
          valor={n(mesData?.realizados_mes)}
          rotulo="Atendimentos realizados"
          info="Atendimentos do mês marcados como realizados."
        />
        <Stat
          valor={n(mesData?.faltas_mes)}
          rotulo="Faltas"
          info="Atendimentos do mês marcados como falta."
        />
        <Stat
          valor={n(mesData?.cancelados_mes)}
          rotulo="Cancelados"
          info="Atendimentos do mês que foram cancelados."
        />
        <Stat
          valor={mesData ? pct(mesData.taxa_comparecimento_mes) : "—"}
          rotulo="Comparecimento"
          info={
            mesData && mesData.taxa_comparecimento_mes != null
              ? `Realizados ÷ (realizados + faltas): ${mesData.realizados_mes} ÷ (${mesData.realizados_mes} + ${mesData.faltas_mes}) = ${pct(mesData.taxa_comparecimento_mes)}.`
              : "Realizados ÷ (realizados + faltas). Sem atendimentos concluídos no mês, não há base de cálculo."
          }
        />
        <Stat
          valor={n(mesData?.dias_com_atendimento_mes)}
          rotulo="Dias com atendimento"
          info="Dias distintos do mês com pelo menos um atendimento realizado."
        />
        <Stat
          valor={n(mesData?.evolucoes_mes)}
          rotulo="Evoluções registradas"
          info="Evoluções clínicas gravadas no prontuário durante o mês."
        />
      </div>

      {/* ---- Pendências / atenção (sempre relativas a agora) ---- */}
      <h3 className="titulo-bloco">Pendências</h3>
      <div className="stats">
        <Stat
          valor={n(mesData?.pacientes_sem_tcle)}
          rotulo="Pacientes sem TCLE ativo"
          alerta={Boolean(mesData && mesData.pacientes_sem_tcle > 0)}
          info="Pacientes ativos sem consentimento (TCLE) vigente — novas evoluções ficam bloqueadas até regularizar (§2.2)."
        />
        <Stat
          valor={n(mesData?.pacientes_sem_agendamento_futuro)}
          rotulo="Sem próximo atendimento"
          alerta={Boolean(mesData && mesData.pacientes_sem_agendamento_futuro > 0)}
          info="Pacientes ativos sem nenhum agendamento futuro — risco de perder a continuidade do acompanhamento."
        />
        <Stat
          valor={n(mesData?.atendimentos_proxima_semana)}
          rotulo="Próxima semana"
          info="Atendimentos agendados para os próximos 7 dias a partir de agora."
        />
      </div>

      {/* ---- Agenda do dia selecionado ---- */}
      <div className="cabecalho-secao">
        <h3>{ehHoje ? "Agenda de hoje" : `Agenda de ${fmtDiaTitulo(dia)}`}</h3>
        <Link to="/agenda">Ver agenda →</Link>
      </div>
      <div className="card">
        {carregandoDia && !diaData ? (
          <p className="muted">Carregando…</p>
        ) : ags === null ? (
          <p className="muted">Não foi possível carregar a agenda agora.</p>
        ) : ags.length === 0 ? (
          <p className="vazio">Nenhum atendimento neste dia.</p>
        ) : (
          <ul className="lista">
            {ags.map((a) => (
              <li key={a.id}>
                <span className="muted">{fmtDataHora(a.inicio)}</span> —{" "}
                <Link to={`/pacientes/${a.paciente_id}`}>{nomePorId.get(a.paciente_id) ?? "—"}</Link>{" "}
                <span className={`tag tag-${a.status}`}>{rotuloStatus(a.status)}</span>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="acoes">
        <Link className="botao" to="/agenda/novo">
          Novo agendamento
        </Link>
        <Link className="botao secundario" to="/pacientes/novo">
          Novo paciente
        </Link>
      </div>
    </section>
  );
}
