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

O usuário da credencial PostgreSQL deve receber apenas `SELECT, INSERT` sobre
`agenda_webhook_eventos`. Não reutilizar o superusuário do contêiner no workflow.

## Contrato

- `X-Agenda-Event-Id`: UUID idempotente, igual a `body.evento_id`.
- `X-Agenda-Timestamp`: epoch UTC em segundos, tolerância máxima de 300 s.
- `X-Agenda-Signature`: `sha256=HMAC(secret, timestamp + "." + evento_id + "." + corpo_canônico)`.
- JSON canônico: UTF-8, chaves de primeiro nível ordenadas, sem espaços.

A PK no PostgreSQL rejeita replay concorrente. Repetir o mesmo UUID+hash devolve 200
idempotente; o mesmo UUID com corpo diferente devolve 409. Execuções de sucesso/erro não
são salvas para evitar persistir texto clínico no histórico do n8n.

## Estado

O arquivo versionado usa `active: false`. A ativação só ocorre após teste sintético de:
assinatura válida, assinatura inválida, timestamp expirado, retry igual e replay divergente.
