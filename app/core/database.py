import sqlite3
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "vigia.db"

def conectar_db():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    return db

def inicializar_db():
    with conectar_db() as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS conjuntos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL UNIQUE,
            activo INTEGER NOT NULL DEFAULT 1,
            creado_en TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            nombre_completo TEXT NOT NULL,
            rol TEXT NOT NULL DEFAULT 'guardia',
            conjunto_id INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS alertas_ia (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha_hora TEXT NOT NULL,
            tipo_alerta TEXT NOT NULL,
            descripcion TEXT NOT NULL,
            nivel_riesgo TEXT NOT NULL,
            resuelta INTEGER NOT NULL DEFAULT 0,
            conjunto_id INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS residentes (
            id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT NOT NULL,
            documento TEXT DEFAULT '', torre TEXT NOT NULL, apto TEXT NOT NULL,
            placa TEXT DEFAULT '', puesto TEXT DEFAULT '', creado_en TEXT NOT NULL,
            conjunto_id INTEGER NOT NULL DEFAULT 1,
            foto_url TEXT DEFAULT '', chip_rfid TEXT DEFAULT '');
        CREATE TABLE IF NOT EXISTS visitantes (
            id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT NOT NULL,
            anfitrion TEXT NOT NULL, tipo TEXT NOT NULL, placa TEXT DEFAULT '',
            hora TEXT NOT NULL, dentro INTEGER NOT NULL DEFAULT 1,
            conjunto_id INTEGER NOT NULL DEFAULT 1);
        CREATE TABLE IF NOT EXISTS domicilios (
            id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT NOT NULL,
            empresa TEXT DEFAULT '', torre TEXT NOT NULL, apto TEXT NOT NULL,
            placa TEXT DEFAULT '', hora TEXT NOT NULL, dentro INTEGER NOT NULL DEFAULT 1,
            conjunto_id INTEGER NOT NULL DEFAULT 1);
        CREATE TABLE IF NOT EXISTS movimientos (
            id INTEGER PRIMARY KEY AUTOINCREMENT, hora TEXT NOT NULL,
            persona TEXT NOT NULL, tipo TEXT NOT NULL, evento TEXT NOT NULL,
            conjunto_id INTEGER NOT NULL DEFAULT 1);
        ''')
        
        db.execute("INSERT OR IGNORE INTO conjuntos(nombre, activo, creado_en) VALUES(?,1,?)",
                   ("Conjunto principal", datetime.now().astimezone().isoformat(timespec="seconds")))
        
        # Usuario por defecto para el login
        db.execute("INSERT OR IGNORE INTO usuarios(username, password_hash, nombre_completo, rol, conjunto_id) VALUES(?,?,?,?,?)",
                   ("admin", "admin123", "Administrador / Guardia Principal", "admin", 1))

        # Asegurar columnas si la DB ya existía
        for tabla in ("residentes", "visitantes", "domicilios", "movimientos"):
            columnas = {r[1] for r in db.execute(f"PRAGMA table_info({tabla})")}
            if "conjunto_id" not in columnas:
                db.execute(f"ALTER TABLE {tabla} ADD COLUMN conjunto_id INTEGER NOT NULL DEFAULT 1")
        
        columnas_res = {r[1] for r in db.execute("PRAGMA table_info(residentes)")}
        if "foto_url" not in columnas_res: db.execute("ALTER TABLE residentes ADD COLUMN foto_url TEXT DEFAULT ''")
        if "chip_rfid" not in columnas_res: db.execute("ALTER TABLE residentes ADD COLUMN chip_rfid TEXT DEFAULT ''")

def hora_actual():
    return datetime.now().astimezone().strftime("%H:%M:%S")

def guardar_movimiento(persona, tipo, evento, conjunto_id=1):
    with conectar_db() as db:
        db.execute("INSERT INTO movimientos (hora, persona, tipo, evento, conjunto_id) VALUES (?, ?, ?, ?, ?)",
                   (hora_actual(), persona, tipo, evento, conjunto_id))
