# 1. Usa um "computador" Linux leve com Python já instalado
FROM python:3.12-slim

# 2. Atualiza o Linux e instala o LaTeX e as fontes Premium (Palatino)
RUN apt-get update && apt-get install -y \
    texlive-latex-base \
    texlive-latex-recommended \
    texlive-fonts-recommended \
    texlive-latex-extra \
    && rm -rf /var/lib/apt/lists/*

# 3. Cria a pasta do nosso projeto lá no servidor
WORKDIR /app

# 4. Copia a lista de compras e instala o Django e outras bibliotecas
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copia todo o nosso código do StatLab para o servidor
COPY . .

# 6. Empacota o design (CSS) e as imagens
RUN python manage.py collectstatic --noinput

# 7. O grande comando final: Roda o banco de dados e liga o site!
CMD python manage.py migrate && gunicorn statlab.wsgi:application --bind 0.0.0.0:$PORT