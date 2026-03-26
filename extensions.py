"""
extensions.py — Shared Flask extension instances.
Import these in dashboard.py and models.py to avoid circular imports.
"""
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect

db           = SQLAlchemy()
migrate      = Migrate()
login_manager = LoginManager()
bcrypt       = Bcrypt()
limiter      = Limiter(key_func=get_remote_address, storage_uri="memory://")
csrf         = CSRFProtect()
