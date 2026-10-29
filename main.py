from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import sqlite3

from app.core.database import conectar_db, inicializar_db, hora_actual, guardar_movimiento
from app.models.schemas import Residente, Visitante, Domicilio, ConjuntoNuevo, UsuarioLogin, UsuarioNuevo

app = FastAPI(title="SUPRENAMAR - VIGÍA IA Residencial")
inicializar_db()

templates_dir = Path(__file__).parent / "app" / "templates"
app.mount("/static", StaticFiles(directory=str(templates_dir)), name="static")

@app.get("/manifest.json")
def get_manifest():
    return JSONResponse({
        "name": "SUPRENAMAR - Seguridad Privada",
        "short_name": "SUPRENAMAR VIGÍA",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#07111f",
        "theme_color": "#0a1727",
        "icons": [{"src": "/static/logo.png", "sizes": "512x512", "type": "image/png"}]
    })

@app.get("/sw.js")
def get_sw():
    return Response(content="self.addEventListener('install', (e) => self.skipWaiting());", media_type="application/javascript")

@app.post("/api/login")
def login(data: UsuarioLogin):
    with conectar_db() as db:
        user = db.execute("SELECT * FROM usuarios WHERE username=? AND password_hash=? AND conjunto_id=?", 
                          (data.username, data.password, data.conjunto_id)).fetchone()
        if user:
            return {
                "ok": True, 
                "token": "sesion-activa", 
                "rol": user["rol"], 
                "nombre": user["nombre_completo"],
                "conjunto_id": user["conjunto_id"]
            }
        raise HTTPException(status_code=401, detail="Credenciales incorrectas para este conjunto.")

@app.get("/api/conjuntos")
def listar_conjuntos():
    with conectar_db() as db:
        return [dict(r) for r in db.execute("SELECT id, nombre, activo FROM conjuntos WHERE activo=1")]

@app.post("/api/conjuntos")
def crear_conjunto(d: ConjuntoNuevo):
    try:
        with conectar_db() as db:
            cur = db.execute("INSERT INTO conjuntos(nombre, activo, creado_en) VALUES(?,1,?)", (d.nombre.strip(), hora_actual()))
            conjunto_id = cur.lastrowid
            # Crear usuario por defecto para este nuevo conjunto
            db.execute("INSERT INTO usuarios(username, password_hash, nombre_completo, rol, conjunto_id) VALUES(?, ?, ?, 'admin', ?)",
                       (f"admin_{conjunto_id}", "12345", f"Administrador {d.nombre}", conjunto_id))
            db.commit()
            return {"id": conjunto_id, "nombre": d.nombre, "activo": 1}
    except:
        raise HTTPException(status_code=409, detail="Ya existe un conjunto con este nombre.")

def validar_conjunto(db, conjunto_id):
    if not db.execute("SELECT id FROM conjuntos WHERE id=? AND activo=1", (conjunto_id,)).fetchone():
        raise HTTPException(status_code=404, detail="Conjunto no encontrado.")

@app.get("/api/residentes")
def listar_residentes(conjunto_id: int = 1):
    with conectar_db() as db:
        validar_conjunto(db, conjunto_id)
        return [dict(r) for r in db.execute("SELECT * FROM residentes WHERE conjunto_id=? ORDER BY id DESC", (conjunto_id,))]

@app.post("/api/residentes")
def crear_residente(d: Residente, conjunto_id: int = 1):
    with conectar_db() as db:
        validar_conjunto(db, conjunto_id)
        cur = db.execute("INSERT INTO residentes(nombre,documento,torre,apto,placa,puesto,creado_en,conjunto_id) VALUES(?,?,?,?,?,?,?,?)",
            (d.nombre.strip(), d.documento.strip(), d.torre, d.apto.strip(), d.placa.strip(), d.puesto.strip(), hora_actual(), conjunto_id))
        db.commit()
        nuevo_id = cur.lastrowid
    guardar_movimiento(d.nombre.strip(), "Residente", "Registro creado", conjunto_id)
    return {"id": nuevo_id, **d.model_dump(), "conjunto_id": conjunto_id}

@app.get("/api/visitantes")
def listar_visitantes(conjunto_id: int = 1):
    with conectar_db() as db:
        validar_conjunto(db, conjunto_id)
        return [dict(r) for r in db.execute("SELECT * FROM visitantes WHERE conjunto_id=? ORDER BY id DESC", (conjunto_id,))]

@app.post("/api/visitantes")
def crear_visitante(d: Visitante, conjunto_id: int = 1):
    with conectar_db() as db:
        validar_conjunto(db, conjunto_id)
        if not db.execute("SELECT id FROM residentes WHERE nombre=? AND conjunto_id=?", (d.anfitrion, conjunto_id)).fetchone():
            raise HTTPException(status_code=400, detail="Residente no existe en este conjunto.")
        h = hora_actual()
        cur = db.execute("INSERT INTO visitantes(nombre,anfitrion,tipo,placa,hora,dentro,conjunto_id) VALUES(?,?,?,?,?,1,?)",
            (d.nombre.strip(), d.anfitrion, d.tipo, d.placa.strip(), h, conjunto_id))
        db.commit()
        nuevo_id = cur.lastrowid
    guardar_movimiento(d.nombre.strip(), d.tipo, "Entrada registrada", conjunto_id)
    return {"id": nuevo_id, "nombre": d.nombre, "anfitrion": d.anfitrion, "tipo": d.tipo, "placa": d.placa, "hora": h, "dentro": 1, "conjunto_id": conjunto_id}

@app.post("/api/visitantes/{item_id}/salida")
def salida_visitante(item_id: int, conjunto_id: int = 1):
    with conectar_db() as db:
        validar_conjunto(db, conjunto_id)
        r = db.execute("SELECT nombre,tipo,dentro FROM visitantes WHERE id=? AND conjunto_id=?", (item_id, conjunto_id)).fetchone()
        if r and r["dentro"]:
            db.execute("UPDATE visitantes SET dentro=0 WHERE id=? AND conjunto_id=?", (item_id, conjunto_id))
            db.commit()
    if r and r["dentro"]:
        guardar_movimiento(r["nombre"], r["tipo"], "Salida registrada", conjunto_id)
    return {"ok": True}

@app.get("/api/domicilios")
def listar_domicilios(conjunto_id: int = 1):
    with conectar_db() as db:
        validar_conjunto(db, conjunto_id)
        return [dict(r) for r in db.execute("SELECT * FROM domicilios WHERE conjunto_id=? ORDER BY id DESC", (conjunto_id,))]

@app.post("/api/domicilios")
def crear_domicilio(d: Domicilio, conjunto_id: int = 1):
    with conectar_db() as db:
        validar_conjunto(db, conjunto_id)
        h = hora_actual()
        cur = db.execute("INSERT INTO domicilios(nombre,empresa,torre,apto,placa,hora,dentro,conjunto_id) VALUES(?,?,?,?,?,?,1,?)",
            (d.nombre.strip(), d.empresa.strip(), d.torre, d.apto.strip(), d.placa.strip(), h, conjunto_id))
        db.commit()
    guardar_movimiento(d.nombre.strip(), "Domiciliario", f"Ingreso a Torre {d.torre} Apto {d.apto}", conjunto_id)
    return {"ok": True}

@app.get("/api/movimientos")
def listar_movimientos(conjunto_id: int = 1):
    with conectar_db() as db:
        validar_conjunto(db, conjunto_id)
        return [dict(r) for r in db.execute("SELECT * FROM movimientos WHERE conjunto_id=? ORDER BY id DESC LIMIT 100", (conjunto_id,))]

@app.get("/", response_class=HTMLResponse)
def inicio():
    ruta_html = templates_dir / "index.html"
    return ruta_html.read_text(encoding="utf-8")