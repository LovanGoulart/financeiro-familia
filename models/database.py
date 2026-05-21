#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MODELO DE BANCO DE DADOS - SQLite
Gerencia conexoes e inicializacao do banco de dados SQLite.
Inclui criacao automatica de tabelas e dados de exemplo.
"""

import sqlite3
import os
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash

def get_db_connection(db_path):
    """Cria e retorna uma conexao com o banco de dados."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(db_path):
    """Inicializa o banco de dados criando tabelas e dados padrao."""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    conn = get_db_connection(db_path)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'user' CHECK(role IN ('admin', 'user')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            icon TEXT DEFAULT 'tag',
            color TEXT DEFAULT '#6c757d'
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT NOT NULL,
            amount REAL NOT NULL,
            expense_date DATE NOT NULL,
            category_id INTEGER,
            person_id INTEGER NOT NULL,
            expense_type TEXT DEFAULT 'individual' CHECK(expense_type IN ('individual', 'compartilhado')),
            is_recurring INTEGER DEFAULT 0,
            recurring_frequency TEXT DEFAULT 'mensal',
            next_due_date DATE,
            is_installment INTEGER DEFAULT 0,
            installment_total INTEGER DEFAULT 1,
            installment_number INTEGER DEFAULT 1,
            installment_group_id TEXT,
            notes TEXT,
            created_by INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (category_id) REFERENCES categories(id),
            FOREIGN KEY (person_id) REFERENCES users(id),
            FOREIGN KEY (created_by) REFERENCES users(id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS shopping_list (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            quantity TEXT DEFAULT '1',
            category_id INTEGER,
            notes TEXT,
            is_bought INTEGER DEFAULT 0,
            created_by INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (category_id) REFERENCES categories(id),
            FOREIGN KEY (created_by) REFERENCES users(id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_user INTEGER NOT NULL,
            to_user INTEGER NOT NULL,
            amount REAL NOT NULL,
            reference_month INTEGER,
            reference_year INTEGER,
            status TEXT DEFAULT 'pendente' CHECK(status IN ('pendente', 'pago')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (from_user) REFERENCES users(id),
            FOREIGN KEY (to_user) REFERENCES users(id)
        )
    """)

    conn.commit()

    default_categories = [
        ('Alimentacao', 'utensils', '#e74c3c'),
        ('Mercado', 'shopping-cart', '#f39c12'),
        ('Transporte', 'car', '#3498db'),
        ('Lazer', 'gamepad', '#9b59b6'),
        ('Saude', 'heart-pulse', '#e91e63'),
        ('Moradia', 'home', '#2ecc71'),
        ('Contas', 'file-invoice-dollar', '#1abc9c'),
        ('Assinaturas', 'tv', '#ff9800'),
        ('Cartao', 'credit-card', '#607d8b'),
        ('Investimentos', 'trending-up', '#4caf50'),
        ('Outros', 'more-horizontal', '#95a5a6')
    ]

    for name, icon, color in default_categories:
        conn.execute("INSERT OR IGNORE INTO categories (name, icon, color) VALUES (?, ?, ?)", (name, icon, color))

    conn.commit()

    existing = conn.execute("SELECT id FROM users WHERE username = ?", ('admin',)).fetchone()

    if not existing:
        password_hash = generate_password_hash('admin123')
        conn.execute("INSERT INTO users (username, name, email, password_hash, role) VALUES (?, ?, ?, ?, ?)",
                    ('admin', 'Administrador', 'admin@familia.com', password_hash, 'admin'))

        admin_id = conn.execute("SELECT id FROM users WHERE username = ?", ('admin',)).fetchone()['id']

        now = datetime.now()

        sample_expenses = [
            ('Aluguel', 1200.00, (now - timedelta(days=5)).strftime('%Y-%m-%d'), 6, admin_id, 'compartilhado', 1, 'mensal', None, 0, 1, 1, 'Aluguel mensal'),
            ('Supermercado', 450.75, (now - timedelta(days=3)).strftime('%Y-%m-%d'), 2, admin_id, 'compartilhado', 0, 'mensal', None, 0, 1, 1, 'Compras do mes'),
            ('Internet', 89.90, (now - timedelta(days=10)).strftime('%Y-%m-%d'), 7, admin_id, 'compartilhado', 1, 'mensal', None, 0, 1, 1, 'Fibra optica'),
            ('Academia', 120.00, (now - timedelta(days=15)).strftime('%Y-%m-%d'), 3, admin_id, 'individual', 1, 'mensal', None, 0, 1, 1, 'Mensalidade'),
            ('Notebook', 300.00, (now - timedelta(days=20)).strftime('%Y-%m-%d'), 9, admin_id, 'individual', 0, 'mensal', None, 1, 10, 1, 'Parcela 1/10'),
            ('Cinema', 80.00, (now - timedelta(days=1)).strftime('%Y-%m-%d'), 4, admin_id, 'compartilhado', 0, 'mensal', None, 0, 1, 1, 'Filme fds'),
            ('Farmacia', 45.50, (now - timedelta(days=7)).strftime('%Y-%m-%d'), 5, admin_id, 'individual', 0, 'mensal', None, 0, 1, 1, 'Remedios'),
            ('Gasolina', 200.00, (now - timedelta(days=12)).strftime('%Y-%m-%d'), 3, admin_id, 'individual', 0, 'mensal', None, 0, 1, 1, 'Abastecimento'),
            ('Netflix', 39.90, (now - timedelta(days=25)).strftime('%Y-%m-%d'), 8, admin_id, 'compartilhado', 1, 'mensal', None, 0, 1, 1, 'Streaming'),
            ('Luz', 150.00, (now - timedelta(days=8)).strftime('%Y-%m-%d'), 7, admin_id, 'compartilhado', 1, 'mensal', None, 0, 1, 1, 'Conta de luz'),
        ]

        for desc, amount, date, cat_id, person, exp_type, recurring, freq, next_due, installment, inst_total, inst_num, notes in sample_expenses:
            conn.execute("""INSERT INTO expenses (description, amount, expense_date, category_id, person_id, expense_type, is_recurring, recurring_frequency, next_due_date, is_installment, installment_total, installment_number, notes, created_by) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (desc, amount, date, cat_id, person, exp_type, recurring, freq, next_due, installment, inst_total, inst_num, notes, admin_id))

        sample_items = [
            ('Leite', '2 litros', 2, 'Integral', admin_id),
            ('Pao', '1 pacote', 2, 'Forma', admin_id),
            ('Arroz', '5kg', 2, 'Branco', admin_id),
            ('Shampoo', '1 unidade', 5, 'Anticaspa', admin_id),
        ]

        for name, qty, cat_id, notes, created_by in sample_items:
            conn.execute("INSERT INTO shopping_list (name, quantity, category_id, notes, created_by) VALUES (?, ?, ?, ?, ?)",
                        (name, qty, cat_id, notes, created_by))

        conn.commit()

    conn.close()
    print("Banco de dados inicializado com sucesso!")
