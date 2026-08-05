# Backup do Homarr legado

`backup_legado_manual.sh` executa a Fase A do plano de migração. Ele exige terminal
interativo e privilégios administrativos porque monta o staging gocryptfs, pausa apenas
o container `homarr` e desmonta o staging ao final.

Antes de executar, exporte todo o conteúdo em **Management → Tools → Migrate to 1.0** e
guarde a chave de migração separadamente. Transfira somente o ZIP por SSH/SFTP para um
arquivo privado da conta operadora e aplique modo `0600`. O script aceita esse caminho,
valida o ZIP, copia-o para o staging cifrado com conferência de hash e remove a cópia
temporária do servidor. Preserve o original no armazenamento seguro do computador.

```bash
chmod 600 /caminho/privado/export-homarr.zip
sudo /home/hades/vscode/config/workspace/projeto_agenda/infra/homarr/backup_legado_manual.sh \
  /caminho/privado/export-homarr.zip
```

O script falha antes da pausa se container, saúde, imagem, stack Portainer, socket ou os
três volumes divergirem. Antes de parar o Homarr, preserva ZIP, definição da stack,
inspects efetivos e imagem legada. Durante a pausa, arquiva separadamente os três
volumes. Um trap tenta reiniciar o Homarr e desmontar o staging em qualquer saída.

Se uma falha ocorrer depois que o ZIP for movido para o staging, a próxima execução com
o mesmo caminho já ausente retoma automaticamente uma única execução cifrada incompleta,
sem exigir novo upload. Mais de uma execução incompleta causa recusa para revisão manual.

Depois do retorno saudável, valida ZIP, TARs e checksums, envia o conjunto ao Restic com
a tag `homarr-migracao`, executa `restic check` e remove apenas o diretório temporário
criado dentro do staging. O ZIP, a configuração efetiva e os nomes operacionais nunca
são versionados.
