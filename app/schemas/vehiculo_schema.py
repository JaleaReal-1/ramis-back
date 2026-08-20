from pydantic import BaseModel, Field
from typing import Optional

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
    estado: Optional[str] = None

class VehiculoResponse(VehiculoBase):
    id: int
    estado: str

    class Config:
        from_attributes = True
