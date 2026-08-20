from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.services.ruta_service import RutaService
from app.schemas.ruta_asignacion_schema import (
    RutaAsignacionCreate,
    RutaAsignacionUpdate,
    RutaAsignacionResponse,
    RutaAsignacionFinalizar
)

router = APIRouter(
    prefix="/api/rutas",
    tags=["Rutas y Asignaciones"]
)

DbDep = Annotated[Session, Depends(get_db)]

@router.get("/", response_model=list[RutaAsignacionResponse])
def listar_rutas(db: DbDep):
    service = RutaService(db)
    return service.get_all_rutas()

@router.get("/{id}", response_model=RutaAsignacionResponse)
def obtener_ruta(id: int, db: DbDep):
    service = RutaService(db)
    return service.get_ruta_by_id(id)

@router.post("/", response_model=RutaAsignacionResponse, status_code=status.HTTP_201_CREATED)
def crear_ruta(schema: RutaAsignacionCreate, db: DbDep):
    service = RutaService(db)
    return service.create_ruta(schema)

@router.put("/{id}", response_model=RutaAsignacionResponse)
def actualizar_ruta(id: int, schema: RutaAsignacionUpdate, db: DbDep):
    service = RutaService(db)
    return service.update_ruta(id, schema)

@router.patch("/{id}/finalizar", response_model=RutaAsignacionResponse)
def finalizar_ruta(id: int, schema: RutaAsignacionFinalizar, db: DbDep):
    service = RutaService(db)
    return service.finalize_ruta(id, schema)
