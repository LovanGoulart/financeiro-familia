"""Regressão em banco temporário: nunca utiliza o banco familiar fornecido."""
import importlib
import os
import sys
from datetime import datetime
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
# DATABASE_PATH must be set before importing app (which initializes the database).
import tempfile
_test_dir = tempfile.TemporaryDirectory()
os.environ['DATABASE_PATH'] = str(Path(_test_dir.name) / 'test.db')
os.environ['SECRET_KEY'] = 'test-key-only-never-use-in-production'
from app import app, get_all_expenses_for_month, get_expense_totals_for_month
from enhancements import next_payment_date, parse_amount
from models.database import init_db, get_db_connection
from werkzeug.security import generate_password_hash, check_password_hash


@pytest.fixture
def client(tmp_path):
    app.config.update(TESTING=True, DATABASE=str(tmp_path / 'finance.db'))
    init_db(app.config['DATABASE'])
    conn = get_db_connection(app.config['DATABASE'])
    for uid, name, family, role in [(1,'Ana','a@example.com','admin'), (2,'Bruno','a@example.com','user'), (3,'Outra','b@example.com','admin')]:
        conn.execute('INSERT INTO users(id,username,name,email,password_hash,role) VALUES(?,?,?,?,?,?)',
                     (uid, name.lower(), name, family, generate_password_hash('segredo123'), role))
    conn.execute("INSERT INTO categories(id,name,family_email) VALUES(1,'Mercado','a@example.com'),(2,'Outros','b@example.com')")
    conn.commit(); conn.close()
    return app.test_client()


def sign_in(client, uid=1):
    with client.session_transaction() as s:
        s['user_id'] = uid; s['_csrf'] = 'token'; s['name'] = 'Ana'


def post(client, path, data=None):
    return client.post(path, data={'_csrf': 'token', **(data or {})})


def expense(client, **overrides):
    return post(client, '/expenses/add', {**dict(description='Compra', amount='1.234,56', expense_date='31/12/2026',
             category_id='1', person_id='1', expense_type='individual'), **overrides})


def test_public_routes(client):
    for route in ['/login','/register','/forgot-password','/manifest.webmanifest','/sw.js','/static/icons/icon-192.png','/static/icons/icon-512.png']:
        assert client.get(route).status_code == 200, route
    assert client.get('/dashboard').status_code == 302
    assert client.get('/api/notifications').status_code == 401
    assert client.get('/api/notifications/stream').status_code == 401


def test_pages_and_defaults(client):
    sign_in(client)
    next_date = next_payment_date()
    for route in ['/dashboard','/expenses','/expenses/add','/categories','/shopping','/reports','/admin/users','/api/dashboard-data']:
        assert client.get(route).status_code == 200, route
    page = client.get('/dashboard').text
    assert f'value="{next_date.month}"' in page
    assert f'value="{next_date.year}"' in page
    assert f'{next_date.month:02d}/{next_date.year}' in client.get('/expenses').text
    assert next_date.strftime('%d/%m/%Y') in client.get('/expenses/add').text


def test_login_and_registration(client):
    client.get('/login')
    with client.session_transaction() as s: s['_csrf'] = 'token'
    assert post(client, '/register', {'family_email':'nova@example.com', 'user_count':'2',
                'name_1':'Nova','username_1':'nova','password_1':'senha123',
                'name_2':'Novo','username_2':'novo','password_2':'senha123'}).status_code == 302
    response = post(client, '/login', {'username':'nova','password':'senha123'})
    assert response.location.endswith('/dashboard')
    assert client.get('/dashboard').status_code == 200


def test_csrf(client):
    sign_in(client)
    assert client.post('/categories/add', data={'name':'Invasão'}).status_code == 400
    assert post(client,'/categories/add',{'name':'Segura'}).status_code == 302


@pytest.mark.parametrize('raw,expected',[('1.234,56',1234.56),('1234,56',1234.56),('1234.56',1234.56),('0,01',.01)])
def test_currency(raw, expected):
    assert parse_amount(raw) == expected


@pytest.mark.parametrize('raw',['NaN','inf','-1','1,234','1.23,45','0',''])
def test_bad_currency(raw):
    with pytest.raises(ValueError): parse_amount(raw)


def test_year_rollover():
    assert next_payment_date(datetime(2026,12,31)).date().isoformat() == '2027-01-31'
    assert next_payment_date(datetime(2027,1,31)).date().isoformat() == '2027-02-28'
    assert next_payment_date(datetime(2028,1,31)).date().isoformat() == '2028-02-29'


def test_expense_crud_and_notifications(client):
    sign_in(client)
    assert expense(client).status_code == 302
    conn = get_db_connection(app.config['DATABASE'])
    row = conn.execute('SELECT * FROM expenses').fetchone()
    assert row['amount'] == 1234.56 and row['expense_date'] == '2026-12-31'
    eid = row['id'];conn.close()
    page = client.get('/expenses?month=12/2026').text
    assert 'R$ 1.234,56' in page
    assert '31/12/2026' in page
    assert client.get(f'/expenses/edit/{eid}').status_code == 200
    assert post(client,f'/expenses/edit/{eid}',{'description':'Editada','amount':'20,50','expense_date':'01/01/2027',
                'category_id':'1','person_id':'2','expense_type':'compartilhado'}).status_code == 302
    assert post(client,f'/expenses/delete/{eid}').status_code == 302
    events = client.get('/api/notifications?after=0').json['events']
    assert [e['kind'] for e in events] == ['add_expense','edit_expense','delete_expense']
    sign_in(client,3)
    assert client.get('/api/notifications?after=0').json['events'] == []


def test_sse_and_reconnect(client):
    sign_in(client)
    expense(client)
    response = client.get('/api/notifications/stream?after=0', buffered=False)
    it = iter(response.response)
    assert b'conectado' in next(it)
    payload = next(it)
    assert b'event: change' in payload and b'add_expense' in payload
    response.close()
    assert client.get('/api/notifications?after=1').json['events'] == []


def test_tenant_isolation(client):
    sign_in(client)
    expense(client)
    assert expense(client,person_id='3').status_code == 302  # forbidden handler redirects; no write
    assert expense(client,category_id='2').status_code == 302
    assert post(client,'/expenses/edit/1',{'description':'Invasão','amount':'5,00','expense_date':'01/01/2027','person_id':'3'}).status_code == 302
    assert post(client,'/admin/users/change-password/3',{'new_password':'invasao123'}).status_code == 302
    conn=get_db_connection(app.config['DATABASE'])
    assert conn.execute('SELECT COUNT(*) FROM expenses').fetchone()[0] == 1
    assert conn.execute('SELECT person_id FROM expenses').fetchone()[0] == 1
    assert check_password_hash(conn.execute('SELECT password_hash FROM users WHERE id=3').fetchone()[0], 'segredo123')
    conn.close()


def test_installment_exact_cents(client):
    sign_in(client)
    expense(client,amount='100,00',is_installment='on',installment_total='3')
    conn=get_db_connection(app.config['DATABASE'])
    totals=[get_expense_totals_for_month(conn,[1,2], y,m)['total'] for y,m in [(2026,12),(2027,1),(2027,2)]]
    assert totals == [33.33,33.33,33.34]
    assert round(sum(totals),2) == 100
    assert get_expense_totals_for_month(conn,[1,2],2027,3)['total'] == 0
    conn.close()


def test_weekly_and_yearly(client):
    sign_in(client)
    expense(client,amount='10,00',expense_date='30/11/2026',is_recurring='on',recurring_frequency='semanal')
    expense(client,amount='50,00',expense_date='31/12/2026',is_recurring='on',recurring_frequency='anual')
    conn=get_db_connection(app.config['DATABASE'])
    items=get_all_expenses_for_month(conn,[1,2],2026,12)
    assert len(items) == 5 and sum(e['amount'] for e in items) == 90
    assert [e['expense_date'] for e in items if e['amount'] == 10] == ['2026-12-28','2026-12-21','2026-12-14','2026-12-07']
    assert all(e['amount'] != 50 for e in get_all_expenses_for_month(conn,[1,2],2027,1))
    conn.close()


def test_shopping(client):
    sign_in(client)
    post(client,'/shopping/add',{'name':'Arroz','category_id':'1'})
    assert client.post('/shopping/toggle/1',headers={'X-CSRF-Token':'token'},json={}).json['is_bought'] == 1
    assert post(client,'/shopping/delete/1').status_code == 302
    assert len(client.get('/api/notifications').json['events']) == 3


def test_bad_inputs(client):
    sign_in(client)
    for raw in ['NaN','abc','-5','0']:
        assert expense(client,amount=raw).status_code == 302
    assert expense(client,expense_date='31/02/2027').status_code == 302
    for route in ['/dashboard?month=13','/reports?year=foo','/expenses?month=inválido']:
        assert client.get(route).status_code == 400


def test_password_reset_not_public(client):
    with client.session_transaction() as s:s['_csrf']='token'
    post(client,'/forgot-password',{'username':'ana'})
    conn=get_db_connection(app.config['DATABASE'])
    assert check_password_hash(conn.execute('SELECT password_hash FROM users WHERE id=1').fetchone()[0], 'segredo123')
    conn.close()


def test_xss_escaped(client):
    sign_in(client)
    post(client,'/categories/add',{'name':"teste' );alert(1);//<script>bad</script>"})
    page=client.get('/categories').text
    assert '<script>bad</script>' not in page
    assert '\\u003cscript\\u003e' in page


def test_logged_in_404(client):
    sign_in(client)
    assert client.get('/pagina-inexistente').status_code == 404


def test_installment_current_number(client):
    sign_in(client)
    expense(client,amount='100,00',is_installment='on',installment_total='3',installment_number='2')
    conn=get_db_connection(app.config['DATABASE'])
    assert get_all_expenses_for_month(conn,[1,2],2026,12)[0]['installment_number'] == 2
    assert get_all_expenses_for_month(conn,[1,2],2027,1)[0]['installment_number'] == 3
    assert get_all_expenses_for_month(conn,[1,2],2027,2) == []
    conn.close()
