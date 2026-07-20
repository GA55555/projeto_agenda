"""Modulo de dashboard: resumo agregado para a visao geral da SPA (Fase 7c).

Somente leitura, sem tabela/model/migration. Todas as agregacoes correm sob a
sessao com RLS (`get_tenant_session`, §2.1) -> os contadores ja saem escopados
ao tenant (psicologa) ativo, sem `WHERE tenant_id` explicito na app.

Regras de ouro: §2.1
Fase do roadmap: Fase 7c
"""
