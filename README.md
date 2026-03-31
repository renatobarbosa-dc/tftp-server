Atividade 003: TFTP - A Missão


Para rodar, abra o seu terminal no diretório do projeto e execute o comando abaixo 

python server.py --port 6969 --directory data --verbose --read-only


# Como rodar e acessar por outras máquinas:    
 - Preparando o Servidor (Onde o Python vai rodar) Crie a pasta storage ao lado dos scripts (onde os arquivos ficarão). 

 -*Importante:* O cliente nativo do Windows só consegue falar na porta 69. O código atualizado já aponta para a porta 69 por padrão. 

 - Por ser uma porta restrita (abaixo de 1024), você precisa rodar o script como Administrador (no Windows) ou usar sudo (no Linux/Mac). 
 
 - Abra o terminal como Administrador e rode:

 ``` python server.py --verbose ```

# 2. Descobrindo o IP do Servidor    
 - No mesmo computador onde o servidor Python está rodando, abra outro terminal e digite ipconfig (Windows) ou ifconfig (Linux/Mac). 
 
 - Anote o IP IPv4 (ex: 192.168.1.50).              
 
# 3. Acessando pelo Cliente (Em OUTRA máquina)
 - Vá para a máquina com o Windows e abra o terminal (CMD).
 
 - Para baixar um arquivo do seu servidor Python:

 ``` tftp -i 192.168.1.50 GET arquivodoservidor.txt ```

 - Para enviar um arquivo para o seu servidor Python:

 ``` tftp -i 192.168.1.50 PUT meuarquivo.txt ```


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
