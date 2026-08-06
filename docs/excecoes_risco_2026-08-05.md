# Registro de exceções temporárias de risco — 2026-08-05

Este registro separa vulnerabilidades conhecidas que não foram corrigidas no runtime
por falta de correção upstream, incompatibilidade ou ausência de uma mudança segura.
Uma exceção só é efetiva depois de aceite explícito do responsável técnico; este
arquivo não autoriza sozinho publicação do receptor, uso de dados reais ou execução
de uma imagem bloqueada.

## EXC-01 — Advisory RSC do React Router

- **Escopo:** `react-router`/`react-router-dom` `7.18.2`, advisory
  `GHSA-qwww-vcr4-c8h2`.
- **Justificativa:** o advisory é específico de React Server Components. A aplicação
  publicada usa SPA com `BrowserRouter`, rotas declarativas e build Vite; não usa RSC,
  SSR, data routers, loaders ou actions.
- **Controles compensatórios:** manter a arquitetura SPA; não introduzir RSC/SSR/data
  APIs sem nova revisão; TypeScript, build e `npm audit --omit=dev` em cada atualização.
- **Gatilho de encerramento:** versão estável corrigida publicada ou mudança de
  arquitetura que torne o caminho alcançável; revisar em toda atualização frontend.
- **Estado:** exceção temporária proposta; não cobre outros advisories nem autoriza
  ignorar falhas novas.

## EXC-02 — CVEs upstream/base nas imagens operacionais

- **Escopo:** ocorrências sem correção aplicável no fornecedor da base Debian/Alpine,
  runner, n8n, `gosu` PostgreSQL e pgvector, conforme o scan Trivy `0.70.0` registrado
  na revisão de segurança. O scan do runtime e a alcançabilidade variam por imagem;
  não tratar contagens repetidas como CVEs únicas.
- **Justificativa:** trocar a imagem do banco ou do n8n sem restore e teste de
  compatibilidade pode causar perda de serviço ou dados. As imagens próprias corrigíveis
  já foram reconstruídas/implantadas; o frontend final está limpo.
- **Controles compensatórios:** imagens efetivamente executadas preservadas no bundle
  `38272c78`; serviços administrativos contidos por firewall; n8n e workflows clínicos
  permanecem inativos; Homarr `v1.73.0` foi bloqueado antes de criar candidato; repetir
  Trivy após cada nova release e não usar `latest`.
- **Gatilho de encerramento:** correção upstream disponível e validada em staging
  isolado, ou análise individual de alcançabilidade com aceite técnico específico.
- **Estado:** exceção temporária proposta para as imagens em produção; não inclui a
  candidata Homarr bloqueada (`2` críticas e `19` altas corrigíveis).

## EXC-03 — ZDR OpenAI indisponível

- **Escopo:** o projeto OpenAI não possui ZDR/MAM provisionado; chamadas elegíveis
  continuam sujeitas aos controles padrão de monitoramento de abuso.
- **Aceite:** o operador aceitou explicitamente esse risco em 2026-08-06 para permitir
  a continuidade do planejamento de go-live. Isso não autoriza por si só o envio de
  dados clínicos reais, nem altera os gates do webhook, n8n, Drive ou Homarr.
- **Controles compensatórios:** `store=false` onde aplicável; controles de Sharing e
  `API call logging` permanecem desativados; pseudonimização local; nenhum dado clínico
  real até os demais critérios de go-live serem aprovados; revisar Usage e controles do
  projeto periodicamente.
- **Gatilho de encerramento:** ZDR/MAM aprovado e selecionado no projeto, ou retirada
  formal desta aceitação. Reavaliar em cada mudança de política ou arquitetura OpenAI.
- **Estado:** risco aceito temporariamente pelo operador; não confundir com evidência
  de ZDR ativo.

## Governança

- **Revisão:** a cada atualização de imagem/dependência e, no máximo, a cada 30 dias.
- **Evidência mínima:** versão/digest, scan, alcance no runtime, mitigação, responsável
  pelo aceite e data de revisão. Nunca registrar segredos ou payloads.
- **Limites:** as exceções não liberam o workflow n8n, não substituem ZDR, backup,
  restore, firewall ou correção de vulnerabilidades alcançáveis.
