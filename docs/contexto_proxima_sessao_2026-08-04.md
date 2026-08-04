# Contexto para a próxima sessão — 2026-08-04

Este documento é o handoff operacional da Fase 9. Ele registra o que foi concluído,
o estado real do servidor e a ordem segura para continuar. Não contém endereços IP,
credenciais, payloads clínicos nem identificadores reais.

## Objetivo atual

Encerrar os bloqueios de hardening e obter evidência suficiente para decidir o go-live.
O receptor n8n e qualquer processamento de novos dados reais continuam bloqueados até,
no mínimo, haver ZDR comprovado no projeto OpenAI e fechamento das validações de rede.

## Base versionada e deploy concluído

- Branch `main` local e `origin/main`: `daa32b9` (`Registra deploy do hardening da Fase 9`).
- Código de hardening implantado: commit `293a127`.
- Backend e frontend foram reconstruídos e implantados com a revisão OCI correta.
- Migration `0014 (head)` aplicada.
- PostgreSQL Agenda, PostgreSQL n8n, backend, frontend, n8n e runner ficaram saudáveis.
- Workflow receptor e workflow de teste permanecem inativos; n8n terminou com zero
  execuções e zero payloads persistidos.
- Smoke sintético publicado aprovou login, cabeçalhos `no-store`, troca de senha,
  revogação de tokens, logout global e logout idempotente.
- Rate limit de login aprovado: cinco respostas do backend, depois `429` com
  `Retry-After: 60`, sem limitar rota comum.
- Snapshot coordenado pré-deploy: `ebde69c8`.
- Bundle pós-deploy das imagens efetivamente executadas: `38272c78`.
- O staging gocryptfs foi desmontado após ambas as operações.

## OpenAI/ZDR

### Confirmado

- `API call logging` e os três controles de compartilhamento estavam desativados no
  painel, comprovando ausência de opt-in para compartilhamento/treino.
- O projeto usa Chat Completions com `store=false` e Embeddings; ambos são elegíveis aos
  controles de retenção documentados pela OpenAI.
- Conforme a documentação oficial, ZDR/MAM dependem de aprovação prévia da OpenAI.
  `store=false` sozinho não elimina os logs de monitoramento de abuso.

Referência oficial:
[Data retention controls for abuse monitoring](https://developers.openai.com/api/docs/guides/your-data#data-retention-controls-for-abuse-monitoring).

### Pendente

- Solicitar/acompanhar a aprovação de ZDR com a OpenAI.
- Após provisionamento, selecionar ZDR explicitamente no projeto da Agenda e registrar
  evidência sem capturar chave, ID sensível ou dado clínico.
- Até essa confirmação, não publicar o receptor nem enviar novo dado real.

## Firewall: descoberta e correção

### Estado encontrado

- UFW: habilitado e ativo, com IPv6 habilitado.
- `iptables` e `ip6tables`: backend `nf_tables`.
- `nftables.service`: desabilitado e inativo.
- `netfilter-persistent`: não instalado; `/etc/iptables/rules.v4` e `rules.v6` ausentes.
- `/etc/nftables.conf` é o arquivo padrão e contém `flush ruleset`. **Não habilitar
  `nftables.service` nesse estado**, pois ele pode remover regras do UFW/Docker.
- A contenção IPv4 temporária registrada na sessão anterior já havia desaparecido:
  `DOCKER-USER` estava vazia em IPv4 e IPv6.

### Superfície protegida

As publicações administrativas expostas em todas as interfaces usam as portas TCP
`5432`, `8000`, `8080`, `8081`, `8443` e `9443`. A contenção é restrita à interface
física da LAN; loopback, Tailscale e tráfego interno Docker devem continuar permitidos.

### Implementação instalada no host

Foi criado o lote ainda não versionado `infra/firewall/`:

- `agenda-docker-firewall.sh` — aplica/remove regras idempotentes em IPv4 e IPv6;
- `agenda-docker-firewall.service` — serviço oneshot persistente, ordenado depois de
  UFW e Docker e associado a reinícios do daemon Docker;
- `instalar.sh` — pré-valida as regras com `iptables-restore --test` e
  `ip6tables-restore --test`, instala os arquivos e reinicia o serviço;
- `README.md` — operação, verificação e rollback.

Arquivos instalados no host:

- `/usr/local/sbin/agenda-docker-firewall`;
- `/etc/systemd/system/agenda-docker-firewall.service`;
- `/usr/local/share/doc/agenda-firewall/README.md`.

Serviço confirmado `enabled` e `active (exited)`. A primeira versão usava uma única
chain com `--ctorigdstport`; ela bloqueou IPv4, mas não correspondeu ao caminho IPv6
local. A versão corrigida, instalada em 2026-08-03 às 19:12, separa os caminhos:

- `AGENDA-LAN-INPUT`, ligada a `INPUT`, usa `--dport` para listeners locais/proxy IPv6;
- `AGENDA-LAN-DOCKER`, ligada a `DOCKER-USER`, usa `--ctorigdstport` para publicações
  após DNAT, inclusive os mapeamentos `8080 -> 7575` e `8081 -> 80`.

A chain legada `AGENDA-LAN-GUARD` foi removida. Verificação root confirmou os dois hooks,
as seis regras e o `RETURN` em cada família. `bash -n` e as verificações de whitespace
passaram no lote local. ShellCheck não está instalado no host e não foi executado.

### Evidência externa concluída em 2026-08-04

- Pela Tailscale, as seis portas responderam como abertas. Isso comprova que a
  administração privada foi preservada.
- Pela LAN em IPv4, as seis portas expiraram e todas as regras correspondentes em
  `AGENDA-LAN-DOCKER` incrementaram.
- Pela LAN em IPv6, as seis portas foram bloqueadas e todas as regras correspondentes em
  `AGENDA-LAN-INPUT` incrementaram. O primeiro ensaio IPv6 era inválido porque o cliente
  PowerShell havia criado um socket somente IPv4; o reteste usou suporte IPv6 nativo.
- Nenhum endereço foi registrado na conversa ou nos documentos.

## Validações concluídas nesta retomada

### 1. Endereço/rota IPv6

Usar dois terminais distintos e observar o prompt:

- servidor Linux: `hades@hadesserver:...$`;
- Windows PowerShell local: `PS C:\Users\...>`.

No servidor Linux, obter somente o IPv6 global da interface física:

```bash
ip -6 -o addr show dev enp2s0 scope global | awk '{sub(/\/.*/, "", $4); print $4}'
```

No PowerShell, mostrar a variável usada no teste:

```powershell
$ipv6
```

Os valores foram comparados localmente e eram idênticos; ICMPv6 também respondeu. Os
valores não foram copiados para a conversa nem para o repositório.

### 2. Testes externos na versão final

Da máquina Windows na mesma LAN, foi comprovado:

- IPv4 físico: as seis portas resultaram em timeout/bloqueio;
- IPv6 físico: as seis portas resultaram em bloqueio;
- Tailscale: as seis portas continuaram abertas.

No servidor, os contadores aumentaram nas chains esperadas:

```bash
sudo iptables -nvL AGENDA-LAN-INPUT --line-numbers
sudo iptables -nvL AGENDA-LAN-DOCKER --line-numbers
sudo ip6tables -nvL AGENDA-LAN-INPUT --line-numbers
sudo ip6tables -nvL AGENDA-LAN-DOCKER --line-numbers
```

O script temporário `/tmp/agenda-firewall-verify.sh` contém assertions mais completas,
mas pode desaparecer após reboot e não deve ser tratado como artefato versionado.

### 3. Persistência

Após os testes de alcance, uma reaplicação controlada do serviço foi executada:

```bash
sudo systemctl restart agenda-docker-firewall.service
sudo systemctl is-enabled agenda-docker-firewall.service
sudo systemctl is-active agenda-docker-firewall.service
```

O serviço permaneceu `enabled` e `active`; os quatro hooks e as chains completas foram
reaplicados. Docker e servidor não foram reiniciados. A associação
`PartOf=docker.service` está configurada, mas um teste de reinício real do daemon deve
ser planejado separadamente.

## Ponto exato para retomar

### 4. Versionar o checkpoint

Os retestes e a documentação foram concluídos. Antes de versionar:

- revisar `infra/firewall/` e este handoff;
- executar `git diff --check` e checagens estáticas;
- criar commit e push apenas após conferência final do diff.

Estado Git no momento deste handoff: `main` em `daa32b9`, sincronizada com
`origin/main`; `infra/firewall/` e este documento ainda não estão versionados.

### 5. Próximos bloqueios depois do firewall

1. Solicitar/provar ZDR no projeto OpenAI.
2. Planejar a migração do Homarr legado `0.16.0` para a linha atual, com backup e
   rollback, e substituir o mount gravável do Docker socket por socket proxy mínimo.
3. Atribuir e revisar listeners externos que não pertencem à Agenda (`139`, `445` e
   `3000`) sem alterá-los por suposição.
4. Formalizar exceções temporárias das CVEs sem correção upstream e do advisory RSC não
   alcançável pela SPA.
5. Somente quando os critérios de go-live estiverem encerrados, planejar publicação
   controlada do receptor e novo smoke exclusivamente sintético antes de dado real.

## Guardas operacionais

- Não registrar segredos, hashes reutilizáveis, endereços, payloads ou identificadores
  reais em Git, documentação ou conversa.
- Não ativar `nftables.service` com o arquivo atual.
- Não publicar o workflow n8n nem processar novo dado real enquanto ZDR não estiver
  comprovado e os bloqueios de go-live não forem formalmente encerrados.
- Não alterar stacks externas, Docker socket, Homarr ou listeners não pertencentes à
  Agenda sem inventário, backup e autorização específicos.
- Rollback apenas das regras administradas por este lote:

```bash
sudo systemctl disable --now agenda-docker-firewall.service
```
