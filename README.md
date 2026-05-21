# Sistema de Controle Financeiro Familiar

Sistema web/mobile responsivo completo para controle financeiro individual, de casal e familiar.

## Tecnologias

- **Backend:** Python + Flask
- **Frontend:** HTML5 + CSS3 + JavaScript
- **Banco de Dados:** SQLite
- **Graficos:** Chart.js
- **Arquitetura:** MVC

## Funcionalidades

- Controle de despesas compartilhadas e individuais
- Despesas fixas mensais com recorrencia automatica
- Compras parceladas com acompanhamento
- Lista de compras compartilhada
- Relatorios financeiros (mensal, anual, por categoria, por pessoa)
- Divisao automatica de gastos entre membros da familia
- Dashboard completo com graficos
- Multiusuario por familia (mesmo email = mesma familia)
- Isolamento completo de dados por familia
- Autenticacao segura com hash de senha
- Modo escuro/claro
- Interface responsiva mobile-first

## Instalacao Local

```bash
# 1. Clone ou extraia o projeto
cd financeiro_familia

# 2. Crie um ambiente virtual (recomendado)
python -m venv venv

# 3. Ative o ambiente virtual
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 4. Instale as dependencias
pip install -r requirements.txt

# 5. Execute a aplicacao
python app.py
```

Acesse: http://localhost:5000

## Deploy

### Render
1. Crie um novo Web Service
2. Conecte seu repositorio
3. Build Command: `pip install -r requirements.txt`
4. Start Command: `python app.py`
5. Adicione variavel de ambiente `SECRET_KEY`

### Railway
1. Crie um novo projeto
2. Deploy a partir do repositorio
3. Adicione variavel de ambiente `SECRET_KEY`

### PythonAnywhere
1. Upload dos arquivos
2. Crie um virtualenv
3. Instale dependencias
4. Configure WSGI apontando para app.py

### VPS Linux
```bash
# Instale Python e pip
sudo apt update && sudo apt install python3 python3-pip

# Clone o projeto
git clone <repo>
cd financeiro_familia

# Instale dependencias
pip3 install -r requirements.txt

# Execute com Gunicorn (producao)
pip3 install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

## Usuario Padrao

- **Username:** admin
- **Senha:** admin123
- **Email:** admin@familia.com

## Estrutura do Projeto

```
financeiro_familia/
|-- app.py                 # Aplicacao principal
|-- requirements.txt       # Dependencias
|-- README.md             # Documentacao
|-- database/
|   |-- finance.db        # Banco de dados SQLite
|-- models/
|   |-- __init__.py
|   |-- database.py       # Conexao e inicializacao do DB
|   |-- user.py           # Modelo de usuario
|   |-- expense.py        # Modelo de despesa
|   |-- category.py       # Modelo de categoria
|   |-- shopping_item.py  # Modelo de item de compra
|-- routes/
|   |-- __init__.py
|-- templates/            # Templates HTML
|-- static/
|   |-- css/             # Estilos
|   |-- js/              # Scripts
|   |-- img/             # Imagens
```

## Licenca

MIT License
