"use strict";

const crypto = require("node:crypto");
const PDFDocument = require("pdfkit");

const FONTE_REGULAR = "/usr/share/fonts/dejavu/DejaVuSans.ttf";
const FONTE_NEGRITO = "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf";
const MARGEM = 56.7; // 20 mm em pontos
const COR_TEXTO = "#202124";
const COR_SECUNDARIA = "#5f6368";
const COR_LINHA = "#b7bcc3";
const TIPO_DOCUMENTO = "registro_evolucao_prontuario_psicologico";
const UUID_V4 = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

function textoObrigatorio(valor, campo, maximo) {
  if (typeof valor !== "string" || valor.trim() === "" || valor.length > maximo) {
    throw new Error(`campo_documental_invalido:${campo}`);
  }
  // Controles binários não têm representação clínica útil e podem corromper o PDF.
  return valor.replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]/g, "");
}

function dataIso(valor, campo) {
  const texto = textoObrigatorio(valor, campo, 40);
  const data = new Date(texto);
  if (Number.isNaN(data.getTime())) throw new Error(`campo_documental_invalido:${campo}`);
  return data;
}

function dataNascimento(valor) {
  const texto = textoObrigatorio(valor, "paciente.data_nascimento", 10);
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(texto);
  if (!match) throw new Error("campo_documental_invalido:paciente.data_nascimento");
  const ano = Number(match[1]);
  const mes = Number(match[2]);
  const dia = Number(match[3]);
  const data = new Date(Date.UTC(ano, mes - 1, dia));
  if (
    data.getUTCFullYear() !== ano
    || data.getUTCMonth() !== mes - 1
    || data.getUTCDate() !== dia
  ) {
    throw new Error("campo_documental_invalido:paciente.data_nascimento");
  }
  return `${match[3]}/${match[2]}/${match[1]}`;
}

function uuidObrigatorio(valor, campo) {
  const texto = textoObrigatorio(valor, campo, 36);
  if (!UUID_V4.test(texto)) throw new Error(`campo_documental_invalido:${campo}`);
  return texto.toLowerCase();
}

function formatarDataHora(data) {
  return new Intl.DateTimeFormat("pt-BR", {
    timeZone: "America/Sao_Paulo",
    dateStyle: "short",
    timeStyle: "short",
  }).format(data);
}

function formatarAtendimento(inicio, fim) {
  const formatadorData = new Intl.DateTimeFormat("pt-BR", {
    timeZone: "America/Sao_Paulo",
    dateStyle: "short",
  });
  const formatadorHora = new Intl.DateTimeFormat("pt-BR", {
    timeZone: "America/Sao_Paulo",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
  const dataInicio = formatadorData.format(inicio);
  const dataFim = formatadorData.format(fim);
  if (dataInicio === dataFim) {
    return `${dataInicio}, das ${formatadorHora.format(inicio)} às ${formatadorHora.format(fim)}`;
  }
  return `${formatarDataHora(inicio)} a ${formatarDataHora(fim)}`;
}

function linhaRotulada(doc, rotulo, valor) {
  const y = doc.y;
  doc.font("Negrito").fontSize(9.5).fillColor(COR_SECUNDARIA).text(rotulo, MARGEM, y, {
    width: 125,
    continued: false,
  });
  doc.font("Regular").fontSize(10).fillColor(COR_TEXTO).text(valor, MARGEM + 130, y, {
    width: doc.page.width - (2 * MARGEM) - 130,
  });
  doc.moveDown(0.35);
}

function tituloSecao(doc, titulo) {
  doc.moveDown(0.55);
  doc.font("Negrito").fontSize(10).fillColor(COR_TEXTO).text(
    titulo.toUpperCase(),
    MARGEM,
    doc.y,
    { width: doc.page.width - (2 * MARGEM) }
  );
  doc.moveTo(MARGEM, doc.y + 3)
    .lineTo(doc.page.width - MARGEM, doc.y + 3)
    .lineWidth(0.6)
    .strokeColor(COR_LINHA)
    .stroke();
  doc.moveDown(0.75);
}

function validarPayload(payload) {
  if (
    !payload
    || payload.tipo !== "evolucao_assinada"
    || payload.contrato_versao !== 1
    || payload.documento_tipo !== TIPO_DOCUMENTO
  ) {
    throw new Error("contrato_documental_invalido");
  }
  if (!payload.paciente || !payload.atendimento || !payload.psicologa) {
    throw new Error("contrato_documental_incompleto");
  }
  const crp = textoObrigatorio(payload.psicologa.crp, "psicologa.crp", 10);
  if (!/^\d{2}\/\d{4,7}$/.test(crp)) throw new Error("campo_documental_invalido:psicologa.crp");
  const atendimentoInicio = dataIso(payload.atendimento.inicio, "atendimento.inicio");
  const atendimentoFim = dataIso(payload.atendimento.fim, "atendimento.fim");
  if (atendimentoFim <= atendimentoInicio) {
    throw new Error("campo_documental_invalido:atendimento.fim");
  }
  return {
    eventoId: uuidObrigatorio(payload.evento_id, "evento_id"),
    evolucaoId: uuidObrigatorio(payload.evolucao_id, "evolucao_id"),
    texto: textoObrigatorio(payload.texto, "texto", 200000),
    assinadaEm: dataIso(payload.assinada_em, "assinada_em"),
    pacienteNome: textoObrigatorio(payload.paciente.nome, "paciente.nome", 200),
    pacienteNascimento: dataNascimento(payload.paciente.data_nascimento),
    atendimentoInicio,
    atendimentoFim,
    psicologaNome: textoObrigatorio(payload.psicologa.nome, "psicologa.nome", 200),
    crp,
  };
}

function gerarPdf(payload, opcoes = {}) {
  const dados = validarPayload(payload);
  const geradoEm = opcoes.geradoEm ? dataIso(opcoes.geradoEm, "gerado_em") : new Date();
  const doc = new PDFDocument({
    size: "A4",
    margins: { top: MARGEM, right: MARGEM, bottom: 72, left: MARGEM },
    bufferPages: true,
    info: {
      Title: "Registro de Evolução do Prontuário Psicológico",
      Author: `${dados.psicologaNome} — CRP ${dados.crp}`,
      Subject: "Registro clínico confidencial",
      Creator: "Agenda",
      CreationDate: geradoEm,
    },
  });
  const partes = [];
  doc.on("data", (parte) => partes.push(parte));

  doc.registerFont("Regular", FONTE_REGULAR);
  doc.registerFont("Negrito", FONTE_NEGRITO);
  doc.font("Negrito").fontSize(15).fillColor(COR_TEXTO)
    .text("REGISTRO DE EVOLUÇÃO DO PRONTUÁRIO PSICOLÓGICO", { align: "center" });
  doc.moveDown(0.35);
  doc.font("Regular").fontSize(8.5).fillColor(COR_SECUNDARIA)
    .text("DOCUMENTO CLÍNICO CONFIDENCIAL", { align: "center", characterSpacing: 0.7 });

  tituloSecao(doc, "Identificação");
  linhaRotulada(doc, "Paciente", dados.pacienteNome);
  linhaRotulada(doc, "Data de nascimento", dados.pacienteNascimento);
  linhaRotulada(
    doc,
    "Atendimento",
    formatarAtendimento(dados.atendimentoInicio, dados.atendimentoFim)
  );

  tituloSecao(doc, "Evolução registrada");
  doc.font("Regular").fontSize(10.5).fillColor(COR_TEXTO).text(dados.texto, {
    align: "left",
    lineGap: 3,
  });

  tituloSecao(doc, "Autoria e assinatura eletrônica");
  linhaRotulada(doc, "Profissional", `${dados.psicologaNome} — CRP ${dados.crp}`);
  linhaRotulada(doc, "Assinado em", formatarDataHora(dados.assinadaEm));
  doc.moveDown(0.4);
  doc.font("Regular").fontSize(8.5).fillColor(COR_SECUNDARIA).text(
    "Assinatura eletrônica registrada pelo sistema após autenticação e confirmação explícita da profissional."
  );

  tituloSecao(doc, "Integridade do registro");
  linhaRotulada(doc, "ID da evolução", dados.evolucaoId);
  linhaRotulada(doc, "ID do evento", dados.eventoId);
  linhaRotulada(doc, "PDF gerado em", formatarDataHora(geradoEm));

  const paginas = doc.bufferedPageRange();
  for (let indice = 0; indice < paginas.count; indice += 1) {
    doc.switchToPage(paginas.start + indice);
    // O rodape ocupa deliberadamente a area reservada pela margem inferior.
    // Sem zerar a margem apenas durante esta escrita, o PDFKit cria uma pagina
    // nova para cada fragmento do rodape.
    doc.page.margins.bottom = 0;
    const y = doc.page.height - 45;
    doc.moveTo(MARGEM, y - 8)
      .lineTo(doc.page.width - MARGEM, y - 8)
      .lineWidth(0.5)
      .strokeColor(COR_LINHA)
      .stroke();
    doc.font("Regular").fontSize(7.5).fillColor(COR_SECUNDARIA)
      .text("Uso restrito ao prontuário psicológico — preservar sigilo e controle de acesso.", MARGEM, y, {
        width: 365,
        lineBreak: false,
      });
    doc.text(`Página ${indice + 1} de ${paginas.count}`, doc.page.width - MARGEM - 90, y, {
      width: 90,
      align: "right",
      lineBreak: false,
    });
  }

  doc.end();
  return new Promise((resolve, reject) => {
    doc.on("end", () => {
      const buffer = Buffer.concat(partes);
      resolve({
        buffer,
        mimeType: "application/pdf",
        fileName: `evolucao-${dados.evolucaoId}.pdf`,
        sha256: crypto.createHash("sha256").update(buffer).digest("hex"),
      });
    });
    doc.on("error", reject);
  });
}

module.exports = { gerarPdf, validarPayload };
