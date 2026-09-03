from __future__ import annotations
from sqlalchemy import Column, Integer, ForeignKey, DateTime, String, Float
from sqlalchemy.orm import relationship
from app.database.base import Base

class Mantenimiento(Base):
    __tablename__ = "mantenimientos"

    id = Column(Integer, primary_key=True, index=True)
    vehiculo_id = Column(Integer, ForeignKey("vehiculos.id"), nullable=False)

    # Tipo y contexto
    tipo_mantenimiento = Column(String, nullable=False)  # correctivo, preventivo
    averia_id = Column(Integer, ForeignKey("averias.id"), nullable=True)  # Solo para correctivo
    plan_mantenimiento_id = Column(Integer, ForeignKey("planes_mantenimiento.id"), nullable=True)

    # Descripción
    descripcion = Column(String, nullable=False)

    # Estado de mantenimiento (NORMAL, PROXIMO, VENCIDO)
    estado_mantenimiento = Column(String, default="NORMAL", nullable=False)

    # Estado de ejecución
    estado_ejecucion = Column(String, default="pendiente", nullable=False)  # pendiente, en_ejecucion, completado

    # Fechas y kilometraje de REGISTRO (cuando se creó el mantenimiento)
    fecha_registro = Column(DateTime, nullable=False)
    km_registro = Column(Float, nullable=False)
    horas_registro = Column(Float, default=0.0, nullable=False)

    # Valores base para control preventivo (del plan)
    km_base = Column(Float, nullable=True)
    fecha_base = Column(DateTime, nullable=True)
    horas_base = Column(Float, nullable=True)
    tipo_control = Column(String, nullable=True)  # por_km, por_fecha, por_horas, mixto

    # Ejecución del mantenimiento
    fecha_ejecucion = Column(DateTime, nullable=True)
    km_ejecucion = Column(Float, nullable=True)
    horas_ejecucion = Column(Float, nullable=True)
    trabajador_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    observaciones_ejecucion = Column(String, nullable=True)
    costo = Column(Float, default=0.0, nullable=False)

    # Soft delete
    fecha_baja = Column(DateTime, nullable=True)
    usuario_baja = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Relaciones
    vehiculo = relationship("Vehiculo", back_populates="mantenimientos")
    averia = relationship("Averia")
    plan_mantenimiento = relationship("PlanMantenimiento")
    trabajador = relationship("User", foreign_keys=[trabajador_id])
