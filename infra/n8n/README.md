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

A PK no PostgreSQL rejeita replay concorrente. Repetir o mesmo UUID+hash devolve 200
idempotente; o mesmo UUID com corpo diferente devolve 409. Execuções de sucesso/erro não
são salvas para evitar persistir texto clínico no histórico do n8n.

## Estado

O arquivo versionado usa `active: false`. A ativação só ocorre após teste sintético de:
assinatura válida, assinatura inválida, timestamp expirado, retry igual e replay divergente.
