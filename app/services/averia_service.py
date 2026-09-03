"""
Business logic para Averías.
"""
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.averia import Averia
from app.models.vehiculo import Vehiculo
from app.models.ruta_asignacion import RutaAsignacion
from app.models.inspeccion import Inspeccion
from app.models.user import User
from app.schemas.averia_schema import AveriaCreate, AveriaUpdate


class AveriaService:
    """Service para gestionar averías con reglas de negocio"""

    def __init__(self, db: Session):
        self.db = db

    def create_averia(self, schema: AveriaCreate, usuario_id: int) -> Averia:
        """
        Crear avería con validaciones y reglas de bloqueo.

        Reglas:
        - Si criticidad="critica", bloquear vehículo
        - Validar que vehículo existe
        - Validar que trabajador existe (si aplica)
        - Registrar fecha_reporte como ahora
        """
        # Validar vehículo existe
        vehiculo = self.db.query(Vehiculo).filter(Vehiculo.id == schema.vehiculo_id).first()
        if not vehiculo:
            raise HTTPException(status_code=404, detail="Vehículo no encontrado")

        # Validar trabajador (opcional)
        if schema.trabajador_id:
            trabajador = self.db.query(User).filter(User.id == schema.trabajador_id).first()
            if not trabajador:
                raise HTTPException(status_code=404, detail="Trabajador no encontrado")

        # Validar ruta (opcional)
        if schema.ruta_id:
            ruta = self.db.query(RutaAsignacion).filter(RutaAsignacion.id == schema.ruta_id).first()
            if not ruta:
                raise HTTPException(status_code=404, detail="Ruta no encontrada")

        # Validar inspección (opcional)
        if schema.inspeccion_id:
            inspeccion = self.db.query(Inspeccion).filter(Inspeccion.id == schema.inspeccion_id).first()
            if not inspeccion:
                raise HTTPException(status_code=404, detail="Inspección no encontrada")

        # Crear avería
        averia = Averia(
            vehiculo_id=schema.vehiculo_id,
            ruta_id=schema.ruta_id,
            trabajador_id=schema.trabajador_id,
            inspeccion_id=schema.inspeccion_id,
            categoria=schema.categoria,
            componente=schema.componente,
            descripcion=schema.descripcion,
            criticidad=schema.criticidad,
            fecha_reporte=datetime.utcnow(),
            origen=schema.origen,
            estado="reportada"
        )
        self.db.add(averia)
        self.db.flush()

        # REGLA CRÍTICA: Si criticidad es "critica", bloquear vehículo
        if schema.criticidad.lower() == "critica":
            vehiculo.estado = "bloqueado"
            self.db.flush()

        self.db.commit()
        self.db.refresh(averia)
        return averia

    def get_averia_by_id(self, averia_id: int) -> Optional[Averia]:
        """Obtener avería por ID (activas solo)"""
        return self.db.query(Averia).filter(
            Averia.id == averia_id,
            Averia.fecha_baja.is_(None)  # Solo activas
        ).first()

    def get_all_averias(self) -> List[Averia]:
        """Listar todas las averías activas"""
        return self.db.query(Averia).filter(Averia.fecha_baja.is_(None)).order_by(Averia.fecha_reporte.desc()).all()

    def get_averias_by_vehiculo(self, vehiculo_id: int) -> List[Averia]:
        """Listar averías de un vehículo"""
        return self.db.query(Averia).filter(
            Averia.vehiculo_id == vehiculo_id,
            Averia.fecha_baja.is_(None)
        ).order_by(Averia.fecha_reporte.desc()).all()

    def get_averias_by_criticidad(self, criticidad: str) -> List[Averia]:
        """Listar averías por criticidad"""
        return self.db.query(Averia).filter(
            Averia.criticidad == criticidad,
            Averia.fecha_baja.is_(None)
        ).order_by(Averia.fecha_reporte.desc()).all()

    def get_averias_by_estado(self, estado: str) -> List[Averia]:
        """Listar averías por estado"""
        return self.db.query(Averia).filter(
            Averia.estado == estado,
            Averia.fecha_baja.is_(None)
        ).order_by(Averia.fecha_reporte.desc()).all()

    def update_averia(self, averia_id: int, schema: AveriaUpdate, usuario_id: int) -> Averia:
        """
        Actualizar avería.

        Transiciones de estado permitidas:
        reportada → en_evaluacion → programada → en_reparacion → resuelta → cerrada

        Regla especial:
        - Si avería es critica y pasaba a RESUELTA, verificar que vehículo no deba permanecer bloqueado
        """
        averia = self.get_averia_by_id(averia_id)
        if not averia:
            raise HTTPException(status_code=404, detail="Avería no encontrada")

        # Actualizar estado si se proporciona
        if schema.estado:
            # Validar transición de estado
            estados_validos = ["reportada", "en_evaluacion", "programada", "en_reparacion", "resuelta", "cerrada"]
            if schema.estado not in estados_validos:
                raise HTTPException(status_code=400, detail=f"Estado inválido: {schema.estado}")

            averia.estado = schema.estado

            # Si pasa a RESUELTA y es CRITICA, chequear si hay otras averías críticas
            if schema.estado == "resuelta" and averia.criticidad.lower() == "critica":
                # Verificar si hay otras averías críticas activas para el vehículo
                otras_criticas = self.db.query(Averia).filter(
                    Averia.vehiculo_id == averia.vehiculo_id,
                    Averia.id != averia.id,
                    Averia.criticidad == "critica",
                    Averia.estado.notin_(["resuelta", "cerrada"]),
                    Averia.fecha_baja.is_(None)
                ).count()

                # Si NO hay otras críticas, desbloquear vehículo
                if otras_criticas == 0:
                    vehiculo = self.db.query(Vehiculo).filter(Vehiculo.id == averia.vehiculo_id).first()
                    if vehiculo and vehiculo.estado == "bloqueado":
                        vehiculo.estado = "disponible"

        # Actualizar descripción
        if schema.descripcion:
            averia.descripcion = schema.descripcion

        # Actualizar trabajador asignado
        if schema.trabajador_id is not None:
            if schema.trabajador_id > 0:
                trabajador = self.db.query(User).filter(User.id == schema.trabajador_id).first()
                if not trabajador:
                    raise HTTPException(status_code=404, detail="Trabajador no encontrado")
            averia.trabajador_id = schema.trabajador_id

        self.db.commit()
        self.db.refresh(averia)
        return averia

    def delete_averia(self, averia_id: int, usuario_id: int) -> Averia:
        """Soft delete de avería"""
        averia = self.get_averia_by_id(averia_id)
        if not averia:
            raise HTTPException(status_code=404, detail="Avería no encontrada")

        averia.fecha_baja = datetime.utcnow()
        averia.usuario_baja = usuario_id
        self.db.commit()
        self.db.refresh(averia)
        return averia

    def get_averias_criticas_activas(self) -> List[Averia]:
        """Obtener averías críticas no resueltas"""
        return self.db.query(Averia).filter(
            Averia.criticidad == "critica",
            Averia.estado.notin_(["resuelta", "cerrada"]),
            Averia.fecha_baja.is_(None)
        ).order_by(Averia.fecha_reporte.desc()).all()

    def can_vehicle_be_used(self, vehiculo_id: int) -> bool:
        """
        Verificar si vehículo puede ser usado.

        No puede usarse si:
        - Tiene avería CRÍTICA no resuelta
        """
        criticas_activas = self.db.query(Averia).filter(
            Averia.vehiculo_id == vehiculo_id,
            Averia.criticidad == "critica",
            Averia.estado.notin_(["resuelta", "cerrada"]),
            Averia.fecha_baja.is_(None)
        ).count()

        return criticas_activas == 0
