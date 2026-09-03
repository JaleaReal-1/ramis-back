from __future__ import annotations

from app.models.user import User
from app.models.almacen_articulos import AlmacenArticulo
from app.models.almacen_auditoria import AlmacenAuditoria
from app.models.almacen_prestamo import AlmacenPrestamo, AlmacenPrestamoDetalle
from app.models.almacen_devolucion import AlmacenDevolucion
from app.models.vehiculo import Vehiculo
from app.models.ruta_asignacion import RutaAsignacion
from app.models.inspeccion import ChecklistItem, Inspeccion, InspeccionDetalle
from app.models.averia import Averia
from app.models.incidente import Incidente
from app.models.plan_mantenimiento import PlanMantenimiento, PlanMantenimientoDetalle
from app.models.registro_combustible import RegistroCombustible
from app.models.mantenimiento import Mantenimiento
