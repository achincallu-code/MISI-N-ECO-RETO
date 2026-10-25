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
"""

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
        db.commit()
    else:
        db.executescript(SQLITE_SCHEMA)
        db.commit()

def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()
