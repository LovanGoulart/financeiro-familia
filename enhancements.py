"""Localização, proteção de formulários, PWA e eventos isolados por família."""
import hmac
import json
import os
import re
import secrets
import time
from calendar import monthrange
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo
from flask import request, session, jsonify, Response, stream_with_context, abort, redirect, url_for, flash
from models.database import get_db_connection


def now_br():
    return datetime.now(ZoneInfo('America/Sao_Paulo')).replace(tzinfo=None)


def next_payment_date(today=None):
    today = today or now_br()
    year = today.year + (today.month == 12)
    month = today.month % 12 + 1
    return today.replace(year=year, month=month, day=min(today.day, monthrange(year, month)[1]))


def selected_period(month_string=False):
    default = next_payment_date()
    try:
        if month_string:
            value = request.args.get('month', '')
            if not value:
                return default.year, default.month
            if re.fullmatch(r'\d{2}/\d{4}', value):
                month, year = map(int, value.split('/'))
            else:
                year, month = map(int, value.split('-'))
        else:
            year = int(request.args.get('year', default.year))
            month = int(request.args.get('month', default.month))
        if not (1900 <= year <= 9998 and 1 <= month <= 12):
            raise ValueError
        return year, month
    except (ValueError, TypeError):
        abort(400, description='Informe mês e ano válidos.')


def parse_amount(raw):
    value = str(raw).strip().replace('R$', '').replace(' ', '').replace('\xa0', '')
    if ',' in value:
        if not re.fullmatch(r'(?:\d{1,3}(?:\.\d{3})+|\d+),\d{1,2}', value):
            raise ValueError('Informe o valor no formato 1.234,56.')
        value = value.replace('.', '').replace(',', '.')
    if not re.fullmatch(r'\d+(?:\.\d{1,2})?', value):
        raise ValueError('Informe um valor válido com até duas casas decimais.')
    result = Decimal(value)
    if not result.is_finite() or result <= 0 or result > Decimal('999999999.99'):
        raise ValueError('O valor deve ser positivo e menor que um bilhão.')
    return float(result)


def normalize_date(value):
    try:
        if '/' in value:
            return datetime.strptime(value, '%d/%m/%Y').strftime('%Y-%m-%d')
        return datetime.strptime(value, '%Y-%m-%d').strftime('%Y-%m-%d')
    except (ValueError, TypeError):
        raise ValueError('Informe uma data válida no formato dd/mm/aaaa.')


EVENT_TEXT = {
    'add_expense': 'adicionou uma despesa', 'edit_expense': 'atualizou uma despesa',
    'delete_expense': 'excluiu uma despesa', 'add_category': 'criou uma categoria',
    'edit_category': 'atualizou uma categoria', 'delete_category': 'excluiu uma categoria',
    'add_shopping_item': 'adicionou um item à lista de compras',
    'toggle_shopping_item': 'atualizou um item da lista de compras',
    'delete_shopping_item': 'removeu um item da lista de compras',
    'admin_add_user': 'adicionou um usuário à família',
    'admin_delete_user': 'removeu um usuário da família',
    'admin_change_password': 'alterou a senha de um usuário da família',
}


def record_event(conn, family_email, actor, kind):
    conn.execute('INSERT INTO notifications (family_email, actor_id, message, kind) VALUES (?, ?, ?, ?)',
                 (family_email, actor['id'], f"{actor['name']} {EVENT_TEXT[kind]}.", kind))


def configure_app(app):
    key = os.environ.get('SECRET_KEY')
    if not key:
        path = os.path.join(app.instance_path, 'secret.key')
        os.makedirs(app.instance_path, exist_ok=True)
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            pass
        else:
            with os.fdopen(fd, 'w') as out:
                out.write(secrets.token_hex(32))
        with open(path) as source:
            key = source.read().strip()
    app.config.update(SECRET_KEY=key, SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax',
                      SESSION_COOKIE_SECURE=os.environ.get('COOKIE_SECURE') == '1', MAX_CONTENT_LENGTH=1024*1024)

    def csrf_token():
        if '_csrf' not in session:
            session['_csrf'] = secrets.token_urlsafe(32)
        return session['_csrf']

    def authenticated_user():
        uid = session.get('user_id')
        conn = get_db_connection(app.config['DATABASE'])
        user = conn.execute('SELECT id, email FROM users WHERE id=?', (uid,)).fetchone() if uid else None
        conn.close()
        if not user:
            abort(401)
        return dict(user)

    @app.context_processor
    def app_context():
        cursor = 0
        current_user = None
        if session.get('user_id'):
            conn = get_db_connection(app.config['DATABASE'])
            row = conn.execute('SELECT MAX(n.id) AS latest FROM notifications n JOIN users u ON u.email=n.family_email WHERE u.id=?', (session['user_id'],)).fetchone()
            cursor = row['latest'] or 0
            user = conn.execute('SELECT id, name, username, email, role FROM users WHERE id=?', (session['user_id'],)).fetchone()
            current_user = dict(user) if user else None
            if not user:
                session.clear()
            conn.close()
        return dict(csrf_token=csrf_token, event_cursor=cursor, current_br_year=now_br().year, current_user=current_user, is_admin=bool(current_user and current_user['role'] == 'admin'))

    @app.before_request
    def protect_and_validate():
        if request.method not in ('POST', 'PUT', 'PATCH', 'DELETE'):
            return
        sent = request.headers.get('X-CSRF-Token') or request.form.get('_csrf', '')
        if not sent or not hmac.compare_digest(str(sent), session.get('_csrf', '')):
            abort(400, description='Formulário expirado. Atualize a página e tente novamente.')
        # Reject malformed financial input before any connection/transaction in the routes.
        if request.endpoint in ('add_expense', 'edit_expense', 'add_shopping_item') and session.get('user_id'):
            conn = get_db_connection(app.config['DATABASE'])
            try:
                user = conn.execute('SELECT email FROM users WHERE id=?', (session['user_id'],)).fetchone()
                if not user:
                    abort(401)
                cat = request.form.get('category_id')
                if cat and not conn.execute('SELECT id FROM categories WHERE id=? AND family_email=?', (cat, user['email'])).fetchone():
                    abort(403)
                if request.endpoint in ('add_expense', 'edit_expense'):
                    value = parse_amount(request.form.get('amount', ''))
                    normalize_date(request.form.get('expense_date', ''))
                    person = int(request.form.get('person_id', session['user_id']))
                    if not conn.execute('SELECT id FROM users WHERE id=? AND email=?', (person, user['email'])).fetchone():
                        abort(403)
                    if request.form.get('expense_type', 'individual') not in ('individual', 'compartilhado'):
                        raise ValueError('Selecione um tipo de despesa válido.')
                    recurring = bool(request.form.get('is_recurring'))
                    installment = bool(request.form.get('is_installment'))
                    if recurring and installment:
                        raise ValueError('Escolha despesa recorrente ou parcelamento, uma opção por vez.')
                    if recurring and request.form.get('recurring_frequency') not in ('mensal', 'semanal', 'anual'):
                        raise ValueError('Selecione uma frequência válida.')
                    total = int(request.form.get('installment_total', 1))
                    number = int(request.form.get('installment_number', 1))
                    if not 1 <= number <= total <= 600:
                        raise ValueError('Informe parcelas válidas (de 1 a 600).')
                    if installment and request.endpoint == 'add_expense' and value * 100 < total:
                        raise ValueError('Cada parcela deve ter pelo menos R$ 0,01.')
            except (ValueError, InvalidOperation):
                flash('Dados inválidos. Confira valor, data e parcelas. Use 1.234,56 e dd/mm/aaaa.', 'warning')
                return redirect(url_for('add_expense') if request.endpoint == 'add_expense' else request.path)
            finally:
                conn.close()
        if request.endpoint == 'register':
            try:
                count = int(request.form.get('user_count', 1))
                if not 1 <= count <= 10:
                    raise ValueError
            except ValueError:
                abort(400, description='Quantidade de usuários inválida.')
            if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', request.form.get('family_email', '')):
                abort(400, description='Informe um e-mail válido.')

    @app.after_request
    def secure_headers(response):
        if request.endpoint != 'static':
            response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['Referrer-Policy'] = 'same-origin'
        return response

    @app.route('/manifest.webmanifest')
    def manifest():
        response = jsonify(id='/', name='Financeiro Familiar', short_name='Financeiro', lang='pt-BR',
                           start_url='/dashboard', scope='/', display='standalone', background_color='#f8fafc',
                           theme_color='#4f46e5', icons=[{'src': f'/static/icons/icon-{s}.png', 'sizes': f'{s}x{s}', 'type': 'image/png', 'purpose': 'any maskable'} for s in (192, 512)])
        response.mimetype = 'application/manifest+json'
        return response

    @app.route('/sw.js')
    def service_worker():
        return app.send_static_file('sw.js')

    def events_after(family, cursor):
        conn = get_db_connection(app.config['DATABASE'])
        try:
            return [dict(row) for row in conn.execute('SELECT id, actor_id, message, kind, created_at FROM notifications WHERE family_email=? AND id>? ORDER BY id LIMIT 100', (family, cursor))]
        finally:
            conn.close()

    @app.route('/api/notifications')
    def notifications():
        user = authenticated_user()
        cursor = max(0, request.args.get('after', 0, type=int))
        return jsonify(events=events_after(user['email'], cursor))

    @app.route('/api/notifications/stream')
    def notification_stream():
        user = authenticated_user()
        try:
            cursor = max(0, int(request.headers.get('Last-Event-ID') or request.args.get('after', 0)))
        except ValueError:
            abort(400)
        @stream_with_context
        def stream():
            nonlocal cursor
            yield 'retry: 2000\n: conectado\n\n'
            # Curta duração para revalidar a sessão e não reter workers indefinidamente.
            deadline = time.monotonic() + 20
            while time.monotonic() < deadline:
                for event in events_after(user['email'], cursor):
                    cursor = event['id']
                    yield f"id: {cursor}\nevent: change\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"
                yield ': ativo\n\n'
                time.sleep(1)
        return Response(stream(), mimetype='text/event-stream', headers={'X-Accel-Buffering': 'no'})

    @app.errorhandler(400)
    def bad_request(error):
        if request.path.startswith('/api/') or request.is_json:
            return jsonify(error=error.description), 400
        return app.jinja_env.get_template('400.html').render(message=error.description), 400
