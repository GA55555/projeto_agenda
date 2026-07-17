# Arquitetura & Regras de Ouro do Projeto

> **Documento constitucional.** Estas são as normas inegociáveis de arquitetura, segurança e desempenho para a aplicação de gestão de agendamentos e prontuários psicológicos com foco no atendimento de pacientes no Transtorno do Espectro Autista (TEA).
>
> Qualquer decisão técnica, PR ou dependência nova deve ser avaliada contra este documento. Em caso de conflito entre conveniência de desenvolvimento e uma regra aqui descrita, **a regra prevalece**.

---

## 0. Contexto Operacional

### 0.1. Infraestrutura (hardware restrito)

| Recurso | Especificação |
| --- | --- |
| Hospedagem | Self-hosted, servidor doméstico |
| SO | Debian 12 |
| CPU | AMD A6, **2 núcleos** |
| RAM total | **7.2 GB** |
| Armazenamento primário | SSD 120 GB (SO + volumes) |
| Armazenamento secundário | HDD 500 GB (backups) |
| Serviços pré-existentes | n8n, Homer, Portainer |

### 0.2. Stack

- **Backend:** Python + FastAPI (Uvicorn)
- **Frontend:** TypeScript (React ou Vue.js) — SPA servida por Nginx
- **Base de dados:** PostgreSQL + `pgvector` (relacional + vetorial)
- **Administração da BD:** **sem GUI** — acesso via `psql` (`docker compose exec postgres psql`). Decisão deliberada de menor exposição: nenhum console web, zero superfície de ataque adicional, 0 MB de RAM. Acesso privilegiado tratado como caminho *break-glass* (ver §2.1.1).
- **Automação:** n8n (já instalado no servidor)
- **IA:** LLMs da OpenAI (`text-embedding-3-small`, geração de resumos)

### 0.3. Contexto legal (inflexível)

Dados de **saúde de menores de idade** com TEA. Conformidade obrigatória com:

- **LGPD** — dados sensíveis (Art. 11) e proteção de crianças e adolescentes (Art. 14)
- **ECA** — Estatuto da Criança e do Adolescente
- **CFP** — Resolução CFP nº 001/2009 e Resolução CFP nº 06/2019

**Princípios-mestre:** menor exposição possível, segregação estrutural absoluta, anonimização rigorosa e reversível, e IA em ambiente de **risco zero** de vazamento de PII.

---

## 1. Arquitetura e Performance em Hardware Restrito

**Premissa fundamental:** contenção rigorosa de RAM e limitação do processamento assíncrono para evitar a inanição (*starvation*) de recursos do SO e a intervenção do **OOM Killer**.

### 1.1. Orçamento de memória (hard limits obrigatórios no Docker)

Orçamento operacional disponível para a nova aplicação: **~3.5–4 GB**.

| Componente | Limite máximo de RAM | Justificativa |
| --- | --- | --- |
| **PostgreSQL** (com pgvector) | **1.5 GB** | Buffer suficiente para consultas vetoriais exatas e gestão de ligações; força o uso do *page cache* do SSD para o excedente. |
| **Backend** (FastAPI / Uvicorn) | **1.0 GB** | Pegada de memória do Python é elevada; impõe GC rigoroso e trava fugas prolongadas. |
| **Frontend** (Nginx / estáticos) | **100 MB** | SPA — apenas servidor de ficheiros estáticos, consumo residual. |
| Serviços de base (SO, n8n, Homer, Portainer, page cache) | **~4.6 GB** (não limitado) | Margem de segurança para o SO, automações e o indispensável cache de disco do Linux. |

> ℹ️ **Administração da BD sem contentor extra:** não há pgAdmin/CloudBeaver. O acesso administrativo é feito por `psql` dentro do contentor do Postgres (`docker compose exec`), sem custo de RAM nem porta web exposta.

> ⚠️ **Regra:** contentores Docker sem limite explícito consomem toda a RAM disponível e provocam a atuação arbitrária do OOM Killer. **Nenhum contentor da aplicação sobe sem `mem_limit` definido.**

### 1.2. Otimização do PostgreSQL (`postgresql.conf`)

A configuração padrão é conservadora e ineficiente neste cenário. Afinação obrigatória:

| Parâmetro | Valor | Regra |
| --- | --- | --- |
| `shared_buffers` | **512 MB – 1 GB** | **Não** usar os 25–40% habituais (≈2.8 GB) — esgotaria o orçamento. Delega o cache menos crítico ao filesystem do Linux sobre SSD. |
| `work_mem` | **4 MB – 16 MB** | Alocado *por operação de sort/hash, por consulta, por utilizador* — valor alto multiplica RAM exponencialmente. |
| `maintenance_work_mem` | **128 MB** | Para VACUUM/reconstrução de índices. Pode ser elevado pontualmente via `SET LOCAL` só quando necessário. |
| `max_connections` | **50** | Clínica com no máximo 5 psicólogas; 100 (padrão) pré-aloca recursos desnecessários. Margem ampla para o pool do FastAPI + admin. |

### 1.3. Otimização do ecossistema Python / FastAPI

1. **Lazy loading obrigatório para bibliotecas pesadas.**
   Bibliotecas como `spaCy`, `Microsoft Presidio` ou ferramentas analíticas **não** são importadas no escopo global. A importação ocorre **dentro da função** que as utiliza:
   ```python
   def anonimizar_texto(...):
       from presidio_anonymizer import ...  # importa só ao processar a rota
   ```
   Reduz a *baseline footprint* do microserviço.

2. **Uvicorn — 2 workers, uvloop.**
   AMD A6 tem 2 núcleos. Cada worker é um processo independente (interpretador, GIL, event loop, memória próprios). Muitos workers = *context-switching* e pressão de memória, não mais capacidade.
   ```bash
   uvicorn app.main:app --workers 2 --loop uvloop
   ```

3. **Afinação do Garbage Collector.**
   Em serviço de longa duração, forçar varreduras mais frequentes para manter RAM linear e previsível:
   ```python
   import gc
   gc.set_threshold(700, 10, 10)
   ```

---

## 2. Segurança e Proteção de Dados (LGPD, ECA, CFP)

### 2.1. Isolamento multilocatário — Row-Level Security (RLS) obrigatório

Confiar o isolamento apenas a filtros na camada aplicacional (`WHERE psicologa_id = X` em Python) é **risco inaceitável**: uma única omissão causa *cross-tenant data leakage*. Permitir que uma psicóloga acesse o prontuário de paciente de outra (salvo co-terapia explícita) é violação gravíssima do sigilo profissional.

**Regra de ouro:** o controlo de acesso vive no **motor da base de dados**, não na aplicação.

1. Toda tabela com dados de paciente/notas clínicas possui `tenant_id`.
2. RLS ativado e política restritiva:
   ```sql
   ALTER TABLE prontuarios ENABLE ROW LEVEL SECURITY;
   CREATE POLICY isolamento_tenant ON prontuarios
       FOR ALL
       USING (tenant_id = current_setting('app.current_tenant_id')::uuid);
   ```
3. **Integração com FastAPI/SQLAlchemy:** a cada requisição autenticada, o middleware/dependência injeta o contexto **dentro da transação** usando `SET LOCAL` (nunca `SET`):
   ```sql
   SET LOCAL app.current_tenant_id = 'id_do_utilizador';
   ```
   `SET LOCAL` garante que a identidade só vale naquela transação, impedindo que o `tenant_id` transite entre requisições num pool de ligações partilhado.

Com isto, um `SELECT * FROM prontuarios` genérico devolve apenas os registos do locatário ativo — qualquer erro de programação é neutralizado pela base de dados.

#### 2.1.1. Acesso privilegiado (psql) e o *bypass* natural do RLS

O PostgreSQL **ignora as políticas de RLS** para o **superusuário**, para roles com `BYPASSRLS` e para o **dono (owner) da tabela** (salvo `FORCE ROW LEVEL SECURITY`). O acesso administrativo via `psql` costuma usar um role de superusuário — portanto **vê todos os locatários**. É caminho legítimo de administração, mas de altíssimo risco de exposição de PII de menores. Regras obrigatórias:

1. **Role de aplicação sem privilégio.** O backend liga-se com um role dedicado (`agenda_app`) que **não é superusuário nem dono das tabelas clínicas**. As tabelas são criadas/possuídas por um role de migração separado. Só assim o RLS atua sobre a aplicação.
2. **`FORCE ROW LEVEL SECURITY`** em todas as tabelas com dados clínicos, para que **nem o dono da tabela** escape à política sem intenção explícita:
   ```sql
   ALTER TABLE prontuarios FORCE ROW LEVEL SECURITY;
   ```
3. **Acesso administrativo é *break-glass*.** O `psql` como superusuário fica restrito ao administrador do servidor (via `docker compose exec`, sem porta exposta), credenciais via secrets (§4.1). Toda consulta administrativa que atravessa locatários é, por definição, uma operação sensível sob a LGPD (princípio da menor exposição, §0.3). Para inspeção rotineira, preferir o role `agenda_app` (sujeito ao RLS) em vez do superusuário.

### 2.2. Consentimento e conformidade com o ECA

- **Vínculo obrigatório:** paciente (criança) sempre associado ao perfil detalhado do **responsável legal**.
- **Consentimento** específico, livre e inequívoco de ao menos um dos pais/responsável (Art. 14 LGPD), sobretudo para menores de 13 anos.
- **TCLE** gerado pela aplicação **não** pode ter cláusulas genéricas: especifica a finalidade clínica e as limitações de acesso.
- **Sigilo do conteúdo terapêutico** pertence à criança; aos pais é facultado apenas o acesso a **informações gerais** sobre a evolução (diretrizes CFP).
- **Auditoria indelével:** toda revogação de consentimento ou alteração de guarda legal é registada de forma auditável e imutável.

### 2.3. Fluxo criptográfico síncrono de pseudonimização (túnel opaco para o LLM)

O CFP proíbe submeter dados pessoais identificáveis (nomes, CPFs, moradas) a LLMs de terceiros. O backend implementa um **fluxo síncrono de anonimização/desanonimização local**, atuando como túnel opaco entre o registo da psicóloga e o LLM.

- **Bibliotecas:** Microsoft Presidio como base, mas o processamento pesado depende de **Regex otimizado** e correspondência de múltiplas strings.
- **Deteção:** algoritmo **Aho-Corasick** (autómato trie + ligações de falha), complexidade **O(n+m+z)** numa única passagem linear — evita o *catastrophic backtracking* do Regex tradicional e mantém a carga do AMD A6 controlada.

**Fluxo operacional:**

1. **Mapeamento** — o texto é varrido em RAM; PII (paciente, clínica, familiares, locais) é isolada.
2. **Substituição estruturada** — entidades reais → marcadores sequenciais:
   *"O Pedro apresentou crises na escola de Belo Horizonte"* → *"O `<PERSON_1>` apresentou crises na escola de `<LOCATION_1>`"*.
3. **Tabela de equivalência em trânsito** — dicionário `<PERSON_1> → "Pedro"` mantido **apenas em memória volátil**, atrelado à sessão. **Nunca é gravado na base de dados.**
4. **Injeção no LLM** — a OpenAI recebe só o texto mascarado; foca na semântica clínica/comportamental.
5. **Desanonimização reversível** — o *Deanonymizer* restaura os marcadores com o dicionário volátil antes de apresentar o resultado final e legível à psicóloga para aprovação e gravação.

> 🔒 **Regra:** o dicionário de equivalência jamais é persistido. Se a sessão morre, o mapeamento morre com ela.

---

## 3. Base de Dados Vetorial e IA (RAG com pgvector)

O acompanhamento do TEA exige **contexto longitudinal** (marcos de desenvolvimento, reações adversas, gatilhos sensoriais passados). Padrão obrigatório: **RAG (Retrieval-Augmented Generation)** ancorado em `pgvector`, respeitando os limites de tokens da OpenAI e sem introduzir ruído semântico.

### 3.1. Índices vetoriais — **nenhum índice na fase inicial**

Embeddings de `text-embedding-3-small` = **1.536 dimensões** por registo. Opções de índice do pgvector:

| Índice | Consulta | Custo de RAM/construção |
| --- | --- | --- |
| HNSW | Excelente velocidade e recall | RAM **muito elevada**, construção morosa |
| IVFFlat | Boa, precisão ligeiramente menor | Menos RAM/tempo |

**Regra de ouro:** **não criar índice vetorial na fase inicial.** Para coleções pequenas (< 100 mil – 1 milhão de registos), a **Pesquisa Exata** (*sequential scan*) resolve em < 50 ms, garante **100% de recall** e **zero sobrecarga de memória**. Com até 5 profissionais, a base levará anos até o *scan* sequencial se tornar estrangulamento. Reavaliar índices só quando a escala real exigir.

### 3.2. Filtragem híbrida obrigatória (pré-filtragem por metadados)

Calcular distância de cosseno (`<=>`) contra **todos** os vetores satura a CPU. Antes do cálculo de semelhança, **reduzir o espaço de pesquisa** com índices B-Tree sobre metadados. Toda consulta vetorial inclui, invariavelmente, `tenant_id` **e** `paciente_id`:

```sql
SELECT notas
FROM evolucoes
WHERE paciente_id = 'uuid_x'
  AND tenant_id   = 'uuid_y'
ORDER BY embedding <=> $novo_vetor
LIMIT 5;
```

O cálculo vetorial incide só sobre o pequeno subconjunto filtrado → execução quase instantânea.

### 3.3. Segmentação (chunking) e prompt dinâmico

- Prontuários longos são particionados em **blocos lógicos menores** antes de vetorizados.
- Nota nova (ex.: crise por ruído) → vetorizada → filtragem híbrida encontra, no histórico **daquele paciente**, outros gatilhos sonoros.
- Blocos relevantes + anotações do dia → enviados **anonimizados** ao LLM via prompt dinâmico.
- Benefício: poupa tokens, evita alucinações e destaca tendências clínicas sem enviar histórico irrelevante.

---

## 4. Integração, Deploy e Automação

### 4.1. Contentorização (Docker) segura

- **Multi-stage builds obrigatórios.** Ferramentas de compilação em C e pacotes de dev usados só na fase de build; excluídos da imagem final. Imagens `slim`/`alpine` → menor pegada no SSD, arranque mais rápido, menos vetores de ataque.
- **Segredos nunca no código.** Chaves de API (OpenAI), parâmetros JWT e credenciais da BD via **Docker Secrets** ou ficheiros `.env` com permissões restritas ao admin. Protege contra intrusão no repositório ou acesso ilegítimo ao Portainer.
- **Sem console de administração web.** Não há pgAdmin/CloudBeaver exposto. Administração da BD apenas por `psql` via `docker compose exec` (shell interno do servidor) — elimina uma superfície de ataque inteira. O `psql` como superusuário ignora o RLS (§2.1.1) e é reservado a *break-glass*.

### 4.2. Fluxos documentais e webhooks via n8n

A lógica pesada de formatação/exportação é **descarregada do FastAPI para o n8n**.

- **Acionamento seguro:** após assinatura eletrónica da profissional, o backend envia JSON via **Webhook** ao n8n local. O endpoint **exige autenticação** por cabeçalho/token criptográfico partilhado só entre FastAPI e n8n. Comunicação local **não** dispensa segurança.
- **OAuth2 delegado ao n8n:** integração com Google Drive/Gmail gerida **exclusivamente** via OAuth2 no n8n (projeto no Google Cloud Console, *consent screen*, apenas Google Drive API + Google Docs API). A aplicação e a BD **nunca** tocam nas palavras-passe Google; dependem de *refresh tokens* revogáveis cifrados pelo n8n.
- **Conformidade e backups:** o n8n converte a resposta limpa (não anonimizada) em PDF padronizado / Google Sheets e encaminha ao diretório encriptado da psicóloga. Rotinas diárias no **HDD 500 GB** orquestram `pg_dump` + arquivamento de **WAL** para redundância total local.

---

## 5. Checklist de Conformidade (antes de qualquer merge)

- [ ] Contentor novo tem `mem_limit` explícito dentro do orçamento (§1.1)?
- [ ] `postgresql.conf` respeita os limites de `shared_buffers`/`work_mem`/`max_connections` (§1.2)?
- [ ] Bibliotecas pesadas em lazy loading; Uvicorn com 2 workers + uvloop (§1.3)?
- [ ] Tabelas com dados clínicos têm `tenant_id`, RLS ativo e política restritiva (§2.1)?
- [ ] Sessão injeta `SET LOCAL app.current_tenant_id` por transação (§2.1)?
- [ ] Paciente vinculado a responsável legal; TCLE específico; auditoria imutável (§2.2)?
- [ ] Nenhum PII vai ao LLM sem passar pelo túnel de pseudonimização; dicionário nunca persistido (§2.3)?
- [ ] Consultas vetoriais sempre pré-filtradas por `tenant_id` + `paciente_id` (§3.2)?
- [ ] Sem índice vetorial prematuro (§3.1)?
- [ ] Role de app sem privilégio + `FORCE ROW LEVEL SECURITY` nas tabelas clínicas (§2.1.1)?
- [ ] Sem console web de administração; acesso privilegiado só por `psql` via `docker compose exec` (§2.1.1, §4.1)?
- [ ] Segredos fora do código; multi-stage build; webhook n8n autenticado (§4)?

---

*Documento vivo. Alterações às Regras de Ouro exigem revisão explícita e registo da justificativa.*
