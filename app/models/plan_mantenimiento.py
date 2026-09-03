from __future__ import annotations
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.database.base import Base

class PlanMantenimiento(Base):
    __tablename__ = "planes_mantenimiento"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    activo = Column(Boolean, default=True, nullable=False)
    fecha_baja = Column(DateTime, nullable=True)
    usuario_baja = Column(Integer, ForeignKey("users.id"), nullable=True)

    detalles = relationship("PlanMantenimientoDetalle", back_populates="plan", cascade="all, delete-orphan")

class PlanMantenimientoDetalle(Base):
    __tablename__ = "plan_mantenimiento_detalles"

    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("planes_mantenimiento.id"), nullable=False)
    actividad = Column(String, nullable=False)
    descripcion = Column(String, nullable=True)
    tipo_control = Column(String, nullable=False)  # por_km, por_fecha, por_horas, mixto
    intervalo_km = Column(Float, nullable=True)
    intervalo_dias = Column(Integer, nullable=True)
    intervalo_horas = Column(Float, nullable=True)
    alerta_previa_km = Column(Float, nullable=True)
    alerta_previa_dias = Column(Integer, nullable=True)
    criticidad = Column(String, nullable=False)  # baja, media, alta, critica
    activo = Column(Boolean, default=True, nullable=False)

    plan = relationship("PlanMantenimiento", back_populates="detalles")
