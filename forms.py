"""
Formulários (Flask-WTF / WTForms).

Cada campo tem "validators" que rejeitam dados fora do formato esperado
ANTES de chegarem ao banco. Isso, somado ao uso do ORM (veja models.py),
é a nossa defesa contra entradas maliciosas e SQL Injection.
Todas as páginas HTML que usam esses formulários incluem {{ form.hidden_tag() }},
que gera o token anti-CSRF exigido pelo Flask-WTF em cada envio.
"""
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileSize
from wtforms import StringField, PasswordField, BooleanField, SelectField, HiddenField
from wtforms.validators import (
    DataRequired,
    EqualTo,
    Length,
    Regexp,
    Optional,
    URL,
)

HEX_COLOR_MSG = "Use uma cor no formato hexadecimal, ex: #4F46E5"
USERNAME_MSG = "Use apenas letras, números, ponto, hífen ou underline (3 a 30 caracteres)."


class RegisterForm(FlaskForm):
    username = StringField(
        "Usuário",
        validators=[
            DataRequired(),
            Length(min=3, max=30),
            Regexp(r"^[A-Za-z0-9_.\-]+$", message=USERNAME_MSG),
        ],
    )
    password = PasswordField(
        "Senha",
        validators=[
            DataRequired(),
            Length(min=8, message="A senha precisa ter pelo menos 8 caracteres."),
            Regexp(
                r"^(?=.*[A-Za-z])(?=.*\d).+$",
                message="A senha precisa ter pelo menos uma letra e um número.",
            ),
        ],
    )
    confirm_password = PasswordField(
        "Confirmar senha",
        validators=[DataRequired(), EqualTo("password", message="As senhas não coincidem.")],
    )


class LoginForm(FlaskForm):
    username = StringField("Usuário", validators=[DataRequired(), Length(max=120)])
    password = PasswordField("Senha", validators=[DataRequired()])
    remember = BooleanField("Manter conectado")


GRADIENT_CHOICES = [
    ("horizontal", "Horizontal (esquerda → direita)"),
    ("vertical", "Vertical (cima → baixo)"),
    ("radial", "Radial (centro → borda)"),
    ("square", "Quadrada (centro → borda, cantos retos)"),
]


class QRCodeForm(FlaskForm):
    name = StringField("Nome do QR Code", validators=[DataRequired(), Length(max=120)])

    android_url = StringField(
        "URL para Android (Google Play)",
        validators=[Optional(), URL(require_tld=True, message="Informe uma URL válida."), Length(max=500)],
    )
    ios_url = StringField(
        "URL para iOS (App Store)",
        validators=[Optional(), URL(require_tld=True, message="Informe uma URL válida."), Length(max=500)],
    )
    desktop_url = StringField(
        "URL de destino do QR Code (ex: sua página publicada no Netlify)",
        validators=[Optional(), URL(require_tld=True, message="Informe uma URL válida."), Length(max=500)],
    )

    color_start = StringField(
        "Cor inicial do degradê",
        validators=[DataRequired(), Regexp(r"^#[0-9A-Fa-f]{6}$", message=HEX_COLOR_MSG)],
        default="#4F46E5",
    )
    color_end = StringField(
        "Cor final do degradê",
        validators=[DataRequired(), Regexp(r"^#[0-9A-Fa-f]{6}$", message=HEX_COLOR_MSG)],
        default="#06B6D4",
    )
    gradient_direction = SelectField(
        "Direção do degradê", choices=GRADIENT_CHOICES, default="horizontal"
    )

    border_color = StringField(
        "Cor da borda ao redor do QR Code",
        validators=[DataRequired(), Regexp(r"^#[0-9A-Fa-f]{6}$", message=HEX_COLOR_MSG)],
        default="#FFFFFF",
    )
    caption_text = StringField(
        "Texto acima do QR Code",
        validators=[Optional(), Length(max=160)],
        default="Aponte a câmera para o QR Code",
    )
    logo = FileField(
        "Logo central (imagem quadrada, recomendado 300x300)",
        validators=[
            Optional(),
            FileAllowed(["png", "jpg", "jpeg"], "Envie uma imagem PNG ou JPG."),
            FileSize(max_size=3 * 1024 * 1024, message="A imagem deve ter no máximo 3 MB."),
        ],
    )
    remove_logo = BooleanField("Remover logo atual")


class DeleteForm(FlaskForm):
    """Formulário vazio só para carregar o token CSRF em botões de exclusão."""
    pass
