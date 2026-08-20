from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class RutaAsignacionBase(BaseModel):
    origen: str = Field(..., description="Lugar de origen")
    destino: str = Field(..., description="Lugar de destino")
    fecha_salida: datetime = Field(..., description="Fecha y hora de salida")
    fecha_llegada_estimada: datetime = Field(..., description="Fecha y hora estimada de llegada")

class RutaAsignacionCreate(RutaAsignacionBase):
    vehiculo_id: int = Field(..., description="ID del vehículo")
    trabajador_id: int = Field(..., description="ID del trabajador")
    kilometraje_salida: float = Field(..., description="Kilometraje al salir")
    combustible_salida: str = Field(..., description="Nivel de combustible al salir")
    observaciones_salida: Optional[str] = Field(default=None, description="Observaciones al salir")

class RutaAsignacionFinalizar(BaseModel):
    kilometraje_llegada: float = Field(..., description="Kilometraje de llegada")
    combustible_llegada: str = Field(..., description="Nivel de combustible de llegada")
    observaciones_llegada: Optional[str] = Field(default=None, description="Observaciones de llegada")

class RutaAsignacionUpdate(BaseModel):
    origen: Optional[str] = None
    destino: Optional[str] = None
    fecha_salida: Optional[datetime] = None
    fecha_llegada_estimada: Optional[datetime] = None
    estado_ruta: Optional[str] = None
    kilometraje_salida: Optional[float] = None
    kilometraje_llegada: Optional[float] = None
    combustible_salida: Optional[str] = None
    combustible_llegada: Optional[str] = None
    observaciones_salida: Optional[str] = None
    observaciones_llegada: Optional[str] = None

class RutaAsignacionResponse(RutaAsignacionBase):
    id: int
    vehiculo_id: int
    trabajador_id: int
    estado_ruta: str
    kilometraje_salida: float
    kilometraje_llegada: Optional[float] = None
    combustible_salida: str
    combustible_llegada: Optional[str] = None
    observaciones_salida: Optional[str] = None
    observaciones_llegada: Optional[str] = None

    class Config:
        from_attributes = True
