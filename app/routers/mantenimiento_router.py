from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.services.mantenimiento_service import MantenimientoService
from app.schemas.mantenimiento_schema import MantenimientoCreate, MantenimientoUpdate, MantenimientoResponse
from app.dependencies.auth_dependencies import get_current_user
from app.models.user import User

router = APIRouter(
    prefix="/api/mantenimientos",
    tags=["Mantenimiento"],
    dependencies=[Depends(get_current_user)]
)

DbDep = Annotated[Session, Depends(get_db)]
CurrentUserDep = Annotated[User, Depends(get_current_user)]

def require_maintenance_manager(user: CurrentUserDep) -> User:
    if user.role not in ["almacenero", "admin"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No autorizado para gestionar mantenimientos.")
    return user

@router.get("/", response_model=list[MantenimientoResponse])
def listar_mantenimientos(db: DbDep, _: Annotated[User, Depends(require_maintenance_manager)]):
    service = MantenimientoService(db)
    return service.get_all_mantenimientos()

@router.get("/{id}", response_model=MantenimientoResponse)
def obtener_mantenimiento(id: int, db: DbDep, _: Annotated[User, Depends(require_maintenance_manager)]):
    service = MantenimientoService(db)
    return service.get_mantenimiento_by_id(id)

@router.post("/", response_model=MantenimientoResponse, status_code=status.HTTP_201_CREATED)
def crear_mantenimiento(schema: MantenimientoCreate, db: DbDep, _: Annotated[User, Depends(require_maintenance_manager)]):
    service = MantenimientoService(db)
    return service.create_mantenimiento(schema)

@router.put("/{id}", response_model=MantenimientoResponse)
def actualizar_mantenimiento(id: int, schema: MantenimientoUpdate, db: DbDep, _: Annotated[User, Depends(require_maintenance_manager)]):
    service = MantenimientoService(db)
    return service.update_mantenimiento(id, schema)

@router.delete("/{id}")
def eliminar_mantenimiento(id: int, db: DbDep, _: Annotated[User, Depends(require_maintenance_manager)]):
    service = MantenimientoService(db)
    return service.delete_mantenimiento(id)
