from flask import current_app

from .db import execute

XP_PER_LEVEL = 100

GARDEN_LEVELS = (
    (0, "Semilla", 1),
    (3, "Brote", 2),
    (7, "Jardín en crecimiento", 4),
    (12, "Jardín floreciente", 6),
    (20, "Jardín ecológico", 9),
)


def garden_level_for_actions(action_count):
    return max(
        level
        for level, (required_actions, _name, _plant_count) in enumerate(
            GARDEN_LEVELS, start=1
        )
        if action_count >= required_actions
    )


def get_garden_action_count(user_id):
    row = execute(
        """SELECT COUNT(*) AS total
           FROM (
               SELECT CAST(a.id AS TEXT) AS action_id
               FROM acciones AS a
               WHERE a.usuario_id = ?
               UNION
               SELECT l.source_code AS action_id
               FROM eco_point_ledger AS l
               WHERE l.user_id = ? AND l.source_type = 'action'
           ) AS completed_actions""",
        (user_id, user_id)
    ).fetchone()
    return row["total"]


def reward_action(user_id, action_id, title, category, description):
    reason = f"{title} · {category}: {description}"
    points = current_app.config["ACTION_REWARD_POINTS"]
    experience_points = current_app.config["ACTION_REWARD_EXPERIENCE"]

    previous = execute(
        "SELECT level FROM eco_progress WHERE user_id = ?",
        (user_id,)
    ).fetchone()
    if previous is None:
        execute("INSERT INTO eco_progress (user_id) VALUES (?)", (user_id,))
        previous_level = 1
    else:
        previous_level = previous["level"]

    ledger_entry = execute(
        """INSERT INTO eco_point_ledger
           (user_id, source_type, source_code, points_delta, experience_delta, reason)
           VALUES (?, 'action', ?, ?, ?, ?)
           ON CONFLICT (user_id, source_type, source_code) DO NOTHING""",
        (user_id, str(action_id), points, experience_points, reason)
    )
    if ledger_entry.rowcount != 1:
        raise RuntimeError("La recompensa de esta acción ya existe.")

    updated = execute(
        """UPDATE eco_progress
           SET points = points + ?, experience = experience + ?
           WHERE user_id = ?""",
        (points, experience_points, user_id)
    )
    if updated.rowcount != 1:
        raise RuntimeError("No se pudo actualizar el progreso del usuario.")

    experience = execute(
        "SELECT experience FROM eco_progress WHERE user_id = ?",
        (user_id,)
    ).fetchone()["experience"]
    level = experience // XP_PER_LEVEL + 1
    execute(
        "UPDATE eco_progress SET level = ? WHERE user_id = ?",
        (level, user_id)
    )
    return {
        "points": points,
        "experience": experience_points,
        "mission_title": f"{category} continua",
        "level": level,
        "leveled_up": level > previous_level,
    }


def level_name(level):
    if level >= 20:
        return "Leyenda ecológica"
    if level >= 10:
        return "Héroe del planeta"
    if level >= 5:
        return "Guardián ecológico"
    if level >= 3:
        return "Protector de la naturaleza"
    if level >= 2:
        return "Aprendiz verde"
    return "Explorador ecológico"


def sync_user_progress(user_id):
    execute(
        "INSERT INTO eco_progress (user_id) VALUES (?) ON CONFLICT (user_id) DO NOTHING",
        (user_id,)
    )
    counts = execute(
        """SELECT
               COUNT(*) AS total,
               SUM(CASE WHEN LOWER(categoria) = 'reciclaje' THEN 1 ELSE 0 END) AS recycling,
               SUM(CASE WHEN LOWER(categoria) IN ('agua', 'ahorro de agua') THEN 1 ELSE 0 END) AS water,
               SUM(CASE WHEN LOWER(categoria) IN ('energía', 'energia') THEN 1 ELSE 0 END) AS energy,
               SUM(CASE WHEN LOWER(categoria) IN
                   ('áreas verdes', 'areas verdes', 'reutilización', 'reutilizacion')
                   THEN 1 ELSE 0 END) AS nature
           FROM acciones
           WHERE usuario_id = ?""",
        (user_id,)
    ).fetchone()
    category_counts = {
        None: counts["total"],
        "reciclaje": counts["recycling"] or 0,
        "agua": counts["water"] or 0,
        "energia": counts["energy"] or 0,
        "naturaleza": counts["nature"] or 0,
    }

    missions = execute("SELECT * FROM eco_missions ORDER BY code").fetchall()
    for mission in missions:
        progress = category_counts[mission["category"]]
        execute(
            """INSERT INTO eco_user_missions (user_id, mission_code, progress)
               VALUES (?, ?, ?)
               ON CONFLICT (user_id, mission_code) DO UPDATE SET
                   progress = excluded.progress""",
            (user_id, mission["code"], progress)
        )

    progress = execute(
        "SELECT points, experience FROM eco_progress WHERE user_id = ?",
        (user_id,)
    ).fetchone()
    level = progress["experience"] // XP_PER_LEVEL + 1
    execute(
        "UPDATE eco_progress SET level = ? WHERE user_id = ?",
        (level, user_id)
    )

    mission_rows = execute(
        """SELECT m.*, um.progress, um.completed_at
           FROM eco_missions AS m
           LEFT JOIN eco_user_missions AS um
             ON um.mission_code = m.code AND um.user_id = ?
           ORDER BY m.code""",
        (user_id,)
    ).fetchall()
    displayed_missions = []
    for mission in mission_rows:
        item = dict(mission)
        item["progress"] = item["progress"] or 0
        displayed_missions.append(item)

    history_rows = execute(
        """SELECT reason, points_delta, experience_delta, created_at
           FROM eco_point_ledger
           WHERE user_id = ?
           ORDER BY created_at DESC
           LIMIT 10""",
        (user_id,)
    ).fetchall()

    return {
        "points": progress["points"],
        "experience": progress["experience"],
        "level": level,
        "level_name": level_name(level),
        "level_progress": progress["experience"] % XP_PER_LEVEL,
        "xp_per_level": XP_PER_LEVEL,
        "points_per_action": current_app.config["ACTION_REWARD_POINTS"],
        "experience_per_action": current_app.config["ACTION_REWARD_EXPERIENCE"],
        "missions": displayed_missions,
        "history": [dict(row) for row in history_rows],
    }


def sync_user_achievements(user_id, progression):
    counts = execute(
        """SELECT COUNT(*) AS total,
                  SUM(CASE WHEN LOWER(categoria) = 'reciclaje' THEN 1 ELSE 0 END) AS recycling
           FROM acciones
           WHERE usuario_id = ?""",
        (user_id,)
    ).fetchone()
    garden_count = execute(
        "SELECT COUNT(*) AS total FROM eco_garden_items WHERE user_id = ?",
        (user_id,)
    ).fetchone()["total"]
    achieved_codes = []
    if counts["total"] >= 1:
        achieved_codes.append("first_action")
    if counts["total"] >= 10:
        achieved_codes.append("actions_10")
    if counts["total"] >= 50:
        achieved_codes.append("actions_50")
    if (counts["recycling"] or 0) >= 10:
        achieved_codes.append("recycling_10")
    if progression["level"] >= 5:
        achieved_codes.append("level_5")
    if garden_count >= 1:
        achieved_codes.append("garden_item")

    for code in achieved_codes:
        execute(
            """INSERT INTO eco_user_achievements (user_id, achievement_code)
               VALUES (?, ?)
               ON CONFLICT (user_id, achievement_code) DO NOTHING""",
            (user_id, code)
        )

    rows = execute(
        """SELECT a.code, a.title, a.description, a.icon, ua.earned_at
           FROM eco_achievements AS a
           LEFT JOIN eco_user_achievements AS ua
             ON ua.achievement_code = a.code AND ua.user_id = ?
           ORDER BY a.code""",
        (user_id,)
    ).fetchall()
    return [
        {**dict(row), "unlocked": row["earned_at"] is not None}
        for row in rows
    ]


def get_garden_data(user_id):
    action_count = get_garden_action_count(user_id)
    item_count = execute(
        "SELECT COUNT(*) AS total FROM eco_garden_items WHERE user_id = ?",
        (user_id,)
    ).fetchone()["total"]
    stage = garden_level_for_actions(action_count)
    required_actions, stage_name, plant_count = GARDEN_LEVELS[stage - 1]
    next_level = stage < len(GARDEN_LEVELS)
    next_actions = GARDEN_LEVELS[stage][0] if next_level else None
    actions_to_next = max(0, next_actions - action_count) if next_level else 0
    if next_level:
        next_level_span = next_actions - required_actions
        progress_percent = int(
            ((action_count - required_actions) / next_level_span) * 100
        )
        action_word = "acción" if actions_to_next == 1 else "acciones"
        growth_message = (
            f"¡Completa {actions_to_next} {action_word} más para que tu jardín crezca!"
        )
    else:
        progress_percent = 100
        growth_message = (
            "¡Tu jardín alcanzó su máximo desarrollo! Sigue completando acciones: "
            "tu progreso y recompensas continúan sin límite."
        )

    plant_styles = ("broadleaf", "flowering", "evergreen", "fruiting", "native")
    plants = [
        {
            "age": min(4, max(0, stage - 1 - index)),
            "style": plant_styles[index % len(plant_styles)],
        }
        for index in range(plant_count)
    ]
    growth_rows = max(1, (max(plant_count, item_count) + 4) // 5)
    garden_items = execute(
        """SELECT gi.id, i.title, i.icon, i.category, gi.placed_at,
                  gi.position_x, gi.position_y
           FROM eco_garden_items AS gi
           JOIN eco_store_items AS i ON i.code = gi.item_code
           WHERE gi.user_id = ?
           ORDER BY gi.id DESC""",
        (user_id,)
    ).fetchall()
    inventory = execute(
        """SELECT i.code, i.title, i.description, i.price, i.icon, i.category,
                  COALESCE(inv.quantity, 0) AS quantity
           FROM eco_store_items AS i
           LEFT JOIN eco_user_inventory AS inv
             ON inv.item_code = i.code AND inv.user_id = ?
           WHERE COALESCE(inv.quantity, 0) > 0
           ORDER BY i.category, i.title""",
        (user_id,)
    ).fetchall()
    return {
        "action_count": action_count,
        "item_count": item_count,
        "stage": stage,
        "stage_name": stage_name,
        "next_actions": next_actions,
        "actions_to_next": actions_to_next,
        "progress_percent": progress_percent,
        "growth_message": growth_message,
        "plant_count": plant_count,
        "growth_rows": growth_rows,
        "scene_height": max(270, 156 + growth_rows * 112),
        "plants": plants,
        "items": [dict(item) for item in garden_items],
        "inventory": [dict(item) for item in inventory],
    }


def get_store_items(user_id):
    rows = execute(
        """SELECT i.code, i.title, i.description, i.price, i.icon, i.category,
                  COALESCE(inv.quantity, 0) AS quantity,
                  COALESCE(placed.quantity, 0) AS placed_quantity,
                  COALESCE(inv.quantity, 0) + COALESCE(placed.quantity, 0)
                      AS owned_quantity
           FROM eco_store_items AS i
           LEFT JOIN eco_user_inventory AS inv
             ON inv.item_code = i.code AND inv.user_id = ?
           LEFT JOIN (
               SELECT item_code, COUNT(*) AS quantity
               FROM eco_garden_items
               WHERE user_id = ?
               GROUP BY item_code
           ) AS placed ON placed.item_code = i.code
           ORDER BY i.category, i.price""",
        (user_id, user_id)
    ).fetchall()
    return [dict(row) for row in rows]
