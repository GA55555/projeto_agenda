import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { Agendamento, Resumo } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { Stat } from "../components/Stat";
import { useAsync } from "../utils/useAsync";
import { fmtDataHora, hojeISO, mesAtualISO } from "../utils/format";
import { rotuloStatus } from "../utils/status";

function pct(taxa: number | null | undefined): string {
  return taxa == null ? "—" : `${Math.round(taxa * 100)}%`;
}

function fmtDiaTitulo(diaISO: string): string {
  return new Date(`${diaISO}T00:00:00`).toLocaleDateString("pt-BR", { dateStyle: "full" });
}

function fmtMesTitulo(mesISO: string): string {
  return new Date(`${mesISO}-01T00:00:00`).toLocaleDateString("pt-BR", {
    month: "long",
    year: "numeric",
  });
}

// Visão geral com HISTÓRICO (Fase 7e): dia (inicia sempre em hoje) e mês são
// selecionáveis desde a criação da conta (`desde`). Contadores agregados no
// backend (GET /dashboard/resumo, sem N+1); cada tile explica no ⓘ como o
// número foi construído. allSettled: uma falha não apaga a tela inteira.
export function Dashboard() {
  const { user } = useAuth();
  const [dia, setDia] = useState(hojeISO()); // sempre nasce no dia atual
  const [mes, setMes] = useState(mesAtualISO());

  // Roster de pacientes (só nomes p/ a lista) — buscado UMA vez, não muda com
  // dia/mês.
  const { data: pacientes } = useAsync(() => api.pacientes(), []);
  const { data, loading, error } = useAsync(async () => {
    const resumo = await api.resumo({ dia, mes }).catch(() => null);
    // A agenda do dia usa a MESMA janela [dia_inicio, dia_fim) que o backend
    // usou p/ os contadores (fuso da clínica) -> tile e lista nunca divergem.
    // Fallback (resumo indisponível): janela do fuso local.
    const janela = resumo
      ? { de: resumo.dia_inicio, ate: resumo.dia_fim }
      : (() => {
          const de = new Date(`${dia}T00:00:00`);
          return { de: de.toISOString(), ate: new Date(de.getTime() + 864e5).toISOString() };
        })();
    const ags = await api.agendamentos(janela).catch(() => null);
    return { resumo, ags };
  }, [dia, mes]);

  if (loading && !data) return <p className="muted">Carregando…</p>;
  if (error || !data) return <p className="erro">{error ?? "Erro ao carregar."}</p>;

  const { resumo, ags } = data as { resumo: Resumo | null; ags: Agendamento[] | null };
  const nomePorId = new Map((pacientes ?? []).map((p) => [p.id, p.nome]));
  const primeiroNome = user?.nome?.split(" ")[0];
  const n = (v: number | undefined) => v ?? "—";
  // Limite inferior dos seletores: mês de criação da conta.
  const desdeDia = resumo ? `${resumo.desde}-01` : undefined;
  const desdeMes = resumo?.desde;
  const ehHoje = dia === hojeISO();

  return (
    <section>
      <div className="page-header">
        <h2>{primeiroNome ? `Olá, ${primeiroNome}` : "Dashboard"}</h2>
      </div>

      {resumo === null && <p className="aviso">Não foi possível carregar os indicadores agora.</p>}

      {/* ---- Estado atual ---- */}
      <div className="stats">
        <Stat
          valor={n(resumo?.pacientes_ativos)}
          rotulo="Pacientes ativos"
          info="Pacientes com cadastro ativo (não arquivados), independente do período selecionado."
        />
        <Stat
          valor={n(resumo?.responsaveis)}
          rotulo="Responsáveis"
          info="Total de responsáveis legais cadastrados."
        />
      </div>

      {/* ---- Dia selecionado ---- */}
      <div className="cabecalho-secao">
        <h3 className="titulo-bloco">{ehHoje ? "Hoje" : fmtDiaTitulo(dia)}</h3>
        <div className="seletor-periodo">
          <input
            type="date"
            value={dia}
            min={desdeDia}
            max={hojeISO()}
            onChange={(e) => e.target.value && setDia(e.target.value)}
            aria-label="Escolher dia"
          />
          {!ehHoje && (
            <button className="mini secundario" onClick={() => setDia(hojeISO())}>
              Hoje
            </button>
          )}
        </div>
      </div>
      <div className="stats">
        <Stat
          valor={n(resumo?.atendimentos_dia)}
          rotulo="Atendimentos no dia"
          info="Agendamentos com início neste dia, excluindo os cancelados (agendados + realizados + faltas)."
        />
        <Stat
          valor={n(resumo?.realizados_dia)}
          rotulo="Realizados"
          info="Atendimentos deste dia marcados como realizados."
        />
        <Stat
          valor={n(resumo?.faltas_dia)}
          rotulo="Faltas"
          info="Atendimentos deste dia marcados como falta."
        />
        <Stat
          valor={n(resumo?.cancelados_dia)}
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
          valor={n(resumo?.realizados_mes)}
          rotulo="Atendimentos realizados"
          info="Atendimentos do mês marcados como realizados."
        />
        <Stat
          valor={n(resumo?.faltas_mes)}
          rotulo="Faltas"
          info="Atendimentos do mês marcados como falta."
        />
        <Stat
          valor={n(resumo?.cancelados_mes)}
          rotulo="Cancelados"
          info="Atendimentos do mês que foram cancelados."
        />
        <Stat
          valor={resumo ? pct(resumo.taxa_comparecimento_mes) : "—"}
          rotulo="Comparecimento"
          info={
            resumo && resumo.taxa_comparecimento_mes != null
              ? `Realizados ÷ (realizados + faltas): ${resumo.realizados_mes} ÷ (${resumo.realizados_mes} + ${resumo.faltas_mes}) = ${pct(resumo.taxa_comparecimento_mes)}.`
              : "Realizados ÷ (realizados + faltas). Sem atendimentos concluídos no mês, não há base de cálculo."
          }
        />
        <Stat
          valor={n(resumo?.dias_com_atendimento_mes)}
          rotulo="Dias com atendimento"
          info="Dias distintos do mês com pelo menos um atendimento realizado."
        />
        <Stat
          valor={n(resumo?.evolucoes_mes)}
          rotulo="Evoluções registradas"
          info="Evoluções clínicas gravadas no prontuário durante o mês."
        />
      </div>

      {/* ---- Pendências / atenção (sempre relativas a agora) ---- */}
      <h3 className="titulo-bloco">Pendências</h3>
      <div className="stats">
        <Stat
          valor={n(resumo?.pacientes_sem_tcle)}
          rotulo="Pacientes sem TCLE ativo"
          alerta={Boolean(resumo && resumo.pacientes_sem_tcle > 0)}
          info="Pacientes ativos sem consentimento (TCLE) vigente — novas evoluções ficam bloqueadas até regularizar (§2.2)."
        />
        <Stat
          valor={n(resumo?.pacientes_sem_agendamento_futuro)}
          rotulo="Sem próximo atendimento"
          alerta={Boolean(resumo && resumo.pacientes_sem_agendamento_futuro > 0)}
          info="Pacientes ativos sem nenhum agendamento futuro — risco de perder a continuidade do acompanhamento."
        />
        <Stat
          valor={n(resumo?.atendimentos_proxima_semana)}
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
        {ags === null ? (
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
