from __future__ import annotations
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.database.base import Base

class ChecklistItem(Base):
    __tablename__ = "checklist_items"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    categoria = Column(String, nullable=False)
    criticidad = Column(String, nullable=False)  # baja, media, alta, critica
    orden = Column(Integer, default=0, nullable=False)
    activo = Column(Boolean, default=True, nullable=False)

class Inspeccion(Base):
    __tablename__ = "inspecciones"

    id = Column(Integer, primary_key=True, index=True)
    vehiculo_id = Column(Integer, ForeignKey("vehiculos.id"), nullable=False)
    ruta_id = Column(Integer, ForeignKey("rutas_asignaciones.id"), nullable=True)
    trabajador_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    tipo = Column(String, nullable=False)  # salida, llegada, extraordinaria, post_accidente, post_mantenimiento
    fecha = Column(DateTime, nullable=False)
    kilometraje = Column(Float, nullable=False)
    combustible = Column(String, nullable=False)
    firma = Column(String, nullable=True)
    resultado = Column(String, nullable=False)  # aprobada, aprobada_con_observaciones, rechazada
    observaciones = Column(String, nullable=True)

    # Relaciones
    vehiculo = relationship("Vehiculo")
    ruta = relationship("RutaAsignacion")
    trabajador = relationship("User", foreign_keys=[trabajador_id])
    detalles = relationship("InspeccionDetalle", back_populates="inspeccion", cascade="all, delete-orphan")

class InspeccionDetalle(Base):
    __tablename__ = "inspeccion_detalles"

    id = Column(Integer, primary_key=True, index=True)
    inspeccion_id = Column(Integer, ForeignKey("inspecciones.id"), nullable=False)
    checklist_item_id = Column(Integer, ForeignKey("checklist_items.id"), nullable=False)
    resultado_item = Column(String, nullable=False)  # conforme, observado, no_conforme, no_aplica

    # Relaciones
    inspeccion = relationship("Inspeccion", back_populates="detalles")
    checklist_item = relationship("ChecklistItem")
