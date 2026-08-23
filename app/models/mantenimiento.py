from __future__ import annotations
from sqlalchemy import Column, Integer, ForeignKey, DateTime, String, Float
from sqlalchemy.orm import relationship
from app.database.base import Base

class Mantenimiento(Base):
    __tablename__ = "mantenimientos"

    id = Column(Integer, primary_key=True, index=True)
    vehiculo_id = Column(Integer, ForeignKey("vehiculos.id"), nullable=False)
    fecha_ingreso = Column(DateTime, nullable=False)
    descripcion_falla = Column(String, nullable=False)
    costo = Column(Float, nullable=False)
    estado = Column(String, default="en_taller", nullable=False)
    fecha_baja = Column(DateTime, nullable=True)
    usuario_baja = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Relaciones
    vehiculo = relationship("Vehiculo", back_populates="mantenimientos")
