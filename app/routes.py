from datetime import date
from functools import wraps
import math
import secrets
from flask import (
    Blueprint, flash, redirect, render_template, request, session, url_for, abort
)
from werkzeug.security import generate_password_hash, check_password_hash
from .db import execute, get_db, transaction, using_postgres
from .progression import (
    GARDEN_LEVELS, garden_level_for_actions, get_garden_action_count,
    get_garden_data, get_store_items, reward_action,
    sync_user_achievements, sync_user_progress,
)

bp = Blueprint("main", __name__)


class InsufficientPointsError(Exception):
    pass


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
    with transaction():
        progression = sync_user_progress(session["user_id"])
        achievements = sync_user_achievements(session["user_id"], progression)

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
        reciclaje=reciclaje, agua=agua, energia=energia, progression=progression,
        achievements=achievements,
    )


@bp.route("/jardin")
@login_required
def jardin():
    with transaction():
        progression = sync_user_progress(session["user_id"])
        achievements = sync_user_achievements(session["user_id"], progression)
        garden = get_garden_data(session["user_id"])
    return render_template(
        "jardin.html",
        garden=garden,
        progression=progression,
        achievements=achievements,
    )


@bp.route("/tienda")
@login_required
def tienda():
    with transaction():
        progression = sync_user_progress(session["user_id"])
        store_items = get_store_items(session["user_id"])
    return render_template(
        "tienda.html",
        progression=progression,
        store_items=store_items,
        shop_tokens={item["code"]: secrets.token_urlsafe(32) for item in store_items},
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
        submission_token = request.form.get("submission_token", "").strip()
        data, error = read_action_form()
        if not submission_token or len(submission_token) > 100:
            error = "No se pudo validar el envío. Vuelve a intentarlo."
        if error:
            flash(error, "error")
            return render_template(
                "formulario.html", accion=None, modo="nueva",
                submission_token=submission_token or secrets.token_urlsafe(32)
            )
        with transaction():
            reservation = execute(
                """INSERT INTO eco_action_submissions (user_id, token)
                   VALUES (?, ?)
                   ON CONFLICT (user_id, token) DO NOTHING""",
                (session["user_id"], submission_token)
            )
            duplicate_submission = reservation.rowcount == 0
            if not duplicate_submission:
                garden_level_before = garden_level_for_actions(
                    get_garden_action_count(session["user_id"])
                )
                action = execute(
                    """INSERT INTO acciones
                       (titulo, categoria, descripcion, propuesto_por, fecha, impacto, usuario_id)
                       VALUES (?, ?, ?, ?, ?, ?, ?)
                       RETURNING id""",
                    (data["titulo"], data["categoria"], data["descripcion"],
                     session["username"], data["fecha"], data["impacto"], session["user_id"])
                ).fetchone()
                execute(
                    """UPDATE eco_action_submissions SET action_id = ?
                       WHERE user_id = ? AND token = ?""",
                    (action["id"], session["user_id"], submission_token)
                )
                reward = reward_action(
                    session["user_id"], action["id"], data["titulo"],
                    data["categoria"], data["descripcion"]
                )
                sync_user_progress(session["user_id"])
                garden_level_after = garden_level_for_actions(
                    get_garden_action_count(session["user_id"])
                )

        if duplicate_submission:
            flash("Este envío ya se había registrado; no se creó otra acción.", "info")
            return redirect(url_for("main.dashboard"))
        message = (
            f"¡Acción registrada! +{reward['points']} puntos y "
            f"+{reward['experience']} XP por {reward['mission_title']}."
        )
        if reward["leveled_up"]:
            message += f" ¡Subiste al nivel {reward['level']}!"
        if garden_level_after > garden_level_before:
            garden_name = GARDEN_LEVELS[garden_level_after - 1][1]
            message += f" ¡Tu jardín creció al nivel {garden_level_after}: {garden_name}!"
        flash(message, "success")
        return redirect(url_for("main.dashboard"))
    return render_template(
        "formulario.html", accion=None, modo="nueva",
        submission_token=secrets.token_urlsafe(32)
    )


@bp.route("/tienda/comprar/<item_code>", methods=["POST"])
@login_required
def comprar_articulo(item_code):
    item = execute(
        "SELECT code, title, price FROM eco_store_items WHERE code = ?",
        (item_code,)
    ).fetchone()
    if item is None:
        abort(404)

    token = request.form.get("purchase_token", "").strip()
    if not token or len(token) > 100:
        flash("No se pudo validar la compra. Recarga e inténtalo de nuevo.", "error")
        return redirect(url_for("main.tienda"))

    user_id = session["user_id"]
    duplicate_purchase = False
    insufficient_points = False
    try:
        with transaction():
            reservation = execute(
                """INSERT INTO eco_shop_purchases (user_id, token, item_code)
                   VALUES (?, ?, ?)
                   ON CONFLICT (user_id, token) DO NOTHING""",
                (user_id, token, item_code)
            )
            duplicate_purchase = reservation.rowcount == 0
            if not duplicate_purchase:
                debit = execute(
                    """UPDATE eco_progress SET points = points - ?
                       WHERE user_id = ? AND points >= ?""",
                    (item["price"], user_id, item["price"])
                )
                if debit.rowcount != 1:
                    raise InsufficientPointsError
                execute(
                    """INSERT INTO eco_point_ledger
                       (user_id, source_type, source_code, points_delta,
                        experience_delta, reason)
                       VALUES (?, 'shop_purchase', ?, ?, 0, ?)""",
                    (user_id, token, -item["price"], f"Compra: {item['title']}")
                )
                execute(
                    """INSERT INTO eco_user_inventory (user_id, item_code, quantity)
                       VALUES (?, ?, 1)
                       ON CONFLICT (user_id, item_code) DO UPDATE SET
                           quantity = eco_user_inventory.quantity + 1""",
                    (user_id, item_code)
                )
    except InsufficientPointsError:
        insufficient_points = True

    if insufficient_points:
        flash("No tienes suficientes puntos para esa recompensa.", "error")
    elif duplicate_purchase:
        flash("Esta compra ya se había procesado; no se descontaron puntos otra vez.", "info")
    else:
        flash(f"¡Compraste {item['title']} por {item['price']} puntos!", "success")
    return redirect(url_for("main.tienda"))


def garden_position_from_request():
    try:
        position_x = float(request.form.get("position_x", ""))
        position_y = float(request.form.get("position_y", ""))
    except ValueError:
        flash("Elige un lugar válido dentro del jardín.", "error")
        return None
    if (
        not math.isfinite(position_x)
        or not math.isfinite(position_y)
        or not 5 <= position_x <= 95
        or not 42 <= position_y <= 88
    ):
        flash("Elige un lugar válido dentro de la zona de jardín.", "error")
        return None
    return position_x, position_y


@bp.route("/jardin/colocar/<item_code>", methods=["POST"])
@login_required
def colocar_articulo_jardin(item_code):
    item = execute(
        "SELECT code, title FROM eco_store_items WHERE code = ?",
        (item_code,)
    ).fetchone()
    if item is None:
        abort(404)

    position = garden_position_from_request()
    if position is None:
        return redirect(url_for("main.jardin"))
    position_x, position_y = position

    user_id = session["user_id"]
    with transaction():
        consumed = execute(
            """UPDATE eco_user_inventory SET quantity = quantity - 1
               WHERE user_id = ? AND item_code = ? AND quantity > 0""",
            (user_id, item_code)
        )
        if consumed.rowcount == 1:
            execute(
                """INSERT INTO eco_garden_items
                   (user_id, item_code, position_x, position_y)
                   VALUES (?, ?, ?, ?)""",
                (user_id, item_code, position_x, position_y)
            )

    if consumed.rowcount != 1:
        flash("No tienes ese artículo disponible en tu inventario.", "error")
    else:
        flash(f"¡Colocaste {item['title']} en el lugar que elegiste!", "success")
    return redirect(url_for("main.jardin"))


@bp.route("/jardin/mover/<int:garden_item_id>", methods=["POST"])
@login_required
def mover_articulo_jardin(garden_item_id):
    position = garden_position_from_request()
    if position is None:
        return redirect(url_for("main.jardin"))
    position_x, position_y = position

    with transaction():
        updated = execute(
            """UPDATE eco_garden_items
               SET position_x = ?, position_y = ?
               WHERE id = ? AND user_id = ?""",
            (position_x, position_y, garden_item_id, session["user_id"])
        )
    if updated.rowcount != 1:
        abort(404)

    flash("¡Moviste el objeto a su nueva posición!", "success")
    return redirect(url_for("main.jardin"))


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
