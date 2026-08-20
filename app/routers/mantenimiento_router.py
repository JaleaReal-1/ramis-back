from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.services.mantenimiento_service import MantenimientoService
from app.schemas.mantenimiento_schema import MantenimientoCreate, MantenimientoUpdate, MantenimientoResponse

router = APIRouter(
    prefix="/api/mantenimientos",
    tags=["Mantenimiento"]
)

DbDep = Annotated[Session, Depends(get_db)]

@router.get("/", response_model=list[MantenimientoResponse])
def listar_mantenimientos(db: DbDep):
    service = MantenimientoService(db)
    return service.get_all_mantenimientos()

@router.get("/{id}", response_model=MantenimientoResponse)
def obtener_mantenimiento(id: int, db: DbDep):
    service = MantenimientoService(db)
    return service.get_mantenimiento_by_id(id)

@router.post("/", response_model=MantenimientoResponse, status_code=status.HTTP_201_CREATED)
def crear_mantenimiento(schema: MantenimientoCreate, db: DbDep):
    service = MantenimientoService(db)
    return service.create_mantenimiento(schema)

@router.put("/{id}", response_model=MantenimientoResponse)
def actualizar_mantenimiento(id: int, schema: MantenimientoUpdate, db: DbDep):
    service = MantenimientoService(db)
    return service.update_mantenimiento(id, schema)

@router.delete("/{id}")
def eliminar_mantenimiento(id: int, db: DbDep):
    service = MantenimientoService(db)
    return service.delete_mantenimiento(id)
