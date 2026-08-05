# Revisão defensiva de segurança — 2026-08-01

## Resumo executivo

Escopo inicial: repositório no commit `96e3f50`, histórico Git alcançável e configuração
observável do host Docker. O reteste posterior incluiu o deploy controlado do commit
`293a127`, migration `0014` e requisições de autenticação inteiramente sintéticas. Não
houve exploração, publicação do webhook ou uso de dados clínicos reais.

**Conclusão:** a aplicação Agenda tem bons controles internos, mas o ambiente ainda não
deve ser liberado para novos dados reais. Os segredos expostos foram rotacionados e a
LAN física recebeu contenção persistente IPv4/IPv6 nas seis portas administrativas,
preservando Tailscale. Permanecem painéis administrativos com bindings amplos, Homarr
legado e ZDR OpenAI ainda sem provisionamento. O receptor n8n permanece despublicado,
reduzindo o risco imediato.

Resultado da passagem inicial de 2026-08-01 (a seção de reteste abaixo prevalece):

- nenhum achado crítico confirmado;
- cinco achados altos;
- doze achados médios;
- quatro achados baixos;
- nenhuma chave privada, token conhecido, `.env`, dump ou backup encontrado no Git;
- nenhuma vulnerabilidade conhecida no conjunto Python em execução ou no módulo PDF;
- duas vulnerabilidades moderadas nas dependências de produção do frontend;
- uma vulnerabilidade alta restrita à ferramenta de desenvolvimento Vite.

Uma porta vinculada a `0.0.0.0` não prova exposição à Internet: firewall, roteador e NAT
podem bloqueá-la. Ela prova, porém, que o processo aceita tráfego por todas as interfaces
que o firewall permitir. As regras efetivas de firewall não puderam ser lidas porque o
host exige senha administrativa.

## Reteste parcial — 2026-08-02

- **ALT-01 mitigado:** senha administrativa do PostgreSQL n8n e HMAC Agenda↔n8n foram
  rotacionados sem registrar valores. Após corrigir o script para os comandos atuais de
  publicação/despublicação e reiniciar n8n antes do runner, a matriz sintética passou
  `401/401/200/200/409`. O receptor voltou a despublicado; n8n terminou com zero
  execuções e zero payloads globais.
- **MED-05 parcialmente mitigado:** React Router passou de `6.30.4` para `7.18.2`,
  removendo os advisories anteriores. O `npm audit --omit=dev` agora aponta apenas
  `GHSA-qwww-vcr4-c8h2`, relativo a execução de actions no modo RSC. A aplicação usa
  somente `BrowserRouter`, `Routes`, `Route`, links e navegação declarativa; não usa RSC,
  SSR, data router, actions ou loaders. A versão estável mais nova publicada é `7.18.2`,
  ainda sem correção para a faixa informada (`<8.3.0`); exceção temporária, revisar a cada
  atualização.
- **MED-06 mitigado:** Vite passou de `5.4.21` para `6.4.3` e esbuild para `0.25.12`;
  TypeScript e build de produção passaram. Vite não integra a imagem final Nginx.
- As 12 execuções com payload do workflow inativo e inteiramente sintético **TESTE - PDF
  sintético Google Drive** (5 sucessos e 7 erros) foram removidas por transação que
  abortava se workflow, contagem, estados ou receptor divergissem. Nenhum conteúdo foi
  aberto na classificação ou limpeza.
- **Firewall parcialmente comprovado:** UFW está ativo, com log `low`, políticas padrão
  `deny incoming`, `allow outgoing` e `deny routed`. Há liberações globais IPv4/IPv6 para
  SSH (`22/tcp`), HTTP (`80/tcp`) e HTTPS (`443`), além de uma regra SSH específica para
  `tailscale0`; a liberação global de SSH torna a específica redundante. Isso protege
  listeners normais não autorizados, mas não comprova bloqueio de portas publicadas pelo
  Docker: o DNAT do Docker pode desviar o tráfego antes das cadeias usadas pelo UFW. A
  próxima evidência obrigatória é a cadeia `DOCKER-USER`/backend nftables e um teste a
  partir de outra máquina da LAN.
- **Docker IPv4 sem filtro adicional:** `iptables -S DOCKER-USER` retornou somente a
  declaração da cadeia (`-N DOCKER-USER`), sem regras. Assim, nenhuma allowlist/drop do
  operador é aplicada antes das regras Docker. As portas publicadas em `0.0.0.0` aceitam
  qualquer origem que tenha rota até o host; acesso ao pgAdmin pela interface Tailscale
  já foi comprovado. Alcance pela LAN e Internet ainda exige teste externo/upstream.
- **Docker IPv6 sem filtro adicional:** `ip6tables -S DOCKER-USER` também retornou
  somente `-N DOCKER-USER`. Não existe regra adicional do operador para limitar as
  publicações Docker em IPv6; o alcance depende de roteamento e firewall upstream.
- **Alcance LAN confirmado para PostgreSQL auxiliar:** teste TCP executado de outra
  máquina da mesma rede retornou sucesso na porta `5432`, sem tentativa de autenticação.
  Isso prova empiricamente que as publicações Docker contornam o default-deny do UFW
  neste host. Endereços de origem/destino não foram registrados no repositório.
- **Alcance LAN confirmado para Portainer:** teste TCP externo ao servidor retornou
  sucesso na porta TLS `9443`. O painel com Docker socket gravável está, portanto,
  alcançável por qualquer máquina da LAN; não houve tentativa de autenticação.
- **Alcance LAN confirmado para code-server:** o mesmo teste retornou sucesso em `8443`.
  O editor com mount gravável do workspace/`.env` está alcançável pela LAN; não houve
  tentativa de autenticação.
- **Alcance LAN confirmado para pgAdmin:** o teste retornou sucesso em `8081`. Somado ao
  PostgreSQL auxiliar em `5432`, o painel e o banco dessa stack externa estão acessíveis
  por qualquer máquina da rede local; não houve tentativa de autenticação.
- **ALT-05 descoberto — Homarr legado com Docker socket gravável:** o container publica
  `8080` em todas as interfaces e monta `/var/run/docker.sock` com escrita. A rota do
  painel redireciona para login, mas uma tomada de conta/vulnerabilidade pode controlar
  containers. A imagem em execução é a linha legada `ghcr.io/ajnart/homarr` `0.16.0`;
  a distribuição atual usa `ghcr.io/homarr-labs/homarr` 1.x e mantém correções de
  segurança somente na estável mais recente. Restringir à Tailscale imediatamente;
  planejar backup/migração 0.x→1.x e socket proxy como mudança separada.
- O inventário de listeners encontrou também `139`, `445` e `3000` em todas as
  interfaces. Não pertencem à Agenda e não foram alterados; devem ser atribuídos ao
  serviço responsável e testados na LAN junto das portas Docker.
- **Contenção IPv4 temporária aplicada:** uma regra no início de `DOCKER-USER` bloqueia
  pela interface LAN as portas internas/publicadas dos painéis e do PostgreSQL auxiliar.
  Reteste de outra máquina confirmou `5432` e `9443` fechadas pela LAN, enquanto Homarr
  `8080` e Portainer `9443` continuaram acessíveis pela Tailscale. A regra não persiste
  após reinício e ainda não possui equivalente IPv6; essas duas pendências foram
  adiadas como mudança separada.
- **Sem opt-in de treino; ZDR não provisionado:** em Data Controls da organização
  OpenAI, `API call logging` está `Disabled` e os três controles de Sharing — feedback,
  avaliação/fine-tuning e inputs/outputs — também estão `Disabled`. Isso comprova que a
  organização não aderiu ao compartilhamento para melhoria/treino. A tela, porém, não
  oferece seletores `Zero Data Retention` ou `Modified Abuse Monitoring` no nível da
  organização/projeto. `store=false` reduz estado de aplicação no Chat Completions, mas
  não elimina os logs de monitoramento de abuso. Solicitar aprovação à OpenAI e manter o
  bloqueio de dados reais até ZDR aparecer e ser selecionado no projeto da Agenda. Em
  2026-08-05, o recurso permanecia indisponível para o projeto; as frentes independentes
  de hardening continuam sem publicar o receptor.
- **Scan de segredos concluído:** Trivy não encontrou segredos no workspace, com `.env`,
  `.git` e dependências excluídos conscientemente. Gitleaks `8.30.1`, validado pelo
  checksum oficial, percorreu 68 commits. As duas ocorrências iniciais eram o mesmo JWT
  determinístico e explicitamente sintético em dois arquivos de teste. Uma allowlist
  exige simultaneamente regra, caminho e padrão sintético; após aplicá-la, o histórico
  terminou com zero vazamentos, sem ignorar os arquivos ou o commit inteiro.
- **Scan das seis imagens Agenda concluído:** Trivy `0.70.0`, binário validado pelo
  checksum oficial, apontou no runtime atual: backend `4C/21A` (as duas altas Python são
  metadados obsoletos do SBOM da base; o filesystem candidato contém as versões
  corrigidas), frontend `2C/33A`, runner `0C/2A`, n8n `0C/8A`, PostgreSQL n8n `1C/14A`
  e pgvector `20C/45A`. `C/A` são ocorrências críticas/altas, não CVEs únicas; muitas
  ocorrências Debian repetem o mesmo CVE em pacotes relacionados e não possuem correção
  do fornecedor.
- **Correção de imagem implantada em 2026-08-03:** frontend migrou o builder para Node 22 e
  o runtime para Nginx `1.30.4-alpine3.24`; build passou e a imagem candidata caiu para
  zero vulnerabilidades em todas as severidades. Backend ganhou pisos
  `msgpack>=1.2.1` e `setuptools>=78.1.1`; candidata importa a aplicação com versões
  corrigidas. O Trivy continua reproduzindo as duas altas Python a partir do SBOM
  terceirizado da base, mas contêiner sem rede comprovou que as versões antigas não
  existem no Python do sistema nem no venv. As candidatas foram promovidas no commit
  `293a127` após snapshot coordenado.
- **Hardening implantado:** toda resposta `/api/` recebe
  `Cache-Control: no-store, private` no backend e na borda; login possui limite por IP
  comprovado (`429` na sexta requisição imediata, warning sem credenciais); configuração
  JWT recusa segredo com menos de 32 bytes e algoritmo diferente de `HS256`.
- **Revogação de sessão implantada:** `0014` adiciona versão de
  sessão ao usuário/JWT. Troca de senha revoga tokens antigos e entrega um cookie novo
  somente ao navegador que comprovou a senha; logout revoga todas as sessões. O schema
  publicado está em `0014 (head)` e o smoke HTTP comprovou revogação após troca de senha
  e logout.

## Code review e reteste final — 2026-08-03

- **Concorrência de sessões corrigida:** troca de senha e logout selecionam a linha do
  usuário com bloqueio pessimista e predicado pela `session_version` do JWT. Uma
  requisição antiga que esperou outra rotação deixa de sobrescrever o incremento ou
  revogar a sessão nova. Três regressões unitárias cobrem bloqueio, incremento e recusa
  de versão obsoleta.
- **Logout tornou-se idempotente:** cookie expirado, inválido ou já revogado é removido
  localmente com resposta de sucesso; somente uma sessão ainda válida pode incrementar a
  versão no banco. Isso evita deixar o navegador preso a um cookie inválido.
- **Valor secreto ocultado em erros:** o primeiro smoke de segredo JWT fraco revelou que
  o Pydantic acrescentava o `input_value` ao traceback, apesar da mensagem customizada.
  `hide_input_in_errors=True` removeu o valor; teste unitário e smoke final confirmaram
  a recusa sem eco do segredo sintético.
- **Fixture integrado reparado:** a limpeza de evoluções agora remove primeiro a outbox
  que possui FK desde a `0012`, e usa UUID de tenant sintético estável. O achado afetava
  somente repetibilidade dos testes, não o runtime.
- **Backend aprovado em banco descartável:** migrations `0001→0014`, ciclo
  `0014→0013→0014`, `157 passed, 1 deselected` nos unitários e `14 passed` nas
  integrações. A integração de autenticação passou novamente após o ciclo da migration.
  Lint focado, `compileall` e `git diff --check` passaram.
- **Frontend reaprovado:** `npm ci`, TypeScript, Vite build, Docker build, `nginx -t` e
  rate limit isolado passaram. O audit completo mantém apenas duas ocorrências do mesmo
  advisory RSC não alcançável; `react-router-dom@7.18.2` continua sendo a release estável
  mais recente no registro.
- **Estado no fechamento do review:** antes da autorização ainda não havia promoção
  operacional. O deploy controlado posterior está registrado na seção seguinte.

## Deploy controlado e reteste publicado — 2026-08-03

- A cópia root-only da chave de recuperação n8n estava desatualizada após a rotação. O
  backup recusou continuar antes de parar serviços; a cópia foi sincronizada diretamente
  do contêiner, sem exibir valor, e o snapshot pré-deploy `ebde69c8` foi validado.
- Backend e frontend anteriores receberam tags locais de rollback. As novas imagens
  registram a revisão OCI `293a1275a79825f41a001a135a691a48e468f06d`; a migration
  transacional `0014` foi aplicada antes de recriar exclusivamente esses dois serviços.
- Agenda, n8n e ambos os PostgreSQL terminaram saudáveis, sem reinícios anormais. O
  receptor e o workflow de teste seguem inativos, com zero execuções n8n; nenhum dado
  clínico real foi processado.
- Um tenant/usuário sintético temporário comprovou pela origem publicada: login, perfil,
  `no-store`, troca de senha, recusa do bearer anterior, relogin, logout global, recusa do
  novo bearer e logout idempotente de cookie inválido. A limpeza deixou zero tenants do
  smoke.
- Sete logins inválidos sintéticos comprovaram `401×5` e `429×2`; ambos os `429`
  incluíram `Retry-After: 60`, toda resposta usou `Cache-Control: no-store, private` e
  uma rota comum permaneceu sem limitação. Logs não mostraram traceback nem credenciais.
- O bundle pós-deploy das imagens efetivamente executadas foi preservado no snapshot
  Restic `38272c78`; o staging gocryptfs foi desmontado após ambos os backups.

## Reteste do firewall — 2026-08-04

- Um serviço oneshot persistente, ordenado depois de UFW e Docker, passou a administrar
  chains próprias em IPv4 e IPv6. `AGENDA-LAN-INPUT`, ligada ao início de `INPUT`, cobre
  listeners locais/proxy IPv6 por `--dport`; `AGENDA-LAN-DOCKER`, ligada ao início de
  `DOCKER-USER`, cobre publicações após DNAT por `--ctorigdstport`.
- Uma máquina distinta na LAN testou `5432`, `8000`, `8080`, `8081`, `8443` e `9443`.
  As seis portas expiraram em IPv4 e os seis contadores correspondentes aumentaram em
  `AGENDA-LAN-DOCKER`. Em IPv6, as seis portas foram bloqueadas e os seis contadores
  aumentaram em `AGENDA-LAN-INPUT`.
- Pela Tailscale, as seis portas permaneceram abertas. Endereços de origem e destino não
  foram registrados.
- Reiniciar somente `agenda-docker-firewall.service` reaplicou os quatro hooks e as
  chains completas; o serviço terminou `enabled` e `active`. Docker e servidor não
  foram reiniciados. O lote e o rollback dirigido estão documentados em
  `infra/firewall/`.
- O controle fecha a exposição pela interface física da LAN, mas não elimina o risco dos
  bindings amplos nem substitui a migração do Homarr e a remoção/proxy do Docker socket.
  Alcance a partir da Internet permanece fora do escopo comprovado.

## Atribuição dos listeners externos — 2026-08-05

- `139/tcp` e `445/tcp` estão em todas as interfaces IPv4/IPv6 e pertencem ao Samba do
  host. `smbd.service` e `nmbd.service` estão ativos e habilitados; o servidor opera no
  modo standalone, sem lista explícita de interfaces e com `bind interfaces only = No`.
- `3000/tcp` está em binding wildcard e pertence ao processo PM2 `mochila`, executado a
  partir do projeto Ascensão fora do Docker. O servidor Node fixa a porta `3000` e chama
  `listen` sem endereço de bind. Nenhum contêiner em execução publica essas três portas.
- A configuração persistida do UFW confirma IPv6 habilitado e políticas padrão `DROP`
  para entrada e encaminhamento. As regras efetivas e os arquivos `user.rules` exigem
  privilégio administrativo, portanto não foi possível concluir por leitura local se há
  exceções específicas. Também não houve reteste a partir de outra máquina da LAN.
- Nenhum serviço, binding ou regra de firewall foi alterado. Restringir Samba ou o
  projeto Ascensão exige validação de uso e autorização dos respectivos responsáveis;
  até lá, a atribuição está concluída, mas o alcance externo permanece pendente.

## Baseline de observabilidade — 2026-08-05

- Um verificador manual cobre estado/health, reinícios, OOM, limites/uso de memória,
  disco e rotação dos seis containers Agenda/n8n sem ler logs, ambientes ou payloads.
- Após o snapshot coordenado `4e602160`, PostgreSQL, backend e frontend foram recriados
  sem rebuild e passaram a usar `json-file` com `max-size: 10m` e `max-file: 5`.
  Volumes, migration `0014`, healthchecks e HTTP foram aprovados.
- n8n, runner e seu PostgreSQL permaneceram saudáveis e sem reinícios, mas ainda usam
  `json-file` sem limites. A mudança deve ser feita na stack Portainer em janela própria;
  encaminhamento de alerta, responsável e eventual timer também permanecem pendentes.

## Plano da operação de code review

### Parte 1 — Inventário e fronteiras de confiança

1. Mapear API, frontend, bancos, n8n, runner, Google Drive e consoles administrativos.
2. Enumerar portas e bindings reais, redes Docker, usuários, mounts e privilégios.
3. Identificar onde existem dados clínicos, credenciais, logs e cópias de recuperação.

**Saída:** diagrama de superfície, inventário de ativos e lista de acessos privilegiados.

### Parte 2 — Segredos, Git e cadeia de fornecimento

1. Examinar árvore atual e todo o histórico Git por `.env`, chaves, tokens, URLs com
   senha, dumps, bancos e backups.
2. Conferir permissões e resíduos em diretórios temporários.
3. Auditar locks npm, dependências Python efetivamente instaladas, imagens e tags.
4. Adicionar scanner de segredo por entropia e scanner de imagens ao CI.

**Saída:** inventário de segredos, plano de rotação, SBOM e relatório de CVEs.

### Parte 3 — Autenticação, autorização e isolamento de tenants

1. Revisar login, cookies, JWT, expiração, revogação, troca de senha e força bruta.
2. Conferir autenticação de todas as rotas e autorização por função.
3. Validar RLS, `FORCE ROW LEVEL SECURITY`, role sem `BYPASSRLS` e isolamento negativo.
4. Testar IDOR horizontal e vertical com dois tenants e papéis diferentes.

**Saída:** matriz rota × papel × tenant e testes automatizados de abuso.

### Parte 4 — Entrada não confiável e integrações

1. Revisar uploads, nomes de arquivos, ZIP bombs, PDF/DOCX ativo e limites de recursos.
2. Revisar anonimização antes da OpenAI e minimização de payload.
3. Revisar HMAC, janela temporal, replay, retry e idempotência n8n/Drive.
4. Testar falhas parciais sem registrar conteúdo clínico.

**Saída:** casos adversariais reproduzíveis e critérios fail-closed.

### Parte 5 — Hardening de runtime e observabilidade

1. Aplicar TLS, firewall allowlist, bind local/Tailscale e segregação administrativa.
2. Reduzir capabilities, usar `no-new-privileges`, filesystem somente leitura quando
   possível e imagens fixadas por digest.
3. Definir retenção de logs/execuções, alertas de login e resposta a incidente.
4. Ensaiar backup/restore e verificar que segredos continuam cifrados e fora do Git.

**Saída:** baseline de produção, runbook de incidente e evidência de restore.

### Parte 6 — Reteste e aceite

1. Reexecutar scanners, testes unitários/integrados e DAST autenticado em ambiente
   descartável.
2. Confirmar fechamento de cada achado por evidência, não apenas por configuração.
3. Somente então publicar o receptor e executar um único fluxo real controlado.

## Achados — do maior para o menor risco

### ALT-01 — Segredos operacionais expostos e não rotacionados

**Severidade:** Alta
**Estado:** Mitigado em 2026-08-02; receptor mantido despublicado
**Ativos:** senha administrativa do PostgreSQL do n8n e segredo HMAC Agenda↔n8n

Os valores apareceram na conversa operacional e foram tratados como comprometidos. A
senha administrativa e o HMAC foram rotacionados de forma coordenada, sem registrar os
novos valores. A matriz pós-rotação passou e terminou com retenção `0/0`.

**Mitigação aplicada:** valores rotacionados, igualdade conferida sem exposição e matriz
sintética aprovada. Manter o receptor despublicado pelos demais bloqueios de go-live e
nunca copiar valores para chat, documentação ou terminal capturado.

### ALT-02 — Portainer publicado em todas as interfaces com Docker socket gravável

**Severidade:** Alta
**Estado:** Binding amplo permanece; LAN física contida persistentemente em IPv4/IPv6,
com Tailscale preservada
**Evidência:** portas `0.0.0.0:8000` e `0.0.0.0:9443`; mount
`/var/run/docker.sock:/var/run/docker.sock` com escrita

Comprometer uma conta ou vulnerabilidade do Portainer equivale, na prática, a controlar
o Docker: criar containers privilegiados, montar volumes, ler ambientes e extrair
segredos clínicos. O impacto potencial é o host inteiro.

**Mitigação:** publicar a interface apenas em `127.0.0.1` ou no IP Tailscale; bloquear as
portas na LAN/WAN; exigir TLS confiável, senha exclusiva e MFA/SSO quando disponível;
atualizar e fixar a versão; não expor a porta de túnel Edge se não for usada.

### ALT-03 — code-server publicado em todas as interfaces e com escrita no workspace

**Severidade:** Alta
**Estado:** Binding amplo permanece; LAN física contida persistentemente em IPv4/IPv6,
com Tailscale preservada
**Evidência:** `0.0.0.0:8443`; mount gravável `/home/hades/vscode/config:/config`

O mount inclui o workspace e o `.env` da Agenda. Uma tomada da conta do code-server pode
ler segredos, alterar fonte e preparar um build malicioso. A existência de senha reduz,
mas não elimina, a superfície de ataque.

**Mitigação:** bind em loopback/Tailscale, firewall allowlist e TLS; manter credencial
forte e exclusiva; restringir o mount ao mínimo necessário; separar edição de produção
e deploy; alertar tentativas de login.

### ALT-04 — PostgreSQL e pgAdmin auxiliares publicados em todas as interfaces

**Severidade:** Alta
**Estado:** Bindings amplos permanecem; LAN física contida persistentemente em
IPv4/IPv6, com Tailscale preservada; Internet ainda não testada
**Evidência:** `postgres_db` em `0.0.0.0:5432`; `pgadmin_viz` em `0.0.0.0:8081`

São stacks distintas do banco privado da Agenda, mas compartilham o mesmo host e plano
administrativo. O PostgreSQL exposto recebe tentativas de descoberta/força bruta; o
pgAdmin amplia a superfície web e pode armazenar destinos/credenciais. Uma invasão pode
servir de pivô para outras redes Docker.

**Mitigação:** remover `ports` do PostgreSQL e administrar por `docker exec`; bind do
pgAdmin em loopback/Tailscale ou remover o serviço; restringir redes; conferir `pg_hba`,
TLS e contas; atualizar e abandonar a tag `latest`.

### ALT-05 — Homarr legado publicado na LAN com Docker socket gravável

**Severidade:** Alta
**Estado:** Confirmado no runtime; LAN física contida persistentemente em IPv4/IPv6,
Tailscale preservada; rota exige login; Fase A de exportação/backup concluída, migração
ainda não executada
**Evidência:** `0.0.0.0:8080`, imagem `ghcr.io/ajnart/homarr:latest` 0.16.0 e mount
`/var/run/docker.sock:/var/run/docker.sock` com escrita

O painel possui autenticação, mas o socket permite iniciar, parar e remover containers.
A linha de imagem instalada foi substituída pelo projeto atual 1.x, que declara suporte
de segurança apenas para a última versão estável.

**Mitigação:** restringir imediatamente a publicação à Tailscale/loopback; preservar os
volumes; planejar separadamente a migração assistida 0.x→1.x; substituir o socket direto
por proxy com permissões mínimas ou remover a integração Docker se não for necessária.
O inventário somente leitura e o plano paralelo com backup/rollback estão em
[`plano_migracao_homarr_2026-08-04.md`](./plano_migracao_homarr_2026-08-04.md).
Em 2026-08-05, ZIP, stack, imagem e três volumes foram preservados no snapshot Restic
`707f30a5`; o legado voltou saudável e o staging foi desmontado.
No mesmo dia, a stable `v1.73.0` foi baixada por digest e bloqueada antes da execução:
Trivy encontrou `2` achados críticos e `19` altos, todos com correção disponível nas
dependências; nenhuma instância candidata foi criada.

### MED-01 — Login sem rate limiting, atraso progressivo ou bloqueio

**Severidade:** Média
**Estado:** Implantado e validado na origem publicada; alerta externo pendente
**Evidência:** `frontend/nginx/nginx.conf` limita exclusivamente
`/api/v1/auth/login` por IP numa zona compartilhada entre workers: cinco requisições
imediatas, drenagem de cinco por minuto e `429` depois do limite. Rejeições são emitidas
em nível `warn`, sem corpo, e-mail ou senha. O `429` usa `Retry-After: 60` e
`Cache-Control: no-store, private`.

O teste em imagem candidata comprovou o contrato antes do deploy. O reteste publicado
repetiu cinco respostas `401`, `429` na sexta e sétima tentativas, `Retry-After: 60` e
ausência de limitação numa rota comum. A resposta continua genérica, evitando enumeração
de contas.

**Risco residual:** o controle é da borda publicada, não do socket local do backend; não
há bloqueio persistente por identificador, deliberadamente, para não permitir que um
atacante trave uma conta conhecida. Os warnings ainda precisam ser encaminhados pela
observabilidade a um alerta operacional.

### MED-02 — Tráfego HTTP e cookies sem `Secure` no deploy atual

**Severidade:** Média
**Estado:** Confirmado; risco reduzido pelo bind local atual
**Evidência:** `COOKIE_SECURE=false`, Nginx em HTTP e n8n com `N8N_SECURE_COOKIE=false`

O modelo atual depende de loopback + túnel seguro. Se qualquer porta for aberta na LAN
ou publicada por proxy inadequado, login, cookie e dados clínicos podem trafegar sem TLS.

**Mitigação:** terminar TLS em proxy confiável, ativar `COOKIE_SECURE=true`, HSTS após a
migração e validar `X-Forwarded-Proto`/hosts confiáveis.

### MED-03 — Código de workflow pode acessar variáveis do ambiente n8n

**Severidade:** Média
**Estado:** Confirmado no runtime
**Evidência:** `N8N_BLOCK_ENV_ACCESS_IN_NODE=false`

Um editor n8n malicioso ou comprometido pode tentar exfiltrar variáveis disponíveis ao
workflow. A configuração existe para o HMAC atual, mas aumenta o raio de impacto de uma
conta administrativa comprometida.

**Mitigação:** migrar o HMAC para mecanismo de credencial/secret file com exposição
mínima ao runner; depois definir `N8N_BLOCK_ENV_ACCESS_IN_NODE=true`; limitar autores de
workflow e auditar alterações.

### MED-04 — Respostas clínicas não declaram `Cache-Control: no-store`

**Severidade:** Média
**Estado:** Implantado e validado na origem publicada
**Evidência:** middleware em `backend/app/main.py` aplica
`Cache-Control: no-store, private` às respostas devolvidas sob `/api/`, inclusive login
e erros tratados; `backend/tests/unit/test_cache_control.py` cobre resposta 404 da API e
confirma que o healthcheck público permanece fora desse escopo. A borda Nginx reaplica a
política inclusive em erros locais/upstream. Smoke em contêiner efêmero sem rede passou.

O controle está no backend, portanto também protege acessos diretos sem Nginx. Na borda,
o proxy remove eventual duplicata upstream e reaplica a mesma política a toda `/api/`,
inclusive ao `429` gerado localmente.

**Reteste publicado:** login, resposta autenticada, erro de bearer revogado, logout e
`429` confirmaram `Cache-Control: no-store, private`. Adicionar `Pragma: no-cache`
somente se um cliente legado o exigir.

### MED-05 — Vulnerabilidades conhecidas no React Router em produção

**Severidade:** Média
**Estado:** Advisories alcançáveis corrigidos e implantados; exceção RSC temporária
**Pacotes implantados:** `react-router-dom@7.18.2` e `react-router@7.18.2`

A atualização removeu os advisories antigos de open redirect/XSS e desserialização. O
`npm audit --omit=dev` ainda reporta duas ocorrências altas do mesmo advisory
`GHSA-qwww-vcr4-c8h2`, exclusivo de React Server Components. Esta SPA não usa RSC, SSR,
data routers, loaders ou actions, e não existe versão estável corrigida no momento do
reteste.

**Evidência:** TypeScript e build Vite passaram. Manter exceção formal temporária,
monitorar release corrigida e retestar em cada atualização; não introduzir RSC/SSR enquanto
o advisory permanecer.

### MED-06 — Vite vulnerável no ambiente de desenvolvimento

**Severidade:** Média no contexto do projeto
**Estado:** Mitigado e implantado
**Pacote implantado no estágio de build:** `vite@6.4.3`

Os advisories de Vite/esbuild foram removidos pela atualização. TypeScript e build
passaram, e o multi-stage continua excluindo Vite da imagem final Nginx.

**Reteste:** manter dev server em loopback e nunca usá-lo como produção; repetir audit e
build na revisão final.

### MED-07 — Dependências Python e imagens-base não são fixadas de forma imutável

**Severidade:** Média
**Estado:** Parcialmente mitigado; scan e primeiras correções concluídos em 2026-08-02

O backend usa limites inferiores (`>=`) sem lock/hash e baixa o modelo spaCy durante o
build. O frontend passou a Node 22 e Nginx versionado `1.30.4-alpine3.24`; o backend
ganhou pisos para os dois pacotes Python corrigíveis. Ainda há tags sem digest
(`python:3.12-slim`, `node:22-alpine`, `n8nio/runners:2.33.0`) e outras stacks usam
`latest`. Dois builds do mesmo commit ainda podem produzir artefatos diferentes.

**Mitigação:** gerar lock Python com hashes, fixar modelo e índices, usar digest para
imagens aprovadas e gerar SBOM próprio. As candidatas revisadas foram implantadas e
preservadas no bundle `38272c78`; monitorar correções upstream do runner, n8n, `gosu`
das imagens PostgreSQL e bases Debian
do Python/pgvector. Não trocar a imagem do banco só para reduzir contagem sem restore e
teste de compatibilidade.

### MED-08 — Sessões JWT não são invalidadas por logout ou troca de senha

**Severidade:** Média
**Estado:** Implantado e validado em PostgreSQL descartável e na origem publicada

Migration `0014` adiciona `usuarios.session_version` positiva, com grant de runtime
limitado à nova coluna. A versão entra na claim `sv` e é conferida no banco junto com
usuário, tenant, papel e estado ativo. Troca de senha e logout incrementam a versão;
suspensão/reativação administrativa também incrementa, evitando que um token antigo
volte a valer após reativar a conta.

Na troca de senha, o navegador que comprovou a credencial atual recebe um JWT novo com
a versão incrementada; todos os tokens anteriores e demais sessões continuam inválidos.
O code review de 2026-08-03 adicionou bloqueio pessimista e predicado pela versão
apresentada, impedindo que logout/trocas concorrentes percam incrementos ou revoguem uma
sessão mais nova. Logout inválido/expirado agora continua idempotente e remove o cookie
local sem alterar a versão corrente no banco.

**Evidência:** `157` unitários e `14` integrações passaram; PostgreSQL 16 descartável
recebeu migrations completas, ciclo `0014→0013→0014` e reteste de autenticação. O teste
integrado cobre revogação do bearer após troca de senha e logout. Tokens anteriores à
migration não possuem `sv` e serão recusados: todos os usuários precisarão entrar
novamente uma vez. No deploy, `0014 (head)` foi confirmado e o smoke sintético publicou
a mesma prova de revogação pela borda Nginx.

### MED-09 — Hardening Docker incompleto

**Severidade:** Média
**Estado:** Confirmado no runtime e Compose

Os containers inspecionados não usam root filesystem somente leitura, `cap_drop: ALL` ou
`no-new-privileges`. Backend, n8n e runner executam como usuários não-root, mas frontend
e bancos usam usuário padrão/root no container.

**Mitigação:** aplicar controles por serviço após teste de compatibilidade; montar
diretórios graváveis explicitamente; adicionar limites de PIDs/CPU e healthchecks aos
serviços auxiliares.

### MED-10 — Retenção global de execuções n8n depende de cada workflow

**Severidade:** Média
**Estado:** Confirmado no runtime

`EXECUTIONS_DATA_PRUNE=false` evita a retenção temporária observada para workflows com
`saveData*=none`, e o receptor atual foi validado com zero payloads. Porém, qualquer
outro workflow que salve execuções pode mantê-las indefinidamente.

**Mitigação:** documentar a exceção, impedir workflows clínicos com salvamento, criar
verificação periódica das tabelas e definir política testada de retenção para workflows
não clínicos.

### MED-11 — Ausência de autorização por papel

**Severidade:** Média se novos papéis forem criados; baixa no modelo atual
**Estado:** Confirmado no código

O JWT carrega `papel`, mas as rotas validam apenas identidade/tenant. Assim, qualquer
conta ativa do tenant pode acessar auditoria e executar operações clínicas disponíveis.

**Mitigação:** declarar a matriz de papéis; criar dependência `require_role`; proteger
ações administrativas e destrutivas; testar negação vertical. Se só existir um papel,
formalizar essa restrição e impedir valores inesperados no banco/CLI.

### MED-12 — Zero Data Retention da OpenAI não está provisionado

**Severidade:** Média; bloqueio de go-live por regra de arquitetura
**Estado:** Confirmado operacionalmente em 2026-08-02
**Evidência:** `API call logging` e os três controles de Sharing desativados; sem
seletores ZDR/MAM na organização/projeto

Sem ZDR, conteúdo de cliente pode integrar logs de monitoramento de abuso por até 30
dias. O projeto envia somente texto anonimizado, usa `store=false` em Chat Completions e
não usa Assistants/Files/Vector Stores externos; esses controles reduzem exposição, mas
não equivalem à aprovação de ZDR. Chat Completions e Embeddings usados pela Agenda são
elegíveis para ZDR.

**Mitigação:** solicitar aprovação/provisionamento à OpenAI; após deferimento, selecionar
Zero Data Retention na organização ou explicitamente no projeto Agenda e registrar data,
modo efetivo e responsável sem IDs ou segredos. Não processar dado real até a prova.

### BAI-01 — Configuração não falha cedo com segredo JWT vazio

**Severidade:** Baixa no deploy atual; potencialmente alta em novo deploy incorreto
**Estado:** Implantado; startup fail-fast validado na imagem publicada

`Settings` agora recusa o startup quando `JWT_SECRET_KEY` possui menos de 32 bytes ou
quando `JWT_ALGORITHM` difere do contrato `HS256`. A validação não inclui o valor do
segredo na mensagem de erro.

**Evidência:** testes unitários cobrem segredo curto sem eco do valor, algoritmo inválido
e caso válido; smoke na imagem final sem rede recusou o caso fraco sem reproduzir o
segredo e importou a aplicação com configuração sintética válida. Ainda é
responsabilidade operacional gerar segredo aleatório; comprimento mínimo não prova
entropia.

### BAI-02 — `infra/.env` possui permissão `0644`

**Severidade:** Baixa
**Estado:** Confirmado; atualmente contém apenas configuração de porta

O nome incentiva operadores a adicionar segredos futuramente, que ficariam legíveis por
outros usuários locais.

**Mitigação:** usar `0600`, remover o arquivo redundante ou documentar que nunca recebe
segredos.

### BAI-03 — API devolve o bearer token no corpo do login

**Severidade:** Baixa
**Estado:** Confirmado; a SPA ignora o corpo e usa cookie HttpOnly

O modo duplo aumenta os lugares em que o token aparece (clientes, proxies e ferramentas
de inspeção). Não é necessário para o navegador.

**Mitigação:** separar endpoint/browser cookie-only de autenticação programática ou
habilitar o retorno por configuração explícita; sempre usar `no-store` no login.

### BAI-04 — Endpoints de documentação FastAPI usam defaults

**Severidade:** Baixa
**Estado:** Confirmado; backend está em loopback

`/docs`, `/redoc` e `/openapi.json` são criados por padrão. Ajudam reconhecimento se a
porta do backend for exposta futuramente.

**Mitigação:** desativar em produção ou protegê-los na rede administrativa.

## Verificações sem achado

- `.env` principal existe apenas localmente, está ignorado e com modo `0600`.
- `.env` real nunca apareceu no histórico Git alcançável.
- não foram encontrados arquivos `.pem`, `.key`, `.p12`, `.pfx`, dumps, bancos ou
  backups no histórico.
- busca por chaves OpenAI/GitHub/Google/AWS, private keys, URLs PostgreSQL com senha e
  pelos prefixos dos dois segredos expostos não encontrou correspondência no Git.
- maiores blobs Git têm cerca de 110 KiB e são documentação; não há sinal de dump
  disfarçado ou backup binário.
- backups temporários dos workflows estão em `/tmp` com modo `0600` e sem padrão de
  credencial; o smoke sintético está `0644`, mas lê o segredo externamente e não o embute.
- banco PostgreSQL da Agenda e banco do n8n não publicam portas no host.
- backend, frontend e editor n8n estão vinculados a `127.0.0.1`.
- rede `agenda-webhook` está `internal=true` e `attachable=false`.
- role de runtime da Agenda é separada do administrador e o desenho usa RLS forçado.
- webhook possui HMAC, janela de cinco minutos, comparação constante, antirreplay e
  conclusão persistente antes do `200`.
- upload usa allowlist, nome interno aleatório, limites de tamanho/recursos, subprocesso
  sem shell, sanitização e download `attachment`/`nosniff`.
- Bandit: zero achados médios/altos; dois baixos referentes ao subprocesso já mitigado.
- `pip-audit` do conjunto Python em execução: nenhuma vulnerabilidade conhecida.
- `npm audit` do módulo `@agenda/pdf-evolucao`: nenhuma vulnerabilidade conhecida.
- Nginx já define CSP restritiva, `X-Frame-Options`, `nosniff` e `Referrer-Policy`.

## Plano de correção priorizado

### P0 — antes de dado real

1. ~~Rotacionar a senha administrativa do PostgreSQL n8n e o segredo HMAC expostos.~~
   Concluído em 2026-08-02.
2. ~~Manter o receptor despublicado até repetir toda a matriz sintética.~~ Matriz aprovada;
   receptor continua despublicado enquanto os demais bloqueios de go-live permanecem.
3. Restringir Portainer, code-server, pgAdmin e PostgreSQL a loopback/Tailscale e
   firewall allowlist; remover portas/serviços desnecessários.
4. Confirmar do lado de outra máquina da LAN e, se aplicável, da Internet que portas não
   autorizadas estão fechadas.

### P1 — em até sete dias

1. ~~Atualizar React Router e Vite; repetir audits, build e deploy.~~ Concluído e
   implantado; permanece a exceção RSC não alcançável documentada.
2. ~~Implantar e retestar o rate limiting do login.~~ Concluído; ainda falta encaminhar
   os warnings para alerta operacional.
3. ~~Adicionar `Cache-Control: no-store, private` à API autenticada e login.~~ Concluído,
   implantado e aprovado na origem publicada.
4. Implantar TLS e cookies `Secure` antes de abandonar o túnel local.
5. Projetar remoção de acesso de workflows às variáveis de ambiente.
6. ~~Implantar validação fail-fast e versão de sessão JWT.~~ Migration `0014` e smoke de
   revogação publicados e aprovados.

### P2 — em até trinta dias

1. Lock Python com hashes, imagens por digest, SBOM e scan Trivy/Grype.
2. Scanner de segredos no pre-commit/CI e proteção de push no provedor Git.
3. Hardening Docker por serviço e revisão de mounts/capabilities.
4. Matriz de autorização por papel e testes IDOR com dois tenants.
5. DAST autenticado em clone descartável, sem dados reais.
6. Política testada de retenção n8n, logs, auditoria e resposta a incidente.

## Critérios de aceite do reteste

- nenhum segredo exposto continua ativo;
- nenhuma interface administrativa aceita conexão fora da allowlist;
- `npm audit --omit=dev` sem vulnerabilidades conhecidas relevantes;
- imagens sem CVEs críticas/altas exploráveis ou com exceção formal documentada;
- força bruta retorna `429`/atraso e gera alerta sem permitir enumeração;
- cookies possuem `Secure`, `HttpOnly`, `SameSite=Strict` sob TLS;
- respostas autenticadas e login usam `Cache-Control: no-store`;
- token anterior à troca de senha é recusado;
- testes de RLS/IDOR e matriz de papéis negam acesso cruzado;
- receptor sintético passa `401/401/200/200/409`, retém zero payloads e não duplica PDF;
- restore isolado recupera banco, documentos, n8n e chaves sem exposição em logs.

## Limitações desta revisão

- UFW e os hooks `INPUT`/`DOCKER-USER` em IPv4/IPv6 foram lidos; persistência e bloqueio
  dual-stack das seis portas foram comprovados. Ainda falta auditoria completa do
  ruleset nftables;
- houve reteste completo das seis portas a partir da LAN em IPv4/IPv6 e pela Tailscale;
  não houve teste a partir do roteador ou da Internet;
- não houve DAST autenticado, exploração de CVE nem força bruta prolongada contra o
  deploy; o limitador foi exercitado por sete logins inválidos sintéticos controlados;
- seis imagens foram escaneadas com Trivy; não houve segundo scanner independente,
  geração de SBOM próprio ou validação contínua em CI;
- Gitleaks percorreu os 68 commits e Trivy o workspace; scanner de segredos ainda não
  integra pre-commit/CI nem proteção de push do provedor;
- o lote final passou `157` unitários (`1 deselected`) e `14` integrações em PostgreSQL
  descartável; o teste NER conhecido continua limitado pelo modelo pequeno. O deploy
  recebeu smoke HTTP direcionado, não a suíte integrada completa contra a base ativa;
- configurações de compartilhamento da pasta Google Drive e do console OAuth não foram
  auditadas por API.

Essas limitações impedem chamar o trabalho de pentest completo. O documento é uma
revisão defensiva inicial e um plano de fechamento verificável.
