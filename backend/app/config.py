"""Configuracion de la aplicacion leida desde variables de entorno."""

import json
from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Variables de entorno del backend.

    Los nombres en minusculas se leen de variables en mayusculas:
    mongo_url <- MONGO_URL.
    """

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Deskly API"
    version: str = "1.0.0"
    entorno: str = "dev"
    log_level: str = "INFO"

    mongo_url: str = "mongodb://localhost:27017"
    mongo_db: str = "deskly"

    redis_url: str = "redis://localhost:6379/0"

    cors_origins: str = "http://localhost:3000"

    # Secreto unico del brief. Se usa como fallback si no hay clientes registrados.
    webhook_secret: str = ""
    # JSON: {"crm_acme": "secreto"} o {"crm_acme": ["nuevo", "anterior"]}
    webhook_clientes: str = ""
    webhook_tolerancia_segundos: int = 300
    webhook_max_body_bytes: int = Field(default=256 * 1024, gt=0)

    rate_limit_cliente_por_segundo: int = Field(default=50, gt=0)
    rate_limit_cliente_rafaga: int = Field(default=50, gt=0)
    rate_limit_ip_por_segundo: int = Field(default=100, gt=0)
    rate_limit_ip_rafaga: int = Field(default=100, gt=0)

    request_id_header: str = "X-Request-ID"

    # Siembra 12 tickets de ejemplo cuando la base esta vacia. Se apaga en
    # produccion con SEED_ON_START=false.
    seed_on_start: bool = True

    @field_validator("log_level")
    @classmethod
    def validar_nivel_log(cls, valor: str) -> str:
        niveles = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        nivel = valor.upper()
        if nivel not in niveles:
            raise ValueError(f"LOG_LEVEL invalido: {valor}. Use uno de {sorted(niveles)}")
        return nivel

    @property
    def cors_origins_list(self) -> list[str]:
        return [origen.strip() for origen in self.cors_origins.split(",") if origen.strip()]

    @property
    def clientes_webhook(self) -> dict[str, list[str]]:
        """Clientes autorizados con uno o dos secretos (rotacion).

        Un cliente nunca debe quedar sin secreto: si el JSON es invalido,
        la aplicacion falla al arrancar en vez de aceptar requests sin verificar.
        """
        if not self.webhook_clientes.strip():
            return {}

        try:
            crudo = json.loads(self.webhook_clientes)
        except json.JSONDecodeError as exc:
            raise ValueError(f"WEBHOOK_CLIENTES no es JSON valido: {exc}") from exc

        if not isinstance(crudo, dict):
            raise ValueError("WEBHOOK_CLIENTES debe ser un objeto JSON")

        clientes: dict[str, list[str]] = {}
        for cliente_id, secretos in crudo.items():
            if isinstance(secretos, str):
                lista = [secretos]
            elif isinstance(secretos, list) and all(isinstance(s, str) for s in secretos):
                lista = secretos
            else:
                raise ValueError(
                    f"El cliente '{cliente_id}' debe tener un secreto o una lista de secretos"
                )
            if not lista or any(not secreto for secreto in lista):
                raise ValueError(f"El cliente '{cliente_id}' tiene un secreto vacio")
            clientes[cliente_id] = lista
        return clientes

    @property
    def webhook_configurado(self) -> bool:
        return bool(self.webhook_secret) or bool(self.clientes_webhook)


@lru_cache
def get_settings() -> Settings:
    return Settings()
