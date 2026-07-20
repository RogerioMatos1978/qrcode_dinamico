"""
Funções auxiliares de segurança e detecção de dispositivo.
"""
from datetime import datetime, timedelta

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15


def detect_device(user_agent: str) -> str:
    """Descobre se o acesso veio de Android, iOS ou outro dispositivo (desktop)."""
    ua = (user_agent or "").lower()
    if "android" in ua:
        return "android"
    if any(token in ua for token in ("iphone", "ipad", "ipod")):
        return "ios"
    return "desktop"


def register_failed_login(user) -> None:
    """Incrementa tentativas falhas e bloqueia a conta temporariamente após o limite."""
    user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
    if user.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
        user.locked_until = datetime.utcnow() + timedelta(minutes=LOCKOUT_MINUTES)


def reset_failed_login(user) -> None:
    user.failed_login_attempts = 0
    user.locked_until = None


def get_client_ip(request) -> str:
    """Obtém o IP do visitante, respeitando cabeçalho de proxy quando presente."""
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.remote_addr or "desconhecido"
