from __future__ import annotations
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database.base import Base

class Averia(Base):
    __tablename__ = "averias"

    id = Column(Integer, primary_key=True, index=True)
    vehiculo_id = Column(Integer, ForeignKey("vehiculos.id"), nullable=False)
    ruta_id = Column(Integer, ForeignKey("rutas_asignaciones.id"), nullable=True)
    trabajador_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    inspeccion_id = Column(Integer, ForeignKey("inspecciones.id"), nullable=True)
    categoria = Column(String, nullable=False)
    componente = Column(String, nullable=False)
    descripcion = Column(String, nullable=False)
    criticidad = Column(String, nullable=False)  # baja, media, alta, critica
    fecha_reporte = Column(DateTime, nullable=False)
    kilometraje = Column(Float, nullable=True)
    estado = Column(String, default="reportada", nullable=False)  # reportada, en_evaluacion, programada, en_reparacion, resuelta, cerrada
    origen = Column(String, nullable=False)  # inspeccion_salida, operacion, inspeccion_llegada, mantenimiento
    fecha_baja = Column(DateTime, nullable=True)
    usuario_baja = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Relaciones
    vehiculo = relationship("Vehiculo")
    ruta = relationship("RutaAsignacion")
    trabajador = relationship("User", foreign_keys=[trabajador_id])
    inspeccion = relationship("Inspeccion")
    usuario_baja_user = relationship("User", foreign_keys=[usuario_baja])
