"""
REST API endpoints para Incidentes.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.dependencies.auth_dependencies import get_current_user
from app.models.user import User
from app.schemas.incidente_schema import IncidenteCreate, IncidenteUpdate, IncidenteResponse, IncidenteListResponse
from app.services.incidente_service import IncidenteService


router = APIRouter(prefix="/api/incidentes", tags=["incidentes"])


def require_almacenero(current_user: User = Depends(get_current_user)) -> User:
    """Verificar que usuario es almacenero"""
    if current_user.role != "almacenero":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo almaceneros pueden acceder a este recurso"
        )
    return current_user


def require_almacenero_o_trabajador(current_user: User = Depends(get_current_user)) -> User:
    """Verificar que usuario es almacenero o trabajador"""
    if current_user.role not in ["almacenero", "trabajador"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo almaceneros y trabajadores pueden acceder"
        )
    return current_user


# ============================================================
# GET - Listar Incidentes
# ============================================================

@router.get("/", response_model=List[IncidenteListResponse])
def listar_incidentes(
    vehiculo_id: int = None,
    tipo: str = None,
    estado: str = None,
    current_user: User = Depends(require_almacenero_o_trabajador),
    db: Session = Depends(get_db)
):
    """
    Listar incidentes activos.

    Filtros opcionales:
    - vehiculo_id: Filtrar por vehículo
    - tipo: colision, choque, volcadura, impacto, dano_estructural, casi_accidente, otro
    - estado: reportado, en_evaluacion, cerrado
    """
    service = IncidenteService(db)

    if vehiculo_id:
        incidentes = service.get_incidentes_by_vehiculo(vehiculo_id)
    elif tipo:
        incidentes = service.get_incidentes_by_tipo(tipo)
    elif estado:
        incidentes = service.get_incidentes_by_estado(estado)
    else:
        incidentes = service.get_all_incidentes()

    return incidentes


# ============================================================
# GET - Obtener detalle de Incidente
# ============================================================

@router.get("/{incidente_id}", response_model=IncidenteResponse)
def obtener_incidente(
    incidente_id: int,
    current_user: User = Depends(require_almacenero_o_trabajador),
    db: Session = Depends(get_db)
):
    """Obtener detalle de un incidente"""
    service = IncidenteService(db)
    incidente = service.get_incidente_by_id(incidente_id)

    if not incidente:
        raise HTTPException(status_code=404, detail="Incidente no encontrado")

    return incidente


# ============================================================
# POST - Crear Incidente
# ============================================================

@router.post("/", response_model=IncidenteResponse, status_code=status.HTTP_201_CREATED)
def crear_incidente(
    schema: IncidenteCreate,
    current_user: User = Depends(require_almacenero_o_trabajador),
    db: Session = Depends(get_db)
):
    """
    Crear nuevo incidente.

    Reglas:
    - Si generar_averia=true o hay_danos=true, puede crear una avería asociada
    - Si hay_personas_afectadas=true, la avería será crítica y bloqueará el vehículo
    """
    service = IncidenteService(db)
    return service.create_incidente(schema, current_user.id)


# ============================================================
# PUT - Actualizar Incidente
# ============================================================

@router.put("/{incidente_id}", response_model=IncidenteResponse)
def actualizar_incidente(
    incidente_id: int,
    schema: IncidenteUpdate,
    current_user: User = Depends(require_almacenero),
    db: Session = Depends(get_db)
):
    """
    Actualizar incidente.

    Transiciones de estado:
    reportado → en_evaluacion → cerrado
    """
    service = IncidenteService(db)
    return service.update_incidente(incidente_id, schema, current_user.id)


# ============================================================
# DELETE - Soft delete de Incidente
# ============================================================

@router.delete("/{incidente_id}", response_model=IncidenteResponse)
def eliminar_incidente(
    incidente_id: int,
    current_user: User = Depends(require_almacenero),
    db: Session = Depends(get_db)
):
    """Soft delete de un incidente (solo almaceneros)"""
    service = IncidenteService(db)
    return service.delete_incidente(incidente_id, current_user.id)


# ============================================================
# GET - Historiales y Reportes
# ============================================================

@router.get("/vehiculo/{vehiculo_id}/historial", response_model=List[IncidenteListResponse])
def historial_incidentes_vehiculo(
    vehiculo_id: int,
    current_user: User = Depends(require_almacenero_o_trabajador),
    db: Session = Depends(get_db)
):
    """Obtener historial de incidentes de un vehículo"""
    service = IncidenteService(db)
    return service.get_incidentes_by_vehiculo(vehiculo_id)


@router.get("/criticos/activos", response_model=List[IncidenteListResponse])
def incidentes_criticos_activos(
    current_user: User = Depends(require_almacenero),
    db: Session = Depends(get_db)
):
    """Obtener incidentes críticos (con personas afectadas)"""
    service = IncidenteService(db)
    return service.get_incidentes_criticos()
