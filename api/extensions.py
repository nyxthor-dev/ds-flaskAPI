"""Extensiones de Flask instanciadas aparte para evitar import circular
entre app.py y los blueprints de routes/."""

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
