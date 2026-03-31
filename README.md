Atividade 003: TFTP - A Missão


Para rodar, abra o seu terminal no diretório do projeto e execute o comando abaixo 

python server.py --port 6969 --directory data --verbose --read-only


# 🛠️ Configuração: SolarWinds TFTP Server
Guia rápido para instalação e provisionamento do serviço de transferência de arquivos (TFTP) em ambiente Windows.

## 📥 1. Instalação
Download: Obtenha o instalador oficial via SolarWinds Portal.

Setup: Execute o assistente e siga o fluxo padrão (Next > Install).

## ⚙️ 2. Provisionamento do Serviço
Para configurar o diretório raiz e o status do daemon:

Acesse o menu File > Configure.

Na aba General, localize a seção Storage.

Defina o Path do diretório raiz (Ex: C:\TFTP-Root).

Certifique-se de que o status esteja como Started. Caso contrário, clique em Start.

## 🛡️ 3. Regra de Firewall (PowerShell)
O protocolo TFTP utiliza a porta 69/UDP. Para liberar o tráfego de entrada, execute o comando abaixo como Administrador:

```
# Liberação da porta 69/UDP para o serviço TFTP
New-NetFirewallRule -DisplayName "SolarWinds TFTP Server (UDP 69)" `
    -Direction Inbound `
    -LocalPort 69 `
    -Protocol UDP `
    -Action Allow `
    -Description "Permite tráfego inbound para transferência de firmware e configs."
    
```
