"""Recuperação administrativa local; não expõe endpoint público de redefinição."""
import getpass
from app import app
from models.database import get_db_connection
from werkzeug.security import generate_password_hash

if __name__ == '__main__':
    username = input('Nome de usuário: ').strip().lower()
    password = getpass.getpass('Nova senha (mínimo 6 caracteres): ')
    confirm = getpass.getpass('Confirme a senha: ')
    if len(password) < 6 or password != confirm:
        raise SystemExit('Senha inválida ou confirmação diferente. Nada foi alterado.')
    conn = get_db_connection(app.config['DATABASE'])
    result = conn.execute('UPDATE users SET password_hash=? WHERE username=?', (generate_password_hash(password), username))
    conn.commit(); conn.close()
    print('Senha alterada.' if result.rowcount else 'Usuário não encontrado.')
