# Receptor n8n — evolução assinada

Artefatos da Fase 8b. O workflow é importado **inativo** e não gera PDF nem chama
Google até HMAC, janela temporal e replay passarem com payload sintético.

## Pré-requisitos operacionais

1. Gerar `AGENDA_WEBHOOK_SECRET` com pelo menos 32 bytes aleatórios fora do Git.
2. Configurar o mesmo valor no backend e no contêiner n8n.
3. Permitir somente o módulo builtin `crypto` no Code node:
   `NODE_FUNCTION_ALLOW_BUILTIN=crypto`.
4. Aplicar `schema.sql` no PostgreSQL dedicado do n8n.
5. Importar `workflows/evolucao-assinada.json`, selecionar uma credencial PostgreSQL
   dedicada no nó **Registrar ou reconhecer evento** e manter o workflow inativo.

## Rede privada

A rede Docker externa `agenda-webhook` é interna (sem saída direta) e compartilhada
somente pelo backend Agenda e pelo serviço n8n. O Compose da Agenda já persiste a
ligação do backend. No stack do n8n no Portainer, declarar a mesma rede como externa e
ligá-la apenas ao serviço n8n:

```yaml
services:
  n8n:
    networks:
      - default
      - agenda_webhook

networks:
  agenda_webhook:
    external: true
    name: agenda-webhook
```

O PostgreSQL dedicado do n8n permanece apenas na rede padrão desse stack. A URL interna
do backend é `http://agenda-n8n-n8n-1:5678/webhook/agenda-evolucao-assinada` enquanto
esse for o nome estável do contêiner criado pelo stack.

## Credencial PostgreSQL mínima

`role_webhook.sql` cria/atualiza o role `agenda_webhook` e limita seus privilégios à
leitura e inserção da tabela antirreplay. Informe a senha por prompt do `psql` ou outro
canal que não grave o valor no Git/histórico. Na credencial PostgreSQL do n8n use o host
do serviço PostgreSQL do próprio stack, banco `n8n`, usuário `agenda_webhook` e essa
senha. Não reutilize o administrador do banco.

O usuário da credencial PostgreSQL deve receber apenas `SELECT, INSERT` sobre
`agenda_webhook_eventos`. Não reutilizar o superusuário do contêiner no workflow.

## Contrato

- `X-Agenda-Event-Id`: UUID idempotente, igual a `body.evento_id`.
- `X-Agenda-Timestamp`: epoch UTC em segundos, tolerância máxima de 300 s.
- `X-Agenda-Signature`: `sha256=HMAC(secret, timestamp + "." + evento_id + "." + corpo_canônico)`.
- JSON canônico: UTF-8, chaves de primeiro nível ordenadas, sem espaços.

O contrato documental v1 (`contrato_versao: 1`) leva somente o retrato necessário
para o registro: evolução e assinatura; nome/data de nascimento do paciente;
início/fim do atendimento; nome/CRP do assinante. O backend falha fechado se algum
vínculo divergir ou se o CRP estiver ausente. O n8n não recebe acesso ao banco clínico.
O payload só é preservado no item do workflow depois de HMAC e janela válidos e nunca
deve ser gravado no histórico de execuções.

A PK no PostgreSQL rejeita replay concorrente. Repetir o mesmo UUID+hash devolve 200
idempotente; o mesmo UUID com corpo diferente devolve 409. Execuções de sucesso/erro não
são salvas para evitar persistir texto clínico no histórico do n8n.

## Estado

O arquivo versionado usa `active: false`. A ativação só ocorre após teste sintético de:
assinatura válida, assinatura inválida, timestamp expirado, retry igual e replay divergente.

## Versão e retenção de execuções

A versão operacional mínima é n8n **2.33.0**, que inclui a correção oficial
`n8n-io/n8n#34670` (commit `0316336`) para timestamps do rollup no PostgreSQL. O n8n e
o `n8nio/runners` devem usar exatamente a mesma versão.

Este receptor proíbe histórico com payload clínico e configura `saveDataErrorExecution`
e `saveDataSuccessExecution` como `none`. No n8n 2.33.0, porém,
`EXECUTIONS_DATA_PRUNE=true` transforma esse descarte em *soft-delete*: a execução some
da interface, mas `execution_entity` e `execution_data` permanecem até o *hard-delete*.
Por isso o stack dedicado usa:

```yaml
EXECUTIONS_DATA_PRUNE: "false"
```

Nesse modo, execuções descartadas seguem para *hard-delete* imediato. Qualquer mudança
dessa variável exige repetir os cinco testes sintéticos e provar diretamente no PostgreSQL
`0` linhas em `execution_entity` e `execution_data` antes de liberar payload real.

## Runner isolado para PDF

O PDF é produzido pelo módulo fechado `@agenda/pdf-evolucao` dentro do runner externo.
Ele usa PDFKit fixado pelo `package-lock.json` e fonte DejaVu Unicode, sem Chromium,
LibreOffice, serviço adicional ou acesso ao banco Agenda. A imagem mantém a mesma versão
do n8n e do launcher:

```bash
docker build -t agenda-n8n-runners:2.33.0-pdf infra/n8n/runner
```

No serviço `task-runners` do stack, usar a imagem acima e permitir exclusivamente:

```yaml
environment:
  NODE_FUNCTION_ALLOW_BUILTIN: crypto
  NODE_FUNCTION_ALLOW_EXTERNAL: "@agenda/pdf-evolucao"
```

O módulo valida o contrato v1, gera A4 com texto selecionável, fonte Unicode, metadados,
autoria/CRP, assinatura eletrônica registrada, identificadores de integridade, aviso de
sigilo e paginação. O nome do arquivo contém somente UUID, nunca nome do paciente.

O alvo descartável `test` gera PDFs totalmente sintéticos curto e multipágina:

```bash
docker build --target test -t agenda-n8n-runners:2.33.0-pdf-test infra/n8n/runner
docker run --rm agenda-n8n-runners:2.33.0-pdf-test
```

Não conectar o módulo ao receptor ativo antes de completar idempotência do processamento
e upload privado no Google Drive. Responder `200` antes do upload sem estado durável faria
uma falha posterior perder o documento; marcar o evento como duplicado antes de concluir
o upload também impediria retry seguro.
