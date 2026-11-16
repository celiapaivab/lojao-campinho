#!/usr/bin/env bash
# Comandos executados pelo Render a cada deploy (Build Command: ./build.sh).

# Para o build no primeiro erro.
set -o errexit

# 1. Instala as dependências do projeto.
pip install -r requirements.txt

# 2. Junta os arquivos estáticos (CSS) na pasta staticfiles/.
python manage.py collectstatic --no-input

# 3. Cria ou atualiza as tabelas do banco de dados (PostgreSQL).
python manage.py migrate

# 4. Cria a conta do dono da loja, se as variáveis DJANGO_SUPERUSER_* existirem.
#    Se a conta já existir (deploys seguintes), apenas mostra um aviso.
if [ -n "$DJANGO_SUPERUSER_USERNAME" ]; then
    python manage.py createsuperuser --no-input \
        || echo "Aviso: superusuário não criado (talvez ele já exista)."
fi
