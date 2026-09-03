from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.services.inspeccion_service import InspeccionService
from app.schemas.inspeccion_schema import (
    InspeccionCreate,
    InspeccionUpdate,
    InspeccionResponse,
    InspeccionListResponse,
    ChecklistItemResponse,
)
from app.dependencies.auth_dependencies import get_current_user
from app.models.user import User
from app.models.inspeccion import ChecklistItem

router = APIRouter(
    prefix="/api/inspecciones",
    tags=["Inspecciones"],
    dependencies=[Depends(get_current_user)]
)

DbDep = Annotated[Session, Depends(get_db)]
CurrentUserDep = Annotated[User, Depends(get_current_user)]


def require_almacenero_o_trabajador(user: CurrentUserDep) -> User:
    """Permitir almacenero, admin y trabajador"""
    if user.role not in ["almacenero", "admin", "trabajador"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No autorizado para gestionar inspecciones."
        )
    return user


def require_almacenero(user: CurrentUserDep) -> User:
    """Solo almacenero y admin"""
    if user.role not in ["almacenero", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el almacenero puede gestionar inspecciones."
        )
    return user


# ============================================================
# ENDPOINTS CHECKLIST ITEMS
# ============================================================

@router.get("/checklist-items/", response_model=list[ChecklistItemResponse])
def listar_checklist_items(db: DbDep, _: Annotated[User, Depends(require_almacenero_o_trabajador)]):
    """Listar todos los items del checklist activos"""
    items = db.query(ChecklistItem).filter(ChecklistItem.activo == True).order_by(ChecklistItem.orden).all()
    return items


@router.get("/checklist-items/{id}", response_model=ChecklistItemResponse)
def obtener_checklist_item(id: int, db: DbDep, _: Annotated[User, Depends(require_almacenero_o_trabajador)]):
    """Obtener un item del checklist específico"""
    item = db.query(ChecklistItem).filter(ChecklistItem.id == id).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item del checklist no encontrado."
        )
    return item


# ============================================================
# ENDPOINTS INSPECCIONES
# ============================================================

@router.get("/", response_model=list[InspeccionListResponse])
def listar_inspecciones(
    db: DbDep,
    current_user: CurrentUserDep,
    vehiculo_id: int | None = None,
    ruta_id: int | None = None,
):
    """
    Listar inspecciones.

    Filtros opcionales:
    - vehiculo_id: listar inspecciones de un vehículo específico
    - ruta_id: listar inspecciones de una ruta específica

    RBAC:
    - Trabajador: solo sus propias inspecciones
    - Almacenero/Admin: todas
    """
    from app.models.inspeccion import Inspeccion

    service = InspeccionService(db)

    if current_user.role == "trabajador":
        # Los trabajadores solo ven sus propias inspecciones
        query = db.query(Inspeccion).filter(Inspeccion.trabajador_id == current_user.id)
        if vehiculo_id:
            query = query.filter(Inspeccion.vehiculo_id == vehiculo_id)
        if ruta_id:
            query = query.filter(Inspeccion.ruta_id == ruta_id)
        return query.order_by(Inspeccion.fecha.desc()).all()

    # Almacenero y admin ven todas
    if vehiculo_id:
        return service.get_inspecciones_by_vehiculo(vehiculo_id)
    if ruta_id:
        return service.get_inspecciones_by_ruta(ruta_id)

    return service.get_all_inspecciones()


@router.get("/{id}", response_model=InspeccionResponse)
def obtener_inspeccion(
    id: int,
    db: DbDep,
    current_user: CurrentUserDep,
):
    """
    Obtener una inspección específica.

    RBAC:
    - Trabajador: solo si es su inspección
    - Almacenero/Admin: cualquiera
    """
    service = InspeccionService(db)
    inspeccion = service.get_inspeccion_by_id(id)

    if current_user.role == "trabajador" and inspeccion.trabajador_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para ver esta inspección."
        )

    return inspeccion


@router.post("/", response_model=InspeccionResponse, status_code=status.HTTP_201_CREATED)
def crear_inspeccion(
    schema: InspeccionCreate,
    db: DbDep,
    current_user: CurrentUserDep,
):
    """
    Crear una nueva inspección con detalles dinámicos del checklist.

    REGLAS:
    - Si existe un item CRÍTICO con resultado NO_CONFORME, la inspección es RECHAZADA
    - El vehículo queda BLOQUEADO si es inspección SALIDA rechazada
    - El kilometraje debe ser monotónico (nunca decrecer)
    - El trabajador que crea la inspección debe estar asignado a la ruta (si aplica)

    Ejemplo de payload:
    {
        "vehiculo_id": 1,
        "trabajador_id": 1,
        "tipo": "salida",
        "kilometraje": 1000.5,
        "combustible": "3/4",
        "firma": "base64_encoded_signature",
        "observaciones": "Sin novedad",
        "ruta_id": 5,
        "detalles": [
            {"checklist_item_id": 1, "resultado_item": "conforme"},
            {"checklist_item_id": 2, "resultado_item": "observado"},
            {"checklist_item_id": 3, "resultado_item": "no_aplica"}
        ]
    }
    """
    # Validar RBAC: solo almacenero/admin pueden crear inspecciones, o el trabajador su propia inspección
    if current_user.role not in ["almacenero", "admin"]:
        if current_user.role == "trabajador":
            # El trabajador solo puede crear su propia inspección
            if schema.trabajador_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No puedes crear inspecciones para otros trabajadores."
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No autorizado para crear inspecciones."
            )

    service = InspeccionService(db)
    return service.create_inspeccion(schema)


@router.put("/{id}", response_model=InspeccionResponse)
def actualizar_inspeccion(
    id: int,
    schema: InspeccionUpdate,
    db: DbDep,
    current_user: CurrentUserDep,
):
    """Actualizar observaciones de una inspección (operación limitada)"""
    service = InspeccionService(db)
    inspeccion = service.get_inspeccion_by_id(id)

    # RBAC: solo el que la creó o admin
    if current_user.role not in ["almacenero", "admin"]:
        if inspeccion.trabajador_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para actualizar esta inspección."
            )

    return service.update_inspeccion(id, schema)


@router.delete("/{id}")
def eliminar_inspeccion(
    id: int,
    db: DbDep,
    user: Annotated[User, Depends(require_almacenero)],
):
    """Eliminar una inspección (soft delete)"""
    service = InspeccionService(db)
    return service.delete_inspeccion(id, user.id)


# ============================================================
# ENDPOINTS CONSULTAS ESPECIALES
# ============================================================

@router.get("/vehiculo/{vehiculo_id}/historial", response_model=list[InspeccionListResponse])
def historial_inspecciones_vehiculo(
    vehiculo_id: int,
    db: DbDep,
    _: Annotated[User, Depends(require_almacenero_o_trabajador)],
):
    """Obtener historial completo de inspecciones de un vehículo"""
    service = InspeccionService(db)
    return service.get_inspecciones_by_vehiculo(vehiculo_id)


@router.get("/vehiculo/{vehiculo_id}/ultima", response_model=InspeccionResponse | None)
def ultima_inspeccion_vehiculo(
    vehiculo_id: int,
    db: DbDep,
    _: Annotated[User, Depends(require_almacenero_o_trabajador)],
):
    """Obtener la última inspección de un vehículo"""
    service = InspeccionService(db)
    return service.get_ultima_inspeccion_by_vehiculo(vehiculo_id)


@router.get("/ruta/{ruta_id}/inspecciones", response_model=list[InspeccionListResponse])
def inspecciones_por_ruta(
    ruta_id: int,
    db: DbDep,
    current_user: CurrentUserDep,
):
    """Obtener inspecciones asociadas a una ruta específica"""
    service = InspeccionService(db)
    return service.get_inspecciones_by_ruta(ruta_id)
