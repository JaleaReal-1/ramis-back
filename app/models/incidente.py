from __future__ import annotations
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.database.base import Base

class Incidente(Base):
    __tablename__ = "incidentes"

    id = Column(Integer, primary_key=True, index=True)
    vehiculo_id = Column(Integer, ForeignKey("vehiculos.id"), nullable=False)
    ruta_id = Column(Integer, ForeignKey("rutas_asignaciones.id"), nullable=True)
    trabajador_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    tipo = Column(String, nullable=False)  # colision, choque, volcadura, impacto, dano_estructural, casi_accidente, otro
    fecha = Column(DateTime, nullable=False)
    ubicacion = Column(String, nullable=False)
    descripcion = Column(String, nullable=False)
    hay_danos = Column(Boolean, default=False, nullable=False)
    hay_personas_afectadas = Column(Boolean, default=False, nullable=False)
    estado = Column(String, default="reportado", nullable=False)  # reportado, en_evaluacion, cerrado
    fecha_baja = Column(DateTime, nullable=True)
    usuario_baja = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Relaciones
    vehiculo = relationship("Vehiculo")
    ruta = relationship("RutaAsignacion")
    trabajador = relationship("User", foreign_keys=[trabajador_id])
    usuario_baja_user = relationship("User", foreign_keys=[usuario_baja])
