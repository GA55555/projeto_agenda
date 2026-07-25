# Backup coordenado — Fase 8a

Estes arquivos automatizam o procedimento de contingência descrito em
`docs/arquitetura_manutenção.md`, mas não devem ser habilitados antes de o primeiro
restore isolado ser ensaiado. O script nunca cria staging em ext4 comum: ele exige que
`BACKUP_STAGE_ROOT` seja um ponto de montagem dedicado e que o responsável confirme que
esse ponto é cifrado.

## Preparação controlada no servidor

1. Como o HDD é compartilhado com todo o servidor, criar e montar um staging cifrado
   **por diretório** nele (preferência: gocryptfs). Não reparticionar, reformatar ou
   aplicar LUKS ao disco inteiro. Registrar a escolha no inventário restrito; não
   registrar senha ou chave no Git.
2. Criar `/etc/agenda-backup/` com permissões `0700` e dois arquivos privados com
   permissões `0600`: `agenda-backup.env` e `restic-repository`. No modo manual, não
   criar `restic-password` no servidor.
3. Inicializar o repositório Restic somente após guardar a senha em cofre externo e
   confirmar o procedimento de recuperação com substituto.
4. Garantir que a imagem configurada em `BACKUP_TAR_IMAGE` já está disponível no host.
   O script falha antes de parar a aplicação se ela não estiver.
5. Uma única vez, executar `sudo bash infra/backup/configurar_manual.sh`. O arquivo
   gerado contém apenas caminhos e opções, nunca senhas.
6. Em cada janela, executar `sudo bash infra/backup/executar_manual.sh`. O wrapper pede
   a senha gocryptfs, monta o staging, chama o backup (que pede a senha Restic) e desmonta
   mesmo em caso de falha. Revisar o snapshot e `restic check`; depois restaurar em
   host/VM isolado.

Não há unidade nem timer systemd neste modo. A execução exige terminal interativo e duas
senhas informadas durante a janela. O wrapper desmonta o staging ao final, inclusive em
falha; se a desmontagem falhar, encerra com erro crítico visível.

## Garantias e limites

- Pausa somente frontend e backend; PostgreSQL permanece ativo para `pg_dump -Fc`.
  Assim banco e `documentos_data` ficam no mesmo ponto lógico de escrita.
- Gera dump, globals, tar documental, checksums, commit, migration e versão do
  PostgreSQL. Gera também `git archive` e `git bundle` do commit implantado, permitindo
  recuperar a fonte mesmo sem acesso ao GitHub. Recusa árvore Git com alterações locais.
  Valida dump/tar/bundle/checksums antes do upload ao Restic.
- Faz upload também de `.env`, `docker-compose.yml` e `postgresql.conf`, sempre para o
  repositório Restic cifrado. Não registra corpo clínico em log.
- Usa lock, timeout e reinício por `trap`, inclusive se alguma etapa falhar.
- Só conclui depois que backend e frontend voltarem ao estado `healthy`; timeout ou
  falha preserva o estágio cifrado para investigação, sem limpeza automática.
- Não executa `forget`, `prune`, WAL/PITR nem configura alertas. Retenção requer uma
  credencial administrativa separada e revisão humana; WAL/PITR só entra após base
  backup, cadeia WAL, alerta de espaço e restore comprovados.

O snapshot Restic, checksum e `pg_restore --list` não substituem o restore isolado. O
backup somente será considerado comprovado depois desse ensaio.

No modo manual, a senha do Restic é digitada uma vez por execução, fica somente no
ambiente do processo durante aquela sessão e é removida no encerramento. O operador
também desmonta o gocryptfs após confirmar o snapshot; assim o servidor não conserva uma
credencial reutilizável nem um staging clínico acessível fora da janela.

## Imagens Docker aprovadas

Depois de um deploy validado, executar `executar_manual.sh imagens` uma vez. Ele exporta
as imagens que estão de fato nos containers PostgreSQL, backend e frontend, criando um
snapshot `agenda-imagens` ligado ao commit atual. Não entra no backup rotineiro: o Restic
deduplica conteúdo, mas o `docker image save` ainda consome disco e I/O relevantes no
AMD A6. Na recuperação, validar o checksum e usar `docker image load` antes de subir o
Compose.

Para preservar as imagens pelo mesmo ciclo manual de montagem/desmontagem, usar:

```bash
sudo bash infra/backup/executar_manual.sh imagens
```
