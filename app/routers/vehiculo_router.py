from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.services.vehiculo_service import VehiculoService
from app.schemas.vehiculo_schema import VehiculoCreate, VehiculoUpdate, VehiculoResponse

router = APIRouter(
    prefix="/api/vehiculos",
    tags=["Vehículos"]
)

DbDep = Annotated[Session, Depends(get_db)]

@router.get("/", response_model=list[VehiculoResponse])
def listar_vehiculos(db: DbDep):
    service = VehiculoService(db)
    return service.get_all_vehiculos()

@router.get("/{id}", response_model=VehiculoResponse)
def obtener_vehiculo(id: int, db: DbDep):
    service = VehiculoService(db)
    return service.get_vehiculo_by_id(id)

@router.post("/", response_model=VehiculoResponse, status_code=status.HTTP_201_CREATED)
def crear_vehiculo(schema: VehiculoCreate, db: DbDep):
    service = VehiculoService(db)
    return service.create_vehiculo(schema)

@router.put("/{id}", response_model=VehiculoResponse)
def actualizar_vehiculo(id: int, schema: VehiculoUpdate, db: DbDep):
    service = VehiculoService(db)
    return service.update_vehiculo(id, schema)

@router.delete("/{id}")
def eliminar_vehiculo(id: int, db: DbDep):
    service = VehiculoService(db)
    return service.delete_vehiculo(id)
