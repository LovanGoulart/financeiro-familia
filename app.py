#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
SISTEMA DE CONTROLE FINANCEIRO FAMILIAR
================================================================================
Aplicacao Flask completa para gestao financeira individual, de casal e familiar.

Arquitetura: MVC
Tecnologias: Python, Flask, SQLite, HTML5, CSS3, JavaScript, Chart.js
================================================================================
"""

import os
import secrets
from datetime import datetime, timedelta
from functools import wraps
from calendar import monthrange

from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, abort
from werkzeug.security import generate_password_hash, check_password_hash

from models.database import init_db, get_db_connection

# ==============================================================================
# CONFIGURACAO DA APLICACAO
# ==============================================================================
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(32))
app.config['DATABASE'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database', 'finance.db')
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)

# Inicializar banco de dados
init_db(app.config['DATABASE'])

# ==============================================================================
# DECORADORES DE AUTENTICACAO E AUTORIZACAO
# ==============================================================================

def login_required(f):
    """Decorador que exige login para acessar a rota."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Por favor, faca login para acessar esta pagina.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def family_context(f):
    """Decorador que carrega o contexto da familia (email) do usuario logado."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))

        conn = get_db_connection(app.config['DATABASE'])
        user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        conn.close()

        if not user:
            session.clear()
            flash('Usuario nao encontrado.', 'danger')
            return redirect(url_for('login'))

        kwargs['current_user'] = dict(user)
        kwargs['family_email'] = user['email']
        kwargs['is_admin'] = user['role'] == 'admin'

        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorador que exige papel de administrador."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))

        conn = get_db_connection(app.config['DATABASE'])
        user = conn.execute('SELECT role FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        conn.close()

        if not user or user['role'] != 'admin':
            flash('Acesso negado. Apenas administradores.', 'danger')
            return redirect(url_for('dashboard'))

        return f(*args, **kwargs)
    return decorated_function

# ==============================================================================
# FUNCOES AUXILIARES
# ==============================================================================

def get_family_members(family_email):
    """Retorna todos os membros da familia (mesmo email)."""
    conn = get_db_connection(app.config['DATABASE'])
    members = conn.execute(
        'SELECT id, username, name, role FROM users WHERE email = ? ORDER BY created_at',
        (family_email,)
    ).fetchall()
    conn.close()
    return [dict(m) for m in members]

def get_family_member_ids(family_email):
    """Retorna IDs de todos os membros da familia."""
    members = get_family_members(family_email)
    return [m['id'] for m in members]

def get_month_range(year=None, month=None):
    """Retorna o primeiro e ultimo dia do mes especificado."""
    now = datetime.now()
    year = year or now.year
    month = month or now.month

    first_day = datetime(year, month, 1)
    if month == 12:
        last_day = datetime(year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = datetime(year, month + 1, 1) - timedelta(days=1)

    return first_day.strftime('%Y-%m-%d'), last_day.strftime('%Y-%m-%d')

def get_last_day_of_month(year, month):
    """Retorna o ultimo dia do mes."""
    return monthrange(year, month)[1]

def generate_recurring_expenses(conn, member_ids, target_year, target_month):
    """
    Gera registros virtuais de despesas recorrentes para o mes alvo.
    Retorna lista de dicionarios com as despesas materializadas.
    """
    first_day, last_day = get_month_range(target_year, target_month)
    target_date = datetime(target_year, target_month, 1)

    # Buscar todas as despesas recorrentes ativas dos membros da familia
    query = "SELECT e.*, u.name as person_name, c.name as category_name, c.color as category_color FROM expenses e JOIN users u ON e.person_id = u.id LEFT JOIN categories c ON e.category_id = c.id WHERE e.person_id IN ({}) AND e.is_recurring = 1 AND e.expense_date <= ? ORDER BY e.expense_date".format(','.join('?' * len(member_ids)))
    recurring = conn.execute(query, (*member_ids, last_day)).fetchall()

    generated = []
    for exp in recurring:
        exp_date = datetime.strptime(exp['expense_date'], '%Y-%m-%d')
        freq = exp['recurring_frequency']

        # Verificar se esta despesa deve aparecer no mes alvo
        should_show = False

        if freq == 'mensal':
            # Aparece todo mes a partir da data inicial
            should_show = (target_date.year > exp_date.year or 
                          (target_date.year == exp_date.year and target_date.month >= exp_date.month))
        elif freq == 'semanal':
            # Calcula semanas entre a data inicial e o mes alvo
            days_diff = (target_date - exp_date).days
            weeks_diff = days_diff // 7
            should_show = weeks_diff >= 0 and days_diff >= 0
        elif freq == 'anual':
            # Aparece no mesmo mes todo ano a partir do ano inicial
            should_show = (target_date.year > exp_date.year or 
                          (target_date.year == exp_date.year and target_date.month >= exp_date.month))
            # Verifica se eh o mes correto para anual
            if should_show:
                should_show = (target_date.month == exp_date.month)

        if should_show:
            # Ajusta a data para o mes alvo
            day = min(exp_date.day, get_last_day_of_month(target_year, target_month))
            adjusted_date = datetime(target_year, target_month, day).strftime('%Y-%m-%d')

            generated.append({
                'id': "rec_{}_{}{:02d}".format(exp['id'], target_year, target_month),
                'original_id': exp['id'],
                'description': exp['description'],
                'amount': exp['amount'],
                'expense_date': adjusted_date,
                'category_id': exp['category_id'],
                'person_id': exp['person_id'],
                'person_name': exp['person_name'],
                'category_name': exp['category_name'],
                'category_color': exp['category_color'],
                'expense_type': exp['expense_type'],
                'is_recurring': 1,
                'recurring_frequency': freq,
                'is_installment': 0,
                'installment_total': 1,
                'installment_number': 1,
                'installment_group_id': None,
                'notes': exp['notes'],
                'created_by': exp['created_by'],
                'created_at': exp['created_at'],
                'is_generated': True,
                'generation_type': 'recorrente'
            })

    return generated

def generate_installment_expenses(conn, member_ids, target_year, target_month):
    """
    Gera registros virtuais de parcelamentos para o mes alvo.
    Retorna lista de dicionarios com as parcelas materializadas.
    """
    first_day, last_day = get_month_range(target_year, target_month)
    target_date = datetime(target_year, target_month, 1)

    # Buscar todas as despesas parceladas dos membros da familia
    query = "SELECT e.*, u.name as person_name, c.name as category_name, c.color as category_color FROM expenses e JOIN users u ON e.person_id = u.id LEFT JOIN categories c ON e.category_id = c.id WHERE e.person_id IN ({}) AND e.is_installment = 1 ORDER BY e.expense_date".format(','.join('?' * len(member_ids)))
    installments = conn.execute(query, tuple(member_ids)).fetchall()

    generated = []
    for exp in installments:
        exp_date = datetime.strptime(exp['expense_date'], '%Y-%m-%d')
        total_installments = exp['installment_total']

        # Calcular em quais meses esta parcela deve aparecer
        for i in range(total_installments):
            # Calcula o mes desta parcela
            month_offset = i
            installment_month = exp_date.month + month_offset
            installment_year = exp_date.year + (installment_month - 1) // 12
            installment_month = ((installment_month - 1) % 12) + 1

            # Verifica se esta parcela cai no mes alvo
            if installment_year == target_year and installment_month == target_month:
                day = min(exp_date.day, get_last_day_of_month(target_year, target_month))
                adjusted_date = datetime(target_year, target_month, day).strftime('%Y-%m-%d')

                generated.append({
                    'id': "inst_{}_{}".format(exp['id'], i+1),
                    'original_id': exp['id'],
                    'description': "{} ({}/{})".format(exp['description'], i+1, total_installments),
                    'amount': exp['amount'],
                    'expense_date': adjusted_date,
                    'category_id': exp['category_id'],
                    'person_id': exp['person_id'],
                    'person_name': exp['person_name'],
                    'category_name': exp['category_name'],
                    'category_color': exp['category_color'],
                    'expense_type': exp['expense_type'],
                    'is_recurring': 0,
                    'recurring_frequency': None,
                    'is_installment': 1,
                    'installment_total': total_installments,
                    'installment_number': i + 1,
                    'installment_group_id': exp['installment_group_id'],
                    'notes': exp['notes'],
                    'created_by': exp['created_by'],
                    'created_at': exp['created_at'],
                    'is_generated': True,
                    'generation_type': 'parcela'
                })

    return generated

def get_all_expenses_for_month(conn, member_ids, year, month, include_regular=True):
    """
    Retorna TODAS as despesas para o mes especificado:
    - Despesas regulares (nao recorrentes, nao parceladas) do mes
    - Despesas recorrentes materializadas para o mes
    - Parcelas materializadas para o mes
    """
    first_day, last_day = get_month_range(year, month)
    all_expenses = []

    # 1. Despesas regulares do mes (nao recorrentes e nao parceladas)
    if include_regular:
        query = "SELECT e.*, u.name as person_name, c.name as category_name, c.color as category_color FROM expenses e JOIN users u ON e.person_id = u.id LEFT JOIN categories c ON e.category_id = c.id WHERE e.person_id IN ({}) AND e.expense_date BETWEEN ? AND ? AND e.is_recurring = 0 AND e.is_installment = 0 ORDER BY e.expense_date DESC".format(','.join('?' * len(member_ids)))
        regular = conn.execute(query, (*member_ids, first_day, last_day)).fetchall()

        for r in regular:
            item = dict(r)
            item['is_generated'] = False
            all_expenses.append(item)

    # 2. Despesas recorrentes materializadas
    recurring_generated = generate_recurring_expenses(conn, member_ids, year, month)
    all_expenses.extend(recurring_generated)

    # 3. Parcelas materializadas
    installment_generated = generate_installment_expenses(conn, member_ids, year, month)
    all_expenses.extend(installment_generated)

    # Ordenar por data
    all_expenses.sort(key=lambda x: x['expense_date'], reverse=True)

    return all_expenses

def get_expense_totals_for_month(conn, member_ids, year, month):
    """Retorna totais calculados para o mes, incluindo recorrentes e parcelas."""
    expenses = get_all_expenses_for_month(conn, member_ids, year, month, include_regular=True)

    total = sum(e['amount'] for e in expenses)
    shared = sum(e['amount'] for e in expenses if e['expense_type'] == 'compartilhado')
    individual = sum(e['amount'] for e in expenses if e['expense_type'] == 'individual')
    fixed = sum(e['amount'] for e in expenses if e['is_recurring'] == 1 or e.get('generation_type') == 'recorrente')
    installments = sum(e['amount'] for e in expenses if e['is_installment'] == 1 or e.get('generation_type') == 'parcela')

    return {
        'total': total,
        'shared': shared,
        'individual': individual,
        'fixed': fixed,
        'installments': installments,
        'expenses': expenses
    }

# ==============================================================================
# ROTAS DE AUTENTICACAO
# ==============================================================================

@app.route('/')
def index():
    """Pagina inicial - redireciona para login ou dashboard."""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Pagina de login."""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            flash('Preencha todos os campos.', 'warning')
            return render_template('login.html')

        conn = get_db_connection(app.config['DATABASE'])
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()

        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['name'] = user['name']
            session['email'] = user['email']
            session.permanent = True
            flash('Bem-vindo, {}!'.format(user['name']), 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Usuario ou senha incorretos.', 'danger')

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Pagina de cadastro multiusuario."""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        family_email = request.form.get('family_email', '').strip().lower()
        user_count = int(request.form.get('user_count', 1))

        if not family_email or user_count < 1 or user_count > 10:
            flash('Dados invalidos.', 'danger')
            return render_template('register.html')

        conn = get_db_connection(app.config['DATABASE'])
        existing = conn.execute('SELECT id FROM users WHERE email = ?', (family_email,)).fetchone()

        if existing:
            conn.close()
            flash('Este email ja esta cadastrado. Faca login ou use outro email.', 'warning')
            return render_template('register.html')

        created_users = []
        for i in range(1, user_count + 1):
            name = request.form.get('name_{}'.format(i), '').strip()
            username = request.form.get('username_{}'.format(i), '').strip().lower()
            password = request.form.get('password_{}'.format(i), '')

            if not name or not username or not password:
                conn.close()
                flash('Preencha todos os dados do Usuario {}.'.format(i), 'warning')
                return render_template('register.html')

            if len(password) < 6:
                conn.close()
                flash('Senha do Usuario {} deve ter no minimo 6 caracteres.'.format(i), 'warning')
                return render_template('register.html')

            existing_user = conn.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()
            if existing_user:
                conn.close()
                flash('Username "{}" ja esta em uso. Escolha outro.'.format(username), 'warning')
                return render_template('register.html')

            role = 'admin' if i == 1 else 'user'
            password_hash = generate_password_hash(password)

            conn.execute('INSERT INTO users (username, name, email, password_hash, role) VALUES (?, ?, ?, ?, ?)',
                        (username, name, family_email, password_hash, role))
            created_users.append(name)

        conn.commit()
        conn.close()

        flash('Familia cadastrada com sucesso! Usuarios criados: {}'.format(', '.join(created_users)), 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/logout')
def logout():
    """Realiza logout do usuario."""
    session.clear()
    flash('Voce saiu do sistema.', 'info')
    return redirect(url_for('login'))

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Recuperacao simples de senha."""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()

        conn = get_db_connection(app.config['DATABASE'])
        user = conn.execute('SELECT name, email FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()

        if user:
            flash('Usuario encontrado: {} (Email: {}). Entre em contato com o administrador da familia para redefinir a senha.'.format(user['name'], user['email']), 'info')
        else:
            flash('Usuario nao encontrado.', 'danger')

    return render_template('forgot_password.html')

# ==============================================================================
# ROTAS DO DASHBOARD
# ==============================================================================

@app.route('/dashboard')
@login_required
@family_context
def dashboard(current_user, family_email, is_admin):
    """Dashboard principal com visao geral financeira."""
    conn = get_db_connection(app.config['DATABASE'])

    family_members = get_family_members(family_email)
    member_ids = get_family_member_ids(family_email)
    member_count = len(family_members)

    current_year = datetime.now().year
    current_month = datetime.now().month

    # TOTAIS DO MES ATUAL (com recorrentes e parcelas materializadas)
    month_totals = get_expense_totals_for_month(conn, member_ids, current_year, current_month)
    total_month = month_totals['total']
    shared_month = month_totals['shared']
    individual_month = month_totals['individual']
    fixed_month = month_totals['fixed']
    installments_month = month_totals['installments']

    # TOTAL POR PESSOA
    person_totals = []
    for member in family_members:
        member_expenses = [e for e in month_totals['expenses'] if e['person_id'] == member['id']]
        member_total = sum(e['amount'] for e in member_expenses)
        member_shared = sum(e['amount'] for e in member_expenses if e['expense_type'] == 'compartilhado')

        person_totals.append({
            'id': member['id'],
            'name': member['name'],
            'total': member_total,
            'shared': member_shared,
            'role': member['role']
        })

    # DIVISAO AUTOMATICA
    division = None
    if member_count > 1 and shared_month > 0:
        ideal_per_person = shared_month / member_count
        division = []
        for member in family_members:
            member_shared = next((p['shared'] for p in person_totals if p['id'] == member['id']), 0)
            difference = member_shared - ideal_per_person
            division.append({
                'id': member['id'],
                'name': member['name'],
                'paid': member_shared,
                'ideal': ideal_per_person,
                'difference': difference,
                'owes': difference < 0,
                'receives': difference > 0,
                'amount': abs(difference)
            })

    # PROXIMAS PARCELAS (somente do proximo mes)
    next_installments = []

    # calcula o proximo mes
    if current_month == 12:
        next_month = 1
        next_year = current_year + 1
    else:
        next_month = current_month + 1
        next_year = current_year

       # PARCELAS do proximo mes
    next_installments = generate_installment_expenses(
        conn,
        member_ids,
        next_year,
        next_month
    )

    # DESPESAS FIXAS do proximo mes
    next_fixed = generate_recurring_expenses(
        conn,
        member_ids,
        next_year,
        next_month
    )

    # junta parcelas + fixas
    next_installments.extend(next_fixed)

    # ordena por data
    next_installments = sorted(
        next_installments,
        key=lambda x: x['expense_date']
    )

    # ULTIMAS MOVIMENTACOES (apenas despesas reais, nao geradas)
    query = "SELECT e.*, u.name as person_name, c.name as category_name, c.color as category_color FROM expenses e JOIN users u ON e.person_id = u.id LEFT JOIN categories c ON e.category_id = c.id WHERE e.person_id IN ({}) ORDER BY e.created_at DESC LIMIT 10".format(','.join('?' * len(member_ids)))

    # ULTIMAS MOVIMENTACOES (apenas despesas reais, nao geradas)
    query = "SELECT e.*, u.name as person_name, c.name as category_name, c.color as category_color FROM expenses e JOIN users u ON e.person_id = u.id LEFT JOIN categories c ON e.category_id = c.id WHERE e.person_id IN ({}) ORDER BY e.created_at DESC LIMIT 10".format(','.join('?' * len(member_ids)))
    recent_expenses = conn.execute(query, tuple(member_ids)).fetchall()

    # DADOS PARA GRAFICOS - CATEGORIAS
    category_totals = {}
    for e in month_totals['expenses']:
        cat_name = e.get('category_name') or 'Sem Categoria'
        cat_color = e.get('category_color') or '#6c757d'
        if cat_name not in category_totals:
            category_totals[cat_name] = {'name': cat_name, 'color': cat_color, 'total': 0}
        category_totals[cat_name]['total'] += e['amount']

    category_data = sorted(category_totals.values(), key=lambda x: x['total'], reverse=True)
    category_data = [c for c in category_data if c['total'] > 0]

    # DADOS PARA GRAFICOS - MENSAL (ultimos 6 meses)
    monthly_data = []
    for i in range(5, -1, -1):
        month_date = datetime.now() - timedelta(days=i*30)
        m_year = month_date.year
        m_month = month_date.month

        m_totals = get_expense_totals_for_month(conn, member_ids, m_year, m_month)
        monthly_data.append({'month': month_date.strftime('%b/%Y'), 'total': m_totals['total']})

    # LISTA DE COMPRAS
    query = "SELECT s.*, c.name as category_name, c.color as category_color FROM shopping_list s LEFT JOIN categories c ON s.category_id = c.id WHERE s.created_by IN ({}) ORDER BY s.is_bought, s.created_at DESC".format(','.join('?' * len(member_ids)))
    shopping_items = conn.execute(query, tuple(member_ids)).fetchall()

    conn.close()

    return render_template('dashboard.html',
        current_user=current_user,
        is_admin=is_admin,
        family_members=family_members,
        member_count=member_count,
        total_month=total_month,
        shared_month=shared_month,
        individual_month=individual_month,
        fixed_month=fixed_month,
        installments_month=installments_month,
        person_totals=person_totals,
        division=division,
        next_installments=next_installments,
        recent_expenses=[dict(e) for e in recent_expenses],
        category_data=category_data,
        monthly_data=monthly_data,
        shopping_items=[dict(s) for s in shopping_items],
        current_month=current_month,
        current_year=current_year
    )

# ==============================================================================
# ROTAS DE DESPESAS
# ==============================================================================

@app.route('/expenses')
@login_required
@family_context
def expenses(current_user, family_email, is_admin):
    """Lista todas as despesas da familia para o mes selecionado."""
    
    conn = get_db_connection(app.config['DATABASE'])
    member_ids = get_family_member_ids(family_email)

    filter_type = request.args.get('type', '')
    filter_category = request.args.get('category', '')
    filter_person = request.args.get('person', '')
    filter_month = request.args.get('month', datetime.now().strftime('%Y-%m'))

    year, month = map(int, filter_month.split('-'))

    # Buscar todas as despesas
    all_expenses = get_all_expenses_for_month(
        conn,
        member_ids,
        year,
        month,
        include_regular=True
    )

    # =========================
    # FILTROS
    # =========================
    if filter_type:
        all_expenses = [
            e for e in all_expenses
            if e['expense_type'] == filter_type
        ]

    if filter_category:
        all_expenses = [
            e for e in all_expenses
            if str(e.get('category_id')) == filter_category
        ]

    if filter_person:
        all_expenses = [
            e for e in all_expenses
            if str(e['person_id']) == filter_person
        ]

    # =========================
    # AJUSTE DOS IDS VIRTUAIS
    # =========================
    for expense in all_expenses:

        # despesas reais
        if not expense.get('is_generated'):
            expense['can_edit'] = True
            expense['edit_id'] = expense['id']
            expense['can_delete'] = True
            expense['delete_id'] = expense['id']

        # despesas virtuais (recorrentes/parcelas)
        else:
            expense['can_edit'] = True
            expense['edit_id'] = expense['original_id']
            expense['can_delete'] = True
            expense['delete_id'] = expense['original_id']

    categories = conn.execute(
        'SELECT * FROM categories ORDER BY name'
    ).fetchall()

    family_members = get_family_members(family_email)

    conn.close()

    return render_template(
        'expenses.html',
        current_user=current_user,
        is_admin=is_admin,
        expenses=all_expenses,
        categories=[dict(c) for c in categories],
        family_members=family_members,
        filter_type=filter_type,
        filter_category=filter_category,
        filter_person=filter_person,
        filter_month=filter_month
    )

@app.route('/expenses/add', methods=['GET', 'POST'])
@login_required
@family_context
def add_expense(current_user, family_email, is_admin):
    """Adiciona nova despesa."""
    conn = get_db_connection(app.config['DATABASE'])

    if request.method == 'POST':
        description = request.form.get('description', '').strip()
        amount = float(request.form.get('amount', 0))
        expense_date = request.form.get('expense_date', datetime.now().strftime('%Y-%m-%d'))
        category_id = request.form.get('category_id')
        person_id = int(request.form.get('person_id', current_user['id']))
        expense_type = request.form.get('expense_type', 'individual')
        notes = request.form.get('notes', '').strip()
        is_recurring = 1 if request.form.get('is_recurring') else 0
        recurring_frequency = request.form.get('recurring_frequency', 'mensal')
        is_installment = 1 if request.form.get('is_installment') else 0
        installment_total = int(request.form.get('installment_total', 1))
        installment_number = int(request.form.get('installment_number', 1))

        if not description or amount <= 0:
            flash('Preencha descricao e valor validos.', 'warning')
            categories = conn.execute('SELECT * FROM categories ORDER BY name').fetchall()
            family_members = get_family_members(family_email)
            conn.close()
            return render_template('expense_form.html',
                current_user=current_user, is_admin=is_admin,
                categories=[dict(c) for c in categories], family_members=family_members,
                expense=None, action='add'
            )

        member_ids = get_family_member_ids(family_email)
        if person_id not in member_ids:
            conn.close()
            abort(403)

        # Para parcelas, armazenamos o valor total da compra, nao o valor da parcela
        # O valor da parcela sera calculado na visualizacao

        installment_group_id = None
        if is_installment:
            installment_group_id = "inst_{}_{}".format(datetime.now().strftime('%Y%m%d%H%M%S'), person_id)

        sql = """INSERT INTO expenses 
            (description, amount, expense_date, category_id, person_id, expense_type, 
             is_recurring, recurring_frequency, next_due_date, is_installment, 
             installment_total, installment_number, installment_group_id, notes, created_by) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
        conn.execute(sql, (description, amount, expense_date, category_id, person_id, 
                          expense_type, is_recurring, recurring_frequency, None, 
                          is_installment, installment_total, installment_number, 
                          installment_group_id, notes, current_user['id']))

        conn.commit()
        conn.close()
        flash('Despesa adicionada com sucesso!', 'success')
        return redirect(url_for('expenses'))

    categories = conn.execute('SELECT * FROM categories ORDER BY name').fetchall()
    family_members = get_family_members(family_email)
    conn.close()

    return render_template('expense_form.html',
        current_user=current_user, is_admin=is_admin,
        categories=[dict(c) for c in categories], family_members=family_members,
        expense=None, action='add'
    )

@app.route('/expenses/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@family_context
def edit_expense(current_user, family_email, is_admin, id):
    """Edita uma despesa existente."""
    conn = get_db_connection(app.config['DATABASE'])
    expense = conn.execute('SELECT * FROM expenses WHERE id = ?', (id,)).fetchone()

    if not expense:
        conn.close()
        abort(404)

    member_ids = get_family_member_ids(family_email)
    if expense['person_id'] not in member_ids:
        conn.close()
        abort(403)

    if not is_admin and expense['created_by'] != current_user['id']:
        conn.close()
        flash('Voce so pode editar suas proprias movimentacoes.', 'danger')
        return redirect(url_for('expenses'))

    if request.method == 'POST':
        description = request.form.get('description', '').strip()
        amount = float(request.form.get('amount', 0))
        expense_date = request.form.get('expense_date')
        category_id = request.form.get('category_id')
        person_id = int(request.form.get('person_id'))
        expense_type = request.form.get('expense_type', 'individual')
        notes = request.form.get('notes', '').strip()
        is_recurring = 1 if request.form.get('is_recurring') else 0
        recurring_frequency = request.form.get('recurring_frequency', 'mensal')
        is_installment = 1 if request.form.get('is_installment') else 0
        installment_total = int(request.form.get('installment_total', 1))
        installment_number = int(request.form.get('installment_number', 1))

        if not description or amount <= 0:
            flash('Preencha descricao e valor validos.', 'warning')
            categories = conn.execute('SELECT * FROM categories ORDER BY name').fetchall()
            family_members = get_family_members(family_email)
            conn.close()
            return render_template('expense_form.html',
                current_user=current_user, is_admin=is_admin,
                categories=[dict(c) for c in categories], family_members=family_members,
                expense=dict(expense), action='edit'
            )

        sql = """UPDATE expenses SET 
            description = ?, amount = ?, expense_date = ?, category_id = ?, person_id = ?, 
            expense_type = ?, is_recurring = ?, recurring_frequency = ?, next_due_date = ?, 
            is_installment = ?, installment_total = ?, installment_number = ?, notes = ? 
            WHERE id = ?"""
        conn.execute(sql, (description, amount, expense_date, category_id, person_id, 
                          expense_type, is_recurring, recurring_frequency, None, 
                          is_installment, installment_total, installment_number, notes, id))

        conn.commit()
        conn.close()
        flash('Despesa atualizada com sucesso!', 'success')
        return redirect(url_for('expenses'))

    categories = conn.execute('SELECT * FROM categories ORDER BY name').fetchall()
    family_members = get_family_members(family_email)
    conn.close()

    return render_template('expense_form.html',
        current_user=current_user, is_admin=is_admin,
        categories=[dict(c) for c in categories], family_members=family_members,
        expense=dict(expense), action='edit'
    )

@app.route('/expenses/delete/<int:id>', methods=['POST'])
@login_required
@family_context
def delete_expense(current_user, family_email, is_admin, id):
    """Exclui uma despesa."""
    conn = get_db_connection(app.config['DATABASE'])
    expense = conn.execute('SELECT * FROM expenses WHERE id = ?', (id,)).fetchone()

    if not expense:
        conn.close()
        abort(404)

    member_ids = get_family_member_ids(family_email)
    if expense['person_id'] not in member_ids:
        conn.close()
        abort(403)

    if not is_admin and expense['created_by'] != current_user['id']:
        conn.close()
        flash('Voce so pode excluir suas proprias movimentacoes.', 'danger')
        return redirect(url_for('expenses'))

    conn.execute('DELETE FROM expenses WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    flash('Despesa excluida com sucesso!', 'success')
    return redirect(url_for('expenses'))

# ==============================================================================
# ROTAS DE CATEGORIAS
# ==============================================================================

@app.route('/categories')
@login_required
@family_context
def categories(current_user, family_email, is_admin):
    """Lista todas as categorias."""
    conn = get_db_connection(app.config['DATABASE'])
    cats = conn.execute('SELECT * FROM categories ORDER BY name').fetchall()
    conn.close()

    return render_template('categories.html',
        current_user=current_user, is_admin=is_admin,
        categories=[dict(c) for c in cats]
    )

@app.route('/categories/add', methods=['POST'])
@login_required
@family_context
def add_category(current_user, family_email, is_admin):
    """Adiciona nova categoria."""
    name = request.form.get('name', '').strip()
    icon = request.form.get('icon', 'tag').strip()
    color = request.form.get('color', '#6c757d').strip()

    if not name:
        flash('Nome da categoria e obrigatorio.', 'warning')
        return redirect(url_for('categories'))

    conn = get_db_connection(app.config['DATABASE'])
    conn.execute('INSERT INTO categories (name, icon, color) VALUES (?, ?, ?)', (name, icon, color))
    conn.commit()
    conn.close()

    flash('Categoria adicionada com sucesso!', 'success')
    return redirect(url_for('categories'))

@app.route('/categories/edit/<int:id>', methods=['POST'])
@login_required
@family_context
def edit_category(current_user, family_email, is_admin, id):
    """Edita uma categoria."""
    name = request.form.get('name', '').strip()
    icon = request.form.get('icon', 'tag').strip()
    color = request.form.get('color', '#6c757d').strip()

    if not name:
        flash('Nome da categoria e obrigatorio.', 'warning')
        return redirect(url_for('categories'))

    conn = get_db_connection(app.config['DATABASE'])
    conn.execute('UPDATE categories SET name = ?, icon = ?, color = ? WHERE id = ?', (name, icon, color, id))
    conn.commit()
    conn.close()

    flash('Categoria atualizada com sucesso!', 'success')
    return redirect(url_for('categories'))

@app.route('/categories/delete/<int:id>', methods=['POST'])
@login_required
@family_context
def delete_category(current_user, family_email, is_admin, id):
    """Exclui uma categoria."""
    conn = get_db_connection(app.config['DATABASE'])
    expenses_using = conn.execute('SELECT COUNT(*) as count FROM expenses WHERE category_id = ?', (id,)).fetchone()['count']

    if expenses_using > 0:
        conn.close()
        flash('Nao e possivel excluir categoria em uso.', 'warning')
        return redirect(url_for('categories'))

    conn.execute('DELETE FROM categories WHERE id = ?', (id,))
    conn.commit()
    conn.close()

    flash('Categoria excluida com sucesso!', 'success')
    return redirect(url_for('categories'))

# ==============================================================================
# ROTAS DA LISTA DE COMPRAS
# ==============================================================================

@app.route('/shopping')
@login_required
@family_context
def shopping(current_user, family_email, is_admin):
    """Lista de compras compartilhada."""
    conn = get_db_connection(app.config['DATABASE'])
    member_ids = get_family_member_ids(family_email)

    query = "SELECT s.*, c.name as category_name, c.color as category_color, u.name as creator_name FROM shopping_list s LEFT JOIN categories c ON s.category_id = c.id JOIN users u ON s.created_by = u.id WHERE s.created_by IN ({}) ORDER BY s.is_bought, s.created_at DESC".format(','.join('?' * len(member_ids)))
    items = conn.execute(query, tuple(member_ids)).fetchall()

    categories = conn.execute('SELECT * FROM categories ORDER BY name').fetchall()
    conn.close()

    return render_template('shopping.html',
        current_user=current_user, is_admin=is_admin,
        items=[dict(i) for i in items],
        categories=[dict(c) for c in categories]
    )

@app.route('/shopping/add', methods=['POST'])
@login_required
@family_context
def add_shopping_item(current_user, family_email, is_admin):
    """Adiciona item a lista de compras."""
    name = request.form.get('name', '').strip()
    quantity = request.form.get('quantity', '1').strip()
    category_id = request.form.get('category_id')
    notes = request.form.get('notes', '').strip()

    if not name:
        flash('Nome do item e obrigatorio.', 'warning')
        return redirect(url_for('shopping'))

    conn = get_db_connection(app.config['DATABASE'])
    conn.execute('INSERT INTO shopping_list (name, quantity, category_id, notes, created_by) VALUES (?, ?, ?, ?, ?)',
                (name, quantity, category_id, notes, current_user['id']))
    conn.commit()
    conn.close()

    flash('Item adicionado a lista!', 'success')
    return redirect(url_for('shopping'))

@app.route('/shopping/toggle/<int:id>', methods=['POST'])
@login_required
@family_context
def toggle_shopping_item(current_user, family_email, is_admin, id):
    """Marca/desmarca item como comprado."""
    conn = get_db_connection(app.config['DATABASE'])
    item = conn.execute('SELECT * FROM shopping_list WHERE id = ?', (id,)).fetchone()

    if not item:
        conn.close()
        abort(404)

    member_ids = get_family_member_ids(family_email)
    if item['created_by'] not in member_ids:
        conn.close()
        abort(403)

    new_status = 0 if item['is_bought'] else 1
    conn.execute('UPDATE shopping_list SET is_bought = ? WHERE id = ?', (new_status, id))
    conn.commit()
    conn.close()

    return jsonify({'success': True, 'is_bought': new_status})

@app.route('/shopping/delete/<int:id>', methods=['POST'])
@login_required
@family_context
def delete_shopping_item(current_user, family_email, is_admin, id):
    """Exclui item da lista de compras."""
    conn = get_db_connection(app.config['DATABASE'])
    item = conn.execute('SELECT * FROM shopping_list WHERE id = ?', (id,)).fetchone()

    if not item:
        conn.close()
        abort(404)

    member_ids = get_family_member_ids(family_email)
    if item['created_by'] not in member_ids:
        conn.close()
        abort(403)

    conn.execute('DELETE FROM shopping_list WHERE id = ?', (id,))
    conn.commit()
    conn.close()

    flash('Item removido da lista.', 'success')
    return redirect(url_for('shopping'))

# ==============================================================================
# ROTAS DE RELATORIOS
# ==============================================================================

@app.route('/reports')
@login_required
@family_context
def reports(current_user, family_email, is_admin):
    """Pagina de relatorios."""
    conn = get_db_connection(app.config['DATABASE'])
    member_ids = get_family_member_ids(family_email)
    family_members = get_family_members(family_email)

    report_type = request.args.get('type', 'monthly')
    year = int(request.args.get('year', datetime.now().year))
    month = int(request.args.get('month', datetime.now().month))

    # Usar a nova funcao para obter totais do mes
    month_totals = get_expense_totals_for_month(conn, member_ids, year, month)
    monthly_total = month_totals['total']

    # Por categoria
    category_totals = {}
    for e in month_totals['expenses']:
        cat_name = e.get('category_name') or 'Sem Categoria'
        cat_color = e.get('category_color') or '#6c757d'
        if cat_name not in category_totals:
            category_totals[cat_name] = {'name': cat_name, 'color': cat_color, 'total': 0}
        category_totals[cat_name]['total'] += e['amount']

    by_category = sorted(category_totals.values(), key=lambda x: x['total'], reverse=True)
    by_category = [c for c in by_category if c['total'] > 0]

    # Por pessoa
    by_person = []
    for member in family_members:
        member_expenses = [e for e in month_totals['expenses'] if e['person_id'] == member['id']]
        p_total = sum(e['amount'] for e in member_expenses)
        p_shared = sum(e['amount'] for e in member_expenses if e['expense_type'] == 'compartilhado')
        p_individual = sum(e['amount'] for e in member_expenses if e['expense_type'] == 'individual')
        by_person.append({'name': member['name'], 'total': p_total, 'shared': p_shared, 'individual': p_individual})

    # Despesas fixas (recorrentes) do mes
    fixed_expenses = [e for e in month_totals['expenses'] 
                      if e['is_recurring'] == 1 or e.get('generation_type') == 'recorrente']

    # Parcelas do mes
    installments = [e for e in month_totals['expenses'] 
                    if e['is_installment'] == 1 or e.get('generation_type') == 'parcela']

    # Dados anuais
    annual_data = []
    for m in range(1, 13):
        m_totals = get_expense_totals_for_month(conn, member_ids, year, m)
        annual_data.append({'month': m, 'total': m_totals['total']})

    conn.close()

    return render_template('reports.html',
        current_user=current_user, is_admin=is_admin,
        report_type=report_type, year=year, month=month,
        monthly_total=monthly_total,
        by_category=by_category,
        by_person=by_person,
        fixed_expenses=fixed_expenses,
        installments=installments,
        annual_data=annual_data,
        family_members=family_members
    )

# ==============================================================================
# ROTAS DE ADMINISTRACAO
# ==============================================================================

@app.route('/admin/users')
@login_required
@family_context
@admin_required
def admin_users(current_user, family_email, is_admin):
    """Gerenciamento de usuarios da familia."""
    family_members = get_family_members(family_email)

    return render_template('admin_users.html',
        current_user=current_user, is_admin=is_admin,
        members=family_members
    )

@app.route('/admin/users/add', methods=['POST'])
@login_required
@family_context
@admin_required
def admin_add_user(current_user, family_email, is_admin):
    """Admin adiciona novo usuario a familia."""
    name = request.form.get('name', '').strip()
    username = request.form.get('username', '').strip().lower()
    password = request.form.get('password', '')

    if not name or not username or not password:
        flash('Preencha todos os campos.', 'warning')
        return redirect(url_for('admin_users'))

    if len(password) < 6:
        flash('Senha deve ter no minimo 6 caracteres.', 'warning')
        return redirect(url_for('admin_users'))

    conn = get_db_connection(app.config['DATABASE'])
    existing = conn.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()
    if existing:
        conn.close()
        flash('Username ja em uso.', 'warning')
        return redirect(url_for('admin_users'))

    password_hash = generate_password_hash(password)
    conn.execute('INSERT INTO users (username, name, email, password_hash, role) VALUES (?, ?, ?, ?, ?)',
                (username, name, family_email, password_hash, 'user'))
    conn.commit()
    conn.close()

    flash('Usuario {} adicionado com sucesso!'.format(name), 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/users/delete/<int:id>', methods=['POST'])
@login_required
@family_context
@admin_required
def admin_delete_user(current_user, family_email, is_admin, id):
    """Admin remove usuario da familia."""
    if id == current_user['id']:
        flash('Voce nao pode remover a si mesmo.', 'warning')
        return redirect(url_for('admin_users'))

    conn = get_db_connection(app.config['DATABASE'])
    user = conn.execute('SELECT * FROM users WHERE id = ? AND email = ?', (id, family_email)).fetchone()
    if not user:
        conn.close()
        flash('Usuario nao encontrado.', 'danger')
        return redirect(url_for('admin_users'))

    conn.execute('UPDATE expenses SET person_id = ?, created_by = ? WHERE person_id = ?', (current_user['id'], current_user['id'], id))
    conn.execute('UPDATE shopping_list SET created_by = ? WHERE created_by = ?', (current_user['id'], id))
    conn.execute('DELETE FROM users WHERE id = ?', (id,))
    conn.commit()
    conn.close()

    flash('Usuario removido com sucesso.', 'success')
    return redirect(url_for('admin_users'))

# ==============================================================================
# ROTAS DE API (JSON)
# ==============================================================================

@app.route('/api/dashboard-data')
@login_required
@family_context
def api_dashboard_data(current_user, family_email, is_admin):
    """API para dados do dashboard."""
    conn = get_db_connection(app.config['DATABASE'])
    member_ids = get_family_member_ids(family_email)
    current_year = datetime.now().year
    current_month = datetime.now().month

    # Dados de categorias do mes atual
    month_totals = get_expense_totals_for_month(conn, member_ids, current_year, current_month)

    category_totals = {}
    for e in month_totals['expenses']:
        cat_name = e.get('category_name') or 'Sem Categoria'
        if cat_name not in category_totals:
            category_totals[cat_name] = 0
        category_totals[cat_name] += e['amount']

    category_labels = list(category_totals.keys())
    category_values = list(category_totals.values())

    # Dados mensais (ultimos 6 meses)
    monthly_labels = []
    monthly_values = []
    for i in range(5, -1, -1):
        month_date = datetime.now() - timedelta(days=i*30)
        m_year = month_date.year
        m_month = month_date.month
        m_totals = get_expense_totals_for_month(conn, member_ids, m_year, m_month)
        monthly_labels.append(month_date.strftime('%b/%Y'))
        monthly_values.append(m_totals['total'])

    conn.close()

    return jsonify({
        'categories': {'labels': category_labels, 'data': category_values},
        'monthly': {'labels': monthly_labels, 'data': monthly_values}
    })

# ==============================================================================
# ERROS
# ==============================================================================

@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(403)
def forbidden(error):
    flash('Acesso negado.', 'danger')
    return redirect(url_for('dashboard'))

# ==============================================================================
# INICIALIZACAO
# ==============================================================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
