# Observabilidade mínima

`verificar_runtime.sh` fornece um baseline manual sem ler logs, ambientes, payloads ou
endereços. Ele verifica os seis containers da Agenda/n8n:

- presença, estado e healthcheck quando disponível;
- OOM e contagem de reinícios;
- limite e percentual de memória;
- ocupação do filesystem Docker;
- presença de limites `max-size` e `max-file` no driver `json-file`.

```bash
./infra/observabilidade/verificar_runtime.sh
# execução manual com registro no journald
./infra/observabilidade/registrar_runtime.sh

# consulta dos registros
journalctl -t agenda-observabilidade -n 100 --no-pager
```

O retorno é `0` sem achados, `1` com erro e `2` somente com avisos. Limiares padrão:
memória em 80% e disco em 85%; podem ser alterados apenas para uma execução com
`AGENDA_MEMORY_WARN_PERCENT` e `AGENDA_DISK_WARN_PERCENT`.

O script não agenda a si próprio e não substitui alertas externos. Antes de habilitar
timer/cron, definir responsável, destino do alerta e retenção. A correção de rotação de
logs exige atualizar as definições Compose/Portainer e recriar os containers de forma
planejada; não alterar globalmente o daemon sem avaliar stacks externas.

O Compose versionado da Agenda prepara `json-file` com `max-size: 10m` e `max-file: 5`
para PostgreSQL, backend e frontend. A política foi aplicada no runtime em 2026-08-05,
após o snapshot coordenado `4e602160`; healthchecks, migration e HTTP foram aprovados.
A stack Portainer separada do n8n também foi atualizada e PostgreSQL, n8n e runner
foram recriados com a mesma política. A validação final dos seis containers terminou
com `0` erros e `0` avisos. A decisão operacional é manter backup e verificação manuais
diários, sem timer/cron por enquanto, registrando as execuções no `journald` local com
a tag `agenda-observabilidade`. Não há dependência de e-mail, Telegram ou n8n para
alertas.
