import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent.parent.parent / "vigia.db"

def conectar_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def inicializar_db():
    with conectar_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS conjuntos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT UNIQUE NOT NULL,
                activo INTEGER DEFAULT 1,
                creado_en TEXT
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                nombre_completo TEXT NOT NULL,
                rol TEXT NOT NULL,
                conjunto_id INTEGER,
                FOREIGN KEY(conjunto_id) REFERENCES conjuntos(id)
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS residentes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                documento TEXT,
                torre TEXT NOT NULL,
                apto TEXT NOT NULL,
                placa TEXT,
                puesto TEXT,
                creado_en TEXT,
                conjunto_id INTEGER,
                FOREIGN KEY(conjunto_id) REFERENCES conjuntos(id)
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS visitantes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                anfitrion TEXT NOT NULL,
                tipo TEXT NOT NULL,
                placa TEXT,
                hora TEXT,
                dentro INTEGER DEFAULT 1,
                conjunto_id INTEGER,
                FOREIGN KEY(conjunto_id) REFERENCES conjuntos(id)
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS domicilios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                empresa TEXT NOT NULL,
                torre TEXT NOT NULL,
                apto TEXT NOT NULL,
                placa TEXT,
                hora TEXT,
                dentro INTEGER DEFAULT 1,
                conjunto_id INTEGER,
                FOREIGN KEY(conjunto_id) REFERENCES conjuntos(id)
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS movimientos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hora TEXT NOT NULL,
                persona TEXT NOT NULL,
                tipo TEXT NOT NULL,
                evento TEXT NOT NULL,
                conjunto_id INTEGER,
                FOREIGN KEY(conjunto_id) REFERENCES conjuntos(id)
            )
        """)
        
        # Conjunto por defecto
        conjunto = db.execute("SELECT id FROM conjuntos WHERE id=1").fetchone()
        if not conjunto:
            db.execute("INSERT INTO conjuntos(id, nombre, activo, creado_en) VALUES(1, 'Conjunto Residencial Principal', 1, ?)", (hora_actual(),))
        
        # Usuario admin por defecto
        admin = db.execute("SELECT id FROM usuarios WHERE username='admin'").fetchone()
        if not admin:
            db.execute("INSERT INTO usuarios(username, password_hash, nombre_completo, rol, conjunto_id) VALUES('admin', 'admin123', 'Administrador General', 'admin', 1)")
            
        db.commit()

def hora_actual():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def guardar_movimiento(persona, tipo, evento, conjunto_id=1):
    with conectar_db() as db:
        db.execute(
            "INSERT INTO movimientos (hora, persona, tipo, evento, conjunto_id) VALUES (?, ?, ?, ?, ?)",
            (hora_actual(), persona, tipo, evento, conjunto_id)
        )
        db.commit()