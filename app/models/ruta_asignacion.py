from __future__ import annotations
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Float, Boolean
from sqlalchemy.orm import relationship
from app.database.base import Base

class RutaAsignacion(Base):
    __tablename__ = "rutas_asignaciones"

    id = Column(Integer, primary_key=True, index=True)
    vehiculo_id = Column(Integer, ForeignKey("vehiculos.id"), nullable=False)
    trabajador_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    origen = Column(String, nullable=False)
    destino = Column(String, nullable=False)
    fecha_salida = Column(DateTime, nullable=False)
    fecha_llegada_estimada = Column(DateTime, nullable=False)
    estado_ruta = Column(String, default="pendiente", nullable=False)
    fecha_baja = Column(DateTime, nullable=True)
    usuario_baja = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Nuevos campos de inspección de vehículo (se llenan al iniciar la ruta, por lo que son nullable)
    kilometraje_salida = Column(Float, nullable=True)
    kilometraje_llegada = Column(Float, nullable=True)
    combustible_salida = Column(String, nullable=True)
    combustible_llegada = Column(String, nullable=True)
    observaciones_salida = Column(String, nullable=True)
    observaciones_llegada = Column(String, nullable=True)

    # Firmas y verificaciones de seguridad
    firma_trabajador = Column(String, nullable=True)
    check_llantas = Column(Boolean, default=False, nullable=True)
    check_frenos = Column(Boolean, default=False, nullable=True)
    check_luces = Column(Boolean, default=False, nullable=True)

    # Relaciones
    vehiculo = relationship("Vehiculo", back_populates="asignaciones")
    trabajador = relationship("User", foreign_keys=[trabajador_id])
