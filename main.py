from fastapi import FastAPI, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pathlib import Path
from pydantic import BaseModel
from typing import Optional
import sqlite3

app = FastAPI(title="SUPRENAMAR VIGÍA IA", version="2.1")

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "vigia.db"

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "app" / "static")), name="static")

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
                foto_rostro TEXT,
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
        
        conjunto = db.execute("SELECT id FROM conjuntos WHERE id=1").fetchone()
        if not conjunto:
            db.execute("INSERT INTO conjuntos(id, nombre, activo, creado_en) VALUES(1, 'Conjunto Residencial Principal', 1, datetime('now'))")
        
        admin = db.execute("SELECT id FROM usuarios WHERE username='admin'").fetchone()
        if not admin:
            db.execute("INSERT INTO usuarios(username, password_hash, nombre_completo, rol, conjunto_id) VALUES('admin', '12345', 'Administrador General', 'admin', 1)")
            
        db.commit()

inicializar_db()

class Residente(BaseModel):
    nombre: str
    documento: Optional[str] = ""
    torre: str
    apto: str
    placa: Optional[str] = ""
    puesto: Optional[str] = ""
    foto_rostro: Optional[str] = ""

class Visitante(BaseModel):
    nombre: str
    anfitrion: str
    tipo: str = "Visitante"
    placa: Optional[str] = ""

class Domicilio(BaseModel):
    nombre: str
    empresa: str
    torre: str
    apto: str
    placa: Optional[str] = ""

class ConjuntoNuevo(BaseModel):
    nombre: str

class UsuarioLogin(BaseModel):
    username: str
    password: str
    conjunto_id: int

def validar_conjunto(db, conjunto_id: int):
    c = db.execute("SELECT id FROM conjuntos WHERE id = ?", (conjunto_id,)).fetchone()
    if not c:
        raise HTTPException(status_code=404, detail="Conjunto residencial no encontrado")

@app.get("/")
def read_index():
    return FileResponse(str(BASE_DIR / "app" / "templates" / "index.html"))

@app.get("/manifest.json")
def manifest():
    return {
        "name": "SUPRENAMAR VIGÍA IA",
        "short_name": "SUPRENAMAR",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#07111f",
        "theme_color": "#0a1727",
        "icons": [{"src": "/static/logo.png", "sizes": "192x192", "type": "image/png"}]
    }

@app.get("/api/conjuntos")
def listar_conjuntos():
    with conectar_db() as db:
        res = db.execute("SELECT id, nombre FROM conjuntos WHERE activo=1").fetchall()
        return [dict(row) for row in res]

@app.post("/api/conjuntos")
def crear_conjunto(d: ConjuntoNuevo):
    with conectar_db() as db:
        try:
            cur = db.execute("INSERT INTO conjuntos(nombre, creado_en) VALUES(?, datetime('now'))", (d.nombre.strip(),))
            conjunto_id = cur.lastrowid
            db.execute("INSERT INTO usuarios(username, password_hash, nombre_completo, rol, conjunto_id) VALUES(?, ?, ?, ?, ?)",
                (f"admin_{conjunto_id}", "12345", f"Administrador {d.nombre.strip()}", "admin", conjunto_id))
            db.commit()
            return {"id": conjunto_id, "nombre": d.nombre.strip()}
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=400, detail="El conjunto ya existe.")

@app.post("/api/login")
def login_sistema(d: UsuarioLogin):
    with conectar_db() as db:
        user = db.execute("SELECT * FROM usuarios WHERE username = ? AND conjunto_id = ?", (d.username.strip(), d.conjunto_id)).fetchone()
        if not user or user["password_hash"] != d.password.strip():
            raise HTTPException(status_code=401, detail="Credenciales incorrectas o no autorizadas para este conjunto.")
        return {"mensaje": "Acceso concedido", "nombre": user["nombre_completo"], "rol": user["rol"], "conjunto_id": user["conjunto_id"]}

@app.get("/api/residentes")
def listar_residentes(conjunto_id: int = 1):
    with conectar_db() as db:
        validar_conjunto(db, conjunto_id)
        res = db.execute("SELECT * FROM residentes WHERE conjunto_id = ? ORDER BY id DESC", (conjunto_id,)).fetchall()
        return [dict(row) for row in res]

@app.post("/api/residentes")
def crear_residente(d: Residente, conjunto_id: int = 1):
    with conectar_db() as db:
        validar_conjunto(db, conjunto_id)
        cur = db.execute("INSERT INTO residentes(nombre,documento,torre,apto,placa,puesto,foto_rostro,creado_en,conjunto_id) VALUES(?,?,?,?,?,?,?,?,datetime('now'))",
            (d.nombre.strip(), d.documento.strip(), d.torre, d.apto.strip(), d.placa.strip(), d.puesto.strip(), d.foto_rostro, conjunto_id))
        db.commit()
        nuevo_id = cur.lastrowid
    
    with conectar_db() as db:
        db.execute("INSERT INTO movimientos (hora, persona, tipo, evento, conjunto_id) VALUES (datetime('now', 'localtime'), ?, 'Residente', 'Registro biométrico facial guardado', ?)", (d.nombre.strip(), conjunto_id))
        db.commit()
        
    return {"id": nuevo_id, **d.model_dump(), "conjunto_id": conjunto_id}

@app.get("/api/movimientos")
def listar_movimientos(conjunto_id: int = 1):
    with conectar_db() as db:
        validar_conjunto(db, conjunto_id)
        res = db.execute("SELECT * FROM movimientos WHERE conjunto_id = ? ORDER BY id DESC LIMIT 30", (conjunto_id,)).fetchall()
        return [dict(row) for row in res]

@app.post("/api/visitantes")
def crear_visitante(d: Visitante, conjunto_id: int = 1):
    with conectar_db() as db:
        validar_conjunto(db, conjunto_id)
        db.execute("INSERT INTO visitantes(nombre,anfitrion,tipo,placa,hora,conjunto_id) VALUES(?,?,?,?,datetime('now', 'localtime'),?)",
            (d.nombre.strip(), d.anfitrion, d.tipo, d.placa.strip(), conjunto_id))
        db.commit()
    with conectar_db() as db:
        db.execute("INSERT INTO movimientos (hora, persona, tipo, evento, conjunto_id) VALUES (datetime('now', 'localtime'), ?, 'Visitante', 'Ingreso autorizado a ' || ?, ?)", (d.nombre.strip(), d.anfitrion, conjunto_id))
        db.commit()
    return {"status": "ok"}

@app.post("/api/domicilios")
def crear_domicilio(d: Domicilio, conjunto_id: int = 1):
    with conectar_db() as db:
        validar_conjunto(db, conjunto_id)
        db.execute("INSERT INTO domicilios(nombre,empresa,torre,apto,placa,hora,conjunto_id) VALUES(?,?,?,?,?,datetime('now', 'localtime'),?)",
            (d.nombre.strip(), d.empresa.strip(), d.torre, d.apto.strip(), d.placa.strip(), conjunto_id))
        db.commit()
    with conectar_db() as db:
        db.execute("INSERT INTO movimientos (hora, persona, tipo, evento, conjunto_id) VALUES (datetime('now', 'localtime'), ?, 'Domiciliario', 'Ruta autorizada Torre ' || ?, ?)", (d.nombre.strip(), d.torre, conjunto_id))
        db.commit()
    return {"status": "ok"}