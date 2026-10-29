from pydantic import BaseModel
from typing import Optional

class UsuarioLogin(BaseModel):
    username: str
    password: str

class Residente(BaseModel):
    nombre: str
    documento: str = ""
    torre: str
    apto: str
    placa: str = ""
    puesto: str = ""
    foto_url: Optional[str] = ""
    chip_rfid: Optional[str] = ""

class Visitante(BaseModel):
    nombre: str
    anfitrion: str
    tipo: str = "Peatonal"
    placa: str = ""

class Domicilio(BaseModel):
    nombre: str
    empresa: str = ""
    torre: str
    apto: str
    placa: str = ""

class ConjuntoNuevo(BaseModel):
    nombre: str
