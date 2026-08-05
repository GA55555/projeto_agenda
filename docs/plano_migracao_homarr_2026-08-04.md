# Plano de migração segura do Homarr — 2026-08-04

## Estado e objetivo

O Homarr atual continua saudável e não foi alterado durante este inventário. Ele usa a
linha legada `ghcr.io/ajnart/homarr`, três volumes graváveis, publicação ampla e mount
gravável direto de `/var/run/docker.sock`. Não há limite de memória; a leitura pontual
indicou aproximadamente 334 MiB em uso.

O objetivo é migrar sem atualização *in-place*, preservar rollback integral e remover o
socket Docker direto. A implantação depende de uma janela aprovada; este documento não
autoriza parar, recriar ou excluir a stack atual.

## Base oficial verificada

- A linha 1.x é uma reescrita completa; mounts e banco anteriores não são compatíveis.
  A migração suportada exporta um ZIP pela interface antiga e o importa durante o
  onboarding da nova instalação. A documentação recomenda manter uma instalação
  paralela durante o processo: [guia oficial de migração](https://homarr.dev/blog/2025/01/19/migration-guide-1.0/).
- A imagem atual é `ghcr.io/homarr-labs/homarr`; a instalação usa somente `/appdata` e
  exige `SECRET_ENCRYPTION_KEY` com 64 caracteres hexadecimais:
  [instalação Docker](https://homarr.dev/docs/getting-started/installation/docker/).
- A versão estável mais recente confirmada em 2026-08-04 é `v1.73.0`. Segurança é
  corrigida somente na versão estável mais nova:
  [release](https://github.com/homarr-labs/homarr/releases/tag/v1.73.0) e
  [política de segurança](https://github.com/homarr-labs/homarr/security).
- O requisito oficial mínimo é 500 MB de RAM e 600 MB livres para a imagem:
  [pré-requisitos](https://homarr.dev/docs/getting-started/).
- O próprio projeto alerta que o socket concede controle amplo do Docker e recomenda
  proxy. Para proxies, `CONTAINERS=1` permite a seção de contêineres; `POST=1` habilita
  ações críticas e deve permanecer desligado neste projeto:
  [integração Docker e segurança](https://homarr.dev/docs/integrations/docker/).

## Inventário sem conteúdo sensível

- container legado saudável, gerenciado pela stack Portainer `homaar`;
- um arquivo de configuração no volume antigo e nenhum ícone customizado detectado;
- um arquivo no volume `/data`; total persistido inferior a 128 KiB;
- três volumes precisam entrar no backup, inclusive o volume anônimo de `/data`;
- política de reinício `unless-stopped`, sem `mem_limit`, `read_only` ou
  `no-new-privileges`;
- porta interna `7575/tcp` publicada pelo host; a contenção dual-stack da LAN já protege
  a publicação ampla, mas o binding deve ser estreitado no corte;
- Docker socket montado diretamente com escrita.

Nomes de volume, caminhos Portainer, endereços, conteúdo do dashboard, integrações e
credenciais permanecem no inventário operacional restrito, fora do Git.

## Decisões da migração

1. **Sem atualização in-place.** A stack antiga fica intacta até o aceite final.
2. **Versão fixada.** Usar `ghcr.io/homarr-labs/homarr:v1.73.0` e registrar o digest
   efetivamente baixado; não implantar `latest`.
3. **Instalação paralela privada.** Subir `homarr-v1-review` com volume novo e porta
   ligada somente a loopback durante o ensaio. Acesso exclusivamente por túnel.
4. **Limites explícitos.** Reservar `768m` para o Homarr candidato e `128m` para eventual
   proxy, validando consumo e OOM antes do corte.
5. **Socket ausente por padrão.** Primeiro validar a importação sem integração Docker.
   Se apenas inventário/estatísticas forem realmente necessários, introduzir proxy
   dedicado, sem porta publicada, em rede interna exclusiva, com `CONTAINERS=1` e
   `POST=0`. Ações de iniciar, parar, reiniciar ou remover contêineres ficam indisponíveis.
6. **Segredos fora do Git.** `SECRET_ENCRYPTION_KEY`, ZIP exportado e chave de
   descriptografia da migração ficam somente em armazenamento cifrado/restrito. Não
   imprimir valores em logs, terminal capturado ou conversa.
7. **Defesa em profundidade.** Testar `cap_drop: [ALL]`, `security_opt:
   [no-new-privileges:true]` e filesystem somente leitura com `tmpfs` mínimo. Manter
   apenas controles compatíveis comprovados no candidato.

## Execução em fases

### Fase A — backup e exportação

1. Pela interface antiga, abrir **Management → Tools → Migrate to 1.0**, selecionar todo
   o conteúdo e baixar o ZIP. Guardar a chave mostrada separadamente em armazenamento
   cifrado.
2. Registrar hash local do ZIP sem versionar o hash reutilizável nem o artefato.
3. Em janela curta, parar somente o Homarr legado, copiar consistentemente os três
   volumes e a definição da stack para staging cifrado, preservar a imagem efetiva e
   reiniciar a stack antiga.
4. Validar que o backup contém os três volumes, a definição e a imagem, e que o Homarr
   antigo voltou saudável. Desmontar o staging.

### Fase B — candidato paralelo

1. Baixar `v1.73.0`, registrar digest e escanear a imagem antes de executar.
2. Criar secret novo de 64 caracteres hexadecimais e armazená-lo somente no inventário
   restrito da stack.
3. Subir o candidato em volume/rede novos, `127.0.0.1:7576`, `mem_limit: 768m`, sem
   socket Docker e sem ligação às redes da Agenda.
4. Importar o ZIP no onboarding com a chave de migração. Conferir usuários, boards,
   apps, layouts e integrações sem revelar valores.
5. Reiniciar somente o candidato e comprovar persistência, saúde, logs sem segredos,
   consumo de RAM e ausência de OOM.

### Fase C — integração Docker opcional

1. Confirmar com o operador se widgets/estatísticas de Docker são necessários. Se não
   forem, manter a integração ausente.
2. Se forem necessários, subir proxy fixado por versão/digest, com socket montado apenas
   nele, nenhuma porta no host e rede interna exclusiva com o Homarr.
3. Conceder inicialmente somente leitura de contêineres (`CONTAINERS=1`, `POST=0`) e
   validar os widgets usados. Não ampliar permissões apenas para recuperar ações
   administrativas; essas ações permanecem no Portainer/caminho operacional próprio.
4. Confirmar por `docker inspect` que o Homarr não possui mount do socket.

### Fase D — corte controlado

1. Fazer backup do candidato já importado.
2. Parar o legado sem apagar container, volumes, imagem ou stack.
3. Publicar o candidato somente em loopback ou no endereço Tailscale mantido fora do
   Git; não usar `0.0.0.0`/`::`.
4. Retestar login, boards, links, integrações necessárias, reinício, Tailscale e bloqueio
   pela LAN em IPv4/IPv6.
5. Manter o legado desligado e recuperável por um período de observação. A remoção é uma
   mudança destrutiva separada, com autorização própria.

## Rollback

Se importação, autenticação, layouts, integrações, memória ou rede falharem:

1. parar somente o candidato;
2. restaurar a publicação original e iniciar o container legado com a imagem e os três
   volumes preservados;
3. validar saúde e acesso privado;
4. manter candidato e evidências para diagnóstico, sem repetir a importação sobre dados
   não respaldados.

O rollback não depende de converter dados 1.x de volta para 0.x: a instalação antiga
nunca é migrada em lugar nem tem seus volumes reutilizados pelo candidato.

## Critérios de aceite

- ZIP oficial e backup cifrado dos três volumes/stack/imagem verificados;
- `v1.73.0` fixada por tag e digest, com scan registrado;
- importação completa aprovada visualmente pelo operador;
- reinício do candidato preserva todos os dados;
- memória permanece dentro de `768m`, sem OOM/restart anormal;
- Homarr sem socket Docker direto;
- proxy ausente ou restrito a rede interna, `CONTAINERS=1` e `POST=0`;
- porta vinculada somente a loopback/Tailscale;
- LAN IPv4/IPv6 bloqueada e acesso privado preservado;
- rollback legado testável e volumes antigos não removidos.
