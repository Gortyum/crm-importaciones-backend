from pydantic import BaseModel


class UsuarioLogin(BaseModel):
    username: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str


class UsuarioOut(BaseModel):
    id: int
    username: str

    model_config = {"from_attributes": True}


class CambioPassword(BaseModel):
    password_actual: str
    password_nueva: str


class UsuarioRegistro(BaseModel):
    username: str
    password: str
