from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

# CORRECTIVO: Vinculado a avería
class MantenimientoCorrectivoCreate(BaseModel):
    vehiculo_id: int
    averia_id: int
    descripcion: str
    costo: float = 0.0

# PREVENTIVO: Desde plan de mantenimiento
class MantenimientoPreventivoCreate(BaseModel):
    vehiculo_id: int
    plan_mantenimiento_id: int
    tipo_control: str  # por_km, por_fecha, por_horas, mixto
    km_base: Optional[float] = None
    fecha_base: Optional[datetime] = None
    horas_base: Optional[float] = None
    descripcion: str

# Actualización genérica
class MantenimientoUpdate(BaseModel):
    descripcion: Optional[str] = None
    costo: Optional[float] = None
    observaciones_ejecucion: Optional[str] = None

# Ejecutar mantenimiento
class MantenimientoEjecutar(BaseModel):
    trabajador_id: int
    km_ejecucion: float
    horas_ejecucion: float = 0.0
    observaciones_ejecucion: Optional[str] = None

# Respuestas
class MantenimientoResponse(BaseModel):
    id: int
    vehiculo_id: int
    tipo_mantenimiento: str
    descripcion: str
    estado_mantenimiento: str
    estado_ejecucion: str
    fecha_registro: datetime
    km_registro: float
    horas_registro: float
    fecha_ejecucion: Optional[datetime]
    km_ejecucion: Optional[float]
    horas_ejecucion: Optional[float]
    costo: float
    averia_id: Optional[int]
    plan_mantenimiento_id: Optional[int]
    trabajador_id: Optional[int]
    observaciones_ejecucion: Optional[str]

    class Config:
        from_attributes = True

class MantenimientoDetailResponse(MantenimientoResponse):
    fecha_baja: Optional[datetime]
    usuario_baja: Optional[int]

class MantenimientoListResponse(BaseModel):
    id: int
    vehiculo_id: int
    tipo_mantenimiento: str
    descripcion: str
    estado_mantenimiento: str
    estado_ejecucion: str
    fecha_registro: datetime
    km_registro: float
    costo: float

    class Config:
        from_attributes = True
