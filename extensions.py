"""
Instâncias das extensões Flask usadas na aplicação.

Ficam em um módulo separado para evitar "import circular" entre app.py e models.py.
"""
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address)

login_manager.login_view = "login"
login_manager.login_message = "Faça login para acessar essa página."
login_manager.login_message_category = "warning"
