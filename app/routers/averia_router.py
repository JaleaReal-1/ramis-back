"""
REST API endpoints para Averías.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.dependencies.auth_dependencies import get_current_user
from app.models.user import User
from app.schemas.averia_schema import AveriaCreate, AveriaUpdate, AveriaResponse, AveriaListResponse
from app.services.averia_service import AveriaService


router = APIRouter(prefix="/api/averias", tags=["averias"])


def require_almacenero(current_user: User = Depends(get_current_user)) -> User:
    """Verificar que usuario es almacenero o admin"""
    if current_user.role not in ["almacenero", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo almaceneros pueden acceder a este recurso"
        )
    return current_user


def require_almacenero_o_trabajador(current_user: User = Depends(get_current_user)) -> User:
    """Verificar que usuario es almacenero, trabajador o admin"""
    if current_user.role not in ["almacenero", "trabajador", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo almaceneros y trabajadores pueden acceder"
        )
    return current_user


# ============================================================
# GET - Listar Averías
# ============================================================

@router.get("/", response_model=List[AveriaListResponse])
def listar_averias(
    vehiculo_id: int = None,
    criticidad: str = None,
    estado: str = None,
    current_user: User = Depends(require_almacenero_o_trabajador),
    db: Session = Depends(get_db)
):
    """
    Listar averías activas.

    Filtros opcionales:
    - vehiculo_id: Filtrar por vehículo
    - criticidad: baja, media, alta, critica
    - estado: reportada, en_evaluacion, programada, en_reparacion, resuelta, cerrada
    """
    service = AveriaService(db)

    if vehiculo_id:
        averias = service.get_averias_by_vehiculo(vehiculo_id)
    elif criticidad:
        averias = service.get_averias_by_criticidad(criticidad)
    elif estado:
        averias = service.get_averias_by_estado(estado)
    else:
        averias = service.get_all_averias()

    return averias


# ============================================================
# GET - Obtener detalle de Avería
# ============================================================

@router.get("/{averia_id}", response_model=AveriaResponse)
def obtener_averia(
    averia_id: int,
    current_user: User = Depends(require_almacenero_o_trabajador),
    db: Session = Depends(get_db)
):
    """Obtener detalle de una avería"""
    service = AveriaService(db)
    averia = service.get_averia_by_id(averia_id)

    if not averia:
        raise HTTPException(status_code=404, detail="Avería no encontrada")

    return averia


# ============================================================
# POST - Crear Avería
# ============================================================

@router.post("/", response_model=AveriaResponse, status_code=status.HTTP_201_CREATED)
def crear_averia(
    schema: AveriaCreate,
    current_user: User = Depends(require_almacenero_o_trabajador),
    db: Session = Depends(get_db)
):
    """
    Crear nueva avería.

    Reglas:
    - Si criticidad es "critica", vehículo será bloqueado automáticamente
    """
    service = AveriaService(db)
    return service.create_averia(schema, current_user.id)


# ============================================================
# PUT - Actualizar Avería
# ============================================================

@router.put("/{averia_id}", response_model=AveriaResponse)
def actualizar_averia(
    averia_id: int,
    schema: AveriaUpdate,
    current_user: User = Depends(require_almacenero),
    db: Session = Depends(get_db)
):
    """
    Actualizar avería.

    Transiciones de estado:
    reportada → en_evaluacion → programada → en_reparacion → resuelta → cerrada

    Regla: Si avería es CRÍTICA y pasa a RESUELTA, vehículo se desbloqueará si no hay otras críticas
    """
    service = AveriaService(db)
    return service.update_averia(averia_id, schema, current_user.id)


# ============================================================
# DELETE - Soft delete de Avería
# ============================================================

@router.delete("/{averia_id}", response_model=AveriaResponse)
def eliminar_averia(
    averia_id: int,
    current_user: User = Depends(require_almacenero),
    db: Session = Depends(get_db)
):
    """Soft delete de una avería (solo almaceneros)"""
    service = AveriaService(db)
    return service.delete_averia(averia_id, current_user.id)


# ============================================================
# GET - Historiales y Reportes
# ============================================================

@router.get("/vehiculo/{vehiculo_id}/historial", response_model=List[AveriaListResponse])
def historial_averias_vehiculo(
    vehiculo_id: int,
    current_user: User = Depends(require_almacenero_o_trabajador),
    db: Session = Depends(get_db)
):
    """Obtener historial de averías de un vehículo"""
    service = AveriaService(db)
    return service.get_averias_by_vehiculo(vehiculo_id)


@router.get("/criticas/activas", response_model=List[AveriaListResponse])
def averias_criticas_activas(
    current_user: User = Depends(require_almacenero),
    db: Session = Depends(get_db)
):
    """Obtener averías críticas no resueltas"""
    service = AveriaService(db)
    return service.get_averias_criticas_activas()
