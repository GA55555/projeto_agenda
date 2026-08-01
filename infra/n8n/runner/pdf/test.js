"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const { gerarPdf, validarPayload } = require("./index");

const payload = {
  evento_id: "11111111-1111-4111-8111-111111111111",
  tipo: "evolucao_assinada",
  contrato_versao: 1,
  documento_tipo: "registro_evolucao_prontuario_psicologico",
  evolucao_id: "22222222-2222-4222-8222-222222222222",
  assinada_em: "2026-07-31T17:45:00Z",
  texto: "Registro sintético com acentos: evolução, vínculo, atenção.\n\nSegundo parágrafo clínico sintético.",
  paciente: {
    id: "33333333-3333-4333-8333-333333333333",
    nome: "Paciente Sintético",
    data_nascimento: "2015-02-03",
  },
  atendimento: {
    id: "44444444-4444-4444-8444-444444444444",
    inicio: "2026-07-31T16:00:00Z",
    fim: "2026-07-31T16:50:00Z",
  },
  psicologa: {
    id: "55555555-5555-4555-8555-555555555555",
    nome: "Psicóloga Sintética",
    crp: "06/123456",
  },
};

async function main() {
  assert.equal(validarPayload(payload).pacienteNascimento, "03/02/2015");
  assert.throws(() => validarPayload({ ...payload, contrato_versao: 2 }), /contrato_documental/);
  assert.throws(
    () => validarPayload({ ...payload, psicologa: { ...payload.psicologa, crp: "invalido" } }),
    /psicologa.crp/
  );
  assert.throws(
    () => validarPayload({ ...payload, evolucao_id: "../../fora-do-destino----------------" }),
    /evolucao_id/
  );
  assert.throws(
    () => validarPayload({
      ...payload,
      paciente: { ...payload.paciente, data_nascimento: "2015-02-30" },
    }),
    /paciente.data_nascimento/
  );
  assert.throws(
    () => validarPayload({
      ...payload,
      atendimento: { ...payload.atendimento, fim: payload.atendimento.inicio },
    }),
    /atendimento.fim/
  );
  const resultado = await gerarPdf(payload, { geradoEm: "2026-07-31T18:00:00Z" });
  assert.equal(resultado.mimeType, "application/pdf");
  assert.match(resultado.fileName, /^evolucao-[0-9a-f-]{36}\.pdf$/);
  assert.equal(resultado.sha256.length, 64);
  assert.ok(resultado.buffer.subarray(0, 5).equals(Buffer.from("%PDF-")));
  assert.ok(resultado.buffer.length > 5000);
  // PDF sintético curto deve caber em uma página; `/Type /Page` não conta
  // `/Type /Pages` por exigir delimitador após Page.
  assert.equal((resultado.buffer.toString("latin1").match(/\/Type \/Page\b/g) || []).length, 1);
  const caminhoCurto = process.env.PDF_TEST_OUTPUT || "/tmp/evolucao-sintetica.pdf";
  fs.writeFileSync(caminhoCurto, resultado.buffer);

  const textoLongo = Array.from(
    { length: 150 },
    (_, indice) => `Linha clínica sintética ${indice + 1}: conteúdo fictício para validar paginação.`
  ).join("\n");
  const resultadoLongo = await gerarPdf(
    { ...payload, texto: textoLongo },
    { geradoEm: "2026-07-31T18:00:00Z" }
  );
  const paginasLongas = (
    resultadoLongo.buffer.toString("latin1").match(/\/Type \/Page\b/g) || []
  ).length;
  assert.ok(paginasLongas >= 2);
  const caminhoLongo = caminhoCurto.replace(/\.pdf$/, "-longo.pdf");
  fs.writeFileSync(caminhoLongo, resultadoLongo.buffer);
  process.stdout.write(`${resultado.fileName} ${resultado.buffer.length} ${resultado.sha256}\n`);
  process.stdout.write(`multipagina ${paginasLongas} ${resultadoLongo.buffer.length}\n`);
}

main().catch((erro) => {
  process.stderr.write(`${erro.stack}\n`);
  process.exitCode = 1;
});
