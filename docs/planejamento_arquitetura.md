# Planejamento & Roadmap do Projeto

> **Mapa executável do projeto.** Este documento é o guia de realização e a **memória viva da sessão**. Ele deriva integralmente de [`arquitetura.md`](./arquitetura.md) — em caso de dúvida técnica, a arquitetura manda.
>
> **Como usar este arquivo:**
> - Trabalhe **uma fase de cada vez**. Não abra várias fases em paralelo — a divisão existe para não encher a janela de contexto.
> - Ao concluir uma tarefa, marque `[x]` e adicione uma linha no **Registro de Progresso**.
> - Ao (re)iniciar uma sessão, leia primeiro o **Estado Atual** e o **Registro de Progresso**; só depois entre na fase corrente.
> - Cada fase tem **Objetivo**, **Tarefas**, **Regras de ouro aplicáveis** e **Critério de conclusão (Definition of Done)**.

---

## 📍 Estado Atual da Sessão

| Campo | Valor |
| --- | --- |
| Fase corrente | **Fase 9 (hardening e go-live) em progresso.** Hardening defensivo implantado no commit `293a127`, migration `0014` aplicada e receptor permanece despublicado. |
| Última atualização | 2026-08-05 |
| Bloqueios ativos | Segredos n8n/HMAC rotacionados, mas a última matriz HTTP precede a rotação de 2026-08-05 e deve ser repetida de forma sintética antes de futura publicação; o receptor permanece despublicado. A LAN física está contida de forma persistente em IPv4 e IPv6 nas seis portas administrativas; o reteste externo preservou o acesso pela Tailscale. Os bindings continuam amplos e Homarr permanece legado com Docker socket gravável; seu backup/rollback está comprovado, mas a stable `v1.73.0` candidata foi bloqueada antes da execução por `2` achados críticos e `19` altos corrigíveis. Os listeners externos `139/445` foram atribuídos ao Samba do host e `3000` ao processo PM2 `mochila` do projeto Ascensão; alcance externo e eventual restrição dependem dos responsáveis por esses serviços. A solicitação de ZDR foi enviada à OpenAI, mas o recurso não está disponível para o projeto; isso mantém o bloqueio de dados reais, sem impedir as demais frentes independentes. Scans de imagens/segredos foram concluídos: frontend corrigido e implantado está limpo, mas imagens upstream de backend/n8n/runner/PostgreSQL/pgvector mantêm CVEs que exigem correção do fornecedor ou exceção formal. O frontend ainda tem exceção temporária para advisory RSC do React Router, caminho não usado pela SPA. |
| Próximo passo imediato | **Go-live continua bloqueado, mas o hardening pode avançar:** configurar relay SMTP root-only para alertas por e-mail, mantendo backup/verificação manuais sem timer; não executar Homarr `v1.73.0`; testar `139/445/3000` a partir da LAN e formalizar exceções das imagens. O restore em host/VM separado foi recusado pelo operador; manter a limitação documentada e não processar dado real enquanto ZDR continuar indisponível. |

> Atualize esta tabela ao fim de cada sessão de trabalho.

### 🔖 Ponto de Retomada (ler primeiro na próxima sessão)

**Onde paramos (2026-08-05 — rotação n8n e logs concluídos):** a stack Portainer do
n8n foi atualizada com `json-file` `10m × 5` e PostgreSQL, n8n e runner foram recriados;
o backend Agenda também foi recriado para receber o HMAC rotacionado. Um filtro textual
amplo expôs na saída operacional a senha administrativa do PostgreSQL n8n e o HMAC;
ambos foram substituídos imediatamente, sem registrar os novos valores. Chave de
cifragem e token do runner não foram expostos. Validação final: seis containers
monitorados estáveis, zero reinícios/OOM, segredos consistentes, 2 workflows inativos,
0 execuções e observabilidade em `0` erros/`0` avisos. O receptor não foi publicado e a
matriz HTTP fica para o smoke sintético obrigatório anterior a qualquer publicação.
**Próximo:** informar endereço/remetente e relay SMTP para preparar o alerta por e-mail;
depois seguir com listeners e exceções de CVE. Backup e verificação permanecem manuais;
o restore em host/VM separado foi recusado pelo operador, mantendo a limitação de
recuperação no mesmo host e o bloqueio de dados reais por ausência de ZDR.

**Onde paramos (2026-08-05 — ZDR indisponível; frentes independentes liberadas):** o
recurso ZDR não está disponível para o projeto, portanto não há nova ação nessa frente
agora e o bloqueio de dados reais permanece. O firewall já está versionado em
`9f7b656`. Os listeners `139/445` pertencem ao Samba do host e `3000` ao processo PM2
`mochila` do projeto Ascensão; nenhum foi alterado e o alcance pela LAN ainda precisa de
teste externo. **Retomar por:** executar a Fase A do plano Homarr somente com janela
autorizada ou coordenar o teste/restrição desses serviços com seus responsáveis.

**Onde paramos (2026-08-04 — ZDR solicitado e Homarr inventariado):** a solicitação de
Zero Data Retention foi enviada pelo canal oficial da OpenAI, sem registrar IDs ou
segredos; aguarda aprovação/provisionamento e seleção explícita no projeto. O Homarr
legado foi inventariado somente por metadados: saudável, três volumes pequenos, sem
limite de memória e com socket Docker direto gravável. A migração paralela para a
release estável atual, backup/rollback, binding privado e proxy sem `POST` estão em
[`plano_migracao_homarr_2026-08-04.md`](./plano_migracao_homarr_2026-08-04.md). Nenhuma
stack foi parada ou alterada. **Retomar por:** acompanhar ZDR; depois obter autorização
de janela para a Fase A do plano Homarr ou atribuir os listeners `139/445/3000`.

**Onde paramos (2026-08-04 — firewall persistente dual-stack comprovado):** o serviço
oneshot `agenda-docker-firewall.service` está instalado, `enabled` e `active`, ordenado
depois de UFW e Docker e associado a reinícios do daemon. Em IPv4, a chain
`AGENDA-LAN-DOCKER` em `DOCKER-USER` bloqueou pela interface física as seis portas
`5432/8000/8080/8081/8443/9443`; em IPv6, a chain `AGENDA-LAN-INPUT` em `INPUT`
bloqueou as mesmas seis portas. O teste externo obteve timeout/bloqueio em ambas as
famílias, com incremento dos seis contadores correspondentes, enquanto as seis portas
continuaram abertas pela Tailscale. Uma reinicialização controlada somente do serviço
reaplicou os quatro hooks e todas as regras; Docker e servidor não foram reiniciados.
O lote versionável está em `infra/firewall/`. **Retomar por:** (1) solicitar/provar ZDR
no projeto OpenAI; (2) planejar Homarr 0.x→1.x e socket proxy mínimo; (3) atribuir os
listeners externos `139`, `445` e `3000`. Receptor e dado real permanecem bloqueados.

**Onde paramos (2026-08-03 — hardening implantado e retestado):** o backup coordenado
pré-deploy falhou de forma fechada antes de parar serviços porque a cópia root-only da
`N8N_ENCRYPTION_KEY` não acompanhara a rotação. A cópia foi sincronizada diretamente do
contêiner, sem exibir o valor; nova execução validou os artefatos e criou o snapshot
`ebde69c8`. O staging gocryptfs foi desmontado e a aplicação voltou saudável.

As imagens anteriores foram preservadas localmente sob tags de rollback. Backend e
frontend foram reconstruídos com revisão OCI
`293a1275a79825f41a001a135a691a48e468f06d`; a migration transacional `0014` foi
aplicada antes da recriação exclusiva desses dois serviços. PostgreSQL, n8n e runner não
foram recriados. Estado final: Agenda e os dois PostgreSQL saudáveis, backend/frontend
sem reinícios anormais, schema `0014 (head)`, redes corretas, receptor e workflow de
teste inativos e `0` execuções no n8n.

**Reteste publicado aprovado:** tenant/usuário inteiramente sintéticos provaram login,
`Cache-Control: no-store, private`, troca de senha com revogação do bearer anterior,
relogin, logout global, revogação do novo bearer e logout idempotente de cookie inválido;
a limpeza terminou com zero tenants do smoke. Pela origem publicada, cinco logins
inválidos chegaram ao backend (`401`), o sexto e o sétimo receberam `429` com
`Retry-After: 60`, e `/auth/me` continuou sem limitação e com `no-store`. Logs não
mostraram erro/traceback nem credenciais. O bundle pós-deploy preservou as imagens
efetivamente executadas no snapshot `38272c78`; staging novamente desmontado.

**Retomar por:** (1) solicitar/provar ZDR no projeto OpenAI; (2) persistir a contenção do
firewall e criar equivalente IPv6 em janela separada; (3) planejar a migração segura do
Homarr e socket proxy. Receptor, workflow e dado real permanecem bloqueados até os
critérios de go-live serem encerrados.

**Onde paramos (2026-08-03 — code review concluído e lote versionado):**
o diff completo foi revisado e quatro problemas foram corrigidos: (1) troca de senha e
logout agora bloqueiam a linha do usuário e exigem a `session_version` apresentada,
evitando perda de incremento ou revogação de sessão nova em corridas; (2) logout
inválido/expirado permanece idempotente e remove o cookie local; (3) erros de validação
das settings ocultam valores de entrada, impedindo que um JWT fraco apareça no traceback;
(4) o fixture integrado de evoluções limpa a outbox antes da evolução e usa tenant
sintético estável, respeitando a FK criada pela `0012`. Estados históricos de firewall e
da Fase 8b também foram reconciliados.

**Validação final deste lote:** imagem backend final importou com segredo sintético forte
e recusou segredo fraco sem exibir o valor; `157 passed, 1 deselected` nos unitários e
`14 passed` nas integrações contra PostgreSQL 16 descartável, após migrations completas,
ciclo `0014→0013→0014` e reteste de autenticação. Frontend passou `npm ci`, TypeScript,
build Vite e build Docker; `nginx -t` passou com hostname sintético e o limitador repetiu
`502×5`, depois `429`, sem limitar rota comum. `npm audit` completo mantém apenas duas
ocorrências do advisory RSC não alcançável, e `7.18.2` segue como release estável mais
nova. Lint focado, `compileall` e `git diff --check` passaram.

**Estado naquele checkpoint, antes da autorização de deploy:** o lote técnico havia sido
versionado no commit `216d461`, mas ainda não houvera migration/deploy/restart,
publicação do receptor ou uso de dado real. O
PostgreSQL/rede de teste foram descartados; apenas imagens Docker locais de revisão podem
permanecer como artefatos recuperáveis. Próximo: (1) planejar deploy com snapshot e
migration `0014` antes do backend; (2) retestar login/cache/revogação somente com dados
sintéticos; (3) manter receptor e dado real bloqueados até ZDR e demais critérios de
go-live.

**Onde paramos (2026-08-02 — lote de hardening pronto para revisão, ainda sem
commit/deploy):** o working tree contém o relatório defensivo, atualização React Router
`7.18.2`/Vite `6.4.3`, imagens candidatas Node 22 + Nginx
`1.30.4-alpine3.24`, pisos Python para `msgpack`/`setuptools`, allowlist Gitleaks restrita
a dois JWTs sintéticos, esclarecimentos sobre `store=false`, `Cache-Control: no-store,
private` em toda `/api/`, rate limiting do login por IP na borda e validação fail-fast
do JWT (segredo ≥32 bytes, somente `HS256`). A migration local `0014` adiciona
`session_version`: troca de senha revoga tokens anteriores e reemite apenas o cookie da
sessão que comprovou a senha; logout global e suspensão/reativação incrementam a versão.
O SQL `0013→0014` foi somente renderizado offline — **não foi aplicado ao PostgreSQL**.

**Evidências deste ponto:** frontend candidato passou TypeScript/build, `nginx -t` e o
teste isolado de rate limit (`502×5`, depois `429`; rota comum não limitada); o `429`
contém `Retry-After: 60` e `no-store`. Backend candidato consolidado contém `0014`, inicia
com configuração sintética válida e recusa segredo fraco. Unitários:
`152 passed, 1 deselected` (NER “Lucas” já conhecido); lint básico dos arquivos alterados
e `git diff --check` passaram. Gitleaks terminou os 68 commits sem vazamento após a
allowlist AND estrita; Trivy e exceções upstream estão descritos em
[`revisao_seguranca_2026-08-01.md`](./revisao_seguranca_2026-08-01.md). Arquivos/logs de
build temporários foram removidos; somente as imagens Docker candidatas foram mantidas.

**Nada operacional foi feito neste lote:** nenhum commit/push, migration, deploy,
reinício de produção, publicação do receptor ou processamento de dado real. O receptor
n8n permanece inativo; produção continua no código/schema anteriores. **Retomar
exatamente por:** (1) revisar o diff e executar code-review; (2) corrigir achados e
repetir unitários/builds; (3) apresentar o lote ao usuário antes de commit; (4) planejar
deploy com snapshot, migration `0014` antes do novo backend e reteste exclusivamente
sintético de login/cache/revogação; (5) manter o receptor despublicado e dado real
bloqueado até ZDR comprovado e demais bloqueios de go-live encerrados.

**Onde paramos (2026-08-02 — retomada da Fase 9):** senha administrativa do PostgreSQL
n8n e HMAC Agenda↔n8n foram rotacionados sem exibir valores. As 12 execuções/payloads do
workflow de teste do Drive foram removidas por transação com guardas estritas. O script
pós-rotação passou a usar `publish:workflow`/`unpublish:workflow`, reiniciar n8n antes do
runner e limitar requisições a 55 segundos; a matriz inteiramente sintética passou
`401/401/200/200/409`. Estado final: receptor e workflow de teste inativos, n8n e banco
saudáveis, **0 execuções e 0 payloads globais**. Frontend validado com React Router
`7.18.2` e Vite `6.4.3`: TypeScript e build aprovados; advisories anteriores foram
fechados. Resta um advisory alto exclusivo de RSC, recurso ausente nesta SPA declarativa;
não há versão estável corrigida publicada, portanto a exceção é temporária e deve ser
monitorada. Exposição de rede e ZDR continuam pendentes. Não processar dado real nem
publicar o receptor.

**Onde paramos (2026-08-01 — revisão defensiva inicial concluída):** criado
[`revisao_seguranca_2026-08-01.md`](./revisao_seguranca_2026-08-01.md), com plano em seis
partes, **4 achados altos, 11 médios e 4 baixos**. Altos: (1) senha administrativa do
PostgreSQL n8n e HMAC expostos na conversa, ainda ativos por decisão do usuário; (2)
Portainer em todas as interfaces com Docker socket gravável; (3) code-server em todas as
interfaces com o workspace/`.env` acessível pelo mount; (4) pgAdmin e PostgreSQL auxiliar
publicados em todas as interfaces. O Git alcançável não contém `.env` real, chave privada,
token conhecido, dump ou backup; `.env` principal está `0600`. `pip-audit` do backend em
execução e `npm audit` do módulo PDF ficaram limpos. Frontend: React Router `6.30.4` tem
dois advisories moderados de produção; Vite `5.4.21`/esbuild têm advisories de dev, sendo
um alto. Bandit encontrou somente dois alertas baixos já mitigados no subprocesso do
sanitizador. n8n efetivo: `N8N_BLOCK_ENV_ACCESS_IN_NODE=false`,
`N8N_SECURE_COOKIE=false`, `EXECUTIONS_DATA_PRUNE=false`; rede `agenda-webhook` interna e
não anexável. **Limitações a fechar:** leitura de UFW/nftables exigiu senha sudo; não houve
scan a partir de outra máquina/Internet, DAST, scanner de imagens ou scanner de segredos
por entropia; pytest não existe no ambiente de produção. Docker socket apresentou esperas
longas, portanto evitar inspeções repetidas e agrupar somente consultas necessárias.
**Retomar exatamente por:** (1) reler o relatório; (2) com o usuário no terminal, capturar
apenas a política efetiva de firewall sem segredos; (3) testar da LAN as portas
`5432/8000/8080/8081/8443/9443`; (4) reclassificar ALT-02..04 pela alcançabilidade; (5)
rodar Trivy/Grype nas imagens e Gitleaks/TruffleHog no histórico; (6) revisar o relatório
antes de qualquer correção. Não rotacionar, fechar portas ou mudar stacks sem autorização
expressa. O workflow n8n continua despublicado e só pode receber payload sintético.

**Onde paramos (2026-07-31 — bloqueio técnico resolvido):** n8n e runner externo foram atualizados em conjunto para 2.33.0. A causa da retenção não era a finalização do workflow: logs `debug` provaram `Execution finalized` e `Execution removed`. Com `EXECUTIONS_DATA_PRUNE=true`, o n8n implementa `saveData*=none` como *soft-delete* e mantém temporariamente `execution_entity`/`execution_data`; a configuração final usa `EXECUTIONS_DATA_PRUNE=false`, que faz *hard-delete* imediato nesse caminho. O smoke externo passou `401/401/200/200/409` e, imediatamente depois, havia `0` execuções e `0` payloads; somente o hash antirreplay sintético permaneceu. Topologia final: n8n em `agenda-n8n_default` + `agenda-webhook`; runner e PostgreSQL apenas em `agenda-n8n_default`. Workflow novamente inativo. **Retomar pela rotação dos segredos expostos no diagnóstico; não enviar dado real antes dela.**

**Onde paramos (2026-07-31 — rotação n8n concluída, bloqueio ampliado):** `AGENDA_WEBHOOK_SECRET`, senha administrativa do PostgreSQL n8n e senha do role mínimo `agenda_webhook` foram rotacionados; a credencial mínima foi recriada cifrada, e chave de cifragem/token do runner permaneceram consistentes. Logging do n8n e broker passou de `debug` para `info`. Novo smoke exclusivamente sintético passou `401/401/200/200/409`, seguido imediatamente de `0` execuções e `0` payloads. O workflow voltou a inativo. Durante a recuperação de variáveis do Portainer, porém, uma inspeção textual ampla produziu saída maior que o filtro e exibiu ao menos uma credencial de outro serviço. Os arquivos temporários foram apagados, mas os segredos de ambientes potencialmente capturados devem ser rotacionados antes de dado real. **Retomar pelo inventário conservador e rotação dessas credenciais, sem repetir dump textual de ambientes.**

**Onde paramos (2026-07-31 — rotação local ampliada concluída):** senhas administrativa e `agenda_app` do PostgreSQL Agenda, `JWT_SECRET_KEY`, senha do code-server, senha web do pgAdmin e senha do PostgreSQL da stack pgAdmin foram rotacionadas. O token n8n legado foi removido. Agenda voltou saudável como `agenda_app`, migration `0012 (head)`; code-server, pgAdmin e seu PostgreSQL estão ativos, e o volume preexistente do pgAdmin foi explicitamente preservado na stack. Novas senhas dos serviços Portainer ficam somente nos respectivos editores de stack. **Ainda bloqueia dado real:** revogar a `OPENAI_API_KEY` anterior no provedor, criar outra, atualizar `.env` e recriar o backend.

**Onde paramos (2026-07-31 — chave OpenAI nova validada):** backend foi recriado com a nova `OPENAI_API_KEY`; igualdade arquivo↔contêiner conferida sem exibir valor. Chamadas exclusivamente sintéticas de embedding (1536 dimensões) e chat JSON passaram; backend saudável. **Ainda pendente:** confirmar no painel que a chave anterior foi apagada e revisar Usage por atividade inesperada. Só então encerrar o incidente e partir para o primeiro evento real controlado do webhook.

**Onde paramos (2026-07-31 — incidente encerrado e receptor publicado):** usuário confirmou a exclusão da chave OpenAI anterior. A outbox Agenda estava vazia antes da publicação, portanto nenhum evento antigo foi disparado. Workflow `agendaEvolucaoAssinadaV1` publicado e n8n reiniciado; HMAC backend↔n8n consistente; n8n/backend saudáveis; credencial mínima presente; `0` execuções e `0` payloads. **Retomar pelo primeiro evento real controlado:** criar/aprovar uma única evolução conhecida pelo operador, despachar e verificar somente metadados/contagens, sem abrir conteúdo clínico em logs ou terminal.

**Onde paramos (2026-07-31 — webhook real aprovado):** uma evolução real controlada gerou exatamente uma linha na outbox, entregue como `enviado` em uma tentativa. O antirreplay n8n aumentou exatamente em um; workflow permaneceu ativo e serviços saudáveis; imediatamente após a entrega havia `0` execuções e `0` payloads no n8n. Nenhum conteúdo, paciente ou identificador foi consultado na verificação. **Webhook FastAPI→n8n concluído. Retomar pelo desenho do PDF padronizado e destino cifrado, antes de qualquer Google/OAuth2.**

**Onde paramos (2026-07-31 — identificação profissional pronta):** requisito do PDF confirmado: cada evolução assinada deve gerar um **Registro de Evolução do Prontuário Psicológico** privado no Google Drive da psicóloga, contendo fielmente as informações salvas em Evoluções. O perfil agora possui CRP normalizado (`NN/NNNN...`), alteração auditada e migration `0013`; backend/frontend publicados e saudáveis. Contas existentes permanecem com CRP nulo somente para transição; a futura exportação deve falhar de forma fechada enquanto nome ou CRP estiver ausente. **Retomar pelo passo 2: ampliar o evento com os dados mínimos do paciente, atendimento e assinante, sem conceder ao n8n leitura geral do banco Agenda.**

**Onde paramos (2026-07-31 — contrato documental v1 publicado):** CRP preenchido confirmado sem revelar seu valor. O backend envia somente evolução/assinatura, nome e nascimento do paciente, início/fim do atendimento e nome/CRP do assinante; confere novamente tenant e vínculos e falha fechado com dados incompletos. O n8n continua sem acesso ao banco clínico. Contrato e perfil somaram **23 testes específicos aprovados**; backend publicado e saudável. O artefato do workflow preserva o payload somente após HMAC válido, sem histórico. **Retomar pelo passo 3: imagem customizada do runner com gerador PDF leve, fonte Unicode e template clínico; validar PDF inteiramente sintético antes de tocar no Google Drive.**

**Onde paramos (2026-07-31 — gerador PDF aprovado e runner publicado):** módulo fechado `@agenda/pdf-evolucao` construído com PDFKit `0.19.1`/lock íntegro e DejaVu Unicode na imagem `agenda-n8n-runners:2.33.0-pdf`, mantendo limite de 192 MiB e somente a rede `agenda-n8n_default`. PDF sintético curto aprovado técnica e visualmente: A4, texto selecionável, horário de São Paulo, metadados, nome opaco, SHA-256, sem JavaScript e uma página/um rodapé. Cenário longo: **4 páginas/4 rodapés**, sem páginas extras. Launcher JS/Python registrado, receptor ativo, `0` execuções e `0` payloads persistidos. Compose atualizado e confirmado no Portainer; todas as cópias temporárias com configuração sensível foram removidas. **Não ligar o gerador ao receptor ainda:** retomar pelo OAuth2/pasta privada e desenhar estado durável de processamento para retry idempotente do upload.**

**Retomada (2026-08-01 — passo 3 revisado e versionado):** o runner PDF foi revisado com validação fail-closed de UUID v4, data de nascimento real e intervalo positivo do atendimento. A imagem de teste foi reconstruída sobre Node 22/n8n runners 2.33.0; os cenários sintéticos curto e multipágina passaram. Não há credencial Google no n8n e nenhum arquivo foi enviado ao Drive. Retomar por: (1) pedir à psicóloga que crie uma pasta privada, sem compartilhamento por link; (2) abrir no n8n **Credentials → Create Credential → Google Drive OAuth2 API** e anotar somente o **OAuth Redirect URL**; (3) configurar no Google Cloud apenas a Google Drive API e o escopo mínimo `drive.file`; (4) testar upload com PDF sintético; (5) implementar estado durável `recebido/processando/processado/falhou` ou equivalente para retry idempotente; somente então conectar gerador+Drive ao receptor ativo. **Nunca pedir/enviar em chat Client Secret, token OAuth, senha Google, ID de paciente ou conteúdo clínico.**

**Onde paramos (2026-08-01 — OAuth/PDF sintético e idempotência local):** app Google externo em teste, credencial OAuth2 do n8n conectada somente com `drive.file`; PDF inteiramente sintético gerado pelo runner `r2`, enviado à pasta privada `Projeto_agenda` e aprovado visualmente. A imagem `r2` corrige o `env-overrides` do launcher, que ignorava a allowlist do Compose. Schema durável e workflow de 21 nós foram construídos localmente: claim/lease/backoff, estados, busca por `appProperties` privadas, upload somente se ausente e `200` após conclusão persistida. Schema passou duas aplicações + matriz funcional em PostgreSQL 16 descartável; workflow importou em n8n 2.33.0 descartável. **Nada disso foi aplicado ao workflow/banco operacional.** Dois segredos operacionais foram expostos na sessão; o usuário optou por não rotacioná-los. Por regra de segurança, continuar somente com payload sintético até a rotação.

**Onde paramos (2026-08-01 — deploy inativo e matriz sintética aprovada):** workflow anterior exportado em duas cópias root-only para `/tmp`; receptor despublicado; schema durável aplicado e workflow de 21 nós importado/configurado com credenciais mínimas e pasta privada. Smoke externo, após aguardar registro da rota, passou `401/401/200/200/409`. Simulação de queda pós-upload apagou apenas o estado local sintético; o retry encontrou o PDF pelas `appProperties`, concluiu na segunda tentativa e o retry seguinte não processou novamente. Imediatamente após os testes havia **0 execuções e 0 payloads** retidos. A pasta foi conferida visualmente: dois testes geraram exatamente dois PDFs, sem duplicata na recuperação. O receptor foi novamente despublicado e reiniciado. Falta apenas versionar o diff. Publicação real permanece bloqueada pela rotação recusada dos segredos expostos.

**Onde paramos (2026-07-29 — estado corrente):** o workflow `agendaEvolucaoAssinadaV1` está **inativo** e o ambiente está limpo (`0` execuções e `0` payloads desse workflow). PostgreSQL e n8n estão saudáveis. O n8n usa a imagem local `agenda-n8n:2.30.5-timestamp-fix`, derivada da 2.30.5 com a correção upstream `0316336` para `firstEvent`; o runner externo usa `n8nio/runners:2.30.5` e registrou launchers JavaScript/Python. A rede deve permanecer assim: n8n em `agenda-n8n_default` + `agenda-webhook`; runner e PostgreSQL somente em `agenda-n8n_default`. Após o deploy, o runner apareceu indevidamente na rede privada e foi desconectado manualmente; conferir isso em todo redeploy.

**Evidência do bloqueio:** os cinco eventos sintéticos retornaram corretamente HMAC inválido→401, timestamp expirado→401, novo válido→200, retry idêntico→200 e mesmo UUID/corpo divergente→409. Apesar disso, as cinco execuções (IDs sintéticos 17–21) permaneceram `running` com cinco registros em `execution_data`. O workflow foi imediatamente despublicado, o n8n reiniciado e somente essas cinco execuções sintéticas foram removidas com transação e filtros estritos. A linha antirreplay sintética `fd3c8cc5-534d-4690-a3b3-b58bd47caf88` permanece como evidência sem PII. Logs confirmaram o runner externo registrado, mas não mostraram erro de finalização.

**Retomar por:** manter o workflow inativo; investigar a trilha de finalização/estatísticas do n8n 2.30.5 e a compatibilidade do runner externo; não enviar evolução real. Para cada hipótese, publicar temporariamente, usar apenas novo UUID e texto sintético, executar os cinco casos, consultar `execution_entity`/`execution_data` e despublicar imediatamente se qualquer linha persistir. A liberação exige simultaneamente contrato HTTP correto, ausência de execução `running`, `0` payloads salvos e logs sem conteúdo clínico. As alterações locais em `infra/n8n/Dockerfile` e `infra/n8n/README.md` ainda estão sem commit.

**Onde paramos (2026-07-28):** o snapshot `aa64be52` e o bundle `4bd3dd57` foram restaurados em PostgreSQL, volume e rede Docker exclusivos. O banco recuperou 114 tabelas; a instalação de origem ainda tinha 0 workflows e 0 credenciais; o volume recuperou exatamente os 4 arquivos do tar; a chave restaurada já havia sido comparada com a ativa. A rede `--internal` bloqueou todas as tentativas externas. Recursos temporários foram removidos, staging desmontado e produção saudável. **Retomar por:** implementar e revisar o webhook autenticado com workflow inicialmente inativo; segunda cópia offline/off-site, retenção, RTO e restore em host separado permanecem pendentes de hardening.

- **Estado de deploy do servidor:** imagens backend/frontend em **`f97d237`**, migration **`0011 (head)`**; Agenda, n8n e os dois PostgreSQL saudáveis após o backup coordenado. O commit operacional do recovery `42c374c` ainda não foi enviado ao remoto nem exige rebuild das imagens da aplicação.
- **Sub-fases da Fase 7 (todas commitadas):** 7a/7b/7c (deployadas) · **7d** (`d6f3a95`): ações na agenda (realizado/falta/cancelar), `GET /dashboard/resumo`, **perfil** (`PATCH /auth/me`+senha; **migration `0006` GRANT UPDATE em `usuarios`** — sem ela o "alterar nome" dá 500, foi a causa do bug relatado) · **7e** (`e5b2d7c`): agenda por cliques + apagar; **arquivar/apagar paciente** (apagar bloqueado com prontuário, CFP §0.3); **evolução ↔ atendimento REALIZADO** (**migration `0007`**); dashboard histórico (dia/mês, cancelados, tooltips); responsável 18+ · **7f** (`65d8a7b`): **calendário** no dashboard (`GET /dashboard/{dia,mes,calendario}`, dashboard dividido dia/mês) + **recorrência** de agendamento (série materializada `serie_id`/`serie_frequencia`, **migration `0008`**; desfazer via `/agenda/:id`) · **7g** (`5603392`): polimento de UX (fonte maior, espaçamento, badge do calendário, **cartões de paciente** com observações editáveis inline). Detalhe de cada uma na seção da Fase 7 abaixo.
- **⚠️ Regra de fluxo nova (7e):** para gravar uma evolução, o atendimento precisa estar **`Realizado`** na agenda (o editor só lista realizados). Reflete o modelo "evolução documenta sessão que ocorreu".
- **Regra de arquivamento (7i):** paciente com atendimento futuro em estado `agendado` não pode ser arquivado; criação de agenda e arquivamento travam a mesma linha do paciente, evitando corrida. Paciente arquivado também não aceita novo agendamento. A ação preserva prontuário, registra ator/data e é auditável (§2.1/§2.2).
- **Escopo aprovado das próximas subfases:** **7j** = mini-dashboard clínico-administrativo na ficha (quantidade e situação das sessões, última, próxima, faltas/cancelamentos, cadência e histórico); **7k** = documentos PDF/DOCX/JPEG/PNG, armazenamento privado, validação e sanitização dentro do backend, sem criar outro serviço ou máquina. Arquivar exige resolver agenda futura; não há máquina auxiliar para varredura antivírus.

**Próximo passo imediato: FASE 8b — INVENTÁRIO n8n.** Descobrir, sem alterar o serviço nem expor segredos, o método de instalação, imagem/versão, banco, volumes, armazenamento binário e a presença da chave de cifragem. Só então definir o backup coordenado do n8n e o desenho do webhook autenticado pós-assinatura (§4.2). A rotação da credencial anteriormente versionada continua obrigatória.

**Fluxo de trabalho (imutável):** plano+perguntas → construir/validar local (WSL, sem Docker: `py_compile` + venv de teste `pytest tests/unit` + render offline do SQL; **frontend**: `npx tsc --noEmit` + `npm run build` — node 22 disponível no WSL) → **revisar com o usuário** (trazer diff/resumo) → `/code-review` alto esforço (usuário quase sempre pede) → **commit direto em `main`** (Co-Authored-By) → **push só quando o usuário pede** → **usuário** faz deploy no servidor e valida → marcar ✅. Comandos ao usuário **uma linha por vez** (terminal quebra pastes compostos). Ver [[feedback-fluxo-trabalho-agenda]].

**⚠️ Lição de deploy (7c):** os **testes de integração só rodam no servidor** (precisam de BD) e **não** são executados no deploy → um bug pego por eles pode escapar. Ex.: `/auth/me` deu 500 em produção porque `PerfilOut.email` era `EmailStr` e o `email-validator` rejeita o TLD `.local` do usuário de teste. **Regra adotada:** *response models (`Out`) usam `str` para e-mail; `EmailStr` só em `Create`/`Update` (entrada)*. Considerar um **smoke pós-deploy** no §9.

**Contexto de ambiente/dados (servidor):** SPA publicada apenas no localhost do servidor e acessada por **túnel SSH/Tailscale iniciado na máquina do usuário**. Endereços, nomes de host, usuários, senhas e identificadores de registros de teste **não são documentados no repositório**; ficam no inventário operacional restrito. O `.env` do servidor mantém as portas locais, o modo de cookie adequado ao transporte atual e a chave OpenAI fora do Git. **Ação obrigatória:** toda credencial que já tenha aparecido no histórico versionado deve ser rotacionada antes do próximo uso. Para testar a criação de evolução (7e+), usar um paciente descartável com TCLE ativo e agendamento **`realizado`**. **Setup de teste local (WSL):** venv py3.12 em scratchpad com `pip install -e '.[dev]'` p/ `pytest tests/unit`; FastAPI 0.139 usa inclusão **lazy** de routers (`app.routes` não expande — checar rotas via `app.openapi()['paths']`). Detalhes não sensíveis ficam na seção **Operação & Deploy**.

**Aderência que o usuário mais cobra:** citar as **§** da `arquitetura.md` em cada mudança; isolamento **no motor** da BD, nunca só na app (§2.1 — RLS+FORCE, FK composto `(tenant_id, id)`); túnel opaco de PII (§2.3) e superfície IA↔BD (§3.4) nas partes de IA.

---

## 🖥️ Operação & Deploy (contexto do servidor)

> Contexto que **não** se deduz do código — ler antes de mexer no ambiente.

- **Repositório:** `github.com/GA55555/projeto_agenda`, branch **`main`**. Dev local em WSL (`/home/hades/dev/agenda_de_atendimentos`) → commit/push. **Servidor só faz `git pull`** (nunca commitar/pushar do servidor).
- **Servidor:** Debian 12, Docker 29 + Compose v2. Nome do host, endereço e caminho operacional ficam no inventário restrito. Já roda outros serviços (Portainer, n8n, code-server, Homarr e serviços de outros projetos).
- **Comandos Docker rodam de dentro de `infra/`** com `--env-file ../.env` (o compose está em `infra/`, o `.env` na raiz). Ex.: `cd infra && docker compose --env-file ../.env up -d`.
- **Portas:** backend publicado em `127.0.0.1:8010` (`BACKEND_HOST_PORT` — a 8000 é do Portainer). **Frontend (SPA) em `127.0.0.1:8090`** (`FRONTEND_HOST_PORT` — a 8080 é do Homarr → `/board`). Postgres **sem** porta exposta. Sem GUI de admin (só `psql` via `exec`, §2.1.1). O browser fala **só com o Nginx** (`8090`), que faz proxy de `/api`→backend.
- **`.env` da Fase 7:** `FRONTEND_HOST_PORT=8090` e **`COOKIE_SECURE=false`** (deploy HTTP; sob TLS no §9 vira `true`, senão o cookie `Secure` não gruda e o login falha silenciosamente).
- **`.env` (fora do git, `chmod 600`):** segredos gerados **no servidor** (`POSTGRES_PASSWORD`, `APP_DB_PASSWORD`, `JWT_SECRET_KEY`, `DATABASE_URL` com a senha do `agenda_app`). Ao adicionar variáveis novas ao `.env.example`, lembrar que o `.env` do servidor **não** é atualizado pelo `git pull` — editar à mão.
- **Deploy padrão de código:** `git pull` → build com revisão OCI
  (`sudo env AGENDA_BUILD_REVISION="$(git rev-parse HEAD)" docker compose --env-file ../.env build backend frontend`)
  → migration → `up -d`. O bundle recusa imagem cuja revisão, ID ou tag não corresponda
  ao contêiner efetivamente executado.
- **Fase 7 (SPA):** deploy `up -d --build backend frontend` (sem migration na 7b/7c). **⚠️ 7d (fechamento) TEM migration:** `alembic upgrade head` → **`0006`** (GRANT UPDATE em `usuarios` p/ o perfil; sem ela, PATCH /auth/me e troca de senha dão 500 por privilégio). Acesso via túnel Tailscale (acima). Validar: login por cookie (`COOKIE_SECURE=false` em HTTP), dashboard, wizard de paciente, agendar (409 se sobrepor), CPF duplicado → 409. **Gotcha:** *response models (`Out`) usam `str` para e-mail, não `EmailStr`* — o `email-validator` rejeita TLDs reservados (`.local`) na serialização e derruba o endpoint (aconteceu no `/auth/me`).
- **Fase 7k (documentos):** o Compose cria o volume privado `documentos_data`, montado **somente** no backend, e um `tmpfs` limitado para originais/intermediários. Deploy exige reconstruir **backend + frontend** e aplicar a migration **`0010`**. Os limites têm defaults seguros; se personalizados no `.env`, usar `DOCUMENTOS_*`. **Backup obrigatório:** copiar o volume de forma cifrada junto do dump/WAL e testar restauração coordenada entre metadados e binários.
- **Fase 5 (RAG):** deploy padrão + **`alembic upgrade head`** (migration `0005`: `evolucoes` + `evolucao_chunks`). Adicionar **`OPENAI_API_KEY`** ao `.env` do servidor à mão (o `git pull` não toca o `.env`). Sem a chave, evoluções são criadas normalmente e os embeddings ficam **pendentes** (null) até a chave existir. `pgvector`/`openai` já entram no build (deps base).
- **Fase 4 (NER):** o `Dockerfile` do backend **já instala** o extra `[nlp]` + baixa `pt_core_news_sm` (modelo pequeno, §1.1) no build — NER ativo após `up -d --build backend`, sem passo manual. Import lazy (§1.3). Flag `NER_HABILITADO` no `.env` liga/desliga; sem o extra o pipeline degrada gracioso (só Aho-Corasick + regex). **Não** há migration na Fase 4.
- **⚠️ Roles/init:** mudanças em `infra/postgres/init/*` (ex.: novo role) só reaplicam com **`docker compose --env-file ../.env down -v`** (recria o volume `pgdata`). Migrations aditivas **não** precisam. Dados atuais são **descartáveis** (só há 1 tenant de teste).
- **Bootstrap de usuário:** `docker compose --env-file ../.env exec backend python -m app.cli criar-tenant-usuario --nome ... --email ... --senha ...`.
- **Dados atuais:** ambiente de teste descartável. Credenciais e identificadores vivem somente no inventário operacional restrito, nunca neste documento.
- **Provas rápidas:** RLS na BD → `infra/postgres/checks/verify_rls.sql`; liveness `GET /health`; readiness `GET /health/ready`; login `POST /api/v1/auth/login` (form `username`/`password`).
- **Validação local (WSL, sem Docker):** `py_compile` + venv de teste (imports + `pytest tests/unit`). Testes de **integração** e `docker compose up` só rodam **no servidor** (têm BD). `pytest` não está na imagem de produção (é dep `[dev]`).

---

## 🗺️ Visão Geral das Fases

| # | Fase | Objetivo central | Status |
| --- | --- | --- | --- |
| 0 | Fundações & Infra Base | Esqueleto do repositório, Docker e limites de RAM | ✅ Concluído |
| 1 | Base de Dados & Multitenancy | PostgreSQL + pgvector + RLS funcionando | ✅ Concluído |
| 2 | Backend Core (FastAPI) | API base, auth, injeção de tenant | ✅ Concluído |
| 3 | Modelo de Domínio & Consentimento | Pacientes, responsáveis, TCLE, auditoria | ✅ Concluído |
| 3.5 | Agenda de Atendimentos | Agendamentos vinculados a paciente + tenant | ✅ Concluído |
| 4 | Pipeline de Pseudonimização | Túnel opaco anonimizar/desanonimizar (Aho-Corasick) | ✅ Concluído |
| 5 | IA Vetorial & RAG | Embeddings, filtragem híbrida, chunking | ✅ Concluído |
| 6 | Integração LLM (OpenAI) | Geração de evoluções via túnel de pseudonimização | ✅ Concluído |
| 7 | Frontend (SPA) | Interface das psicólogas, aprovação de evoluções | ✅ Concluído |
| 8 | Automação n8n & Backups | Webhooks, OAuth2, PDFs, pg_dump/WAL | 🟡 Em progresso (8b: inventário n8n) |
| 9 | Hardening & Go-Live | Segurança final, limites, observabilidade, deploy | ⬜ Não iniciado |

Legenda: ⬜ Não iniciado · 🟡 Em progresso · ✅ Concluído · ⛔ Bloqueado

---

## Fase 0 — Fundações & Infraestrutura Base

**Objetivo:** repositório versionado, esqueleto de serviços em Docker e limites de RAM aplicados desde o primeiro contentor.

**Regras de ouro aplicáveis:** §1.1 (hard limits), §4.1 (multi-stage, segredos).

### Tarefas
- [x] `git init` e `.gitignore` (ignorar `.env`, `__pycache__`, `node_modules`, dumps). Remote: `github.com/GA55555/projeto_agenda`.
- [x] Estrutura de pastas: `backend/`, `frontend/`, `infra/`, `docs/`.
- [x] Mover `arquitetura.md` e `planejamento_arquitetura.md` para `docs/`.
- [x] `docker-compose.yml` base (postgres + backend, `mem_limit` explícito §1.1). Frontend comentado como TODO da Fase 7.
- [x] **Sem contentor de administração** (pgAdmin/CloudBeaver): admin da BD por `psql` via `docker compose exec` (decisão de menor exposição, §2.1.1/§4.1).
- [x] `.env.example` documentando todas as variáveis (sem valores reais).
- [ ] Configurar Docker Secrets ou `.env` com permissões restritas ao admin.
- [x] `README.md` de bootstrap (como subir o ambiente local).

### Definition of Done
- `docker compose up` sobe os 3 contentores (postgres, backend, frontend) sem exceder o orçamento de RAM.
- Nenhum segredo commitado; `.env` está no `.gitignore`.

> ✅ **Concluído 2026-07-17 no servidor Debian.** postgres + backend `healthy`; extensão `vector` ativa; `/health`→`{"status":"ok"}`. **Nota de infra:** a 8000 do host é ocupada pelo Portainer → backend publicado em `127.0.0.1:8010` via `BACKEND_HOST_PORT=8010` no `.env`. Frontend fica para a Fase 7.

---

## Fase 1 — Base de Dados & Multitenancy (RLS)

**Objetivo:** PostgreSQL afinado, pgvector instalado e isolamento por RLS provado com teste.

**Regras de ouro aplicáveis:** §1.1 (1.5 GB), §1.2 (postgresql.conf), §2.1 (RLS), §3.1 (sem índice vetorial).

### Tarefas
- [x] Imagem Postgres com extensão `pgvector` (`CREATE EXTENSION vector`). *(adiantado na Fase 0: imagem `pgvector/pgvector:pg16` + `infra/postgres/init/01-extensions.sql`)*
- [x] `postgresql.conf` afinado: `shared_buffers` 512MB, `work_mem` 8MB, `maintenance_work_mem` 128MB, `max_connections` 50 (§1.2). *(adiantado na Fase 0: `infra/postgres/postgresql.conf`)*
- [x] Ferramenta de migrations (Alembic): `alembic.ini`, `migrations/env.py` (URL admin via settings, nunca no ini), template.
- [x] Migration inicial `0001`: tabela `tenants` (`id UUID` default `gen_random_uuid()`, `nome`, `slug`, `ativo`, timestamps).
- [x] Padrão `tenant_id` + RLS centralizado no helper `app/db/rls.py` (fonte única), pronto para as tabelas clínicas da Fase 3.
- [x] **Dois roles distintos:** `agenda_admin` (migração/owner, superusuário) × `agenda_app` (`NOSUPERUSER NOBYPASSRLS`, provisionado no init `02-roles.sh`) — RLS atua sobre a aplicação (§2.1.1).
- [x] Ativar RLS + política `tenant_isolation` com `current_setting('app.current_tenant_id')` — **fail-closed** (`nullif` → sem contexto retorna vazio) (§2.1).
- [x] **`FORCE ROW LEVEL SECURITY`** aplicado via helper (nem o dono escapa) (§2.1.1).
- [ ] Índices B-Tree sobre `tenant_id` e `paciente_id` — junto das tabelas clínicas (Fase 3, §3.2).
- [x] **Teste de isolamento:** `tests/integration/test_rls_isolation.py` (pytest) + `infra/postgres/checks/verify_rls.sql` (psql, via `SET ROLE agenda_app`) — provam isolamento T1/T2 e fail-closed.

### Definition of Done
- Teste automatizado de *cross-tenant leakage* passa (retorno vazio para tenant errado). ✅
- **Nenhum** índice vetorial criado (Pesquisa Exata, §3.1). ✅

> ✅ **Concluído e validado no servidor 2026-07-18.** `alembic upgrade head` aplicou `0001`; `verify_rls.sql` → **`RLS OK`** (T1 vê só T1, T2 só T2, sem contexto = vazio/fail-closed). Role `agenda_app` confirmado sem Superuser/Bypass RLS.

---

## Fase 2 — Backend Core (FastAPI)

**Objetivo:** API base com autenticação e injeção automática do contexto de tenant por transação.

**Regras de ouro aplicáveis:** §1.3 (lazy loading, 2 workers, uvloop, GC), §2.1 (`SET LOCAL`), §4.1 (JWT via secrets).

**Decisão:** **tenant = psicóloga** (fronteira de isolamento). `usuarios` = control-plane (email global, sem RLS); tabelas clínicas mantêm RLS+FORCE.

### Tarefas
- [x] Estrutura FastAPI + SQLAlchemy + pool (`pool_size=5, max_overflow=5`) como `agenda_app` (`app/db/session.py`).
- [x] Dockerfile **multi-stage** `slim`; `uvicorn --workers 2 --loop uvloop` (§1.3). *(Fase 0)*
- [x] `gc.set_threshold(700, 10, 10)` no arranque (§1.3). *(Fase 0)*
- [x] Autenticação JWT, login das psicólogas (`core/security.py` bcrypt+JWT, `modules/auth/*`, `POST /auth/login`, `GET /auth/me`).
- [x] **Dependência `get_tenant_session` que executa `SET LOCAL` (via `set_config` local) dentro da transação** de cada request autenticado (`app/db/deps.py`) (§2.1).
- [x] Tabela `usuarios` (migration `0002`) + CLI `criar-tenant-usuario` (bootstrap).
- [x] `GET /tenants/atual` (prova RLS pela API) + convenção de imports lazy documentada (§1.3).
- [x] Healthcheck: `/health` (liveness) + `/health/ready` (SELECT 1).

### Definition of Done
- Request autenticado só enxerga dados do seu tenant (RLS + `SET LOCAL` validados juntos). ✅
- Backend arranca com ≤ 2 workers e respeita `mem_limit` de 1 GB. ✅

> ✅ **Concluído e validado no servidor 2026-07-18.** Login → JWT; `GET /tenants/atual` devolve só o tenant do JWT (RLS via `SET LOCAL`); senha errada → 401; `/health/ready` → 200. Migration `0002` aplicada; 1ª psicóloga criada via CLI.
> **Bug corrigido:** `passlib` 1.7 × `bcrypt` ≥4.1 → migrado para a lib `bcrypt` direta.

---

## Fase 3 — Modelo de Domínio & Consentimento

**Objetivo:** modelar pacientes (menores), responsáveis legais, consentimento e auditoria imutável.

**Regras de ouro aplicáveis:** §2.2 (ECA/LGPD Art. 14, TCLE, auditoria indelével).

**Decisões de domínio (2026-07-18):** vínculo responsável↔paciente **N:N** (tabela `vinculos_resp_paciente` com `tipo_vinculo`/`detem_guarda`/`principal`) — suporta pai+mãe, guarda compartilhada, irmãos; auditoria = **log genérico append-only** (`auditoria`), imutabilidade imposta no BD (**REVOKE UPDATE/DELETE + trigger** `BEFORE UPDATE OR DELETE`); TCLE grava metadados+texto/versão (geração de PDF fica p/ Fase 8/n8n); agendamentos movidos p/ **Fase 3.5**.

### Tarefas
- [x] Tabela `responsaveis_legais` (perfil detalhado). CPF único **por tenant** (PII sob RLS).
- [x] Tabela `pacientes` **sempre** vinculada a responsável legal — invariante imposto na criação (transação única: paciente + ≥1 vínculo + TCLE).
- [x] Tabela `consentimentos` (TCLE): `finalidade_clinica`/`limitacoes_acesso` obrigatórias, termo (versão+texto), data, responsável, quem concedeu.
- [x] Distinção de acesso registrada no TCLE (`limitacoes_acesso`). *Imposição sobre o conteúdo clínico (evoluções) entra na Fase 5+.*
- [x] Tabela de **auditoria imutável** (append-only) — REVOKE + trigger no BD; helper `audit.service.registrar_evento` (revogação de consentimento já grava; guarda entra com a edição de vínculo).
- [x] Endpoints CRUD respeitando RLS (`/responsaveis`, `/pacientes`, `/consentimentos`, `/auditoria` read-only).
- [→] Agendamentos vinculados a paciente + tenant → **movido para a Fase 3.5**.
- [x] Índices B-Tree de pré-filtragem por `tenant_id`/`paciente_id` (§3.2).

### Definition of Done
- Impossível criar paciente sem responsável legal e sem TCLE registrado. ✅ *(schema + serviço transacional; testes unitários provam a rejeição)*
- Revogações/alterações ficam em log inalterável e auditável. ✅ *(auditoria append-only; teste de integração prova UPDATE/DELETE bloqueado)*

> ✅ **Concluída e validada no servidor 2026-07-18.** `alembic upgrade head` aplicou `0003`. Provado por API/psql: criação de paciente+vínculo+TCLE em transação única (RLS `WITH CHECK`, grants, FK composto sob FORCE RLS); resposta traz vínculos+responsável aninhados; CPF normalizado; revogação de TCLE gera evento em `auditoria`; `UPDATE` na auditoria barrado pelo trigger **até para o superusuário** (`ERROR: auditoria e append-only`).

---

## Fase 3.5 — Agenda de Atendimentos

**Objetivo:** agenda de atendimentos vinculada a paciente + tenant (desmembrada da Fase 3 para manter o foco em domínio/consentimento).

**Regras de ouro aplicáveis:** §2.1 (RLS + `tenant_id`), §3.2 (índices B-Tree).

**Decisões (2026-07-19):** anti-sobreposição **no motor** via `EXCLUDE` (btree_gist, `tstzrange(inicio,fim,'[)')`) — atendimentos encostados (fim==início) permitidos; agenda **não** exige TCLE (consentimento é pré-req do prontuário, Fase 5+); status `agendado/realizado/cancelado/falta`, cancelamento **soft** (`motivo_cancelamento`, sem DELETE); paciente por **FK composto** `(tenant_id, paciente_id)` (§2.1); datetimes com timezone obrigatório.

### Tarefas
- [x] Tabela `agendamentos` (`tenant_id`, `paciente_id`, `inicio`, `fim`, `status`, `tipo?`, `observacao`, `motivo_cancelamento`, timestamps) + RLS/FORCE.
- [x] Índices B-Tree `(tenant_id, inicio)` e `paciente_id` (§3.2).
- [x] Endpoints CRUD sob RLS (`POST/GET`, `GET/PATCH /{id}`, `POST /{id}/cancelar`); sobreposição → 409, paciente fora do tenant → 422.
- [x] Estados do atendimento + **não-sobreposição imposta no BD** (`EXCLUDE`, §2.1).

### Definition of Done
- Agendamento sempre vinculado a paciente do tenant (RLS provado). ✅
- Nenhum agendamento cruza tenants. ✅ *(FK composto + RLS; teste de integração)*

> ✅ **Concluída e validada no servidor 2026-07-19.** `alembic upgrade head` → `0004` (extensão `btree_gist` + tabela). Smoke via API: agendamento criado (`agendado`); sobreposição rejeitada (**409** pelo `EXCLUDE`). Review de alto esforço aplicado (4 correções: PATCH 422, timezone, alias `status`, teste RLS).

---

## Fase 4 — Pipeline de Pseudonimização (Túnel Opaco)

**Objetivo:** anonimização/desanonimização local, síncrona e reversível — pré-requisito para qualquer chamada ao LLM.

**Regras de ouro aplicáveis:** §2.3 (Aho-Corasick, dicionário volátil, nunca persistir PII), §1.3 (lazy loading de libs pesadas).

**Decisões de design (2026-07-19, via AskUserQuestion):** fonte = **cadastrado (Aho-Corasick) + NER (Presidio) lazy** para PII de texto livre; ciclo do dicionário volátil = **por requisição** (nasce/morre no request, sem estado entre chamadas); entrega = **módulo puro** (sem rota/tabela/migration) consumido pela Fase 6; modelo NER = **`pt_core_news_sm` (pequeno)** para caber no `mem_limit` de 1 GB (§1.1) — camada NER atrás do extra `[nlp]` + flag `ner_habilitado`. Marcadores `<CAT_n>` sequenciais por 1ª aparição, idempotentes por trecho exato (round-trip exato). Sobreposição: **mais longo vence** + fronteira de palavra.

### Tarefas
- [x] Motor de deteção com **Aho-Corasick** (puro, stdlib) + Regex ancorado; Presidio como reforço, importado lazy (§1.3/§2.3). *(`automaton.py`, `recognizers.py`, `nlp.py`)*
- [x] Fonte de entidades PII do paciente (nome, familiares, clínica) sob RLS para alimentar o autômato. *(`sources.py`)*
- [x] `Anonymizer`: mapeia PII → marcadores sequenciais (`<PERSON_1>`, `<LOCATION_1>`). *(`pseudonimizador.py`)*
- [x] **Dicionário de equivalência em memória volátil** (`MapaPseudonimizacao`) — não é model, sem serializador, `__repr__` esconde valores; **jamais gravado na BD** (§2.3).
- [x] `Deanonymizer`: restaura marcadores no texto de resposta. *(`pseudonimizador.desanonimizar`)*
- [x] **Guard-rail de saída** (`guardrail.verificar_sem_pii`) — aborta (`PIIVazadaError`) se PII conhecida escapar (antecipa Fase 6).
- [x] Testes unitários: round-trip preserva o texto; nenhum PII escapa; dicionário não persiste; fronteira de palavra; regex; anti-backtracking. **35 passed, 1 skipped** (NER só roda com o extra `[nlp]`).

### Definition of Done
- Teste prova que texto enviado "para fora" não contém PII. ✅ *(guard-rail + round-trip; validar no servidor com o NER ligado)*
- Teste prova que o dicionário não é persistido em lugar nenhum. ✅ *(não é `Base`; sem `models.py`/`router.py`/migration; `__repr__` não vaza)*

> ✅ **Concluída e validada no servidor (2026-07-19).** Build instalou `[nlp]` + `pt_core_news_sm`. Smoke por dentro do container: Pedro→`<PERSON_1>`, CPF→`<CPF_1>`, **round-trip exato**, **guard-rail** detecta PII que escaparia. **NER provado**: `João Silva`→PERSON, `São Paulo`/`Belo Horizonte`→LOCATION (mapeamento PER→PERSON OK, achado #3 resolvido). Code-review de alto esforço → **5 achados aplicados**: (#1) offset via `_fold` que preserva comprimento no caseless; (#2) O(n²) no `desanonimizar`; (#3) mapeamento explícito de rótulos NER; (#4) removido `presidio-anonymizer` não usado; (#5) desempate de categoria determinístico. **Limitação conhecida:** o modelo `sm` tem recall menor (ex.: não pegou "Lucas" em contexto pobre) — aceitável, o NER é *reforço*; PII de paciente/família é **cadastrada** (Aho-Corasick). RAM idle do backend: 165 MB (o modelo NER carrega lazy por processo, só na Fase 6 aparece nos workers — vigiar o orçamento de 1 GB, §1.1).

---

## Fase 5 — IA Vetorial & RAG (pgvector)

**Objetivo:** memória longitudinal do paciente via embeddings, com filtragem híbrida e chunking.

**Regras de ouro aplicáveis:** §3.1 (sem índice), §3.2 (filtragem híbrida obrigatória), §3.3 (chunking), **§3.4 (superfície IA↔BD: só vetorizar texto anonimizado; RAG sob RLS; guard-rail nos embeddings)**.

**Decisões de design (2026-07-19, via AskUserQuestion):** (1) **nota crua** no BD sob RLS + **embedding só do texto anonimizado** (re-anonimiza no uso, Fase 6); (2) embeddings **síncronos**, nota **persiste mesmo se a OpenAI falhar** (chunk fica `embedding` pendente/null, re-embed depois); (3) criar evolução **exige TCLE ativo** (§2.2, gate no serviço); (4) escopo = tabelas+chunking+embed+retrieval+endpoints, **sem LLM** (Fase 6). Marcadores canonicalizados (`<PERSON_1>`→`<PERSON>`) só para o vetor (reduz ruído).

### Tarefas
- [x] Tabela `evolucoes` (nota crua) + `evolucao_chunks` com coluna `embedding vector(1536)`; RLS+FORCE, FK composto, migration `0005`.
- [x] Estratégia de **chunking** (`chunking.py`): parágrafos + subdivisão por frase com overlap.
- [x] Serviço de embeddings (`embeddings.py`, OpenAI **lazy** §1.3, timeout curto) — texto **já anonimizado** (§3.4) + guard-rail antes da chamada.
- [x] Consulta RAG (`service.buscar_contexto`) pré-filtrada por `tenant_id`+`paciente_id`, depois `ORDER BY embedding <=> $vetor LIMIT k` (§3.2).
- [x] **Ausência de índice vetorial** confirmada no render da migration (Pesquisa Exata, §3.1).
- [x] Gate de **consentimento ativo** (§2.2) + endpoints CRUD (`POST/GET /evolucoes`).
- [~] Testes de recall/latência com dados sintéticos → **movido p/ Fase 6** (quando houver geração real e chave OpenAI no servidor).

### Definition of Done
- Query RAG nunca roda sem os filtros de tenant/paciente. ✅ *(filtro explícito no `buscar_contexto` + RLS; teste do filtro fica p/ Fase 6)*
- Latência da busca exata < 50 ms no volume esperado. *(validar no servidor com dados)*

> ✅ **Concluída e validada no servidor (2026-07-19).** `alembic upgrade head` → `0005`. Provado por psql/API: RLS FORCE nas 2 tabelas (`relforcerowsecurity=t`), coluna `embedding vector(1536)`, índices só B-Tree (**sem `ivfflat`/`hnsw`**, §3.1). Smoke via API: criar evolução p/ paciente com TCLE revogado → **422** (gate §2.2); paciente com consentimento → **201** com `total_chunks:2` (chunking §3.3) e `embeddings_pendentes:2` (sem chave OpenAI ativa → **nota persiste**, degradação graciosa da decisão Fase 5). Code-review de alto esforço → **#1/#2/#4 aplicados** (timeout OpenAI; contagem via `COUNT` sem materializar o vetor; grant sem DELETE §2.1.1). **Registrados p/ depois:** #3 (reuso de entidades/autômato por evolução), #5 (guarda de dimensão do vetor vs. modelo), #6 (teste do filtro híbrido do retrieval — Fase 6).

---

## Fase 6 — Integração LLM (OpenAI)

**Objetivo:** gerar resumos/evoluções clínicas passando **exclusivamente** por texto anonimizado.

**Regras de ouro aplicáveis:** §2.3 (só texto mascarado sai), §3.3 (prompt dinâmico com contexto recuperado), **§3.4 (LLM sem tool de BD; separação instrução/dado; guard-rail em toda saída; OpenAI retenção-zero)**.

**Decisões de design (2026-07-19, via AskUserQuestion):** deliverable = **rascunho de evolução + destaques longitudinais** (resposta em JSON); persistência **stateless** (só retorna; salvar aprovado usa `POST /evolucoes` da Fase 5 na Fase 7 — **sem migration**); modelo **`gpt-4o-mini`** (via env, `temperature` baixa); **gate de TCLE ativo** na geração (§2.2).

### Tarefas
- [x] Montagem de prompt dinâmico (`prompts.py`): nota do dia + blocos históricos (Fase 5), **anonimizados numa única passagem** (marcadores consistentes); instrução separada do dado (§3.4 #5).
- [x] Chamada à OpenAI (`client.py`) recebendo só tokens artificiais; **sem tools** (§3.4 #1), `store=False` (armazenamento desativado na chamada), timeout de chat próprio. A retenção da organização é uma verificação operacional da Fase 9 (§3.4 #6).
- [x] Desanonimização da resposta antes de exibir (Fase 4); marcadores residuais/alucinados limpos.
- [x] **Guard-rail** (§3.4 #4): aborta a chamada (hard-fail, 422) se PII conhecida aparecer no payload de saída.
- [x] Tratamento de erros (OpenAI indisponível → 503; JSON inválido → fallback tolerante).
- [x] Chave OpenAI via `.env` restrito (§4.1); `POST /llm/evolucoes/rascunho`.

### Definition of Done
- Log/inspeção confirma que o payload enviado à OpenAI não tem PII. ✅ *(guard-rail + teste prova que nada de PII crua sai; abortar antes da chamada)*
- Resposta final ao usuário aparece desanonimizada e legível. ✅ *(desanonimização com o mapa volátil; teste de round-trip)*

> ✅ **Concluída e validada no servidor (2026-07-19).** Módulo `llm` stateless (sem tabela/migration). Fluxo: gate TCLE → RAG (`buscar_contexto`) → monta+anonimiza numa passagem → **guard-rail hard-abort** → OpenAI (`gpt-4o-mini`, sem tools, `store=false`) → desanonimiza → rascunho. **55 unit tests** local. Smoke no servidor com `OPENAI_API_KEY` ativa: `POST /llm/evolucoes/rascunho` → **200** com `evolucao` (texto clínico coerente em pt) + `destaques` (lista) + `chunks_contexto` — provou, contra a API viva, o modo `json_object` (achado #2), sem 503 espúrio (achado #1) e o parse JSON→campos. Sem chave → **503** (fail-closed); campo errado → **422** (schema). Code-review de alto esforço → **5 achados aplicados**: (#1) timeout de chat separado (60s); (#2) "json" minúscula no prompt; (#3) limpeza de marcadores residuais; (#4) `anonimizar_com_entidades` reusa entidades (otimiza a Fase 5 tb); (#5) `SemConsentimentoAtivo` centralizada em `consentimentos`.

---

## Fase 7 — Frontend (SPA)

**Objetivo:** interface das psicólogas para agenda, prontuários e **aprovação** de evoluções geradas.

**Regras de ouro aplicáveis:** §1.1 (Nginx 100 MB), §2.2 (separação de acessos), §4.1 (multi-stage), §2.1.1 (backend não-exposto: Nginx faz proxy de `/api`).

**Decisões (2026-07-19, via AskUserQuestion):** **React + Vite + TS**; escopo em **vertical slice** do loop de IA (login→agenda→ficha→gerar→aprovar→gravar); **token JWT em cookie httpOnly** (SameSite strict; `Secure` sob TLS no §9); **só psicólogas** agora (portal dos pais §2.2 fica p/ fase própria). Dividida em **7a (fundação)** e **7b (telas)**.

### Tarefas — 7a (fundação) ✅ construída
- [x] SPA **React + Vite + TS**; Nginx `mem_limit` 100 MB (§1.1), **multi-stage** (§4.1).
- [x] **Nginx serve estáticos + reverse-proxy `/api`→`backend:8000`** (mesma origem, zero CORS, backend não-exposto §2.1.1); CSP + headers de segurança.
- [x] **Auth por cookie httpOnly** no backend (login seta cookie; `get_current_user` lê cookie|bearer; `POST /auth/logout`); dual-mode intencional (bearer p/ curl/testes).
- [x] SPA: cliente de API (`credentials: include`, JS não lê o token), AuthContext (`/auth/me`), handler global de 401, telas Login + Home (prova a sessão).

### Tarefas — 7b (telas) ✅ deployada e validada
- [x] **Agenda do dia** (`GET /agendamentos` filtrado por [de,ate) do dia + mapa de nomes); **ficha do paciente** (dados+responsáveis+**status TCLE**+evoluções). Shell de navegação (Agenda·Pacientes·Sair).
- [x] **Editor de evolução**: nota do dia → `POST /llm/evolucoes/rascunho` → revisar/editar (desanonimizado) → aprovar → `POST /evolucoes`. Trata 422 (mostra `detail` real), 503 (IA), 401 (login).
- [x] Assinatura eletrônica auditável construída na fundação da **8b**: confirmação
  explícita no payload/UI, assinante+data, auditoria atômica e evolução imutável no BD
  (migration `0011`). Não é assinatura com certificado ICP-Brasil; é assinatura eletrônica
  autenticada e auditável adequada ao acionamento interno definido no §4.2.
- [~] Distinção de acesso pais × conteúdo (§2.2) → app **só psicólogas** nesta fase; portal dos pais é fase própria.

### Definition of Done
- Fluxo completo: nota → IA → revisão → aprovação → gravação funciona ponta a ponta. ✅ *(validado no browser no servidor, 2026-07-20)*
- Contentor frontend respeita 100 MB. ✅ *(Nginx alpine estático)*

> ✅ **7b deployada e validada no servidor (2026-07-20).** Loop completo percorrido no browser (via túnel SSH/Tailscale): login → agenda → ficha (TCLE ativo) → Nova evolução → **Gerar rascunho (IA)** → revisar → **Aprovar e gravar**. **RAG provado**: após 1-2 evoluções, o rascunho seguinte trouxe `chunks_contexto > 0` (a IA recuperou histórico do próprio paciente) — valida a convergência Fases 4+5+6+7 e os embeddings da Fase 5 finalmente populados/recuperados. Detalhe da construção/review abaixo. ↓
>
> **Histórico:** a 7b foi primeiro validada localmente em 2026-07-19 e depois deployada e validada no servidor em 2026-07-20, conforme o marco acima.
>
> ✅ **7a deployada e validada no servidor (2026-07-19).** Backend: **61 unit tests** (6 novos de cookie/bearer); frontend `build`+`tsc` OK. Code-review → **7 achados, 6 aplicados** (#4 mantido dual-mode de propósito). No servidor: SPA servida (`200`, headers de segurança/CSP), e **auth por cookie httpOnly provado ponta a ponta** — `login`→`/auth/me` só com cookie devolveu o contexto do JWT via Nginx→backend. **Infra do deploy:** porta host **8090** (a 8080 é do Homarr — conflito, igual à 8000/Portainer→8010); **`COOKIE_SECURE=false`** no `.env` (HTTP). Bug do healthcheck (`wget -qO-` não parseia no BusyBox) corrigido p/ `wget -q -O /dev/null`.

### 7c — Melhorias de Frontend (pedido do usuário, 2026-07-20)

**Objetivo:** app mais completo e usável — dashboard, cadastros (agendar, criar paciente/responsável), menu de perfil e um design **sóbrio, efetivo e fácil** (não mais minimalista).

**Decisões (via AskUserQuestion):** começar por **7c.1 (design+navegação)**; criar paciente por **assistente guiado** (responsável novo/existente → dados → TCLE, uma transação); **enriquecer `/auth/me`** com nome/e-mail p/ o menu de perfil; direção visual **clínico calmo** (sidebar clara, cards, acento verde-azulado, espaçamento generoso, badges suaves).

**Incrementos:**
- **7c.1 — Design & Navegação:** design system (paleta clínica, componentes reutilizáveis), **layout com sidebar** (Dashboard·Agenda·Pacientes·Responsáveis) + **menu de perfil** (nome/e-mail/papel + Sair). Backend: `/auth/me` passa a devolver nome/e-mail (1 query, sem migration). Telas Dashboard/Responsáveis entram como placeholder. → ✅ **deployada e validada no servidor (2026-07-20)**; `tsc`+`build` OK, 61 unit tests; code-review aplicado.
- **7c.2 — Cadastros:** criar **agendamento** (form + 409 de sobreposição); **Responsáveis** (lista + criar/editar + detalhe com contato); criar **paciente** (wizard responsável→dados→TCLE). → ✅ **deployada e validada no servidor (2026-07-20)**; `tsc`+`build` OK, backend 61 unit tests; tratamento de CPF duplicado e guards revisados.
- **7c.3 — Dashboard:** visão geral — hoje na agenda, contadores, acesso rápido. → ✅ **deployada e validada no servidor (2026-07-20)**; `tsc`+`build` OK. O agregado de pendências foi entregue depois em `GET /dashboard/resumo` na 7d.

### 7d — Fechamento da Fase 7 (pedido do usuário, 2026-07-20)

**Objetivo:** 3 frentes que faltavam — **ações na agenda** (realizado/falta/cancelar por linha), **`GET /dashboard/resumo`** (indicadores agregados no BD, §2.1/§3.2) e **configuração de perfil** (`PATCH /auth/me` + `POST /auth/me/senha`).

**Decisões (via AskUserQuestion):** perfil edita **nome+e-mail+senha** (troca de senha exige a atual); agenda = realizado/falta/cancelar c/ **motivo opcional** (sem reagendar); dashboard = 3 blocos (hoje / mês c/ taxa de comparecimento e dias com atendimento / pendências: sem TCLE §2.2, sem próximo atendimento, próxima semana).

**Construção:** módulo `dashboard` (**sem model/migration**, agregações únicas sob RLS §2.1, fuso `APP_TIMEZONE`); perfil no módulo `auth`; ações na agenda são frontend-only (PATCH/cancelar já existiam, Fase 3.5). Tela `/perfil` + link na sidebar; `AuthContext.refresh()`.

### 7e — Mudanças e melhorias de UX/gestão (pedido do usuário, 2026-07-20)

**Escopo (6 blocos):** (0) bugfix 500 no PATCH /auth/me *(causa confirmada e resolvida: migration `0006` não aplicada)*; (1) dados & validações; (2) agenda UX; (3) arquivar/apagar paciente; (4) dashboard histórico; (5) responsividade.

**Decisões (via AskUserQuestion):** apagar paciente **bloqueado se houver evoluções** (guarda 5 anos CFP 001/2009 §0.3 — e o role da app **nem tem GRANT DELETE em `evolucoes`**: garantia no motor §2.1.1); **evolução vinculada a agendamento** (data do atendimento vem dele; coluna nullable p/ legadas); apagar agendamento **só status `agendado`** + auditoria; agenda UX = **dia + grade de horários** com duração por clique.

**Construção (migration `0007`):** `evolucoes.agendamento_id` (FK composto `(tenant_id, agendamento_id)` RESTRICT + `UNIQUE(tenant_id,id)` em agendamentos) + GRANTs DELETE (agendamentos, pacientes, vinculos, consentimentos). Backend: `DELETE /agendamentos/{id}` e `DELETE /pacientes/{id}` (409 com prontuário), arquivar/reativar auditados (`TIPO_PACIENTE_*`), responsável **≥18 anos** (validator), `EvolucaoCreate.agendamento_id` obrigatório (+ validação paciente/status; OUTER JOIN traz `data_atendimento` sem N+1), dashboard com **`?dia=&mes=`** (histórico desde `desde` = mês de criação da conta via `tenants.criado_em`; janelas `janela_do_dia`/`janela_do_mes`; cancelados no dia e no mês). Frontend: AgendamentoForm por cliques (grade 07–20h, slots ocupados marcados, chips de duração, **aviso de conflito ao vivo**); Agenda com Apagar; Ficha completa (dados cadastrais + responsáveis com contato + zona de administração arquivar/apagar); Editor exige atendimento; Dashboard com seletores dia/mês + **tooltips ⓘ** explicando cada indicador (`components/Stat.tsx`); Pacientes com filtro de arquivados; ResponsavelForm com `max` de 18 anos; responsivo (cards com overflow-x, `main` 72rem, alvos de toque, grade adaptável). **99 unit tests** (+11), `tsc`+build OK, SQL da 0007 renderizado offline.

**Code-review alto esforço (8 finders + verificação) → 10 achados + itens cortados APLICADOS:** (1+2) **evolução só vincula atendimento `realizado`**; (3) wizard coleta nascimento do responsável com trava 18+; (4) duração customizável; (5) coerência tile×lista do dashboard; (6) editor zera seleção/rascunho ao trocar de paciente; (7) maioridade alinhada no 29/02; (8) consultas consolidadas; (9) índice `(tenant_id, criado_em)`; (10) helpers compartilhados. **99 unit tests**, `tsc`+build OK, SQL 0007 renderizado. → ✅ **commitada, deployada e validada no servidor (`0007`).**

**Code-review alto esforço (8 finders + verificação) → 10 achados APLICADOS:** migration `0006` com privilégio mínimo; limite bcrypt de 72 bytes; e-mail normalizado; máquina de estados; coerência tile×lista; ações sem refetch; reautenticação e auditoria na troca de e-mail; fonte única de TCLE vigente. **88 unit tests**, `tsc`+build OK. → ✅ **commitada, deployada e validada no servidor (`0006`).**

### 7f — Calendário & Recorrência (pedido do usuário, 2026-07-20)

**Objetivo:** (1) **calendário** no dashboard — grade mensal com dias coloridos quando têm consulta; clicar num dia mostra a agenda daquele dia; navega para meses futuros. (2) **Recorrência** no agendamento — repetir mesmo dia/horário sem remarcar; desfazer abrindo um atendimento da série.

**Decisões (via AskUserQuestion):** frequência **semanal + quinzenal + mensal**; horizonte **~6 meses** (`_HORIZONTE_DIAS=183`); desfazer remove **só futuras ainda 'agendado'** (passadas/realizadas ficam); conflito de horário na série → **pula a semana** (best-effort, informa criados/pulados).

**Modelo:** recorrência = **série materializada** (`agendamentos.serie_id`, migration `0008`) — ocorrências futuras são linhas concretas (mantém EXCLUDE, gate de evolução realizado, contadores). Geração com **SAVEPOINT por ocorrência** (`begin_nested`): conflito (EXCLUDE 23P01) pula a cadência sem abortar. Desfazer = `POST /agendamentos/{id}/desfazer-recorrencia` (deleta futuras 'agendado' da série; auditável `recorrencia_desfeita` §2.2). `POST /agendamentos` retorna `AgendamentoCriadoOut` (`serie_criados`/`serie_pulados`). Calendário = `GET /dashboard/calendario?mes=` → `{dia: contagem}` (fuso da clínica, aceita mês futuro). Frontend: `Calendario.tsx` integrado ao Dashboard (substitui o seletor de data do dia); `AgendamentoForm` com checkbox de recorrência + frequência + duração; **`AgendamentoDetalhe`** (`/agenda/:id`) p/ desfazer; agenda com link no início + 🔁 nas séries. **105 unit tests** (+6), `tsc`+build OK, SQL 0008 renderizado.

**Code-review alto esforço (8 finders + verificação) → 10 achados + cortados APLICADOS:** (1) **cadência a partir do ÂNCORA** (`_ocorrencia(anchor,freq,k)`): mensal não deriva mais (31/01→28/02→31/03…); teste de regressão do drift; (2) **`desfazer` reescrito**: mantém a ocorrência ABERTA (vira avulsa), remove só as OUTRAS futuras 'agendado', **dissolve a série** (`serie_id`/`serie_frequencia`=NULL) — botão some depois, 2ª chamada dá `NaoRecorrente`; 1 DELETE (`rowcount`) + 1 UPDATE; (3) erro não-EXCLUSION na geração **para a série mas preserva** o primário + as criadas (não aborta a tx); (4/5) calendário: `useEffect` sincroniza o mês (conserta "Ir para hoje") + **mostra erro** do fetch; (6) **dashboard dividido** em `GET /dashboard/dia` e `/mes` (+ `pacientes` 1×) — clicar num dia não recomputa mais o mês/pacientes; (7) **frequência persistida** (`serie_frequencia`, migration 0008) → regra sobrevive p/ a Fase 8; (8) POST retorna **datas puladas** (`serie_pulados_datas`) e a SPA lista as lacunas; (9) rótulo **"Todo mês (mesma data)"** (mensal usa a data, não o dia da semana). **Cortados:** `fmtMesTitulo` → utils (dedup); `FREQUENCIAS` morto removido; hook **`useAcao`** extraído (FichaPaciente+AgendamentoDetalhe); resposta do router valida uma vez. **Aceitos/documentados:** DST na aritmética (Brasil sem horário de verão) e clamp inferior do calendário (degrada p/ zeros). **105 unit tests**, `tsc`+build OK, SQL 0008 (serie_id + serie_frequencia + índice) renderizado. → ✅ **commitada+pushada (`65d8a7b`). Aguarda deploy (`alembic upgrade head` → 0008).**

### 7g — Melhorias de UX (pedido do usuário, 2026-07-21)

**Objetivo:** polimento estético/UX (frontend-only, sem backend/migration). Pedidos: fonte maior p/ leitura; harmonia de espaçamento ("Agenda de hoje"/"Ver agenda →"); badge de contagem do calendário mais legível; redesenho da lista de Pacientes (estava vazia) com **espaço para observações da psicóloga**.

**Entregue:** fonte base ~18px (`html{font-size:112.5%}`, rem escala tudo); cabeçalhos de seção com respiro consistente + "Ver agenda →" como pílula discreta (`.cabecalho-secao a:not(.botao)`); calendário com badge maior ancorada na base da célula; **Pacientes como grade de cartões** (`PacienteCard.tsx`: avatar de iniciais, nome, idade·sexo·nascimento, situação, **observações editáveis inline** — grava via `PATCH /pacientes`, caixa de tamanho fixo `resize:none` + contador, sem backend novo). Helpers novos em `utils/format.ts` (`idadeEmAnos`, `iniciais`, `rotuloSexo`, `fmtMesTitulo`). **Preview visual publicado como artifact** p/ aprovação antes do deploy (padrão útil p/ tarefas estéticas).

**Code-review (3 finders) → 6 achados tratados:** `.cabecalho-secao a:not(.botao)`+`align:center` (conserta o botão "Nova evolução" que ficava acento-sobre-acento/invisível); `overflow-wrap` na observação; `rotuloSexo()` dedup (era duplicado na Ficha); `PacienteCard` usa `useAcao`; **nascimento de volta** na meta do cartão (desambigua homônimos); `idadeEmAnos` valida datas fora de faixa. **Aceito/documentado:** `obs` via `useState` fica stale só num futuro refetch (a lista não refaz fetch; o fix ingênuo quebraria o update otimista); célula do calendário não-quadrada em faixa estreita de largura (cosmético). `tsc`+build OK. → ✅ **commitada+pushada (`5603392`). Frontend-only: deploy = `up -d --build frontend` (sem migration).**

### 7h — Fluxo do calendário e organização do dashboard (pedido do usuário, 2026-07-21)

**Objetivo:** transformar o calendário em ponto de entrada para um novo agendamento e reduzir ruído visual no dashboard.

**Entregue:** clique em qualquer dia navega para `/agenda/novo?dia=AAAA-MM-DD`; o formulário valida o parâmetro e já carrega a ocupação da data. O bloco **Hoje** e a agenda de hoje ficam antes do calendário. O botão redundante "Novo agendamento" foi removido do dashboard. O histórico mensal ganhou seletores verticais de mês/ano e só consulta o backend ao clicar na lupa. **Pendências** aparecem antes de **Pacientes ativos/Responsáveis**. Frontend-only, sem migration. `tsc --noEmit` e `vite build` aprovados.

**Governança corrigida junto da 7h:** removidos endereços/credenciais/IDs operacionais do roadmap; rotação da credencial antes exposta marcada como obrigatória; embeddings `text-embedding-3-small` encerrados como decisão; README atualizado para React; estados obsoletos das seções 7b–7e reconciliados; retenção OpenAI separada entre garantia de código e evidência operacional obrigatória na Fase 9 (§3.4 #6).

### 7i — Localização, listas compactas e arquivamento (pedido do usuário, 2026-07-22)

**Objetivo:** tornar pacientes e responsáveis localizáveis rapidamente, reduzir a densidade visual da lista de pacientes e transformar o arquivamento em um fluxo explícito, rastreável e seguro.

**Entregue localmente:** busca por nome sem diferenciar maiúsculas/acentos e ordenação A–Z/Z–A; responsáveis também são encontrados pelo nome da criança vinculada, sem N+1; aba/rota dedicada `/pacientes/arquivados`; cartões compactos com observações recolhíveis; arquivar/reativar por endpoints próprios; data, ator e motivo opcional do arquivamento; filtro ativo no backend e índice `(tenant_id, ativo, nome)`.

**Invariantes:** `PacienteUpdate` não altera mais `ativo`; o motor exige metadados coerentes e FK composta do ator para o mesmo tenant (§2.1); a auditoria não replica nome/motivo clínico no payload (§2.2); paciente com agendamento futuro `agendado` não é arquivado. Arquivamento e criação de agenda usam `SELECT ... FOR UPDATE` na mesma linha, fechando a condição de corrida; paciente arquivado não recebe novo agendamento. **Migration `0009`.**

**Code-review (`review-agent`) — 3 achados aplicados:** (P1) reagendamentos/alterações também travam o paciente e recusam agenda futura quando arquivado; (P1) nomes pesquisados permanecem em estado local, fora de URL/logs/Referer; (P2) próximos passos duplicados foram reconciliados. **Validação local:** backend **110 testes aprovados, 1 integração ignorada**; Ruff aprovado nos arquivos da entrega; SQL `0008:0009` renderizado offline; frontend `tsc --noEmit` e build Vite aprovados. → 🟡 **construída, revisada e validada localmente; aguarda aprovação, commit/push e deploy.**

**Aprimoramentos pós-teste:** ficha passou a listar agenda futura (`764ad8a`). Nova rodada local acrescenta `POST /agendamentos/{id}/apagar-recorrencia-futura`: remove inclusive a ocorrência selecionada e todas as futuras `agendado`, preserva o histórico não pendente, dissolve a série restante e audita contagem/ID da série. O detalhe do atendimento permite editar início, fim, tipo e observação enquanto `agendado`; em recorrência, altera somente a ocorrência aberta. **112 testes aprovados, 1 skip; Ruff, OpenAPI, `tsc` e build aprovados; sem migration nova.**

> ✅ **7i aprovada no servidor até `86ebd6e` (2026-07-22).** Busca/ordenação, responsáveis por criança, aba de arquivados, resolução da agenda futura/recorrente e edição de agendamentos validadas pelo usuário. **Decisão:** a UX está suficiente por enquanto; congelar novos polimentos visuais e reabrir somente diante de defeito ou necessidade operacional concreta.

### 7j — Controle de sessões na ficha do paciente (commitada/pushada)

**Objetivo:** mini-dashboard administrativo para a psicóloga controlar continuidade e volume de atendimentos, sem tentar inferir diagnóstico ou substituir o prontuário.

**Informações previstas:** total de sessões realizadas; realizadas no mês/ano; última sessão e dias desde ela; próxima sessão e situação da agenda; faltas e cancelamentos no período; taxa de comparecimento com denominador explícito; intervalo médio/mediano recente; alerta de paciente ativo sem próximo atendimento; linha histórica paginada com data, status, tipo e vínculo para evolução quando existir. Filtros por período e definições visíveis evitam indicadores ambíguos. Agregações permanecem no backend/BD sob RLS (§2.1), sem carregar todo o histórico no navegador.

**Construção:** `GET /dashboard/pacientes/{id}/sessoes` agrega sob RLS: total/mês/ano realizados, faltas, cancelamentos, taxa `realizadas ÷ (realizadas + faltas)`, última/próxima sessão, dias desde a última e mediana dos intervalos entre até 11 sessões realizadas recentes. O histórico aceita `de`/`ate`/`status`, `limite` (1–50) e `offset`, retorna vínculo opcional de evolução e nunca carrega a série inteira no navegador. A ficha usa tiles explicados, alerta para ativo sem próxima sessão, filtros por período/status e paginação de 10 itens. **Revisão:** carregamento passou a ser fail-closed para nunca mostrar por instantes as sessões do paciente anterior; teste garante que paciente invisível por RLS encerra antes das agregações. **115 testes aprovados, 1 skip; Ruff, OpenAPI, `tsc` e build OK; sem migration.** → ✅ commitada e enviada em `fb01709`; validação no servidor ainda não registrada.

### 7k — Documentos clínicos do paciente (construída localmente)

**Decisões aprovadas:** formatos **PDF/DOCX/JPEG/PNG**; sanitização no próprio backend com bibliotecas locais e limites estritos, respeitando o monólito modular e o orçamento de RAM (§1.1/§1.3); não haverá máquina/serviço auxiliar de antivírus. Upload nunca será enviado à IA.

**Controles mínimos antes da implementação:** armazenamento privado fora da raiz pública, nome interno aleatório e metadados no PostgreSQL; autorização por tenant/paciente com RLS + FK composta (§2.1); limite por arquivo e cota; verificação por assinatura real (não confiar em extensão/`Content-Type`); parsing isolado, sem macros/objetos ativos; regravação segura de imagens, PDF e DOCX em formato canônico; proteção contra ZIP bomb/path traversal; download autenticado com `nosniff`, disposição `attachment` e nome seguro; hash, tamanho, tipo detectado, ator e timestamps auditáveis; quarentena/fail-closed quando a validação falhar; retenção, backup e exclusão coerentes com prontuário (§0.3/§4.2). A sanitização reduz risco, mas não será descrita como antivírus completo; arquivos que não possam ser reconstruídos com segurança serão recusados.

**Construção:** migration `0010` cria `documentos_paciente` com RLS+FORCE, FKs compostas para paciente/ator, hash/tipo/tamanho e grants apenas `SELECT, INSERT` (sem apagar prontuário). Binários usam chave aleatória no volume `documentos_data`, exclusivo do backend; originais e intermediários ficam no `tmpfs` e só o resultado reconstruído entra no volume. Upload limita **20 MiB**, cota inicial **2 GiB/tenant**, detecta assinatura real e serializa o subprocesso com timeout e teto de memória para os dois workers não competirem. Pillow regrava JPEG/PNG sem metadados e com anti-decompression-bomb; pikepdf remove JavaScript, anexos, acesso externo e multimídia antes de salvar; DOCX é validado contra ZIP bomb/path traversal/duplicatas/macros/relações externas e reconstruído por conteúdo. Download é autenticado sob RLS, auditado, `attachment`, `nosniff`, `no-store` e CSP sandbox. Arquivo com documento passa a ser prontuário e bloqueia exclusão definitiva do paciente.

**Limite de garantia:** esta defesa em profundidade reduz a superfície, mas **não equivale a antivírus completo** nem torna qualquer PDF universalmente “seguro”. Falha, timeout, senha, formato complexo/ativo ou reconstrução incerta resultam em recusa. Dependências devem permanecer atualizadas e entrar no hardening/SBOM da Fase 9.

**Referências primárias consultadas:** [Pillow — segurança](https://pillow.readthedocs.io/en/stable/handbook/security.html), [pikepdf — sanitização](https://pikepdf.readthedocs.io/en/latest/topics/sanitize.html), [Python `zipfile` — arquivos não confiáveis](https://docs.python.org/3.12/library/zipfile.html) e [python-docx](https://python-docx.readthedocs.io/en/latest/). As próprias referências reforçam allowlist, limite de pixels/recursos, validação de caminhos e que sanitização PDF é uma camada dependente do modelo de ameaça.

---

## Fase 8 — Automação n8n & Backups

**Objetivo:** descarregar exportação/documentos para o n8n e garantir redundância local.

**Regras de ouro aplicáveis:** §4.2 (webhook autenticado, OAuth2 no n8n, pg_dump/WAL no HDD).

### Ordem de execução

Backup/restauração vem antes de n8n: os documentos clínicos já existem e precisam de
proteção operacional agora; automação externa aumenta a superfície e só entra depois que
o recovery estiver provado. O inventário e o desenho podem ocorrer em paralelo, mas
nenhum webhook/workflow é ativado antes de o backup do próprio n8n estar comprovado.

### 8a — Backup coordenado e restauração

- [x] Inventariar montagem, filesystem, capacidade, saúde e criptografia do HDD sem alterar volumes. *(HDD ext4 sem criptografia de bloco; ~434 GiB livres em 2026-07-23.)*
- [x] Confirmar Restic instalado. *(Restic 0.14.0 instalado pelo repositório Debian em 2026-07-23.)*
- [x] Criar staging gocryptfs por diretório no HDD compartilhado, sem alterar partições ou os demais serviços, e inicializar repositório Restic cifrado. *(Senhas manuais fora do servidor; primeiro snapshot verificado em 2026-07-25.)*
- [ ] Guardar a senha do repositório fora do servidor em cofre controlado; registrar responsável e procedimento de substituição.
- [x] Implantar e provar o wrapper manual idempotente: `pg_dump -Fc`, globals, `documentos_data`, checksums, commit, migration, configurações e relatório sem PII. *(Snapshot `bb14c397`; pausa/restart e desmontagem comprovados em 2026-07-27.)*
- [x] Salvar bundle das imagens aprovadas por versão enquanto dependências/digests não estiverem integralmente fixados. *(Bundle `2e87219b` carregado com sucesso; `1129498` torna o manifesto SHA-256 portátil para os próximos bundles.)*
- [ ] Definir janela e responsável para execução **manual diária** com lock, timeout, retorno não zero e registro; RPO inicial de 24 h. Não habilitar timer enquanto a decisão manual vigorar.
- [ ] Aplicar retenção `14 diários + 8 semanais + 3 mensais` agrupada por `host,tags`; `prune` somente com credencial administrativa.
- [ ] Executar `restic check` e restaurar banco + documentos em host/VM isolado; conferir hashes e binários ausentes/órfãos. *(`restic check`, hashes, imagens e `pg_restore` foram provados no mesmo host, em recursos exclusivos e sem rede; falta a prova em host/VM separado.)*
- [ ] Documentar duração real e confirmar ou revisar o RTO inicial de 4 h.
- [ ] Planejar segunda cópia cifrada fora do servidor/local; HDD no mesmo host não completa 3-2-1.
- [ ] Avaliar WAL/PITR separadamente; não anunciar PITR antes de base backup + cadeia WAL + restore testados.

### 8b — Automação n8n e exportação

- [x] Construir gate de assinatura eletrônica: intenção explícita, identidade autenticada,
  assinante/data, auditoria na mesma transação e imutabilidade no BD. *(Migration `0011`;
  implantada e confirmada como `head`.)*
- [x] Inventariar banco, volumes, versão e presença da `N8N_ENCRYPTION_KEY` do n8n, sem expor valores. *(n8n 2.30.5 + PostgreSQL 16 dedicado, dois volumes persistentes, chave explícita; 2026-07-28.)*
- [x] Incluir banco, volume persistente e cópia root-only da chave no backup coordenado e provar restore isolado. *(Snapshot `aa64be52`, bundle `4bd3dd57`; 114 tabelas e 4/4 arquivos recuperados em recursos exclusivos, depois removidos.)*
- [x] Webhook FastAPI → n8n disparado **após assinatura eletrônica**, com autenticação e proteção contra replay (§4.2). *(HMAC/janela/replay `401/401/200/200/409`; evento real entregue em uma tentativa; antirreplay +1; retenção imediata `0` execuções/`0` payloads em n8n 2.33.0.)*
- [~] Fluxo n8n: JSON mínimo → PDF padronizado e processamento durável/idempotente aprovados sinteticamente; segredos já rotacionados, mas receptor mantido despublicado pelos bloqueios de go-live da Fase 9. Google Sheets somente se houver finalidade aprovada.
- [x] OAuth2 do Google **inteiramente no n8n**, com escopo mínimo `drive.file`; upload sintético aprovado. App/BD nunca tocam senhas Google (§4.2).
- [~] Entrega à pasta privada da psicóloga com idempotência e tratamento de falha sem
  duplicação aprovada sinteticamente. Ainda falta fechar a garantia de destino cifrado,
  auditoria operacional e liberação real pelos critérios da Fase 9.

**Contrato de segurança antes da implementação:** evento UUID único; timestamp UTC com
janela máxima de 5 minutos; HMAC-SHA256 sobre timestamp + evento + hash do corpo;
comparação em tempo constante; persistência do `evento_id` para rejeitar replay; retries
com a mesma chave idempotente; payload clínico mínimo e nunca registrado em logs. O n8n
permanece desativado até seu banco, binários e chave de cifragem entrarem no backup.

### Definition of Done
- Backup diário do banco **e documentos** é cifrado, verificado, alertado e restaurável como conjunto coordenado.
- Uma restauração isolada prova hashes, coerência banco↔binários e RTO documentado.
- Evolução assinada chega ao destino via n8n sem a app tocar em credenciais Google e sem duplicação em retry.

---

## Fase 9 — Hardening & Go-Live

**Objetivo:** fechar segurança, validar limites sob carga e colocar em produção.

**Regras de ouro aplicáveis:** todas — revisão contra o **Checklist §5 da arquitetura**.

### Tarefas
- [ ] Rodar o **Checklist de Conformidade (§5)** ponta a ponta.
- [ ] Teste de carga leve validando os `mem_limit` (sem OOM Killer).
- [~] Revisão de segredos, permissões, imagens e exposição registrada em
  [`revisao_seguranca_2026-08-01.md`](./revisao_seguranca_2026-08-01.md): Trivy do
  workspace e Gitleaks dos 68 commits terminaram sem vazamentos; seis imagens foram
  escaneadas e as correções de frontend/backend foram validadas e implantadas. A LAN
  física tem contenção persistente comprovada em IPv4 e IPv6 nas seis portas
  administrativas, com Tailscale preservada; consoles web auxiliares continuam com
  bindings amplos e há CVEs upstream pendentes/excepcionáveis.
  A proteção `Cache-Control: no-store, private` para toda a API e o limitador de login
  por IP foram retestados na origem publicada (`401×5`, `429×2`, `Retry-After: 60` e
  warning sem credenciais). O encaminhamento do warning para alerta externo permanece
  pendente.
- [~] Obter aprovação/provisionamento e ativar **Zero Data Retention** no projeto/organização OpenAI; registrar projeto, modo efetivo, data e responsável, sem segredos (§3.4 #6). **Solicitação enviada em 2026-08-04; em 2026-08-05 o recurso permanecia indisponível para o projeto, sem nova ação possível nesta retomada.** Ausência de opt-in de treino comprovada em 2026-08-02: os três controles de Sharing estão `Disabled`, assim como `API call logging`. Ainda não há seletor ZDR/MAM; `store=false` sozinho não encerra esta tarefa.
- [~] Observabilidade mínima: `infra/observabilidade/verificar_runtime.sh` monitora
  manualmente estado/health, reinícios, OOM, limites/uso de RAM, disco e rotação de logs.
  Após snapshot `4e602160`, os seis containers Agenda/n8n usam rotação `10m × 5`;
  health, migration `0014`, HTTP e persistência foram aprovados. Baseline final: `0`
  erros, `0` avisos e disco 65%. Decisão: backup/verificação manuais, sem timer/cron;
  alerta por e-mail aguarda configuração de relay SMTP root-only.
- [ ] Verificação de conformidade LGPD/ECA/CFP (consentimento, sigilo, auditoria).
- [~] Documentar procedimento de restore e plano de contingência. O procedimento e o
  ensaio no mesmo host existem; o operador recusou restore em host/VM separado, então
  RTO/isolamento externo permanecem como limitação aceita e não como evidência concluída.
- [x] Deploy do hardening no servidor Debian 12. *(Commit `293a127`, migration `0014`,
  snapshots `ebde69c8` e `38272c78`, smokes sintéticos aprovados em 2026-08-03.)*

### Definition of Done
- Checklist §5 100% verde.
- Sistema estável em produção dentro do orçamento de RAM.

---

## 📝 Registro de Progresso (memória da sessão)

> Uma linha por entrega significativa. Formato: `AAAA-MM-DD — [Fase X] descrição curta do que foi feito / decidido`.
> Mantenha conciso — este é o resumo que será lido no início das próximas sessões.
> As linhas são cronológicas: estados 🟡 antigos documentam o momento da entrega e são substituídos pelas linhas ✅ mais recentes; o estado corrente vive no topo deste arquivo.

- 2026-08-05 — [Fase 9/Observabilidade] 🟡 **Rotação de logs concluída nos seis containers; alerta ainda pendente.** Stack Portainer persistida com `json-file` `10m × 5`; PostgreSQL n8n, n8n, runner e backend recriados. Durante uma inspeção estrutural, a senha administrativa PostgreSQL n8n e o HMAC apareceram na saída operacional; ambos foram rotacionados imediatamente sem imprimir os substitutos. Chave n8n/token do runner não foram expostos. Validação: serviços estáveis, zero reinícios/OOM, segredos consistentes, 2 workflows inativos, 0 execuções e verificador em `0` erros/`0` avisos. Receptor permaneceu despublicado; matriz sintética obrigatória antes de futura publicação. **Próximo:** definir destino e responsável pelo alerta antes de timer/cron.
- 2026-08-05 — [Fase 9/Observabilidade] 🟡 **Rotação aplicada na Agenda; n8n ainda pendente.** Push até `49ba0e8` concluído. Snapshot coordenado pré-recriação `4e602160`; staging desmontado. PostgreSQL/backend/frontend recriados sem rebuild, com volumes preservados, `0014 (head)`, health e HTTP aprovados; os três usam `json-file` `10m × 5`. n8n, runner, Homarr e serviços auxiliares permaneceram saudáveis/sem reinícios. Verificador: `0` erros, disco 65%, memória máxima ~30% e aviso apenas para os três containers n8n sem rotação. **Próximo:** atualizar a stack n8n em janela própria e definir alerta/responsável.
- 2026-08-05 — [Fase 9/Observabilidade] 🟡 **Baseline manual implementado; rotação preparada sem deploy.** Verificador dos seis containers Agenda/n8n terminou com `0` erros: todos running, health aplicável verde, zero OOM/reinícios, memória máxima ~40% e disco 65%. Único aviso: `json-file` sem limites. Compose Agenda agora prepara `max-size: 10m`/`max-file: 5`, mas nenhum container foi recriado; n8n/runner/PostgreSQL exigem mudança equivalente na stack Portainer. **Próximo:** validar Compose, planejar recriação e definir alerta/responsável antes de timer.
- 2026-08-05 — [Fase 9/Homarr] 🔴 **Fase B bloqueada antes de executar a stable `v1.73.0`.** Latest oficial confirmado; imagem fixa baixada no digest `sha256:72f98c87…0fdd0`, sem criar container. Trivy `0.70.0` validado e base atualizada encontrou `2C/19A`, todos com correção disponível: `protobufjs` crítico e Next.js alto estão em `app/node_modules`; `tar` crítico está no npm global. Não iniciar, não customizar silenciosamente e não usar build não lançado. **Próximo:** nova stable + novo digest/scan, ou exceção formal após análise individual.
- 2026-08-05 — [Fase 9/Homarr] ✅ **Fase A concluída e rollback legado preservado.** ZIP oficial, definição/inspect da stack, imagem efetiva e três volumes foram capturados no staging cifrado; somente o Homarr parou durante os TARs e retornou `running/healthy`, com zero reinícios. Checksums passaram, snapshot Restic `707f30a5` criado com tag `homarr-migracao` e `restic check` sem erros. Staging desmontado, upload temporário removido e nenhum auxiliar residual. A primeira tentativa falhou antes da pausa por ausência de `test` no Portainer; `63b4698` corrigiu para `docker cp` e retomou o conjunto cifrado. **Próximo:** Fase B, sem socket e em paralelo privado.
- 2026-08-05 — [Fase 9/Homarr] 🟡 **Execução segura da Fase A preparada; aguarda transferência privada do ZIP.** O ZIP oficial foi exportado pelo operador e a janela foi autorizada. `infra/homarr/backup_legado_manual.sh` valida arquivo `0600`, staging gocryptfs, stack, imagem, saúde, socket e três volumes antes da pausa; preserva imagem/definição, para somente o Homarr, reinicia por trap, valida checksums, envia ao Restic e executa `restic check`. `bash -n` e `git diff --check` passaram; ShellCheck não está instalado. Homarr continua saudável e não foi parado. **Próximo:** transferir o ZIP por SSH/SFTP para caminho privado e executar o helper interativamente.
- 2026-08-05 — [Fase 9/Homarr] 🟡 **Pré-flight da Fase A aprovado sem mudança operacional.** Legado permanece saudável, sem reinícios, com três volumes e socket Docker graváveis, sem limite e usando aproximadamente 378 MiB; há cerca de 39 GiB locais livres. A candidata `v1.73.0` ainda não foi baixada. O backup coordenado existente é específico da Agenda/n8n: somente sua fronteira gocryptfs/Restic pode ser reaproveitada, em execução separada que pare apenas o Homarr. Nenhum pull, parada, exportação ou cópia ocorreu. **Próximo:** autorizar janela e exportar o ZIP pela interface antiga antes da captura consistente.
- 2026-08-05 — [Fase 9/Listeners] 🟡 **Listeners externos atribuídos sem alteração.** `139/445` são do Samba standalone do host (`smbd`/`nmbd`, serviços ativos e habilitados, interfaces não restringidas); `3000` é do processo PM2 `mochila`, do projeto Ascensão, cujo Node usa binding wildcard. Nenhum contêiner publica essas portas. A política padrão persistida do UFW é `DROP`, mas as regras efetivas exigem privilégio e o alcance pela LAN não foi retestado, portanto exposição não foi presumida. **Próximo:** janela da Fase A do Homarr ou teste externo e decisão com os responsáveis.
- 2026-08-05 — [Fase 9/Retomada] 🟡 **ZDR indisponível; trabalho independente continua.** A solicitação já havia sido enviada, mas o recurso não está disponível para o projeto. O bloqueio de dados reais permanece; acompanhamento de ZDR deixa de ser a ação imediata. O firewall está versionado em `9f7b656` e o plano Homarr está pronto para execução somente com janela autorizada. **Próximo:** Fase A do Homarr ou atribuição somente leitura dos listeners `139/445/3000`.
- 2026-08-04 — [Fase 9/ZDR+Homarr] 🟡 **ZDR solicitado; migração Homarr planejada sem mudança operacional.** Solicitação enviada pelo canal oficial da OpenAI; aprovação, provisionamento e seleção no projeto seguem pendentes. Inventário somente leitura confirmou Homarr legado saudável, três volumes pequenos, ausência de limite de memória e socket Docker gravável. Plano fixa migração paralela para `v1.73.0`, exportação oficial + backup cifrado, rollback sem conversão reversa, binding privado e socket ausente ou proxy `CONTAINERS=1`/`POST=0`. Nenhuma stack foi parada ou alterada. **Próximo:** acompanhar ZDR e autorizar separadamente a fase de backup/exportação do Homarr.
- 2026-08-04 — [Fase 9/Firewall] ✅ **Contenção persistente IPv4/IPv6 da LAN comprovada; Tailscale preservada.** Serviço oneshot `enabled/active` aplica chains separadas em `INPUT` e `DOCKER-USER`. Teste externo das seis portas administrativas terminou bloqueado nas duas famílias e incrementou todas as regras esperadas; as seis portas permaneceram abertas pela Tailscale. Reinício controlado somente do serviço reaplicou os quatro hooks e as chains completas; Docker/host não foram reiniciados. Bindings amplos permanecem como defesa em profundidade a reduzir. **Próximo:** ZDR e plano Homarr/socket proxy; nenhum dado real até o go-live.
- 2026-08-03 — [Fase 9/Deploy] ✅ **Hardening `293a127` implantado e retestado; receptor continua inativo.** Após sincronizar sem exposição a cópia de recuperação da chave n8n, snapshot coordenado pré-deploy `ebde69c8` aprovado. Imagens com revisão OCI correta, migration `0014` antes do backend e recriação exclusiva de backend/frontend concluídas; serviços saudáveis e redes corretas. Smoke publicado sintético aprovou login/cache/troca de senha/revogação/logout e limpeza; rate limit repetiu `401×5`/`429×2` com `Retry-After: 60`, sem limitar rota comum. Bundle pós-deploy `38272c78` preservou as imagens executadas. **Próximo:** ZDR, firewall persistente/IPv6 e Homarr/socket proxy; nenhum dado real até o go-live.
- 2026-08-03 — [Fase 9/Code review] 🟡 **Lote de hardening revisado, validado e versionado no commit `216d461`; sem deploy naquele checkpoint.** Corrigidas corridas de `session_version`, logout idempotente de cookie inválido, exposição do valor JWT em traceback Pydantic e limpeza integrada outbox→evolução. Backend final: `157` unitários + `14` integrações aprovados em PostgreSQL descartável, migration `0014` validada em upgrade/downgrade e startup fail-fast sem ecoar segredo. Frontend: lock íntegro, TypeScript/build/Docker/Nginx/rate limit aprovados; audit mantém somente exceção RSC não alcançável. Lint focado, compileall e diff-check aprovados.
- 2026-08-02 — [Fase 9/Segurança] 🟡 **Rotação n8n/HMAC e reteste concluídos; hardening em curso.** As 12 execuções do workflow sintético do Drive foram removidas com guardas estritas. Script corrigido para publicação/despublicação atual e ordem segura n8n→runner; matriz pós-rotação passou `401/401/200/200/409`. Estado final: workflows inativos, serviços saudáveis, `0` execuções e `0` payloads globais. React Router `7.18.2` e Vite `6.4.3` passaram TypeScript/build; advisories antigos foram removidos, restando exceção RSC não alcançável pela arquitetura atual e ainda sem release corrigida. **Próximo:** firewall/alcance, scans de imagens/segredos e comprovação ZDR.
- 2026-08-02 — [Fase 9/OpenAI] 🔴 **ZDR verificado e ainda não provisionado.** Em Data Controls, `API call logging` está desativado, mas não há seletores `Zero Data Retention`/`Modified Abuse Monitoring` para organização ou projeto. Conforme a documentação oficial, ZDR exige aprovação prévia da OpenAI. O código usa somente Chat Completions com `store=false` e Embeddings, ambos elegíveis, mas isso não substitui ZDR. Manter receptor despublicado e não processar dado real até aprovação e ativação explícita no projeto Agenda.
- 2026-08-02 — [Fase 9/OpenAI] ✅ **Ausência de opt-in de treino comprovada.** Em Sharing, feedback de modelo, dados de avaliação/fine-tuning e inputs/outputs estão todos `Disabled`; `API call logging` também está desativado. Essa evidência fecha o item de compartilhamento para treinamento, mas não o ZDR, que continua aguardando aprovação/provisionamento.
- 2026-08-02 — [Fase 9/Supply chain] 🟡 **Scans de segredos e imagens concluídos; correções candidatas validadas sem deploy.** Trivy do workspace não encontrou segredos; Gitleaks `8.30.1` validado por checksum percorreu 68 commits e, após allowlist AND restrita aos JWTs sintéticos de teste, terminou em zero. Trivy `0.70.0` validado por checksum escaneou seis imagens. Frontend atual tinha `2C/33A`; com Node 22 + Nginx `1.30.4-alpine3.24`, build e scan da candidata ficaram zerados em todas as severidades. Backend candidata usa `msgpack 1.2.1`/`setuptools 83.0.0` e importa a aplicação; duas altas residuais são SBOM obsoleto da base, desmentido por inspeção do filesystem. Permanecem CVEs upstream no Debian, runner, n8n, `gosu` PostgreSQL e pgvector; produção não foi reiniciada.
- 2026-08-02 — [Fase 9/Cache] 🟡 **Cache de respostas sensíveis bloqueado no código, sem deploy.** Middleware cobre toda resposta `/api/`, inclusive login e erros, com `Cache-Control: no-store, private`; healthcheck público fica fora. Teste de regressão criado e smoke em contêiner efêmero sem rede aprovado. Nginx documentado conforme o controle efetivo do backend.
- 2026-08-02 — [Fase 9/Auth] 🟡 **Rate limiting de login validado localmente, sem deploy.** Zona compartilhada do Nginx limita apenas `/api/v1/auth/login` por IP: cinco requisições imediatas, depois `429` com `Retry-After: 60` e `no-store`; rejeições geram warning sem e-mail/senha. Imagem candidata passou build, `nginx -t` e teste sem rede (`502×5`, depois `429`; rota comum não limitada). Falta encaminhar warnings para alerta externo e retestar no deploy.
- 2026-08-02 — [Fase 9/JWT] 🟡 **Configuração JWT agora falha cedo, sem deploy.** `JWT_SECRET_KEY` com menos de 32 bytes e algoritmo diferente de `HS256` impedem a carga de `Settings`, sem imprimir o segredo. Três testes de regressão adicionados; smoke em backend candidato sem rede recusou os casos inseguros e iniciou com configuração sintética válida. A revogação por versão de sessão foi tratada na etapa seguinte, registrada abaixo.
- 2026-08-02 — [Fase 9/Sessões] 🟡 **Revogação imediata de JWT construída, sem aplicar migration.** `0014` adiciona `session_version`; a claim `sv` é conferida em toda requisição e incrementada na troca de senha, logout global e suspensão/reativação. Trocar a senha revoga tokens anteriores e reemite somente o cookie do navegador que comprovou a senha. SQL renderizado offline; fluxo sintético validou `2→3→4`; unitários: `152 passed, 1 deselected` (NER “Lucas” já conhecido). Imagem backend consolidada passou startup/recusa de segredo sem mounts. O teste PostgreSQL cobre bearer antigo recusado, mas aguarda deploy. A implantação encerrará todas as sessões antigas uma única vez.
- 2026-08-01 — [Fase 9/Segurança] 🟡 **Revisão defensiva inicial registrada, sem correções operacionais.** Relatório prioriza 4 altos/11 médios/4 baixos; Git sem segredo/backup conhecido; backend Python e PDF sem CVE conhecida; React Router/Vite exigem atualização. Superfícies principais: segredos n8n recusados para rotação, Portainer+Docker socket, code-server+workspace e pgAdmin/PostgreSQL em todas as interfaces. Receptor n8n segue despublicado. **Próxima sessão:** confirmar firewall/alcance LAN, scan de imagens e scan Git por entropia; só depois propor remediação.
- 2026-07-28 — [Fase 8b] 🟡 **n8n incluído e provado no backup coordenado.** n8n 2.30.5 em localhost, PostgreSQL 16 dedicado, volumes separados e chave explícita confirmados sem expor valores. Cópia root-only corresponde à chave ativa. O snapshot `aa64be52` contém e validou dump/globals, volume, configuração efetiva, chave e checksums. O primeiro bundle recusou corretamente imagens `f97d237` contra fonte `4965916`; após rebuild/deploy coerente, `4bd3dd57` preservou as cinco imagens exatas. Serviços saudáveis e staging desmontado. Restore isolado do n8n ainda bloqueia o webhook.
- 2026-07-28 — [Fase 8b] ✅ **Restore isolado do n8n comprovado e limpo.** Snapshot/bundle restaurados em rede interna, PostgreSQL e volumes exclusivos: 114 tabelas, 0 workflows/credenciais (origem recém-instalada), 4/4 arquivos e chave correspondente. Tentativas de telemetria foram bloqueadas pela rede sem saída; nenhum workflow existia. Contêineres, volumes, rede e staging temporários removidos; produção saudável. Recovery deixa de bloquear o desenho do webhook.
- 2026-07-28 — [Fase 8b/webhook] 🟡 **Emissor construído e validado localmente, sem deploy.** Migration `0012` cria outbox por tenant com RLS+FORCE, FK composta e UUID estável por evolução. Assinatura enfileira atomicamente; envio posterior usa JSON canônico, timestamp, HMAC-SHA256 e retry idempotente, sem corpo clínico em logs. SPA tenta despachar após o commit sem desfazer prontuário em falha. SQL offline, imports/rotas, Ruff, TypeScript/Vite e 137 testes passaram; 1 teste NER conhecido foi excluído (modelo `sm` não reconhece “Lucas”, limitação já registrada). Receptor/replay no n8n ainda não existe.
- 2026-07-28 — [Fase 8b/receptor] 🟡 **Receptor realmente criado, ainda inativo.** `infra/n8n` versiona schema antirreplay e workflow importável. Tabela `agenda_webhook_eventos` aplicada no PostgreSQL dedicado; workflow `agendaEvolucaoAssinadaV1` importado no n8n 2.30.5 e confirmado `active=false`. Fluxo valida segredo, UUID, janela de 300 s e HMAC com `timingSafeEqual`; PK+hash distinguem retry idêntico de replay divergente; execuções não salvam payload clínico. Faltam segredo/módulo crypto, credencial DB mínima e testes sintéticos antes de ativar.
- 2026-07-28 — [Fase 8b/rede] 🟡 **Canal privado backend→n8n criado e tornado persistente no lado Agenda.** Rede Docker interna `agenda-webhook` criada e conectividade backend→`/healthz` comprovada. O Compose liga somente o backend à rede externa; `infra/n8n` documenta a ligação equivalente do serviço n8n no Portainer e fornece provisionamento do role PostgreSQL mínimo. Faltam aplicar segredo/role no ambiente e persistir a rede no stack n8n.
- 2026-07-29 — [Fase 8b/webhook] 🟡 **Ponto de parada operacional — receptor pronto para ativação controlada.** Stack n8n persistiu a rede externa interna `agenda-webhook` somente no serviço n8n; `AGENDA_WEBHOOK_SECRET` e `NODE_FUNCTION_ALLOW_BUILTIN=crypto` estão ativos, e o mesmo segredo HMAC foi configurado no `.env` da Agenda (valores não registrados). O role PostgreSQL `agenda_webhook` foi criado sem superusuário/createdb/createrole e possui somente `SELECT, INSERT` em `agenda_webhook_eventos`; sua credencial cifrada está vinculada ao nó `Registrar ou reconhecer evento`. Snapshot coordenado pré-deploy `034c490d` concluído. Backend/frontend do commit `fc042cb` foram construídos e implantados; migration `0012 (head)` aplicada; serviços saudáveis; backend está em `infra_internal` + `agenda-webhook` e alcança o healthcheck do n8n por HTTP 200. **Workflow `agendaEvolucaoAssinadaV1` permanece inativo. Retomar por:** ativá-lo/publicá-lo no editor n8n, executar os cinco eventos exclusivamente sintéticos (HMAC inválido→401, timestamp expirado→401, novo válido→200, retry idêntico→200 e mesmo UUID com corpo divergente→409); se todos passarem, mantê-lo ativo e provar uma evolução assinada real de ponta a ponta.
- 2026-07-29 — [Fase 8b/webhook] 🔴 **Contrato aprovado, finalização do n8n ainda bloqueia produção.** HMAC/replay passou nos cinco casos sintéticos (`401/401/200/200/409`), primeiro na imagem 2.30.5 corrigida com o patch upstream `0316336` e depois com runner externo oficial `n8nio/runners:2.30.5`. Em ambos os arranjos as execuções ficaram `running` e persistiram dados, mesmo com `saveData*Execution=none`. O receptor foi despublicado, reiniciado e limpo apenas dos IDs sintéticos 17–21; verificação final: workflow `active=false`, `0` execuções, `0` payloads, serviços saudáveis. **Não usar evento real. Retomar pelo diagnóstico da finalização e repetir exclusivamente smoke sintético até provar zero persistência.**
- 2026-07-31 — [Fase 8b/webhook] ✅ **Bloqueio de retenção resolvido em n8n 2.33.0.** Logs provaram que o workflow sempre finalizava; o pruning ativo convertia `saveData*=none` em soft-delete com payload no buffer. `EXECUTIONS_DATA_PRUNE=false` força hard-delete imediato para execuções descartadas. Runner externo 2.33.0 somente na rede padrão; contrato final `401/401/200/200/409`; verificação imediata `0` execuções/`0` payloads. Workflow voltou a inativo porque os segredos vistos no diagnóstico precisam ser rotacionados antes do uso real.
- 2026-07-31 — [Fase 8b/segredos] 🟡 **Ponto de parada durante a rotação obrigatória dos segredos expostos no diagnóstico.** Snapshot coordenado `33c2b51b` preserva o estado anterior. A única credencial n8n (`Agenda Webhook - PostgreSQL mínimo`) foi removida de forma controlada; workflow preservado e inativo. `N8N_ENCRYPTION_KEY` foi substituída por valor novo; o primeiro redeploy falhou porque `/home/node/.n8n/config` ainda guardava a chave antiga, arquivo que foi removido do volume e recriado corretamente. Correspondência Environment↔arquivo validada somente por hash. `N8N_RUNNERS_AUTH_TOKEN` também foi rotacionado e a igualdade n8n↔runner validada por hash. Estado final confirmado: n8n/PostgreSQL saudáveis, runner ativo, redes corretas, `0` credenciais, `0` execuções e `0` payloads. **Ainda pendente e não presumir concluído:** gerar novo `AGENDA_WEBHOOK_SECRET`, aplicar o mesmo valor no Environment da stack n8n e em `N8N_WEBHOOK_SECRET` no `.env` da Agenda, atualizar a stack, reiniciar o backend e validar por hash; depois rotacionar `N8N_POSTGRES_PASSWORD` no role e no Portainer, recriar a credencial PostgreSQL mínima no n8n, remover logging `debug`, repetir smoke sintético `401/401/200/200/409` com retenção imediata `0/0` e só então considerar publicar o workflow. Não registrar valores de segredo em docs, commits ou conversa.
- 2026-07-31 — [Fase 8b/segredos] 🟡 **Rotação n8n concluída; novo bloqueio de exposição registrado.** HMAC Agenda↔n8n, senha administrativa PostgreSQL e senha do role mínimo foram rotacionados; credencial mínima recriada cifrada; chave e token validados somente por igualdade de hashes. Logging `info`; smoke sintético `401/401/200/200/409`; retenção imediata `0` execuções/`0` payloads; workflow novamente inativo. Uma tentativa de recuperar variáveis persistidas no Portainer recriou brevemente a stack com variáveis vazias, sem perda de volume, e foi revertida a partir do cadastro persistente. Durante essa recuperação, uma inspeção textual ampla do banco do Portainer excedeu o mascaramento e exibiu ao menos uma credencial de outro serviço. Cópias temporárias foram apagadas. **Não liberar evento real:** inventariar conservadoramente e rotacionar os segredos dos ambientes potencialmente presentes naquela saída, começando pela credencial comprovadamente exibida; validar sem imprimir valores.
- 2026-07-31 — [Fase 8b/segredos] 🟡 **Rotação local ampliada concluída.** Foram rotacionados PostgreSQL admin/app e JWT da Agenda, code-server, login web do pgAdmin e PostgreSQL da stack pgAdmin; token n8n legado removido. Agenda saudável como `agenda_app` em `0012 (head)`; stacks externas ativas; volume do pgAdmin preservado explicitamente. As novas senhas ficam somente nas stacks do Portainer. **Único bloqueio de credencial conhecido:** revogar e substituir `OPENAI_API_KEY` no provedor; não enviar dado real antes disso.
- 2026-07-31 — [Fase 8b/segredos] 🟡 **Nova chave OpenAI carregada e validada.** Backend saudável; valor do `.env` corresponde ao contêiner por hash; embedding sintético com 1536 dimensões e chat JSON sintético passaram. **Pendente para encerrar o incidente:** apagar a chave anterior no painel OpenAI e revisar Usage; não liberar evento real até essa confirmação.
- 2026-07-31 — [Fase 8b/webhook] ✅ **Incidente de credenciais encerrado e receptor publicado.** Chave OpenAI anterior apagada pelo usuário; outbox previamente vazia; workflow ativo após restart; HMAC consistente; serviços saudáveis; credencial PostgreSQL mínima presente; retenção inicial `0` execuções/`0` payloads. Próximo passo é um único evento real controlado, com verificação apenas de metadados.
- 2026-07-31 — [Fase 8b/webhook] ✅ **Primeiro evento real aprovado ponta a ponta.** Uma evolução controlada resultou em `outbox_enviado=1`, exatamente uma tentativa e incremento unitário no antirreplay; workflow ativo e serviços saudáveis; retenção n8n imediatamente `0` execuções/`0` payloads. Verificação usou somente estados e contagens, sem conteúdo clínico ou identificadores. Webhook concluído; próxima entrega é PDF padronizado e destino cifrado.
- 2026-07-23 — [Fase 7k → 8a] ✅ **Fase 7k aprovada no servidor; Fase 8a iniciada pelo planejamento do recovery.** Deploy em `e876997`, migration `0010 (head)`, serviços saudáveis; PDF/DOCX/JPEG/PNG, recusa, persistência e downloads aprovados; `documentos_paciente` com RLS+FORCE e `agenda_app` sem `DELETE`. Roadmap da Fase 8 foi ordenado em **8a backup/restauração** antes de **8b n8n/exportação**, com inventário do HDD/Restic como primeira ação somente leitura.
- 2026-07-23 — [Fase 8a] 🟡 **Ponto de parada preparado.** Inventário concluiu que o HDD compartilhado tem ~466 GiB, ~434 GiB livres e ext4 sem criptografia de bloco; Restic `0.14.0` foi instalado. Nenhum dado clínico, senha, repositório Restic, staging ou tarefa agendada foi criado. **Retomar por:** criar uma área de estágio cifrada e definir o cofre externo da senha; somente depois inicializar o repositório e executar o primeiro backup coordenado.
- 2026-07-25 — [Fase 8a] 🟡 **Restrição de infraestrutura confirmada:** o HDD é compartilhado com todo o servidor. Logo, é proibido reparticioná-lo, reformatá-lo ou aplicar criptografia de bloco ao disco inteiro para esta fase. O caminho aprovado para análise é staging cifrado por diretório (preferência: gocryptfs), com repositório cifrado pelo Restic; ainda sem montagem, segredo, repositório ou agendamento.
- 2026-07-25 — [Fase 8a] 🟡 **Modo de operação decidido:** montagem e backup manuais. A senha do gocryptfs e a do Restic ficam fora do servidor; são informadas durante a janela e o staging é desmontado ao final. O timer systemd não será habilitado. Isso privilegia recuperação contra comprometimento/ransomware sobre automação sem supervisão.
- 2026-07-25 — [Fase 8a] ✅ **Primeiro backup coordenado local criado e verificado.** HDD compartilhado preservado; staging gocryptfs usado somente durante a janela e desmontado ao final. Conjunto autocontido com banco, globals, documentos, código clonável, commit/migration, configurações e SHA-256 foi enviado ao Restic; catálogo do dump, tar, bundle, snapshot e `restic check` aprovados. Aplicação voltou a responder. **Limite explícito:** o repositório está no HDD interno sempre acessível ao host; protege confidencialidade e falha do SSD, mas não é cópia offline contra root/ransomware nem satisfaz 3-2-1. Restore isolado e segunda cópia continuam obrigatórios.
- 2026-07-25 — [Fase 8a] 🟡 **Wrapper manual pronto para implantação.** `configurar_manual.sh` grava apenas caminhos root-only; `executar_manual.sh` monta o gocryptfs, valida tipo/origem, solicita as duas senhas em terminal, executa o conjunto ou bundle de imagens e desmonta em `trap`. Sem timer e sem senha persistida. Corrigidos durante o ensaio: staging vazio na troca de shell, healthcheck IPv6 falso-negativo e incompatibilidade do Restic 0.14 com `backup --group-by`. Sintaxe Bash e `git diff --check` aprovados; execução integrada do wrapper depende do pull no servidor.
- 2026-07-25 — [Fase 8a] 🟡 **Falha segura observada na prova integrada do wrapper.** Após o pull e a configuração root-only, `docker compose exec` bloqueou antes de criar a sessão `pg_dump`. O grupo suspenso foi encerrado de forma dirigida; o `trap` reiniciou backend/frontend saudáveis, preservou o staging incompleto e o wrapper desmontou o gocryptfs. A correção usa IDs validados com `docker exec`, `timeout --foreground --kill-after`, Compose com arquivo absoluto e mensagens de progresso; aguarda nova implantação e prova completa.
- 2026-07-26 — [Fase 8a] 🟡 **Correção `1c62bc9` implantada e preflight aprovado.** Os três containers permanecem saudáveis, o staging está desmontado e um `pg_dump -Fc` descartado em `/dev/null` terminou imediatamente por `docker exec` direto. **Retomar por:** montar manualmente `/mnt/dados/agenda-backup-stage`, inspecionar/remover somente o conjunto incompleto `20260725T221307Z` e então repetir `sudo bash backup/executar_manual.sh`.
- 2026-07-27 — [Fase 8a → 8b] ✅ **Backup e restore mínimo comprovados; inventário n8n iniciado.** O wrapper gerou o snapshot coordenado `bb14c397` e o bundle `2e87219b`; `restic check`, SHA-256, carregamento de imagens e `pg_restore` para PostgreSQL temporário sem rede passaram. Staging, contêiner e volume de ensaio foram removidos. O ensaio no mesmo host não substitui restore em host/VM separado nem mede RTO; ambos continuam pendentes. Corrigido `1129498`: checksum do bundle passa a usar caminho relativo. A 8b inicia com inventário somente leitura de n8n, sem expor `N8N_ENCRYPTION_KEY`.
- 2026-07-27 — [Fase 8b] 🟡 **Fundação segura corrigida após code review e validada localmente.** Backend/frontend recebem a revisão Git em label OCI; o bundle recusa árvore suja, tag/ID divergentes ou revisão errada e inclui o manifesto no checksum. A evolução exige confirmação explícita, registra assinante/data e auditoria atômica e fica imutável no PostgreSQL pela migration `0011`. Webhook/workflow continua bloqueado até deploy dessa migration e backup comprovado do n8n. **135 testes unitários passaram, 1 skip; Ruff alterados, compileall, SQL upgrade/downgrade, Bash, TypeScript, Vite e diff-check aprovados.**
- 2026-07-23 — [Manutenção/Segurança] ✅ **Manual operacional criado, revisado e validado localmente; execução real do recovery pendente no servidor.** `docs/arquitetura_manutenção.md` cobre rotina, capacidade, backup coordenado banco+documentos, Restic, restore isolado, deploy, prontuário e incidentes. Correções do review: retenção Restic agrupa por host+tag apesar do caminho datado; recovery localiza a árvore restaurada e aguarda readiness; n8n/chave entram no backup da Fase 8; imagens próprias recebem nomes estáveis e bundle aprovado enquanto faltam locks/digests; suspensão de usuário passa a revogar JWT emitido por consulta de conta ativa em toda requisição e ganha CLI administrativa. **133 unit tests, 1 skip; Ruff dos arquivos alterados, compileall, pip-check, OpenAPI e estrutura YAML/limites/imagens OK.** Integração com PostgreSQL e `docker compose config` dependem do ambiente do servidor.
- 2026-07-22 — [Fase 7k] ✅ **Construída, revisada, validada e autorizada para envio; deploy pendente.** Upload/lista/download de PDF/DOCX/JPEG/PNG na ficha; volume privado exclusivo do backend; originais/intermediários em `tmpfs`; assinatura real; 20 MiB/arquivo e 2 GiB/tenant; reconstrução em subprocesso serializado com timeout/RAM; anti-ZIP/decompression bomb; PDF sem JavaScript/anexos/acesso externo; download autenticado, auditado e verificado por SHA-256. Migration `0010` com RLS+FORCE, FKs compostas, CHECKs e sem DELETE. **Code review final corrigiu:** ZIP aberto antes do isolamento; mídia DOCX órfã/perda silenciosa de estruturas; corrida upload×exclusão; cleanup atômico após rollback; marcador Unicode enganoso e revogação prematura do download no browser. **130 unit tests, 1 skip; 15 testes específicos reais; Ruff/compileall/pip-check/OpenAPI/SQL/Compose/tsc/build OK.** Integração de RLS adicionada, mas depende do PostgreSQL do servidor. Backup da Fase 8 ampliado para banco+`documentos_data`.
- 2026-07-22 — [Fases 7i/7j] ✅ **7i aprovada no servidor até `86ebd6e`; UX considerada suficiente por enquanto.** 🟡 **7j construída, revisada e validada localmente, sem commit/push:** endpoint de controle de sessões sob RLS; total/mês/ano, última/próxima, faltas/cancelamentos, comparecimento, mediana recente; histórico filtrável e paginado na ficha. Review fechou exibição transitória entre pacientes e adicionou regressão de paciente invisível por RLS. **115 unit tests, 1 skip; Ruff/OpenAPI/tsc/build OK; sem migration.**
- 2026-07-22 — [Fase 7i/recorrência+edição] 🟡 **Construída e validada localmente; sem commit/push.** Série futura recorrente pode ser apagada integralmente (inclui a selecionada; preserva passadas/realizadas/faltas/canceladas; auditada). Detalhe permite editar data/horário/tipo/observação de ocorrência `agendado`, inclusive futura; série altera somente a ocorrência aberta. **112 unit tests, 1 skip; Ruff/OpenAPI/tsc/build OK; sem migration.**
- 2026-07-22 — [Fase 7i/hotfix] 🟡 **Validação no servidor encontrou falta de visibilidade da agenda futura.** Busca/ordenação, responsáveis por criança e aba de arquivados aprovados. Hotfix local: ficha carrega somente agendamentos futuros `agendado`, mostra início/fim/tipo, abre o detalhe e permite cancelar no local; após cancelar, recarrega a lista para liberar o arquivamento. Frontend `tsc` + build OK; aguarda commit/push e reteste.
- 2026-07-22 — [Fase 7i + plano 7j/7k] 🟡 **7i construída, revisada e validada localmente; sem commit/push/deploy.** Busca normalizada e A–Z/Z–A em Pacientes/Responsáveis, com termos somente em memória (sem PII na URL); busca de responsável pelo nome da criança; aba dedicada de arquivados; cartões compactos; endpoints próprios com ator/data/motivo; bloqueio de agenda futura e trava transacional compartilhada com criação **e alteração** de agendamento; migration `0009`. Review-agent: **3 achados aplicados**. **110 unit tests, 1 skip; Ruff/SQL/tsc/build OK.** 7j e 7k registradas, ainda não iniciadas.
- 2026-07-21 — [Fase 7h/Docs] ✅ **UX do dashboard e saneamento de governança construídos, validados, commitados e enviados (`0ef55b1`).** Calendário→novo agendamento com data; Hoje antes do calendário; período mensal aplicado pela lupa; cadastros ativos depois das pendências; botão redundante removido. Credenciais/endereços/IDs removidos dos docs; rotação pendente no servidor; modelo de embedding encerrado; README e estados antigos reconciliados; verificação operacional de retenção OpenAI adicionada à Fase 9. `tsc` + build OK. **7f+7g+7h aguardam deploy.**
- 2026-07-21 — [Fase 7 e/f/g] ✅ **Commitadas+pushadas (`main` até `5603392`); 7f+7g aguardam deploy (servidor em `0007`).** **7e** (`e5b2d7c`): agenda por cliques + apagar; arquivar/apagar paciente (apagar bloqueado com prontuário, CFP §0.3); **evolução ↔ atendimento `realizado`** (migration `0007`); dashboard histórico dia/mês + cancelados + tooltips; responsável 18+. **7f** (`65d8a7b`): **calendário** no dashboard (dias coloridos; `/dashboard/{dia,mes,calendario}`) + **recorrência** de agendamento (série materializada `serie_id`/`serie_frequencia`, migration `0008`; cadência a partir do âncora; desfazer via `/agenda/:id`). **7g** (`5603392`): UX (fonte maior, espaçamento, badge do calendário, **cartões de paciente** com observações inline). Cada uma com code-review aplicado (7e:10, 7f:10, 7g:6). **Bug 7d resolvido no servidor:** "alterar nome → 500" era a migration `0006` não-aplicada (servidor estava em `0005`); `alembic upgrade head` aplicou 0006+0007. **Próximo: deploy 7f+7g (`up -d --build` + `alembic upgrade head` → 0008), depois Fase 8.**
- 2026-07-20 — [Fase 7d] 🟡 **Fechamento da Fase 7 construído + revisado + validado local (aguarda deploy).** 3 frentes: ações na agenda (realizado/falta/cancelar, backend já suportava), `GET /dashboard/resumo` (módulo novo sem migration, agregado sob RLS §2.1, 3 blocos de indicadores), configuração de perfil (`PATCH /auth/me` + `POST /auth/me/senha`, tela `/perfil`). Code-review alto esforço (8 finders) → **10 achados aplicados**, destaque: **migration `0006`** (GRANT UPDATE em `usuarios` — bloqueador de deploy), senha 72 **bytes**, e-mail minúsculo + login case-insensitive, **máquina de estados do agendamento no backend** (cancelado terminal; cancelar só de agendado), troca de e-mail exige senha atual + **auditoria** (`perfil_email_alterado`), TCLE com fonte única (`clausula_consentimento_ativo`), agenda sem refetch (overrides do retorno do PATCH), tile "hoje" coerente com a lista. 88 unit tests. **Deploy: `up -d --build backend frontend` + `alembic upgrade head` (0006).**
- 2026-07-17 — [Fase 0] Criados `arquitetura.md` (regras de ouro) e `planejamento_arquitetura.md` (este roadmap). Projeto ainda sem `git init`.
- 2026-07-17 — [Fase 0] Docs movidos para `docs/`. Estrutura rígida de diretórios criada: backend por domínio/módulo (`core/`, `db/`, `middleware/`, `api/`, `modules/` × 11 domínios), `frontend/`, `infra/`, `tests/`. Criados `.gitignore`, `.env.example`, `README.md`. **Decisão:** backend organizado por domínio/módulo (não por camada).
- 2026-07-17 — [Fase 0] `git init` (branch `main`), primeiro commit e push para `github.com/GA55555/projeto_agenda`. Falta `docker-compose.yml` (§1.1) + `postgresql.conf` (§1.2) + Dockerfiles para fechar a fase.
- 2026-07-20 — [Fase 7c] ✅ **Sub-fase Melhorias de Frontend CONCLUÍDA e validada no servidor.** Login→dashboard→cadastros percorridos no browser. **Hotfix pós-deploy:** `/auth/me` deu **500** porque `PerfilOut.email` era `EmailStr` e o validador rejeitou o TLD reservado `.local` na serialização da resposta → corrigido: response models (`Out`) usam `str`, `EmailStr` só na entrada. Commit `cbaebdf`.
- 2026-07-20 — [Fase 7c] 🟡 **Sub-fase Melhorias de Frontend construída+revisada+validada local (validar no servidor).** 7c.1 (design system clínico + sidebar + menu de perfil; `/auth/me`→nome/email), 7c.2 (cadastros: AgendamentoForm, Responsáveis lista/detalhe/form, **PacienteWizard**; backend: CPF dup→409), 7c.3 (**Dashboard** real como landing: stat tiles + agenda de hoje + ações, `allSettled`). Commits `8c7aa7c`/`4b89524`/(este). `tsc`+`build` OK; backend 61 unit tests. Pendências do dashboard (sem TCLE/embeddings) → futuro `GET /dashboard/resumo`.
- 2026-07-20 — [Fase 7] ✅ **CONCLUÍDA e validada no servidor (loop completo + RAG no browser).** Percorrido ponta a ponta via túnel SSH/Tailscale: login por cookie → agenda do dia → ficha (TCLE ativo) → Nova evolução → gerar rascunho (túnel opaco) → revisar/desanonimizar → aprovar/gravar. **RAG funcionando**: rascunhos seguintes trouxeram `chunks_contexto > 0` (histórico recuperado). Convergência Fases 4+5+6+7 provada; embeddings da Fase 5 populados/recuperados de fato. **Marco: backend + IA + frontend completos.** Restam Fases 8 (n8n/backups) e 9 (hardening).
- 2026-07-19 — [Fase 7b] 🟡 **Telas construídas + revisadas + validadas localmente (validar no servidor).** Frontend-only. Shell (nav Agenda·Pacientes·Sair); **Agenda do dia** (read-only, filtro [de,ate)); **Pacientes**; **Ficha** (TCLE ativo/revogado, responsáveis, evoluções, botão "Nova evolução" só com TCLE); **Editor** (loop IA: nota→`/llm/evolucoes/rascunho`→revisar/editar→aprovar→`/evolucoes`; trata 422/503/401). Cliente API estendido + tipos, hook `useAsync`, datas pt-BR. `tsc`+`build` OK. Code-review → 5 achados aplicados (422 mostra `detail` real; agenda-do-dia; ordena no BD; `allSettled` na ficha; confirma sobrescrita do rascunho). Decisões: landing=agenda-do-dia; agenda read-only; grava só a evolução editada; aprovação auditável (assinatura formal→§9).
- 2026-07-19 — [Fase 7a] ✅ **Deployada e validada no servidor.** SPA em `127.0.0.1:8090` (8080 é do Homarr); `COOKIE_SECURE=false` (HTTP). Provado: `GET /`→200 com CSP/headers; **login→/auth/me só com cookie httpOnly** devolveu o contexto do JWT via Nginx→backend (auth por cookie ponta a ponta, backend não-exposto). Healthcheck do BusyBox corrigido (`wget -q -O /dev/null`). Ver detalhe abaixo. ↓
- 2026-07-19 — [Fase 7a] 🟡 **Fundação da SPA construída + revisada + validada localmente.** **React + Vite + TS**; Nginx serve estáticos + proxy `/api`→backend (mesma origem, zero CORS, backend não-exposto §2.1.1), multi-stage 100 MB (§1.1). **Auth por cookie httpOnly** (login seta cookie; `get_current_user` lê cookie|bearer; `/auth/logout`); SPA com cliente `credentials:include` (JS não lê token), AuthContext via `/auth/me`, handler global de 401, telas Login+Home. Decisões: React; vertical slice; cookie httpOnly; só psicólogas. Backend 61 unit tests; frontend `build`+`tsc` OK. Code-review → 7 achados, 6 aplicados (COOKIE_SECURE default false, 401 global, erros diferenciados, logout espelha atributos, catch simplificado, npm ci); #4 mantido dual-mode. **Deploy exige `COOKIE_SECURE=false` no `.env` (HTTP).** Próxima: **7b (telas)**.
- 2026-07-19 — [Fase 6] ✅ **Concluída e validada no servidor.** Smoke com `OPENAI_API_KEY` ativa: `POST /llm/evolucoes/rascunho` → **200** com `evolucao` (evolução clínica coerente em pt, contextualizada) + `destaques` (3 alertas) + `chunks_contexto:0`. Provou contra a API viva: modo `json_object` (achado #2), sem 503 espúrio (achado #1), parse JSON→campos, desanonimização. Sem chave → 503 (fail-closed); campo errado → 422. **`OPENAI_API_KEY` agora ativa no servidor** (embeddings da Fase 5 também passam a preencher).
- 2026-07-19 — [Fase 6] 🟡 **Construída + revisada + validada localmente (validar no servidor).** Módulo `llm` stateless (sem migration): túnel completo `prompts.py`/`client.py`/`service.py`. Fluxo: gate TCLE §2.2 → RAG (`buscar_contexto`) → monta nota+histórico e **anonimiza numa passagem** (marcadores consistentes) → **guard-rail hard-abort** §3.4 → OpenAI (`gpt-4o-mini`, **sem tools**, `store=false`, timeout de chat) → **desanonimiza** → rascunho (evolução + destaques) p/ aprovação (Fase 7). Endpoint `POST /llm/evolucoes/rascunho`. Decisões: ambos deliverables (JSON); stateless; gpt-4o-mini; gate consentimento. Code-review alto esforço → **5 achados aplicados** (timeout de chat separado; "json" minúsculo p/ `json_object`; limpa marcadores residuais; `anonimizar_com_entidades` reusa entidades — otimiza Fase 5 tb; `SemConsentimentoAtivo` centralizada). **55 unit tests, 1 skip.**
- 2026-07-19 — [Fase 5] ✅ **Concluída e validada no servidor.** `alembic upgrade head` → `0005`. RLS FORCE nas 2 tabelas, `embedding vector(1536)`, **sem índice vetorial** (§3.1). Smoke API: gate §2.2 (TCLE revogado → **422**); criação → **201** com `total_chunks:2` e `embeddings_pendentes:2` (sem chave OpenAI → nota persiste, degradação graciosa). Paciente descartável com consentimento ativo usado para os testes da Fase 6, sem identificador versionado.
- 2026-07-19 — [Fase 5] 🟡 **Construída + revisada + validada localmente (validar no servidor).** IA Vetorial & RAG: tabelas `evolucoes` (nota crua sob RLS) + `evolucao_chunks` (`embedding vector(1536)`), migration `0005` (RLS+FORCE, FK composto, **sem índice vetorial** §3.1). `chunking.py` (parágrafo+frase c/ overlap), `embeddings.py` (OpenAI lazy §1.3 + canonicalização de marcadores + timeout), `service.py` (gate TCLE §2.2 + anonimiza→guard-rail→embeda §3.4 + retrieval híbrido §3.2). Endpoints `POST/GET /evolucoes`. **Decisões:** nota crua + embedding só anonimizado; síncrono c/ nota persistindo se OpenAI falhar (embedding pendente); gate de consentimento; sem LLM (Fase 6). Code-review alto esforço → **#1/#2/#4 aplicados** (timeout OpenAI; contagem via COUNT sem materializar vetor; grant sem DELETE). **42 unit tests, 1 skip.** Deps novas: `pgvector`, `openai`.
- 2026-07-19 — [Arquitetura] **Nova regra de ouro §3.4 "Superfície de ataque IA↔BD"** (constituição alterada, justificativa registada). Fixa 6 invariantes p/ a Fase 5/6: LLM sem tool/acesso ao BD; RAG sob RLS + filtro §3.2; **só vetorizar texto anonimizado** (embeddings são reversíveis); guard-rail em chat **e** embeddings; separação instrução/dado (anti prompt-injection); OpenAI retenção-zero. Checklist §5 atualizado. Motivada por pergunta do usuário sobre vazamento via prompts com BD compartilhado.
- 2026-07-19 — [Fase 4] ✅ **Concluída e validada no servidor.** Build com `[nlp]`+`pt_core_news_sm`. Smoke no container: round-trip exato, Pedro/CPF mascarados, guard-rail detecta vazamento, **NER prova mapeamento PER→PERSON** (`João Silva`→PERSON, `São Paulo`/`Belo Horizonte`→LOCATION — achado #3 resolvido). Modelo `sm` com recall menor é aceitável (NER é reforço; PII cadastrada cai no Aho-Corasick). `/health`→200. Sem migration nova.
- 2026-07-19 — [Fase 4] 🟡 **Construída + revisada + validada localmente.** Túnel opaco §2.3 como **módulo puro** (sem rota/tabela/migration — a não-persistência é a garantia da regra). Camadas: **Aho-Corasick puro** (`automaton.py`, offset via `_fold` que preserva comprimento), **regex ancorado** CPF/telefone/e-mail/CEP (`recognizers.py`), **NER Presidio+`pt_core_news_sm` lazy** atrás do extra `[nlp]`+flag (`nlp.py`). `sources.py` coleta PII cadastrada sob RLS; `pseudonimizador.py` = dicionário volátil só-RAM (`__repr__` não vaza) + round-trip exato; `guardrail.py` aborta se PII conhecida escapar. **Decisões:** cadastrado+NER; dicionário por requisição; módulo puro; modelo pequeno (§1.1). Code-review alto esforço → **5 achados aplicados** (offset caseless, O(n²), mapeamento NER, dep não usada, desempate). **35 unit tests passed, 1 skipped** (NER). Sem migration nova (última = `0004`).
- 2026-07-19 — [Fase 3.5] ✅ **Concluída e validada no servidor.** `alembic upgrade head` → `0004` (extensão `btree_gist` + tabela `agendamentos`). Anti-sobreposição **no motor** via `EXCLUDE` (GiST, `tstzrange '[)'`); FK composto `(tenant_id, paciente_id)`; RLS+FORCE; status agendado/realizado/cancelado/falta, cancelamento soft. Smoke API: criar → `agendado`; sobrepor → **409**. Review de alto esforço aplicado (PATCH parcial→422, datetime tz obrigatório, filtro `status` aliased, teste RLS da agenda). Módulo `agendamentos` (models/schemas/service/router) + router na API.
- 2026-07-18 — [Fase 3] ✅ **Concluída e validada no servidor.** `alembic upgrade head` → `0003`. Smoke via API/psql: paciente+vínculo+TCLE em transação única (RLS WITH CHECK + grants + FK composto sob FORCE RLS); resposta com vínculos+responsável; CPF normalizado (`11122233344`); revogação → evento `consentimento_revogado` em `auditoria`; `UPDATE` na auditoria → `ERROR: auditoria e append-only` (trigger barra até superusuário). §2.1/§2.2 provados ponta a ponta.
- 2026-07-18 — [Fase 3] Construída (validar no servidor). **Decisões:** vínculo resp↔paciente **N:N** (`vinculos_resp_paciente`); auditoria = **log genérico append-only** com imutabilidade no BD (REVOKE UPDATE/DELETE + trigger); TCLE grava metadados+texto (PDF fica p/ Fase 8); **agendamentos → Fase 3.5**. Migration `0003` cria `responsaveis_legais`, `pacientes`, `vinculos_resp_paciente`, `consentimentos`, `auditoria` (todas RLS+FORCE, índices §3.2, CHECK de `tipo_vinculo`). Módulos preenchidos (models/schemas/service/router) + 4 routers na API. Invariante do DoD (paciente exige responsável+TCLE) imposto por schema + criação transacional. Validado local: 8 unit tests + render offline do SQL da migration. Testes de integração (RLS + auditoria imutável) aguardam BD no servidor.
- 2026-07-18 — [Fase 2] ✅ **Concluída e validada no servidor.** Login → JWT; `/tenants/atual` só o tenant do JWT (RLS via `SET LOCAL`); senha errada → 401; `/health/ready` → 200. 1ª psicóloga criada via CLI. Bug passlib×bcrypt corrigido.
- 2026-07-18 — [Fase 2] Construída (validar no servidor). **Decisão: tenant = psicóloga.** Sessão/pool como `agenda_app`; auth JWT (bcrypt+PyJWT); `get_tenant_session` injeta `SET LOCAL` por transação; migration `0002` (`usuarios`, control-plane); CLI `criar-tenant-usuario`; `GET /tenants/atual` prova RLS pela API; `/health/ready`. **Bug corrigido:** passlib×bcrypt≥4.1 → lib `bcrypt` direta. Validado local: unit tests + rotas + `/health` 200.
- 2026-07-18 — [Fase 1] ✅ **Concluída e validada no servidor.** `alembic upgrade head` aplicou `0001` (tabela `tenants` + RLS `FORCE`); `verify_rls.sql` → `RLS OK` (isolamento T1/T2 + fail-closed provados); role `agenda_app` sem Superuser/Bypass RLS. Isolamento multitenant garantido no motor da BD (§2.1).
- 2026-07-17 — [Fase 1] Construída (validar no servidor): Alembic (`env.py` usa role admin via settings); migration `0001` cria `tenants` + RLS `tenant_isolation` **FORCE**, fail-closed; helper único `app/db/rls.py`; role `agenda_app` (`NOSUPERUSER NOBYPASSRLS`) via init `02-roles.sh`; `config.py` com URLs admin/app; teste `test_rls_isolation.py` + `verify_rls.sql` (SET ROLE). Validado local: imports + render do SQL de RLS OK. **Deploy exige `docker compose down -v`** (dados descartáveis) p/ o init criar o role.
- 2026-07-17 — [Fase 0] ✅ **Fase 0 concluída e validada no servidor Debian.** `docker compose up` sobe postgres (`healthy`, ~52 MB) + backend (`healthy`), extensão `vector` 0.8.5, `/health`→200. Ajuste: `BACKEND_HOST_PORT=8010` (Portainer ocupa a 8000). Repo do servidor reconciliado (`master`→`main`, remote `origin` adicionado).
- 2026-07-17 — [Fase 0/1] Rota 1: `infra/postgres/postgresql.conf` afinado (§1.2, sem log de statements p/ evitar PII) + `init/01-extensions.sql` (pgvector, sem índice §3.1); backend `pyproject.toml` + `Dockerfile` multi-stage slim (§4.1) + app mínimo runnable (`/health`, GC §1.3); `infra/docker-compose.yml` (postgres 1.5GB + backend 1GB, `mem_limit` §1.1; BD sem porta exposta; backend só no localhost). Validado local: app boota e `/health`→200. Docker não roda neste WSL; `docker compose up` fica p/ o servidor Debian (requer criar `.env`).
- 2026-07-17 — [Docs] Avaliada administração da BD. **Decisão: sem GUI** — acesso por `psql` via `docker compose exec` (menor exposição, §0.3; 0 MB, §1.1). pgAdmin descartado. Mantida a **§2.1.1 (nova regra)**: role de app sem privilégio + `FORCE ROW LEVEL SECURITY`; o superusuário/`psql` ignora o RLS por desenho e é *break-glass*. Docs (§0.2, §1.1, §2.1.1, §4.1, §5) e Fases 0/1/9 reconciliados. Debian já constava.

---

## ⚖️ Decisões em Aberto (a resolver)

- [x] **Framework do frontend:** **React + Vite + TS**. ✔ Resolvido 2026-07-19 (Fase 7a).
- [x] **Localização dos docs:** `docs/`. ✔ Resolvido 2026-07-17.
- [x] **Layout do backend:** por domínio/módulo. ✔ Resolvido 2026-07-17.
- [x] **Vínculo responsável↔paciente:** N:N (`vinculos_resp_paciente`). ✔ Resolvido 2026-07-18 (Fase 3).
- [x] **Auditoria:** log genérico append-only, imutabilidade no BD (REVOKE + trigger). ✔ Resolvido 2026-07-18. *Hash-chain fica como reforço futuro opcional (§2.2).*
- [x] **Provedor/modelo de embeddings:** OpenAI `text-embedding-3-small`, 1.536 dimensões. ✔ Resolvido e validado na Fase 5; mudar exige migration da coluna `vector(1536)`.
- [ ] Estratégia de rotação de segredos (Docker Secrets vs. `.env`). (Fase 0)

*Registre aqui toda decisão arquitetural que fugir do `arquitetura.md` e a justificativa.*
