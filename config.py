"""
Configurações da aplicação.

Tudo que é "segredo" ou muda entre ambientes (dev/produção) vem de variáveis
de ambiente (arquivo .env), nunca fica escrito direto no código.
"""
import os
from dotenv import load_dotenv

# Carrega o arquivo .env (se existir) para dentro de os.environ
load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    # --- Segurança básica ---
    SECRET_KEY = os.environ.get("SECRET_KEY", "chave-insegura-so-para-teste-local")

    # --- Banco de dados ---
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'app.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- Endereço público do site (usado para montar os links curtos) ---
    # .rstrip("/") remove uma eventual barra no final (ex: "https://site.com/"),
    # evitando links quebrados como "https://site.com//r/abc123" (barra dupla).
    BASE_URL = os.environ.get("BASE_URL", "http://localhost:5000").rstrip("/")

    # --- Cookies de sessão seguros ---
    SESSION_COOKIE_HTTPONLY = True          # JavaScript não consegue ler o cookie (mitiga XSS)
    SESSION_COOKIE_SAMESITE = "Lax"         # mitiga CSRF em navegação cross-site
    SESSION_COOKIE_SECURE = os.environ.get("FORCE_HTTPS", "0") == "1"  # só via HTTPS em produção
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"

    # --- Uploads / geração de QR Code ---
    QRCODE_FOLDER = os.path.join(BASE_DIR, "static", "qrcodes")
    LOGO_FOLDER = os.path.join(BASE_DIR, "static", "logos")
    MAX_CONTENT_LENGTH = 4 * 1024 * 1024  # limite geral de upload (4 MB), evita abuso

    # --- Rate limiting (proteção contra força bruta) ---
    RATELIMIT_STORAGE_URI = os.environ.get("RATELIMIT_STORAGE_URI", "memory://")
