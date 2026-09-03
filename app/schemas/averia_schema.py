"""
Schemas Pydantic para Averías.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class AveriaBase(BaseModel):
    """Base schema para Avería"""
    vehiculo_id: int
    ruta_id: Optional[int] = None
    trabajador_id: Optional[int] = None
    inspeccion_id: Optional[int] = None
    categoria: str = Field(..., min_length=1, description="Categoría: Motor, Eléctrico, Carrocería, etc.")
    componente: str = Field(..., min_length=1, description="Componente específico afectado")
    descripcion: str = Field(..., min_length=1, description="Descripción detallada del problema")
    criticidad: str = Field(..., description="baja, media, alta, critica")
    origen: str = Field(..., description="inspeccion_salida, operacion, inspeccion_llegada, mantenimiento")


class AveriaCreate(AveriaBase):
    """Schema para crear Avería"""
    pass


class AveriaUpdate(BaseModel):
    """Schema para actualizar Avería"""
    estado: Optional[str] = Field(None, description="reportada, en_evaluacion, programada, en_reparacion, resuelta, cerrada")
    descripcion: Optional[str] = None
    trabajador_id: Optional[int] = None


class AveriaResponse(AveriaBase):
    """Schema para respuesta de Avería"""
    id: int
    fecha_reporte: datetime
    kilometraje: Optional[float]
    estado: str
    fecha_baja: Optional[datetime] = None
    usuario_baja: Optional[int] = None

    class Config:
        from_attributes = True


class AveriaListResponse(BaseModel):
    """Schema simplificado para lista de Averías"""
    id: int
    vehiculo_id: int
    categoria: str
    componente: str
    criticidad: str
    estado: str
    fecha_reporte: datetime

    class Config:
        from_attributes = True


class AveriaDetailResponse(AveriaResponse):
    """Schema de detalle con información relacionada"""
    pass
