"""
================================================================================
MODELS - BANCO DE DADOS
================================================================================
Configuracao e inicializacao do banco SQLite.
Tabelas: users, categories, expenses, shopping_list
================================================================================
"""

import sqlite3
import os

def get_db_connection(db_path):
    """Retorna uma conexao com row_factory = sqlite3.Row."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(db_path):
    """Cria as tabelas se nao existirem."""
    # Garantir que o diretorio existe
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    # Tabela de usuarios
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Tabela de categorias - AGORA COM family_email para isolamento por familia
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            icon TEXT DEFAULT 'tag',
            color TEXT DEFAULT '#6c757d',
            family_email TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Tabela de despesas
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT NOT NULL,
            amount REAL NOT NULL,
            expense_date DATE NOT NULL,
            category_id INTEGER,
            person_id INTEGER NOT NULL,
            expense_type TEXT DEFAULT 'individual',
            is_recurring INTEGER DEFAULT 0,
            recurring_frequency TEXT,
            next_due_date DATE,
            is_installment INTEGER DEFAULT 0,
            installment_total INTEGER DEFAULT 1,
            installment_number INTEGER DEFAULT 1,
            installment_group_id TEXT,
            notes TEXT,
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (category_id) REFERENCES categories(id),
            FOREIGN KEY (person_id) REFERENCES users(id),
            FOREIGN KEY (created_by) REFERENCES users(id)
        )
    """)

    # Tabela de lista de compras
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS shopping_list (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            quantity TEXT DEFAULT '1',
            category_id INTEGER,
            notes TEXT,
            is_bought INTEGER DEFAULT 0,
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (category_id) REFERENCES categories(id),
            FOREIGN KEY (created_by) REFERENCES users(id)
        )
    """)

    # NENHUMA CATEGORIA PRE-CADASTRADA - banco vem vazio!

    conn.commit()
    conn.close()
    print("Banco de dados inicializado com sucesso (sem dados pré-cadastrados).")