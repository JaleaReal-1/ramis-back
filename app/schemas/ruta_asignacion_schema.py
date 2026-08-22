from pydantic import BaseModel, Field, field_validator
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
    observaciones_salida: Optional[str] = Field(default=None, description="Observaciones al salir")

class RutaAsignacionIniciar(BaseModel):
    firma_trabajador: str = Field(..., description="Firma en base64 del trabajador")
    check_llantas: bool = Field(..., description="Inspección de llantas")
    check_frenos: bool = Field(..., description="Inspección de frenos")
    check_luces: bool = Field(..., description="Inspección de luces")
    kilometraje_salida: float = Field(..., description="Kilometraje de salida")
    combustible_salida: str = Field(..., description="Nivel de combustible de salida")
    observaciones_salida: Optional[str] = Field(default=None, description="Observaciones al salir")

    @field_validator("check_llantas", "check_frenos", "check_luces", mode="after")
    @classmethod
    def validate_checks(cls, v: bool) -> bool:
        if v is not True:
            raise ValueError("Todos los checks de inspección deben ser aprobados (True).")
        return v

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
    firma_trabajador: Optional[str] = None
    check_llantas: Optional[bool] = None
    check_frenos: Optional[bool] = None
    check_luces: Optional[bool] = None

class RutaAsignacionResponse(RutaAsignacionBase):
    id: int
    vehiculo_id: int
    trabajador_id: int
    estado_ruta: str
    kilometraje_salida: Optional[float] = None
    kilometraje_llegada: Optional[float] = None
    combustible_salida: Optional[str] = None
    combustible_llegada: Optional[str] = None
    observaciones_salida: Optional[str] = None
    observaciones_llegada: Optional[str] = None
    firma_trabajador: Optional[str] = None
    check_llantas: Optional[bool] = None
    check_frenos: Optional[bool] = None
    check_luces: Optional[bool] = None

    class Config:
        from_attributes = True
