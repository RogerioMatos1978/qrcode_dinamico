"""
Modelos do banco de dados (SQLAlchemy ORM).

Importante sobre segurança: como usamos o ORM do SQLAlchemy (db.session.query,
filter_by, etc.) em vez de montar comandos SQL manualmente com f-strings/%,
os valores são sempre passados como parâmetros vinculados ("bind parameters").
Isso é o que evita SQL Injection — nunca concatene texto do usuário em SQL cru.
"""
from datetime import datetime
import secrets

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from extensions import db


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Proteção extra contra força bruta: contamos tentativas falhas
    failed_login_attempts = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime, nullable=True)

    qrcodes = db.relationship(
        "QRCode", backref="owner", lazy=True, cascade="all, delete-orphan"
    )

    def set_password(self, password: str) -> None:
        # pbkdf2:sha256 é o padrão seguro do Werkzeug (hash + salt automático)
        self.password_hash = generate_password_hash(password, method="pbkdf2:sha256")

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def is_locked(self) -> bool:
        return bool(self.locked_until and self.locked_until > datetime.utcnow())


class QRCode(db.Model):
    __tablename__ = "qrcodes"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    name = db.Column(db.String(120), nullable=False)
    # slug curto e único usado na URL pública de redirecionamento: /r/<slug>
    slug = db.Column(db.String(16), unique=True, nullable=False, index=True)

    android_url = db.Column(db.String(500), nullable=True)
    ios_url = db.Column(db.String(500), nullable=True)
    desktop_url = db.Column(db.String(500), nullable=True)

    # Personalização visual (gradiente conforme identidade da empresa)
    color_start = db.Column(db.String(7), default="#4F46E5")  # hex, ex: #4F46E5
    color_end = db.Column(db.String(7), default="#06B6D4")
    gradient_direction = db.Column(db.String(20), default="horizontal")  # horizontal|vertical|radial|square

    # Borda colorida ao redor do QR Code
    border_color = db.Column(db.String(7), default="#FFFFFF")

    # Texto exibido acima do QR Code na imagem exportada (ex: "Aponte a câmera")
    caption_text = db.Column(db.String(160), default="Aponte a câmera para o QR Code")

    # Logo central (arquivo salvo em static/logos/<arquivo>); None = sem logo
    logo_filename = db.Column(db.String(255), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @staticmethod
    def generate_slug() -> str:
        """Gera um código curto e único para a URL pública do QR Code."""
        while True:
            candidate = secrets.token_urlsafe(6).replace("_", "").replace("-", "")[:8]
            if not QRCode.query.filter_by(slug=candidate).first():
                return candidate

    def target_url(self, device_type: str) -> str | None:
        """Escolhe a URL certa conforme o dispositivo que escaneou o QR Code."""
        if device_type == "android" and self.android_url:
            return self.android_url
        if device_type == "ios" and self.ios_url:
            return self.ios_url
        # fallback: desktop_url, ou qualquer URL configurada, nessa ordem
        return self.desktop_url or self.android_url or self.ios_url
