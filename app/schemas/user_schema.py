from __future__ import annotations

from typing import Optional

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
)


class UserCreate(BaseModel):

    nombre: str = Field(
        ...,
        min_length=2,
        description="Nombres"
    )

    apellidos: str = Field(
        ...,
        min_length=2,
        description="Apellidos"
    )

    dni: str = Field(
        ...,
        pattern=r"^\d{8}$",
        description="DNI (8 dígitos numéricos)"
    )

    cargo: Optional[str] = Field(
        default=None,
        description="Cargo del usuario"
    )

    email: EmailStr

    password: str = Field(
        ...,
        min_length=8,
        description="Contraseña (mínimo 8 caracteres)"
    )

    codigo_unico: Optional[str] = Field(
        default=None,
        description="Código único o correlativo (opcional)"
    )

    role: Optional[str] = Field(
        default="user",
        validation_alias=AliasChoices("role", "rol"),
        description=(
            "Rol del usuario. "
            "Opciones válidas: "
            "user, trabajador, almacenero, admin"
        )
    )


class UserLogin(BaseModel):

    email: EmailStr

    password: str = Field(
        ...,
        min_length=8,
        description="Contraseña (mínimo 8 caracteres)"
    )


class UserResponse(BaseModel):

    model_config = ConfigDict(from_attributes=True)

    id: int

    nombre: str

    apellidos: str

    dni: str

    cargo: Optional[str] = None

    email: EmailStr

    codigo_unico: Optional[str] = None

    role: Optional[str] = "user"


class Token(BaseModel):

    access_token: str

    token_type: str = "bearer"

    role: str

    user: UserResponse


class UserUpdate(BaseModel):

    nombre: str = Field(
        ...,
        min_length=2
    )

    apellidos: str = Field(
        ...,
        min_length=2
    )

    dni: str = Field(
        ...,
        pattern=r"^\d{8}$"
    )

    cargo: str | None = None

    email: EmailStr
