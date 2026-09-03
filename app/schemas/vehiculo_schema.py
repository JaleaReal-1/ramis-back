from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class VehiculoBase(BaseModel):
    placa: str = Field(..., description="Placa única del vehículo")
    marca: str = Field(..., description="Marca del vehículo")
    modelo: str = Field(..., description="Modelo del vehículo")
    capacidad_carga: float = Field(..., description="Capacidad de carga en toneladas/kg")

class VehiculoCreate(VehiculoBase):
    pass

class VehiculoUpdate(BaseModel):
    placa: Optional[str] = None
    marca: Optional[str] = None
    modelo: Optional[str] = None
    capacidad_carga: Optional[float] = None

class VehiculoResponse(VehiculoBase):
    id: int
    estado: str
    kilometraje_actual: float = 0.0
    fecha_baja: Optional[datetime] = None
    usuario_baja: Optional[int] = None

    class Config:
        from_attributes = True
