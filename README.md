# Lojão do Campinho

Aplicação web simples para controle de estoque de uma pequena papelaria
(loja de material escolar). O objetivo é substituir o controle manual de
estoque por um sistema fácil de usar.

Projeto individual da disciplina de Desenvolvimento de Software.

## Tecnologias

- Python 3.12
- Django 5.2 LTS
- SQLite (banco de dados padrão do Django)
- Django Templates, HTML5 e CSS3
- Arquitetura monolítica no padrão MVT (Model-View-Template) do Django

## Estrutura do projeto

```
lojao-do-campinho/
├── lojao_campinho/   # Configurações do projeto (settings.py, urls.py)
├── estoque/          # App responsável pelo controle de estoque
├── manage.py         # Utilitário de linha de comando do Django
└── requirements.txt  # Dependências do projeto
```

## Como rodar o projeto localmente

Os comandos abaixo devem ser executados no terminal, dentro da pasta do projeto.

### 1. Criar o ambiente virtual (apenas na primeira vez)

```bash
python3.12 -m venv .venv
```

### 2. Ativar o ambiente virtual

No macOS ou Linux:

```bash
source .venv/bin/activate
```

No Windows:

```bash
.venv\Scripts\activate
```

Com o ambiente ativo, o nome `(.venv)` aparece no início da linha do terminal.

### 3. Instalar as dependências

```bash
pip install -r requirements.txt
```

### 4. Criar o banco de dados

```bash
python manage.py migrate
```

### 5. Iniciar o servidor de desenvolvimento

```bash
python manage.py runserver
```

Depois, acesse <http://127.0.0.1:8000/> no navegador.
Para parar o servidor, pressione `Ctrl + C` no terminal.

## Observação sobre a chave secreta

A `SECRET_KEY` presente em `settings.py` serve apenas para desenvolvimento local.
Em qualquer outro ambiente, defina a variável de ambiente `DJANGO_SECRET_KEY`.
