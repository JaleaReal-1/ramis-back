"""
Schemas Pydantic para Incidentes.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class IncidenteBase(BaseModel):
    """Base schema para Incidente"""
    vehiculo_id: int
    ruta_id: Optional[int] = None
    trabajador_id: int
    tipo: str = Field(..., description="colision, choque, volcadura, impacto, dano_estructural, casi_accidente, otro")
    ubicacion: str = Field(..., min_length=1, description="Ubicación del incidente")
    descripcion: str = Field(..., min_length=1, description="Descripción del incidente")
    hay_danos: bool = False
    hay_personas_afectadas: bool = False


class IncidenteCreate(IncidenteBase):
    """Schema para crear Incidente"""
    # Opcional: crear avería relacionada
    generar_averia: bool = False
    averia_categoria: Optional[str] = None
    averia_componente: Optional[str] = None
    averia_criticidad: Optional[str] = None
    averia_descripcion: Optional[str] = None


class IncidenteUpdate(BaseModel):
    """Schema para actualizar Incidente"""
    estado: Optional[str] = Field(None, description="reportado, en_evaluacion, cerrado")
    descripcion: Optional[str] = None
    hay_danos: Optional[bool] = None
    hay_personas_afectadas: Optional[bool] = None


class IncidenteResponse(IncidenteBase):
    """Schema para respuesta de Incidente"""
    id: int
    fecha: datetime
    estado: str
    fecha_baja: Optional[datetime] = None
    usuario_baja: Optional[int] = None

    class Config:
        from_attributes = True


class IncidenteListResponse(BaseModel):
    """Schema simplificado para lista de Incidentes"""
    id: int
    vehiculo_id: int
    tipo: str
    fecha: datetime
    ubicacion: str
    estado: str
    hay_danos: bool
    hay_personas_afectadas: bool

    class Config:
        from_attributes = True
