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
 
## Estrutura do Projeto

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
