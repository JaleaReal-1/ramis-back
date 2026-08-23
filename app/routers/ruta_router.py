from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.services.ruta_service import RutaService
from app.schemas.ruta_asignacion_schema import (
    RutaAsignacionCreate,
    RutaAsignacionUpdate,
    RutaAsignacionResponse,
    RutaAsignacionFinalizar,
    RutaAsignacionIniciar
)
from app.dependencies.auth_dependencies import get_current_user
from app.models.user import User

router = APIRouter(
    prefix="/api/rutas",
    tags=["Rutas y Asignaciones"],
    dependencies=[Depends(get_current_user)]
)

DbDep = Annotated[Session, Depends(get_db)]
CurrentUserDep = Annotated[User, Depends(get_current_user)]

def require_route_manager(user: CurrentUserDep) -> User:
    if user.role not in ["almacenero", "admin"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No autorizado para gestionar rutas.")
    return user

@router.get("/", response_model=list[RutaAsignacionResponse])
def listar_rutas(db: DbDep, current_user: CurrentUserDep):
    service = RutaService(db)
    if current_user.role == "trabajador":
        return service.get_rutas_by_trabajador(current_user.id)
    if current_user.role not in ["almacenero", "admin"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No autorizado para consultar rutas.")
    return service.get_all_rutas()

@router.get("/{id}", response_model=RutaAsignacionResponse)
def obtener_ruta(id: int, db: DbDep, current_user: CurrentUserDep):
    service = RutaService(db)
    ruta = service.get_ruta_by_id(id)
    if current_user.role == "trabajador" and ruta.trabajador_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No autorizado para consultar esta ruta.")
    if current_user.role not in ["trabajador", "almacenero", "admin"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No autorizado para consultar rutas.")
    return ruta

@router.post("/", response_model=RutaAsignacionResponse, status_code=status.HTTP_201_CREATED)
def crear_ruta(schema: RutaAsignacionCreate, db: DbDep, _: Annotated[User, Depends(require_route_manager)]):
    service = RutaService(db)
    return service.create_ruta(schema)

@router.put("/{id}", response_model=RutaAsignacionResponse)
def actualizar_ruta(id: int, schema: RutaAsignacionUpdate, db: DbDep, _: Annotated[User, Depends(require_route_manager)]):
    service = RutaService(db)
    return service.update_ruta(id, schema)

@router.patch("/{id}/iniciar", response_model=RutaAsignacionResponse)
def iniciar_ruta(
    id: int,
    schema: RutaAsignacionIniciar,
    db: DbDep,
    current_user: CurrentUserDep
):
    service = RutaService(db)
    ruta = service.get_ruta_by_id(id)
    # Validar que el usuario que inicia la ruta sea preferentemente el asignado o al menos un trabajador
    if current_user.role != "trabajador" or current_user.id != ruta.trabajador_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para iniciar esta ruta. Debe ser iniciada por el trabajador asignado."
        )
    return service.iniciar_ruta(id, schema)

@router.delete("/{id}")
def eliminar_ruta(id: int, db: DbDep, user: Annotated[User, Depends(require_route_manager)]):
    service = RutaService(db)
    return service.delete_ruta(id, user.id)

@router.patch("/{id}/finalizar", response_model=RutaAsignacionResponse)
def finalizar_ruta(id: int, schema: RutaAsignacionFinalizar, db: DbDep, current_user: CurrentUserDep):
    ruta = RutaService(db).get_ruta_by_id(id)
    if current_user.role == "trabajador" and ruta.trabajador_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No autorizado para finalizar esta ruta.")
    if current_user.role not in ["trabajador", "almacenero", "admin"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No autorizado para finalizar rutas.")
    service = RutaService(db)
    return service.finalize_ruta(id, schema)
