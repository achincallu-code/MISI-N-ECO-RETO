import os
import sqlite3
from flask import current_app, g

SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(80) NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS acciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo VARCHAR(80) NOT NULL,
    categoria VARCHAR(40) NOT NULL,
    descripcion TEXT NOT NULL,
    propuesto_por VARCHAR(100) NOT NULL,
    fecha DATE,
    impacto VARCHAR(100) DEFAULT '',
    usuario_id INTEGER,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);
CREATE TABLE IF NOT EXISTS eco_action_submissions (
    user_id BIGINT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    token TEXT NOT NULL,
    action_id BIGINT REFERENCES acciones(id) ON DELETE SET NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, token)
);
CREATE INDEX IF NOT EXISTS idx_acciones_usuario_categoria
    ON acciones(usuario_id, categoria);
CREATE TABLE IF NOT EXISTS eco_progress (
    user_id BIGINT PRIMARY KEY REFERENCES usuarios(id) ON DELETE CASCADE,
    points INTEGER NOT NULL DEFAULT 0 CHECK (points >= 0),
    experience INTEGER NOT NULL DEFAULT 0 CHECK (experience >= 0),
    level INTEGER NOT NULL DEFAULT 1 CHECK (level >= 1)
);
CREATE TABLE IF NOT EXISTS eco_missions (
    code TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    category TEXT,
    difficulty TEXT NOT NULL,
    target_count INTEGER NOT NULL CHECK (target_count > 0),
    points_reward INTEGER NOT NULL CHECK (points_reward >= 0),
    experience_reward INTEGER NOT NULL CHECK (experience_reward >= 0),
    icon TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS eco_user_missions (
    user_id BIGINT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    mission_code TEXT NOT NULL REFERENCES eco_missions(code) ON DELETE CASCADE,
    progress INTEGER NOT NULL DEFAULT 0 CHECK (progress >= 0),
    completed_at TIMESTAMP,
    PRIMARY KEY (user_id, mission_code)
);
CREATE TABLE IF NOT EXISTS eco_point_ledger (
    user_id BIGINT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    source_type TEXT NOT NULL,
    source_code TEXT NOT NULL,
    points_delta INTEGER NOT NULL,
    experience_delta INTEGER NOT NULL,
    reason TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, source_type, source_code)
);
CREATE TABLE IF NOT EXISTS eco_achievements (
    code TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    icon TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS eco_user_achievements (
    user_id BIGINT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    achievement_code TEXT NOT NULL REFERENCES eco_achievements(code) ON DELETE CASCADE,
    earned_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, achievement_code)
);
CREATE TABLE IF NOT EXISTS eco_store_items (
    code TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    price INTEGER NOT NULL CHECK (price >= 0),
    icon TEXT NOT NULL,
    category TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS eco_user_inventory (
    user_id BIGINT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    item_code TEXT NOT NULL REFERENCES eco_store_items(code),
    quantity INTEGER NOT NULL DEFAULT 0 CHECK (quantity >= 0),
    PRIMARY KEY (user_id, item_code)
);
CREATE TABLE IF NOT EXISTS eco_garden_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id BIGINT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    item_code TEXT NOT NULL REFERENCES eco_store_items(code),
    position_x REAL NOT NULL DEFAULT 0,
    position_y REAL NOT NULL DEFAULT 0,
    placed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS eco_shop_purchases (
    user_id BIGINT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    token TEXT NOT NULL,
    item_code TEXT NOT NULL REFERENCES eco_store_items(code),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, token)
);
"""

POSTGRES_SCHEMA = """
CREATE TABLE IF NOT EXISTS usuarios (
    id BIGSERIAL PRIMARY KEY,
    username VARCHAR(80) NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS acciones (
    id BIGSERIAL PRIMARY KEY,
    titulo VARCHAR(80) NOT NULL,
    categoria VARCHAR(40) NOT NULL,
    descripcion TEXT NOT NULL,
    propuesto_por VARCHAR(100) NOT NULL,
    fecha DATE,
    impacto VARCHAR(100) DEFAULT '',
    usuario_id BIGINT REFERENCES usuarios(id) ON DELETE SET NULL,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS eco_action_submissions (
    user_id BIGINT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    token TEXT NOT NULL,
    action_id BIGINT REFERENCES acciones(id) ON DELETE SET NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, token)
);
CREATE INDEX IF NOT EXISTS idx_acciones_usuario_categoria
    ON acciones(usuario_id, categoria);
CREATE TABLE IF NOT EXISTS eco_progress (
    user_id BIGINT PRIMARY KEY REFERENCES usuarios(id) ON DELETE CASCADE,
    points INTEGER NOT NULL DEFAULT 0 CHECK (points >= 0),
    experience INTEGER NOT NULL DEFAULT 0 CHECK (experience >= 0),
    level INTEGER NOT NULL DEFAULT 1 CHECK (level >= 1)
);
CREATE TABLE IF NOT EXISTS eco_missions (
    code TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    category TEXT,
    difficulty TEXT NOT NULL,
    target_count INTEGER NOT NULL CHECK (target_count > 0),
    points_reward INTEGER NOT NULL CHECK (points_reward >= 0),
    experience_reward INTEGER NOT NULL CHECK (experience_reward >= 0),
    icon TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS eco_user_missions (
    user_id BIGINT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    mission_code TEXT NOT NULL REFERENCES eco_missions(code) ON DELETE CASCADE,
    progress INTEGER NOT NULL DEFAULT 0 CHECK (progress >= 0),
    completed_at TIMESTAMP,
    PRIMARY KEY (user_id, mission_code)
);
CREATE TABLE IF NOT EXISTS eco_point_ledger (
    user_id BIGINT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    source_type TEXT NOT NULL,
    source_code TEXT NOT NULL,
    points_delta INTEGER NOT NULL,
    experience_delta INTEGER NOT NULL,
    reason TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, source_type, source_code)
);
CREATE TABLE IF NOT EXISTS eco_achievements (
    code TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    icon TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS eco_user_achievements (
    user_id BIGINT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    achievement_code TEXT NOT NULL REFERENCES eco_achievements(code) ON DELETE CASCADE,
    earned_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, achievement_code)
);
CREATE TABLE IF NOT EXISTS eco_store_items (
    code TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    price INTEGER NOT NULL CHECK (price >= 0),
    icon TEXT NOT NULL,
    category TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS eco_user_inventory (
    user_id BIGINT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    item_code TEXT NOT NULL REFERENCES eco_store_items(code),
    quantity INTEGER NOT NULL DEFAULT 0 CHECK (quantity >= 0),
    PRIMARY KEY (user_id, item_code)
);
CREATE TABLE IF NOT EXISTS eco_garden_items (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    item_code TEXT NOT NULL REFERENCES eco_store_items(code),
    position_x DOUBLE PRECISION NOT NULL DEFAULT 0,
    position_y DOUBLE PRECISION NOT NULL DEFAULT 0,
    placed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS eco_shop_purchases (
    user_id BIGINT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    token TEXT NOT NULL,
    item_code TEXT NOT NULL REFERENCES eco_store_items(code),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, token)
);
"""

MISSION_SEEDS = (
    ("first_action", "Acciones ecológicas", "Cada acción nueva suma puntos y experiencia, sin límite.", None, "Continua", 1, 10, 15, "🌱"),
    ("five_actions", "Naturaleza y reutilización", "Cada registro de esta categoría recibe una recompensa.", "naturaleza", "Continua", 1, 10, 15, "🍃"),
    ("recycling_three", "Reciclaje continuo", "Cada nueva acción de reciclaje recibe una recompensa.", "reciclaje", "Continua", 1, 10, 15, "♻️"),
    ("water_three", "Cuidado del agua", "Cada nueva acción de cuidado del agua recibe una recompensa.", "agua", "Continua", 1, 10, 15, "💧"),
    ("energy_three", "Ahorro de energía", "Cada nueva acción de ahorro de energía recibe una recompensa.", "energia", "Continua", 1, 10, 15, "⚡"),
)

ACHIEVEMENT_SEEDS = (
    ("first_action", "Primer paso verde", "Registra tu primera acción ecológica.", "🌱"),
    ("actions_10", "Manos a la obra", "Registra 10 acciones ecológicas.", "🌿"),
    ("actions_50", "Agente del cambio", "Registra 50 acciones ecológicas.", "🌳"),
    ("recycling_10", "Reciclador constante", "Registra 10 acciones de reciclaje.", "♻️"),
    ("level_5", "Guardián del planeta", "Alcanza el nivel 5.", "🛡️"),
    ("garden_item", "Jardín con vida", "Coloca tu primer artículo en el jardín.", "🪴"),
)

STORE_ITEM_SEEDS = (
    ("girasol", "Semilla de girasol", "Una flor alegre para tu jardín.", 25, "🌻", "planta"),
    ("arbol", "Arbolito", "Un pequeño árbol para hacer crecer tu bosque.", 60, "🌳", "planta"),
    ("suculenta", "Suculenta", "Una planta resistente que decora tu espacio.", 35, "🪴", "planta"),
    ("piedra", "Piedra decorativa", "Un detalle natural para el sendero.", 20, "🪨", "decoracion"),
)

def using_postgres():
    return bool(current_app.config.get("DATABASE_URL"))

def get_db():
    if "db" not in g:
        if using_postgres():
            import psycopg
            from psycopg.rows import dict_row
            g.db = psycopg.connect(
                current_app.config["DATABASE_URL"],
                row_factory=dict_row,
                connect_timeout=10
            )
        else:
            db_path = current_app.config["DATABASE_PATH"]
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            g.db = sqlite3.connect(db_path)
            g.db.row_factory = sqlite3.Row
            g.db.execute("PRAGMA foreign_keys = ON")
    return g.db

def execute(sql, params=()):
    """Ejecuta SQL con el controlador configurado y confirma escrituras."""
    db = get_db()
    if using_postgres():
        sql = sql.replace("?", "%s")
        cur = db.cursor()
        cur.execute(sql, params)
        return cur
    cur = db.execute(sql, params)
    return cur

def init_db():
    db = get_db()
    if using_postgres():
        with db.cursor() as cur:
            for statement in POSTGRES_SCHEMA.split(";"):
                if statement.strip():
                    cur.execute(statement)
            cur.execute(
                """ALTER TABLE eco_garden_items
                   ADD COLUMN IF NOT EXISTS position_x DOUBLE PRECISION NOT NULL DEFAULT 0"""
            )
            cur.execute(
                """ALTER TABLE eco_garden_items
                   ADD COLUMN IF NOT EXISTS position_y DOUBLE PRECISION NOT NULL DEFAULT 0"""
            )
            cur.execute(
                """UPDATE eco_garden_items
                   SET position_x = 8 + ((id * 37) % 84),
                       position_y = 58 + ((id * 19) % 26)
                   WHERE position_x = 0 AND position_y = 0"""
            )
            cur.executemany(
                """INSERT INTO eco_missions
                   (code, title, description, category, difficulty, target_count,
                    points_reward, experience_reward, icon)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (code) DO UPDATE SET
                       title = excluded.title,
                       description = excluded.description,
                       category = excluded.category,
                       difficulty = excluded.difficulty,
                       target_count = excluded.target_count,
                       points_reward = excluded.points_reward,
                       experience_reward = excluded.experience_reward,
                       icon = excluded.icon""",
                MISSION_SEEDS
            )
            cur.executemany(
                """INSERT INTO eco_achievements (code, title, description, icon)
                   VALUES (%s, %s, %s, %s)
                   ON CONFLICT (code) DO UPDATE SET
                       title = excluded.title,
                       description = excluded.description,
                       icon = excluded.icon""",
                ACHIEVEMENT_SEEDS
            )
            cur.executemany(
                """INSERT INTO eco_store_items
                   (code, title, description, price, icon, category)
                   VALUES (%s, %s, %s, %s, %s, %s)
                   ON CONFLICT (code) DO UPDATE SET
                       title = excluded.title,
                       description = excluded.description,
                       price = excluded.price,
                       icon = excluded.icon,
                       category = excluded.category""",
                STORE_ITEM_SEEDS
            )
        db.commit()
    else:
        db.executescript(SQLITE_SCHEMA)
        garden_columns = {
            row["name"] for row in db.execute("PRAGMA table_info(eco_garden_items)")
        }
        if "position_x" not in garden_columns:
            db.execute(
                "ALTER TABLE eco_garden_items ADD COLUMN position_x REAL NOT NULL DEFAULT 0"
            )
        if "position_y" not in garden_columns:
            db.execute(
                "ALTER TABLE eco_garden_items ADD COLUMN position_y REAL NOT NULL DEFAULT 0"
            )
        db.execute(
            """UPDATE eco_garden_items
               SET position_x = 8 + ((id * 37) % 84),
                   position_y = 58 + ((id * 19) % 26)
               WHERE position_x = 0 AND position_y = 0"""
        )
        db.executemany(
            """INSERT INTO eco_missions
               (code, title, description, category, difficulty, target_count,
                points_reward, experience_reward, icon)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT (code) DO UPDATE SET
                   title = excluded.title,
                   description = excluded.description,
                   category = excluded.category,
                   difficulty = excluded.difficulty,
                   target_count = excluded.target_count,
                   points_reward = excluded.points_reward,
                   experience_reward = excluded.experience_reward,
                   icon = excluded.icon""",
            MISSION_SEEDS
        )
        db.executemany(
            """INSERT INTO eco_achievements (code, title, description, icon)
               VALUES (?, ?, ?, ?)
               ON CONFLICT (code) DO UPDATE SET
                   title = excluded.title,
                   description = excluded.description,
                   icon = excluded.icon""",
            ACHIEVEMENT_SEEDS
        )
        db.executemany(
            """INSERT INTO eco_store_items
               (code, title, description, price, icon, category)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT (code) DO UPDATE SET
                   title = excluded.title,
                   description = excluded.description,
                   price = excluded.price,
                   icon = excluded.icon,
                   category = excluded.category""",
            STORE_ITEM_SEEDS
        )
        db.commit()

def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()
