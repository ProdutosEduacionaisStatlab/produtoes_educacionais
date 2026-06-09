=========================================================
GUIA DE ACESSO E MANUTENÇÃO - SERVIDOR STATLAB
=========================================================

--- COMO ACESSAR O SERVIDOR ---

1. ABRIR O TERMINAL:
No seu Windows, clique no menu Iniciar, digite "PowerShell" e pressione Enter.

2. CONECTAR AO SERVIDOR (Comando SSH):
Copie, cole o comando abaixo no PowerShell e pressione Enter:

ssh -i "C:\Users\Eduardo\Downloads\ssh-key-2026-05-21 (3).key" ubuntu@163.176.51.10

* Nota: Se na primeira vez ele fizer uma pergunta em inglês sobre "authenticity of host", digite a palavra yes e dê Enter.

3. ENTRAR NA PASTA DO PROJETO:
Assim que o terminal mostrar "ubuntu@statlab-server...", digite o comando abaixo e dê Enter:

cd statlab


--- COMANDOS ESSENCIAIS DE MANUTENÇÃO ---

Sempre certifique-se de estar dentro da pasta do projeto (cd statlab) antes de usar os comandos abaixo.

* PUXAR CÓDIGO NOVO DO GITHUB:
git pull origin main

* REINICIAR O SITE RÁPIDO (Se mudou apenas o Python):
sudo docker compose restart

* RECONSTRUIR O SERVIDOR (Se instalou bibliotecas novas ou mexeu no .env):
sudo docker compose up -d --build

* VERIFICAR SE O SITE ESTÁ LIGADO (Status deve ser "Up"):
sudo docker ps

* VER OS ERROS DO SITE (Se ele cair):
sudo docker logs statlab-web-1