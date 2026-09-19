from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.database import get_db, es_peticion_demo
from app.models.usuario import Usuario
from app.schemas.usuario import (
    UsuarioLogin,
    TokenOut,
    CambioPassword,
    UsuarioOut,
)
from app.services.auth_service import (
    hash_password,
    verify_password,
    crear_token,
    decodificar_token,
)
from app.services.cache import cache_get, cache_set
from app.services.demo_data import USUARIO_DEMO, asegurar_bd_demo
from app.services.referencias import construir_referencias

router = APIRouter(prefix="/api/auth", tags=["auth"])

security = HTTPBearer(auto_error=False)

REFERENCIAS_KEY_PREFIX = "crm:referencias:"
REFERENCIAS_TTL = 600


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


async def referencias_para_usuario(db: Session, usuario: Usuario, tenant: str = "prod") -> dict:
    """Referencias del usuario, servidas desde caché (Redis o memoria).

    La clave incluye el "tenant" (prod/demo) para que el modo demo nunca
    reutilice referencias cacheadas de la aplicación real.
    """
    key = f"{REFERENCIAS_KEY_PREFIX}{tenant}:{usuario.username}"
    data = cache_get(key)
    if data is None:
        data = await construir_referencias(db, usuario)
        cache_set(key, data, ttl=REFERENCIAS_TTL)
    return data


@router.post("/login", response_model=TokenOut)
async def login(data: UsuarioLogin, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(Usuario.username == data.username).first()
    if not usuario or not verify_password(data.password, usuario.password_hash):
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")
    referencias = await referencias_para_usuario(db, usuario)
    return TokenOut(
        access_token=crear_token(usuario.username),
        username=usuario.username,
        referencias=referencias,
    )


@router.post("/demo-login", response_model=TokenOut)
async def demo_login():
    """Inicia sesión en el modo demo con datos 100% sintéticos.

    La base de datos demo es independiente de la aplicación; el token que se
    devuelve lleva la marca "demo" y get_db enruta todas sus consultas a esa
    base. El usuario no necesita credenciales ni registro.
    """
    db = asegurar_bd_demo()
    try:
        usuario = db.query(Usuario).filter(Usuario.username == USUARIO_DEMO).first()
        if not usuario:
            raise HTTPException(status_code=503, detail="No se pudo preparar el modo demo")
        referencias = await referencias_para_usuario(db, usuario, tenant="demo")
        return TokenOut(
            access_token=crear_token(usuario.username, demo=True),
            username=usuario.username,
            referencias=referencias,
        )
    finally:
        db.close()


@router.get("/me", response_model=UsuarioOut)
def obtener_me(usuario: Usuario = Depends(obtener_usuario_actual)):
    return usuario


@router.get("/referencias")
async def obtener_referencias(
    request: Request,
    usuario: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
):
    tenant = "demo" if es_peticion_demo(request) else "prod"
    return await referencias_para_usuario(db, usuario, tenant=tenant)


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
