from datetime import date
from functools import wraps
from flask import (
    Blueprint, flash, redirect, render_template, request, session, url_for, abort
)
from werkzeug.security import generate_password_hash, check_password_hash
from .db import execute, get_db, using_postgres

bp = Blueprint("main", __name__)

def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    cur = execute("SELECT id, username FROM usuarios WHERE id = ?", (user_id,))
    return cur.fetchone()

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            flash("Inicia sesión para continuar.", "info")
            return redirect(url_for("main.login"))
        return view(*args, **kwargs)
    return wrapped

def commit():
    get_db().commit()

def get_action(action_id):
    cur = execute("SELECT * FROM acciones WHERE id = ?", (action_id,))
    action = cur.fetchone()
    if action is None:
        abort(404)
    return action

@bp.app_context_processor
def inject_user():
    return {"usuario_actual": current_user(), "today": date.today().isoformat()}

@bp.route("/")
def home():
    if session.get("user_id"):
        return redirect(url_for("main.dashboard"))
    return redirect(url_for("main.login"))

@bp.route("/registro", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        if len(username) < 3:
            flash("El usuario debe tener al menos 3 caracteres.", "error")
        elif len(password) < 8:
            flash("La contraseña debe tener al menos 8 caracteres.", "error")
        elif password != confirm:
            flash("Las contraseñas no coinciden.", "error")
        else:
            try:
                execute(
                    "INSERT INTO usuarios (username, password_hash) VALUES (?, ?)",
                    (username, generate_password_hash(password))
                )
                commit()
                flash("Cuenta creada. Ya puedes iniciar sesión.", "success")
                return redirect(url_for("main.login"))
            except Exception:
                get_db().rollback()
                flash("No se pudo crear la cuenta. Prueba con otro nombre de usuario.", "error")
    return render_template("registro.html")

@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        cur = execute("SELECT * FROM usuarios WHERE username = ?", (username,))
        user = cur.fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            flash("¡Bienvenido a Misión Eco-Reto!", "success")
            return redirect(url_for("main.dashboard"))
        flash("Usuario o contraseña incorrectos.", "error")
    return render_template("login.html")

@bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("Has cerrado sesión.", "info")
    return redirect(url_for("main.login"))

@bp.route("/dashboard")
@login_required
def dashboard():
    search = request.args.get("q", "").strip()
    categoria = request.args.get("categoria", "").strip().lower()
    params = [session["user_id"]]
    sql = "SELECT * FROM acciones WHERE usuario_id = ?"
    if categoria == "agua":
        sql += " AND LOWER(categoria) IN ('agua', 'ahorro de agua')"
    elif categoria == "energia":
        sql += " AND LOWER(categoria) IN ('energía', 'energia')"
    elif categoria:
        sql += " AND LOWER(categoria) = LOWER(?)"
        params.append(categoria)
    if search:
        sql += " AND (LOWER(titulo) LIKE LOWER(?) OR LOWER(categoria) LIKE LOWER(?) OR LOWER(descripcion) LIKE LOWER(?))"
        term = f"%{search}%"
        params.extend([term, term, term])
    sql += " ORDER BY id DESC"
    cur = execute(sql, tuple(params))
    acciones = cur.fetchall()

    cur = execute("SELECT COUNT(*) AS total FROM acciones WHERE usuario_id = ?", (session["user_id"],))
    total = cur.fetchone()["total"]
    cur = execute("SELECT COUNT(*) AS total FROM acciones WHERE usuario_id = ? AND LOWER(categoria) = 'reciclaje'", (session["user_id"],))
    reciclaje = cur.fetchone()["total"]
    cur = execute("SELECT COUNT(*) AS total FROM acciones WHERE usuario_id = ? AND LOWER(categoria) IN ('agua', 'ahorro de agua')", (session["user_id"],))
    agua = cur.fetchone()["total"]
    cur = execute("SELECT COUNT(*) AS total FROM acciones WHERE usuario_id = ? AND LOWER(categoria) IN ('energía', 'energia')", (session["user_id"],))
    energia = cur.fetchone()["total"]
    return render_template(
        "index.html", acciones=acciones, search=search, categoria=categoria, total=total,
        reciclaje=reciclaje, agua=agua, energia=energia
    )

def read_action_form():
    titulo = request.form.get("titulo", "").strip()
    categoria = request.form.get("categoria", "").strip()
    descripcion = request.form.get("descripcion", "").strip()
    fecha = request.form.get("fecha", "").strip() or None
    impacto = request.form.get("impacto", "").strip()
    if not titulo or not categoria or not descripcion:
        return None, "Completa el título, la categoría y la descripción."
    if len(titulo) > 80:
        return None, "El título debe tener máximo 80 caracteres."
    if len(categoria) > 40:
        return None, "La categoría debe tener máximo 40 caracteres."
    return {
        "titulo": titulo, "categoria": categoria, "descripcion": descripcion,
        "fecha": fecha, "impacto": impacto
    }, None

@bp.route("/acciones/nueva", methods=["GET", "POST"])
@login_required
def nueva_accion():
    if request.method == "POST":
        data, error = read_action_form()
        if error:
            flash(error, "error")
        else:
            execute(
                """INSERT INTO acciones
                   (titulo, categoria, descripcion, propuesto_por, fecha, impacto, usuario_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (data["titulo"], data["categoria"], data["descripcion"],
                 session["username"], data["fecha"], data["impacto"], session["user_id"])
            )
            commit()
            flash("Tu acción ecológica se guardó correctamente.", "success")
            return redirect(url_for("main.dashboard"))
    return render_template("formulario.html", accion=None, modo="nueva")

@bp.route("/acciones/<int:action_id>")
@login_required
def detalle(action_id):
    accion = get_action(action_id)
    if accion["usuario_id"] != session["user_id"]:
        abort(403)
    return render_template("detalle.html", accion=accion)

@bp.route("/acciones/<int:action_id>/editar", methods=["GET", "POST"])
@login_required
def editar_accion(action_id):
    accion = get_action(action_id)
    if accion["usuario_id"] != session["user_id"]:
        abort(403)
    if request.method == "POST":
        data, error = read_action_form()
        if error:
            flash(error, "error")
            return render_template("formulario.html", accion=accion, modo="editar")
        execute(
            """UPDATE acciones SET titulo = ?, categoria = ?, descripcion = ?,
               fecha = ?, impacto = ? WHERE id = ? AND usuario_id = ?""",
            (data["titulo"], data["categoria"], data["descripcion"], data["fecha"],
             data["impacto"], action_id, session["user_id"])
        )
        commit()
        flash("La acción se actualizó.", "success")
        return redirect(url_for("main.detalle", action_id=action_id))
    return render_template("formulario.html", accion=accion, modo="editar")

@bp.route("/acciones/<int:action_id>/eliminar", methods=["POST"])
@login_required
def eliminar_accion(action_id):
    accion = get_action(action_id)
    if accion["usuario_id"] != session["user_id"]:
        abort(403)
    execute("DELETE FROM acciones WHERE id = ? AND usuario_id = ?", (action_id, session["user_id"]))
    commit()
    flash("La acción se eliminó.", "info")
    return redirect(url_for("main.dashboard"))
