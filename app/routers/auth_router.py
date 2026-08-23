from __future__ import annotations

from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status
)

from sqlalchemy.orm import Session

from app.dependencies.auth_dependencies import (
    get_current_user
)
from app.schemas.user_schema import (
    UserCreate,
    UserLogin,
    UserResponse,
    UserUpdate,
    Token
)

from app.schemas.user_schema import (
    UserCreate,
    UserLogin,
    UserResponse,
    Token
)

from app.services.auth_service import AuthService
from app.database.connection import get_db
from app.security.jwt_handler import create_access_token

import traceback


router = APIRouter(
    prefix="/auth",
    tags=["auth"]
)

ALLOWED_ROLES = {
    "user",
    "trabajador",
    "almacenero",
    "admin"
}

DbDep = Annotated[
    Session,
    Depends(get_db)
]

UserDep = Annotated[
    dict,
    Depends(get_current_user)
]


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED
)
def register(
    user_data: UserCreate,
    db: DbDep
):

    service = AuthService(db)

    role = user_data.role or "user"

    if role not in ALLOWED_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Rol no válido. "
                f"Roles permitidos: "
                f"{', '.join(sorted(ALLOWED_ROLES))}"
            )
        )

    if role in [
        "trabajador",
        "almacenero"
    ]:
        if (
            not user_data.dni or
            not user_data.apellidos
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "DNI y apellidos "
                    "son obligatorios "
                    "para este rol"
                )
            )

    try:

        new_user = service.register_user(
            nombre=user_data.nombre,
            apellidos=user_data.apellidos,
            dni=user_data.dni,
            cargo=user_data.cargo,
            email=user_data.email,
            password=user_data.password,
            role=role
        )

        return new_user

    except ValueError as e:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    except Exception:

        print(traceback.format_exc())

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al registrar usuario"
        )


@router.post(
    "/login",
    response_model=Token
)
def login(
    user: UserLogin,
    db: DbDep
):

    service = AuthService(db)

    try:

        auth_user = service.authenticate_user(
            user.email,
            user.password
        )

        if not auth_user:

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales inválidas"
            )

        token = create_access_token(
            {
                "sub": auth_user.email,
                "role": auth_user.role
            }
        )

        return {
            "access_token": token,
            "token_type": "bearer",
            "role": auth_user.role,
            "user": {
                "id": auth_user.id,
                "nombre": auth_user.nombre,
                "apellidos": auth_user.apellidos,
                "dni": auth_user.dni,
                "cargo": auth_user.cargo,
                "email": auth_user.email,
                "codigo_unico": auth_user.codigo_unico
            }
        }

    except HTTPException:
        raise

    except Exception:

        print(traceback.format_exc())

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al autenticar usuario"
        )


@router.get(
    "/trabajadores",
    response_model=list[UserResponse],
    summary="Listar trabajadores y almaceneros"
)
def obtener_trabajadores(
    db: DbDep,
    user: UserDep
):

    if user.role not in [
        "almacenero",
        "admin"
    ]:

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No autorizado"
        )

    service = AuthService(db)

    return service.obtener_trabajadores()
@router.put(
    "/usuario/{user_id}",
    response_model=UserResponse
)
def actualizar_usuario(
    user_id: int,
    data: UserUpdate,
    db: DbDep,
    user: UserDep
):

    if user.role not in [
        "admin"
    ]:

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No autorizado"
        )

    service = AuthService(db)

    try:

        return (
            service.actualizar_usuario(
                user_id=user_id,
                nombre=data.nombre,
                apellidos=data.apellidos,
                dni=data.dni,
                cargo=data.cargo,
                email=data.email,
                usuario_auditoria=user.id
            )
        )

    except ValueError as e:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )