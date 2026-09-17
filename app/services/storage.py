"""Servicio reutilizable de almacenamiento Cloudflare R2 (API compatible con S3).

Las credenciales y configuración se leen desde variables de entorno:

  R2_ACCOUNT_ID          ID de cuenta de Cloudflare (para armar el endpoint por defecto)
  R2_ACCESS_KEY_ID       Token de acceso R2 (Access Key ID)
  R2_SECRET_ACCESS_KEY   Token de acceso R2 (Secret Access Key)
  R2_BUCKET_NAME         Nombre del bucket
  R2_ENDPOINT            URL del endpoint S3-compatible (opcional; default:
                         https://<account_id>.r2.cloudflarestorage.com)
  R2_PUBLIC_URL          URL pública del bucket (dominio personalizado o r2.dev).
                         Solo afecta a archivos marcados como públicos. (opcional)

El único interface de almacenamiento es ``Almacen`` (quick fix del reporte de
arquitectura: un dueño de la regla público/firmado y un adaptador nulo en
lugar de ``None``). ``obtener_storage()`` nunca devuelve ``None``: sin
credenciales devuelve ``AlmacenNulo`` (lecturas en falso, escrituras lanzan
``AlmacenNoConfigurado``); el resto de la aplicación se mantiene operativa
(los endpoints devuelven 503 con mensaje claro).
"""
import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Protocol

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError


class AlmacenNoConfigurado(Exception):
    pass


class Almacen(Protocol):
    def url_publica(self, key: str) -> str | None: ...

    def url_firmada(self, key: str, expira_segundos: int = 900) -> str: ...

    def url(self, key: str, es_publico: bool, expira_segundos: int = 900) -> str: ...

    def subir(self, key: str, contenido: bytes, content_type: str) -> None: ...

    def eliminar(self, key: str) -> None: ...

    def contenido(self, key: str) -> bytes: ...

    def existe(self, key: str) -> bool: ...


class AlmacenNulo:
    """Adaptador para entornos sin R2 configurado: nada se persiste realmente."""

    def url_publica(self, key: str) -> str | None:
        return None

    def url_firmada(self, key: str, expira_segundos: int = 900) -> str | None:
        return None

    def url(self, key: str, es_publico: bool, expira_segundos: int = 900) -> str | None:
        return None

    def subir(self, key: str, contenido: bytes, content_type: str) -> None:
        raise AlmacenNoConfigurado()

    def eliminar(self, key: str) -> None:
        raise AlmacenNoConfigurado()

    def contenido(self, key: str) -> bytes:
        raise AlmacenNoConfigurado()

    def existe(self, key: str) -> bool:
        return False


@dataclass
class R2Storage:
    account_id: str
    access_key_id: str
    secret_access_key: str
    bucket_name: str
    endpoint_url: str
    public_url: str = ""

    def __post_init__(self):
        self._client = boto3.client(
            "s3",
            endpoint_url=self.endpoint_url or f"https://{self.account_id}.r2.cloudflarestorage.com",
            aws_access_key_id=self.access_key_id,
            aws_secret_access_key=self.secret_access_key,
            config=Config(signature_version="s3v4", retries={"max_attempts": 2}),
        )

    def url_publica(self, key: str) -> str | None:
        if not self.public_url:
            return None
        return f"{self.public_url.rstrip('/')}/{key}"

    def subir(self, key: str, contenido: bytes, content_type: str) -> None:
        self._client.put_object(Bucket=self.bucket_name, Key=key, Body=contenido, ContentType=content_type)

    def eliminar(self, key: str) -> None:
        self._client.delete_object(Bucket=self.bucket_name, Key=key)

    def contenido(self, key: str) -> bytes:
        """Lee el contenido completo de un objeto privado."""
        resp = self._client.get_object(Bucket=self.bucket_name, Key=key)
        return resp["Body"].read()

    def existe(self, key: str) -> bool:
        try:
            self._client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError:
            return False

    def url_firmada(self, key: str, expira_segundos: int = 900) -> str:
        """URL temporal y firmada para leer un objeto privado."""
        return self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket_name, "Key": key},
            ExpiresIn=expira_segundos,
        )

    def url(self, key: str, es_publico: bool, expira_segundos: int = 900) -> str:
        """Regla única: URL pública si está disponible y el archivo es público;
        en cualquier otro caso, URL firmada."""
        if es_publico:
            publica = self.url_publica(key)
            if publica:
                return publica
        return self.url_firmada(key, expira_segundos)


@lru_cache(maxsize=1)
def obtener_storage() -> Almacen:
    """Devuelve la instancia configurada de Almacen; AlmacenNulo si faltan credenciales."""
    account_id = os.getenv("R2_ACCOUNT_ID", "").strip()
    access_key = os.getenv("R2_ACCESS_KEY_ID", "").strip()
    secret = os.getenv("R2_SECRET_ACCESS_KEY", "").strip()
    bucket = os.getenv("R2_BUCKET_NAME", "").strip()
    if not (account_id and access_key and secret and bucket):
        return AlmacenNulo()
    return R2Storage(
        account_id=account_id,
        access_key_id=access_key,
        secret_access_key=secret,
        bucket_name=bucket,
        endpoint_url=os.getenv("R2_ENDPOINT", "").strip(),
        public_url=os.getenv("R2_PUBLIC_URL", "").strip(),
    )