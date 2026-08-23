from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.services.vehiculo_service import VehiculoService
from app.schemas.vehiculo_schema import VehiculoCreate, VehiculoUpdate, VehiculoResponse
from app.dependencies.auth_dependencies import get_current_user
from app.models.user import User

router = APIRouter(
    prefix="/api/vehiculos",
    tags=["Vehículos"],
    dependencies=[Depends(get_current_user)]
)

DbDep = Annotated[Session, Depends(get_db)]
CurrentUserDep = Annotated[User, Depends(get_current_user)]

def require_almacenero(user: CurrentUserDep) -> User:
    if user.role != "almacenero":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo el almacenero puede gestionar vehículos.")
    return user

@router.get("/", response_model=list[VehiculoResponse])
def listar_vehiculos(db: DbDep, _: Annotated[User, Depends(require_almacenero)]):
    service = VehiculoService(db)
    return service.get_all_vehiculos()

@router.get("/{id}", response_model=VehiculoResponse)
def obtener_vehiculo(id: int, db: DbDep, _: Annotated[User, Depends(require_almacenero)]):
    service = VehiculoService(db)
    return service.get_vehiculo_by_id(id)

@router.post("/", response_model=VehiculoResponse, status_code=status.HTTP_201_CREATED)
def crear_vehiculo(schema: VehiculoCreate, db: DbDep, _: Annotated[User, Depends(require_almacenero)]):
    service = VehiculoService(db)
    return service.create_vehiculo(schema)

@router.put("/{id}", response_model=VehiculoResponse)
def actualizar_vehiculo(id: int, schema: VehiculoUpdate, db: DbDep, _: Annotated[User, Depends(require_almacenero)]):
    service = VehiculoService(db)
    return service.update_vehiculo(id, schema)

@router.delete("/{id}")
def eliminar_vehiculo(id: int, db: DbDep, user: Annotated[User, Depends(require_almacenero)]):
    service = VehiculoService(db)
    return service.delete_vehiculo(id, user.id)
