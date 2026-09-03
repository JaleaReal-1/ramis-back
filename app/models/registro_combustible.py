from __future__ import annotations
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database.base import Base

class RegistroCombustible(Base):
    __tablename__ = "registros_combustible"

    id = Column(Integer, primary_key=True, index=True)
    vehiculo_id = Column(Integer, ForeignKey("vehiculos.id"), nullable=False)
    trabajador_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    fecha = Column(DateTime, nullable=False)
    kilometraje = Column(Float, nullable=False)
    nivel_anterior = Column(String, nullable=False)
    litros = Column(Float, nullable=False)
    nivel_posterior = Column(String, nullable=False)
    tipo_combustible = Column(String, nullable=False)
    costo = Column(Float, default=0.0, nullable=False)
    observaciones = Column(String, nullable=True)
    fecha_baja = Column(DateTime, nullable=True)
    usuario_baja = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Relaciones
    vehiculo = relationship("Vehiculo")
    trabajador = relationship("User", foreign_keys=[trabajador_id])
    usuario_baja_user = relationship("User", foreign_keys=[usuario_baja])
