from pydantic import BaseModel
from typing import Optional

class Residente(BaseModel):
    nombre: str
    documento: Optional[str] = ""
    torre: str
    apto: str
    placa: Optional[str] = ""
    puesto: Optional[str] = ""

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

class UsuarioNuevo(BaseModel):
    username: str
    password: str
    nombre_completo: str
    rol: str = "guardia"
    conjunto_id: int