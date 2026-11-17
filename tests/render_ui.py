"""Renderização isolada para testes de interface; não utiliza dados reais."""
import contextlib
import os
from pathlib import Path
import sys
import tempfile
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
with tempfile.TemporaryDirectory() as temp:
    os.environ['DATABASE_PATH'] = str(Path(temp) / 'test.db')
    os.environ['SECRET_KEY'] = 'test-ui-only'
    with contextlib.redirect_stdout(sys.stderr):
        from app import app
    from models.database import get_db_connection
    conn = get_db_connection(app.config['DATABASE'])
    conn.execute("INSERT INTO users(id,username,name,email,password_hash,role) VALUES(2,'bruno','Bruno','test@example.com','unused','user')")
    conn.commit(); conn.close()
    client = app.test_client()
    with client.session_transaction() as session:
        session['user_id'] = 2
        session['_csrf'] = 'token'
    print(client.get('/dashboard').text)
