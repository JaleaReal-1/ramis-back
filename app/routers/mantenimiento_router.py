from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.user import User
from app.services.mantenimiento_service import MantenimientoService
from app.schemas.mantenimiento_schema import (
    MantenimientoCorrectivoCreate,
    MantenimientoPreventivoCreate,
    MantenimientoUpdate,
    MantenimientoEjecutar,
    MantenimientoResponse,
    MantenimientoListResponse,
)
from app.dependencies.auth_dependencies import get_current_user

router = APIRouter(prefix="/api/mantenimientos", tags=["Mantenimientos"])

# RBAC Helpers
def require_almacenero(current_user: User = Depends(get_current_user)):
    if current_user.role not in ["almacenero", "admin"]:
        raise HTTPException(status_code=403, detail="Acceso denegado. Se requiere rol almacenero.")
    return current_user

def require_almacenero_o_trabajador(current_user: User = Depends(get_current_user)):
    if current_user.role not in ["almacenero", "trabajador", "admin"]:
        raise HTTPException(status_code=403, detail="Acceso denegado.")
    return current_user

# LISTAR MANTENIMIENTOS
@router.get("/", response_model=list[MantenimientoListResponse])
async def listar_mantenimientos(
    vehiculo_id: int = None,
    tipo: str = None,
    estado: str = None,
    current_user: User = Depends(require_almacenero_o_trabajador),
    db: Session = Depends(get_db),
):
    """Listar mantenimientos con filtros opcionales"""
    service = MantenimientoService(db)

    if vehiculo_id:
        mantenimientos = service.get_mantenimientos_by_vehiculo(vehiculo_id)
    elif tipo:
        mantenimientos = service.get_mantenimientos_by_tipo(tipo)
    elif estado:
        mantenimientos = service.get_mantenimientos_by_estado(estado)
    else:
        mantenimientos = service.get_all_mantenimientos()

    return mantenimientos

# OBTENER DETALLE
@router.get("/{mantenimiento_id}", response_model=MantenimientoResponse)
async def obtener_mantenimiento(
    mantenimiento_id: int,
    current_user: User = Depends(require_almacenero_o_trabajador),
    db: Session = Depends(get_db),
):
    """Obtener detalle de mantenimiento"""
    service = MantenimientoService(db)
    mant = service.get_mantenimiento_by_id(mantenimiento_id)
    if not mant:
        raise HTTPException(status_code=404, detail="Mantenimiento no encontrado")
    return mant

# CREAR MANTENIMIENTO CORRECTIVO
@router.post("/correctivo", response_model=MantenimientoResponse, status_code=201)
async def crear_mantenimiento_correctivo(
    schema: MantenimientoCorrectivoCreate,
    current_user: User = Depends(require_almacenero_o_trabajador),
    db: Session = Depends(get_db),
):
    """Crear mantenimiento CORRECTIVO vinculado a una avería"""
    service = MantenimientoService(db)
    return service.create_mantenimiento_correctivo(schema, current_user.id)

# CREAR MANTENIMIENTO PREVENTIVO
@router.post("/preventivo", response_model=MantenimientoResponse, status_code=201)
async def crear_mantenimiento_preventivo(
    schema: MantenimientoPreventivoCreate,
    current_user: User = Depends(require_almacenero_o_trabajador),
    db: Session = Depends(get_db),
):
    """Crear mantenimiento PREVENTIVO desde plan"""
    service = MantenimientoService(db)
    return service.create_mantenimiento_preventivo(schema, current_user.id)

# EJECUTAR MANTENIMIENTO
@router.patch("/{mantenimiento_id}/ejecutar", response_model=MantenimientoResponse)
async def ejecutar_mantenimiento(
    mantenimiento_id: int,
    schema: MantenimientoEjecutar,
    current_user: User = Depends(require_almacenero),
    db: Session = Depends(get_db),
):
    """Registrar ejecución del mantenimiento"""
    service = MantenimientoService(db)
    return service.ejecutar_mantenimiento(mantenimiento_id, schema, current_user.id)

# ACTUALIZAR MANTENIMIENTO
@router.put("/{mantenimiento_id}", response_model=MantenimientoResponse)
async def actualizar_mantenimiento(
    mantenimiento_id: int,
    schema: MantenimientoUpdate,
    current_user: User = Depends(require_almacenero),
    db: Session = Depends(get_db),
):
    """Actualizar descripción, costo y observaciones"""
    service = MantenimientoService(db)
    return service.update_mantenimiento(mantenimiento_id, schema, current_user.id)

# ELIMINAR MANTENIMIENTO (soft delete)
@router.delete("/{mantenimiento_id}", status_code=204)
async def eliminar_mantenimiento(
    mantenimiento_id: int,
    current_user: User = Depends(require_almacenero),
    db: Session = Depends(get_db),
):
    """Soft delete de mantenimiento"""
    service = MantenimientoService(db)
    service.delete_mantenimiento(mantenimiento_id, current_user.id)

# LISTAR POR VEHÍCULO
@router.get("/vehiculo/{vehiculo_id}/historial", response_model=list[MantenimientoListResponse])
async def historial_mantenimientos_vehiculo(
    vehiculo_id: int,
    current_user: User = Depends(require_almacenero_o_trabajador),
    db: Session = Depends(get_db),
):
    """Obtener historial de mantenimientos de un vehículo"""
    service = MantenimientoService(db)
    return service.get_mantenimientos_by_vehiculo(vehiculo_id)

# LISTAR MANTENIMIENTOS VENCIDOS
@router.get("/reportes/vencidos", response_model=list[MantenimientoListResponse])
async def mantenimientos_vencidos(
    current_user: User = Depends(require_almacenero),
    db: Session = Depends(get_db),
):
    """Obtener todos los mantenimientos VENCIDOS"""
    service = MantenimientoService(db)
    return service.get_mantenimientos_vencidos()
