"""
Gerador de QR Code Dinâmico
---------------------------
Aplicação Flask para gerar QR Codes personalizados (degradê de cores, borda
colorida, logo central e texto de chamada) com destinos diferentes para
Android e iOS, exportáveis em PNG/JPG/PDF, e uma página estática pronta para
publicar em qualquer host (ex: Netlify) que faz o redirecionamento por
dispositivo sozinha.

Este arquivo concentra as rotas (endpoints). A lógica fica dividida em:
  - models.py       -> tabelas do banco (User, QRCode)
  - forms.py        -> formulários e validação de entrada
  - qr_utils.py     -> geração da imagem do QR Code (degradê, logo, borda, texto)
  - security_utils.py -> detecção de dispositivo, controle de tentativas de login
  - extensions.py   -> instâncias de banco/login/csrf/rate-limit
"""
import io
import os
import uuid

from flask import (
    Flask,
    render_template,
    redirect,
    url_for,
    request,
    flash,
    abort,
    send_file,
    Response,
)
from flask_login import (
    login_user,
    logout_user,
    login_required,
    current_user,
)
from PIL import Image
from werkzeug.utils import secure_filename

from sqlalchemy import inspect, text

from config import Config
from extensions import db, login_manager, csrf, limiter
from models import User, QRCode, ROLE_MASTER, ROLE_PADRAO
from forms import RegisterForm, LoginForm, QRCodeForm, DeleteForm
from security_utils import (
    detect_device,
    register_failed_login,
    reset_failed_login,
    MAX_FAILED_ATTEMPTS,
)
from qr_utils import (
    generate_qr_image,
    image_to_bytes,
    resize_logo_to_square,
    add_border_and_caption,
)


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)

    os.makedirs(os.path.join(app.instance_path), exist_ok=True)
    os.makedirs(app.config["QRCODE_FOLDER"], exist_ok=True)
    os.makedirs(app.config["LOGO_FOLDER"], exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    with app.app_context():
        db.create_all()
        _migrate_add_role_column()

    register_routes(app)
    return app


def _migrate_add_role_column() -> None:
    """Migração leve e aditiva: quem já vinha usando uma versão anterior do
    app (sem a coluna "role") não perde o banco de dados. Só adiciona a
    coluna que falta e promove o usuário mais antigo a master, se ainda não
    houver nenhum master cadastrado."""
    inspector = inspect(db.engine)
    if "users" not in inspector.get_table_names():
        return

    columns = {col["name"] for col in inspector.get_columns("users")}
    if "role" not in columns:
        with db.engine.begin() as conn:
            conn.execute(text(
                f"ALTER TABLE users ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT '{ROLE_PADRAO}'"
            ))

    tem_master = User.query.filter_by(role=ROLE_MASTER).first()
    if not tem_master:
        primeiro_usuario = User.query.order_by(User.id.asc()).first()
        if primeiro_usuario:
            primeiro_usuario.role = ROLE_MASTER
            db.session.commit()


def register_routes(app: Flask) -> None:

    # ---------------------------------------------------------------
    # Autenticação
    # ---------------------------------------------------------------

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    @app.route("/registrar", methods=["GET", "POST"])
    @limiter.limit("10 per hour")
    def register():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))

        form = RegisterForm()
        if form.validate_on_submit():
            existing = User.query.filter_by(username=form.username.data).first()
            if existing:
                flash("Usuário já cadastrado.", "danger")
                return render_template("register.html", form=form)

            eh_primeiro_usuario = User.query.count() == 0
            user = User(username=form.username.data, role=ROLE_MASTER if eh_primeiro_usuario else ROLE_PADRAO)
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            flash("Conta criada com sucesso! Faça login.", "success")
            return redirect(url_for("login"))

        return render_template("register.html", form=form)

    @app.route("/login", methods=["GET", "POST"])
    @limiter.limit("15 per 5 minutes")
    def login():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))

        form = LoginForm()
        if form.validate_on_submit():
            identifier = form.username.data
            user = User.query.filter_by(username=identifier).first()

            if user and user.is_locked():
                flash(
                    "Conta temporariamente bloqueada por excesso de tentativas. "
                    "Tente novamente em alguns minutos.",
                    "danger",
                )
                return render_template("login.html", form=form)

            if user and user.check_password(form.password.data):
                reset_failed_login(user)
                db.session.commit()
                login_user(user, remember=form.remember.data)
                flash(f"Bem-vindo(a), {user.username}!", "success")
                return redirect(url_for("dashboard"))

            # Usuário não existe ou senha errada: mesma mensagem genérica,
            # para não revelar qual dos dois estava incorreto.
            if user:
                register_failed_login(user)
                db.session.commit()
            flash("Usuário ou senha inválidos.", "danger")

        return render_template("login.html", form=form)

    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        flash("Você saiu da sua conta.", "info")
        return redirect(url_for("login"))

    # ---------------------------------------------------------------
    # Páginas principais
    # ---------------------------------------------------------------

    @app.route("/")
    def index():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))
        return redirect(url_for("login"))

    @app.route("/dashboard")
    @login_required
    def dashboard():
        # Painel compartilhado: todo usuário logado vê os QR Codes criados
        # por qualquer pessoa. Só editar/excluir é restrito (ver can_manage).
        qrcodes = QRCode.query.order_by(QRCode.created_at.desc()).all()
        delete_form = DeleteForm()
        return render_template("dashboard.html", qrcodes=qrcodes, delete_form=delete_form)

    # ---------------------------------------------------------------
    # CRUD de QR Codes
    # ---------------------------------------------------------------

    def get_qrcode_or_404(slug: str) -> QRCode:
        """Busca o QR Code pelo slug. A visualização é liberada para
        qualquer usuário logado (painel compartilhado); quem pode
        editar/excluir é decidido à parte, por require_manage()."""
        qr = QRCode.query.filter_by(slug=slug).first()
        if qr is None:
            abort(404)
        return qr

    def require_manage(qr: QRCode) -> None:
        """Só o dono do QR Code ou o usuário master podem editar/excluir."""
        if not current_user.can_manage(qr):
            abort(403)

    def require_master() -> None:
        if not current_user.is_master:
            abort(403)

    def qr_encoded_target(app, qr: QRCode) -> str:
        """Decide qual URL fica gravada dentro da imagem do QR Code.

        Se o campo "URL de destino do QR Code" (qr.desktop_url) estiver
        preenchido -- normalmente a página publicada no Netlify -- o QR
        Code aponta direto para ela, e essa página cuida do redirecionamento
        por dispositivo sozinha (sem depender deste servidor local estar no
        ar). Caso contrário, usa o link interno /r/<slug> deste app (só
        funciona enquanto este servidor estiver rodando e acessível).
        """
        return qr.desktop_url or f"{app.config['BASE_URL']}/r/{qr.slug}"

    def save_logo(file_storage, slug: str) -> str:
        """Padroniza (300x300) e salva o logo enviado; retorna o nome do arquivo."""
        image = Image.open(file_storage.stream)
        squared = resize_logo_to_square(image)
        filename = f"{slug}-{uuid.uuid4().hex[:8]}.png"
        squared.save(os.path.join(app.config["LOGO_FOLDER"], filename), format="PNG")
        return filename

    def build_qr_image(qr: QRCode):
        target = qr_encoded_target(app, qr)
        logo_path = None
        if qr.logo_filename:
            candidate = os.path.join(app.config["LOGO_FOLDER"], qr.logo_filename)
            if os.path.exists(candidate):
                logo_path = candidate
        img = generate_qr_image(
            target, qr.color_start, qr.color_end, qr.gradient_direction, logo_path=logo_path
        )
        img = add_border_and_caption(img, qr.border_color, qr.caption_text)
        return img

    @app.route("/qr/novo", methods=["GET", "POST"])
    @login_required
    def qr_new():
        form = QRCodeForm()
        if form.validate_on_submit():
            slug = QRCode.generate_slug()
            qr = QRCode(
                user_id=current_user.id,
                name=form.name.data,
                slug=slug,
                android_url=form.android_url.data or None,
                ios_url=form.ios_url.data or None,
                desktop_url=form.desktop_url.data or None,
                color_start=form.color_start.data,
                color_end=form.color_end.data,
                gradient_direction=form.gradient_direction.data,
                border_color=form.border_color.data,
                caption_text=form.caption_text.data,
            )
            if not (qr.android_url or qr.ios_url or qr.desktop_url):
                flash("Informe pelo menos uma URL de destino (Android, iOS ou alternativa).", "danger")
                return render_template("qr_form.html", form=form, mode="novo")

            if form.logo.data:
                qr.logo_filename = save_logo(form.logo.data, slug)

            db.session.add(qr)
            db.session.commit()
            flash("QR Code criado com sucesso!", "success")
            return redirect(url_for("qr_detail", slug=qr.slug))

        return render_template("qr_form.html", form=form, mode="novo")

    @app.route("/qr/<slug>", methods=["GET"])
    @login_required
    def qr_detail(slug):
        qr = get_qrcode_or_404(slug)
        delete_form = DeleteForm()
        internal_url = f"{app.config['BASE_URL']}/r/{qr.slug}"
        encoded_url = qr_encoded_target(app, qr)
        return render_template(
            "qr_detail.html",
            qr=qr,
            redirect_url=internal_url,
            encoded_url=encoded_url,
            delete_form=delete_form,
            can_manage=current_user.can_manage(qr),
        )

    @app.route("/qr/<slug>/editar", methods=["GET", "POST"])
    @login_required
    def qr_edit(slug):
        qr = get_qrcode_or_404(slug)
        require_manage(qr)
        form = QRCodeForm(obj=qr)
        if request.method == "GET":
            form.remove_logo.data = False
        if form.validate_on_submit():
            qr.name = form.name.data
            qr.android_url = form.android_url.data or None
            qr.ios_url = form.ios_url.data or None
            qr.desktop_url = form.desktop_url.data or None
            qr.color_start = form.color_start.data
            qr.color_end = form.color_end.data
            qr.gradient_direction = form.gradient_direction.data
            qr.border_color = form.border_color.data
            qr.caption_text = form.caption_text.data

            if not (qr.android_url or qr.ios_url or qr.desktop_url):
                flash("Informe pelo menos uma URL de destino (Android, iOS ou alternativa).", "danger")
                return render_template("qr_form.html", form=form, mode="editar", qr=qr)

            if form.logo.data:
                qr.logo_filename = save_logo(form.logo.data, qr.slug)
            elif form.remove_logo.data:
                qr.logo_filename = None

            db.session.commit()
            flash("QR Code atualizado.", "success")
            return redirect(url_for("qr_detail", slug=qr.slug))

        return render_template("qr_form.html", form=form, mode="editar", qr=qr)

    @app.route("/qr/<slug>/excluir", methods=["POST"])
    @login_required
    def qr_delete(slug):
        form = DeleteForm()
        if not form.validate_on_submit():
            abort(400)
        qr = get_qrcode_or_404(slug)
        require_manage(qr)
        db.session.delete(qr)
        db.session.commit()
        flash("QR Code excluído.", "info")
        return redirect(url_for("dashboard"))

    # ---------------------------------------------------------------
    # Gerenciamento de usuários (restrito ao usuário master): permite
    # promover um usuário padrão a master ou rebaixar um master a padrão.
    # ---------------------------------------------------------------

    @app.route("/usuarios")
    @login_required
    def usuarios_list():
        require_master()
        usuarios = User.query.order_by(User.created_at.asc()).all()
        delete_form = DeleteForm()  # reaproveitado só para o token CSRF
        return render_template("usuarios.html", usuarios=usuarios, form=delete_form)

    @app.route("/usuarios/<int:user_id>/papel", methods=["POST"])
    @login_required
    def usuarios_alternar_papel(user_id):
        require_master()
        form = DeleteForm()
        if not form.validate_on_submit():
            abort(400)

        alvo = db.session.get(User, user_id)
        if alvo is None:
            abort(404)

        if alvo.is_master:
            outros_masters = User.query.filter(User.role == ROLE_MASTER, User.id != alvo.id).count()
            if outros_masters == 0:
                flash("Não é possível rebaixar o único usuário master do sistema.", "danger")
                return redirect(url_for("usuarios_list"))
            alvo.role = ROLE_PADRAO
            flash(f'Usuário "{alvo.username}" agora é padrão.', "info")
        else:
            alvo.role = ROLE_MASTER
            flash(f'Usuário "{alvo.username}" agora é master.', "success")

        db.session.commit()
        return redirect(url_for("usuarios_list"))

    # ---------------------------------------------------------------
    # Página estática pronta para publicar no Netlify (ou qualquer host
    # de site estático). Ela faz o redirecionamento por dispositivo sozinha,
    # em JavaScript, usando as URLs de Android/iOS cadastradas aqui.
    # ---------------------------------------------------------------

    @app.route("/qr/<slug>/pagina-netlify")
    @login_required
    def qr_netlify_page(slug):
        require_master()
        qr = get_qrcode_or_404(slug)
        html = render_template(
            "netlify_page.html",
            qr_name=qr.name,
            android_url=qr.android_url,
            ios_url=qr.ios_url,
        )
        return Response(
            html,
            mimetype="text/html",
            headers={"Content-Disposition": "attachment; filename=index.html"},
        )

    # ---------------------------------------------------------------
    # Imagem do QR Code: preview (inline) e exportação (download)
    # ---------------------------------------------------------------

    @app.route("/qr/<slug>/preview.png")
    @login_required
    def qr_preview(slug):
        qr = get_qrcode_or_404(slug)
        img = build_qr_image(qr)
        data = image_to_bytes(img, "PNG")
        return send_file(
            io.BytesIO(data), mimetype="image/png", as_attachment=False, download_name=f"{qr.slug}.png"
        )

    @app.route("/qr/<slug>/download/<fmt>")
    @login_required
    def qr_download(slug, fmt):
        fmt = fmt.lower()
        if fmt not in ("png", "jpg", "pdf"):
            abort(400)
        qr = get_qrcode_or_404(slug)
        img = build_qr_image(qr)
        data = image_to_bytes(img, fmt)
        mimetypes = {"png": "image/png", "jpg": "image/jpeg", "pdf": "application/pdf"}
        safe_name = "".join(c for c in qr.name if c.isalnum() or c in " -_").strip() or qr.slug
        return send_file(
            io.BytesIO(data),
            mimetype=mimetypes[fmt],
            as_attachment=True,
            download_name=f"{safe_name}.{fmt}",
        )

    # ---------------------------------------------------------------
    # Redirecionamento público (o que o celular abre ao ler o QR Code,
    # quando ele não aponta direto para uma página externa/Netlify)
    # ---------------------------------------------------------------

    @app.route("/r/<slug>")
    def public_redirect(slug):
        qr = QRCode.query.filter_by(slug=slug).first()
        if qr is None:
            abort(404)

        device_type = detect_device(request.headers.get("User-Agent", ""))
        target = qr.target_url(device_type)
        if not target:
            abort(404)

        return redirect(target)

    # ---------------------------------------------------------------
    # Páginas de erro
    # ---------------------------------------------------------------

    @app.errorhandler(403)
    def forbidden(_e):
        return render_template("403.html"), 403

    @app.errorhandler(404)
    def not_found(_e):
        return render_template("404.html"), 404

    @app.errorhandler(429)
    def too_many_requests(_e):
        return render_template("429.html"), 429


app = create_app()

if __name__ == "__main__":
    # debug=True apenas em desenvolvimento local!
    app.run(host="0.0.0.0", port=5000, debug=True)
