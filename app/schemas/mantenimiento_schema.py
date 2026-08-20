from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class MantenimientoBase(BaseModel):
    fecha_ingreso: datetime = Field(..., description="Fecha de ingreso al taller")
    descripcion_falla: str = Field(..., description="Descripción detallada de la falla")
    costo: float = Field(..., description="Costo del mantenimiento")

class MantenimientoCreate(MantenimientoBase):
    vehiculo_id: int = Field(..., description="ID del vehículo")

class MantenimientoUpdate(BaseModel):
    fecha_ingreso: Optional[datetime] = None
    descripcion_falla: Optional[str] = None
    costo: Optional[float] = None
    estado: Optional[str] = None

class MantenimientoResponse(MantenimientoBase):
    id: int
    vehiculo_id: int
    estado: str

    class Config:
        from_attributes = True
