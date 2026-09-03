from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.usuario import Usuario
from app.schemas.usuario import UsuarioLogin, TokenOut, CambioPassword, UsuarioRegistro
from app.services.auth_service import (
    hash_password,
    verify_password,
    crear_token,
    decodificar_token,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])

security = HTTPBearer(auto_error=False)


def requiere_autenticacion(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> str:
    """Valida el token JWT sin consultar la BD. Devuelve el username.

    Se usa como dependencia global de los routers de negocio: sin un
    token valido, cualquier peticion es rechazada con 401.
    """
    if credentials is None:
        raise HTTPException(status_code=401, detail="No autenticado")
    username = decodificar_token(credentials.credentials)
    if not username:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")
    return username


def obtener_usuario_actual(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> Usuario:
    if credentials is None:
        raise HTTPException(status_code=401, detail="No autenticado")
    username = decodificar_token(credentials.credentials)
    if not username:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")
    usuario = db.query(Usuario).filter(Usuario.username == username).first()
    if not usuario:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
    return usuario


@router.post("/login", response_model=TokenOut)
def login(data: UsuarioLogin, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(Usuario.username == data.username).first()
    if not usuario or not verify_password(data.password, usuario.password_hash):
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")
    return TokenOut(access_token=crear_token(usuario.username), username=usuario.username)


@router.post("/register", response_model=TokenOut)
def registrar(data: UsuarioRegistro, db: Session = Depends(get_db)):
    """Registro de usuario (temporal; se retira cuando se indique)."""
    username = data.username.strip()
    if not username:
        raise HTTPException(status_code=400, detail="El usuario no puede estar vacío")
    if not data.password:
        raise HTTPException(status_code=400, detail="La contraseña no puede estar vacía")
    if db.query(Usuario).filter(Usuario.username == username).first():
        raise HTTPException(status_code=400, detail="Ese usuario ya existe")
    usuario = Usuario(username=username, password_hash=hash_password(data.password))
    db.add(usuario)
    db.commit()
    return TokenOut(access_token=crear_token(usuario.username), username=usuario.username)


@router.get("/me", response_model=None)
def obtener_me(usuario: Usuario = Depends(obtener_usuario_actual)):
    return {"id": usuario.id, "username": usuario.username}


@router.post("/cambiar-password")
def cambiar_password(
    data: CambioPassword,
    usuario: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
):
    if not verify_password(data.password_actual, usuario.password_hash):
        raise HTTPException(status_code=400, detail="La contraseña actual es incorrecta")
    if not data.password_nueva:
        raise HTTPException(status_code=400, detail="La nueva contraseña no puede estar vacía")
    usuario.password_hash = hash_password(data.password_nueva)
    db.commit()
    return {"ok": True}
