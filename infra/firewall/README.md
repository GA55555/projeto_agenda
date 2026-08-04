# Firewall das publicações Docker

Este controle bloqueia conexões TCP recebidas pela interface física da LAN para as
portas administrativas publicadas `5432`, `8000`, `8080`, `8081`, `8443` e `9443`.
Loopback, a interface Tailscale e tráfego interno entre contêineres não são afetados.

O filtro é aplicado em IPv4 e IPv6 por duas chains especializadas. `AGENDA-LAN-INPUT`
usa a porta publicada atual para cobrir listeners locais e o proxy IPv6 do Docker.
`AGENDA-LAN-DOCKER`, ligada a `DOCKER-USER`, usa a porta de destino original do
conntrack porque algumas publicações fazem DNAT para outra porta no contêiner, como
`8080 -> 7575` e `8081 -> 80`.

O serviço espera UFW e Docker iniciarem antes de inserir sua chain. `PartOf=docker.service`
faz a regra acompanhar reinícios do daemon Docker. O serviço `nftables.service` deve
continuar desativado enquanto `/etc/nftables.conf` contiver `flush ruleset`.

## Instalação

No diretório raiz do projeto:

```bash
sudo bash infra/firewall/instalar.sh
```

O instalador primeiro valida, sem aplicar, a sintaxe das regras contra os backends
ativos de `iptables` e `ip6tables`. Se qualquer família falhar, o serviço não é ativado.

A interface padrão é `enp2s0`. Para outra interface, crie um override do systemd que
defina `Environment=AGENDA_LAN_INTERFACE=...` antes de iniciar o serviço.

## Verificação

```bash
sudo systemctl status agenda-docker-firewall.service
sudo iptables -S AGENDA-LAN-INPUT
sudo iptables -S AGENDA-LAN-DOCKER
sudo ip6tables -S AGENDA-LAN-INPUT
sudo ip6tables -S AGENDA-LAN-DOCKER
```

Depois, testar as seis portas a partir de outra máquina na LAN, em IPv4 e IPv6, e
confirmar que os acessos administrativos pela Tailscale continuam funcionando.

## Reaplicação e rollback

Reaplicar após uma alteração manual de UFW:

```bash
sudo systemctl reload agenda-docker-firewall.service
```

Remover somente as regras administradas por este controle:

```bash
sudo systemctl disable --now agenda-docker-firewall.service
```
