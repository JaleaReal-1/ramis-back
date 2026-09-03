from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ============================================================
# ChecklistItem Schemas
# ============================================================

class ChecklistItemBase(BaseModel):
    nombre: str = Field(..., description="Nombre del item del checklist")
    categoria: str = Field(..., description="Categoría (ej: Seguridad, Motor, Iluminación)")
    criticidad: str = Field(
        ...,
        description="Criticidad: baja, media, alta, critica"
    )
    orden: int = Field(default=0, description="Orden de presentación")
    activo: bool = Field(default=True, description="Si el item está activo")


class ChecklistItemCreate(ChecklistItemBase):
    pass


class ChecklistItemUpdate(BaseModel):
    nombre: Optional[str] = None
    categoria: Optional[str] = None
    criticidad: Optional[str] = None
    orden: Optional[int] = None
    activo: Optional[bool] = None


class ChecklistItemResponse(ChecklistItemBase):
    id: int

    class Config:
        from_attributes = True


# ============================================================
# InspeccionDetalle Schemas
# ============================================================

class InspeccionDetalleBase(BaseModel):
    checklist_item_id: int = Field(..., description="ID del item del checklist")
    resultado_item: str = Field(
        ...,
        description="Resultado del item: conforme, observado, no_conforme, no_aplica"
    )


class InspeccionDetalleCreate(InspeccionDetalleBase):
    pass


class InspeccionDetalleResponse(InspeccionDetalleBase):
    id: int
    inspeccion_id: int
    checklist_item: Optional[ChecklistItemResponse] = None

    class Config:
        from_attributes = True


# ============================================================
# Inspeccion Schemas
# ============================================================

class InspeccionBase(BaseModel):
    tipo: str = Field(
        ...,
        description="Tipo de inspección: salida, llegada, extraordinaria, post_accidente, post_mantenimiento"
    )
    kilometraje: float = Field(..., description="Kilometraje del vehículo al momento de la inspección")
    combustible: str = Field(..., description="Nivel de combustible (ej: 1/4, 1/2, 3/4, lleno)")
    observaciones: Optional[str] = Field(
        default=None,
        description="Observaciones generales de la inspección"
    )


class InspeccionCreate(InspeccionBase):
    vehiculo_id: int = Field(..., description="ID del vehículo")
    trabajador_id: int = Field(..., description="ID del trabajador que realiza la inspección")
    ruta_id: Optional[int] = Field(
        default=None,
        description="ID de la ruta asociada (opcional)"
    )
    firma: Optional[str] = Field(
        default=None,
        description="Firma digital en base64 del trabajador"
    )
    detalles: List[InspeccionDetalleCreate] = Field(
        ...,
        description="Lista de resultados de items del checklist"
    )


class InspeccionUpdate(BaseModel):
    observaciones: Optional[str] = None


class InspeccionResponse(InspeccionBase):
    id: int
    vehiculo_id: int
    ruta_id: Optional[int] = None
    trabajador_id: int
    tipo: str
    fecha: datetime
    firma: Optional[str] = None
    resultado: str  # aprobada, aprobada_con_observaciones, rechazada
    detalles: List[InspeccionDetalleResponse] = []

    class Config:
        from_attributes = True


class InspeccionListResponse(BaseModel):
    """Respuesta simplificada para listados"""
    id: int
    vehiculo_id: int
    tipo: str
    fecha: datetime
    resultado: str
    trabajador_id: int
    ruta_id: Optional[int] = None

    class Config:
        from_attributes = True
