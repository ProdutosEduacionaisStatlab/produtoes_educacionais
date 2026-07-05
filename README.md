## ⚙️ Primeira Instalação (Setup em um PC novo)

Se você for rodar este projeto pela primeira vez ou configurá-lo em um computador novo, siga este passo a passo do zero:

1. **Clone o repositório e entre na pasta:**
```bash
git clone https://github.com/ProdutosEduacionaisStatlab/produtoes_educacionais.git
cd produtoes_educacionais
```

2. **Crie o ambiente virtual:**

```bash
python -m venv .venv
```

3. **Ative o ambiente virtual:**

```bash
.venv\Scripts\activate
```

*(O terminal deve exibir um `(.venv)` verde no começo da linha).*

4. **Instale as bibliotecas obrigatórias:**

```bash
pip install -r requirements.txt
```

5. **Configure a Chave Secreta da API:**

* Crie um arquivo chamado `.env` na raiz do projeto (na mesma pasta do `manage.py`).
* Cole a sua chave da NVIDIA dentro dele assim:

```text
NVIDIA_API_KEY=nvapi-sua-chave-aqui
```

6. **Prepare o Banco de Dados inicial e crie o Usuário Admin:**

```bash
python manage.py migrate
python manage.py createsuperuser
```

---

## 🚀 Como Rodar o Projeto no Dia a Dia

Se o projeto já está configurado e você quer apenas ligar o sistema para programar ou testar:

1. **Ative o Ambiente Virtual:**

```bash
.venv\Scripts\activate
```

2. **Ligue o Servidor:**

```bash
python manage.py runserver
```

3. **Acesse o Sistema no Navegador (localmente):**

* **Página Inicial (Gerador):** http://127.0.0.1:8000/
* **Painel do Professor (Admin):** http://127.0.0.1:8000/admin/
---

## 🛠️ Comandos Úteis (Manutenção)

* **Atualizar o Banco de Dados (Use sempre que modificar o arquivo `models.py`):**

```bash
python manage.py makemigrations
python manage.py migrate
```

* **Criar um usuário administrador extra:**

```bash
python manage.py createsuperuser
```