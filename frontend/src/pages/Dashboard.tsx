import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
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

function deslocarMes(mesISO: string, meses: number): string {
  const [ano, mes] = mesISO.split("-").map(Number);
  const data = new Date(ano, mes - 1 + meses, 1);
  return `${data.getFullYear()}-${String(data.getMonth() + 1).padStart(2, "0")}`;
}

function limitarMes(mesISO: string, minimo?: string): string {
  const maximo = mesAtualISO();
  if (mesISO > maximo) return maximo;
  if (minimo && mesISO < minimo) return minimo;
  return mesISO;
}

// Visão geral com HOJE fixo e consulta histórica mensal aplicada pela lupa.
// O calendário é o atalho de entrada para criar um agendamento na data clicada.
export function Dashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const dia = hojeISO();
  const [mes, setMes] = useState(mesAtualISO());
  const [mesConsulta, setMesConsulta] = useState(mesAtualISO());

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
  const ajustarConsulta = (meses: number) =>
    setMesConsulta((atual) => limitarMes(deslocarMes(atual, meses), desdeMes));

  const ajustarAnoConsulta = (anos: number) =>
    setMesConsulta((atual) => limitarMes(deslocarMes(atual, anos * 12), desdeMes));

  const consultarMes = () => setMes(limitarMes(mesConsulta, desdeMes));

  return (
    <section>
      <div className="page-header">
        <h2>{primeiroNome ? `Olá, ${primeiroNome}` : "Dashboard"}</h2>
      </div>

      {/* ---- Hoje: informação mais imediata vem antes do calendário ---- */}
      <h3 className="titulo-bloco">Hoje</h3>
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

      <div className="cabecalho-secao">
        <h3>Agenda de hoje</h3>
        <Link to="/agenda">Ver agenda →</Link>
      </div>
      <div className="card">
        {carregandoDia && !diaData ? (
          <p className="muted">Carregando…</p>
        ) : ags === null ? (
          <p className="muted">Não foi possível carregar a agenda agora.</p>
        ) : ags.length === 0 ? (
          <p className="vazio">Nenhum atendimento hoje.</p>
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

      {/* ---- Calendário: clicar no dia inicia um novo agendamento ---- */}
      <div className="cabecalho-secao">
        <div>
          <h3 className="titulo-bloco">Calendário</h3>
          <p className="muted subtitulo-bloco">Selecione um dia para criar um agendamento.</p>
        </div>
      </div>
      <Calendario
        diaSelecionado={dia}
        onSelecionar={(diaSelecionado) => navigate(`/agenda/novo?dia=${diaSelecionado}`)}
      />

      {/* ---- Mês selecionado ---- */}
      <div className="cabecalho-secao">
        <h3 className="titulo-bloco">{fmtMesTitulo(mes)}</h3>
        <div className="seletor-periodo" aria-label="Selecionar mês e ano do dashboard">
          <div className="periodo-stepper">
            <button type="button" onClick={() => ajustarConsulta(1)} disabled={mesConsulta >= mesAtualISO()} aria-label="Próximo mês">▲</button>
            <span>{fmtMesTitulo(mesConsulta).split(" de ")[0]}</span>
            <button type="button" onClick={() => ajustarConsulta(-1)} disabled={Boolean(desdeMes && mesConsulta <= desdeMes)} aria-label="Mês anterior">▼</button>
          </div>
          <div className="periodo-stepper periodo-ano">
            <button type="button" onClick={() => ajustarAnoConsulta(1)} disabled={mesConsulta >= mesAtualISO()} aria-label="Próximo ano">▲</button>
            <span>{mesConsulta.slice(0, 4)}</span>
            <button type="button" onClick={() => ajustarAnoConsulta(-1)} disabled={Boolean(desdeMes && mesConsulta <= desdeMes)} aria-label="Ano anterior">▼</button>
          </div>
          <button type="button" className="periodo-buscar" onClick={consultarMes} aria-label="Consultar período" title="Consultar período">
            🔍
          </button>
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

      {/* ---- Estado atual: depois das pendências ---- */}
      <h3 className="titulo-bloco">Cadastros ativos</h3>
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

      <div className="acoes">
        <Link className="botao" to="/pacientes/novo">
          Novo paciente
        </Link>
      </div>
    </section>
  );
}
