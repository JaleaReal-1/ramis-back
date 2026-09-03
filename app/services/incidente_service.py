"""
Business logic para Incidentes.
"""
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.incidente import Incidente
from app.models.averia import Averia
from app.models.vehiculo import Vehiculo
from app.models.ruta_asignacion import RutaAsignacion
from app.models.user import User
from app.schemas.incidente_schema import IncidenteCreate, IncidenteUpdate


class IncidenteService:
    """Service para gestionar incidentes con reglas de negocio"""

    def __init__(self, db: Session):
        self.db = db

    def create_incidente(self, schema: IncidenteCreate, usuario_id: int) -> Incidente:
        """
        Crear incidente.

        Reglas:
        - Validar vehículo existe
        - Validar trabajador existe
        - Validar ruta (opcional)
        - Opcionalmente crear avería relacionada
        - Si hay_personas_afectadas o hay_danos, considerar criticidad alta
        """
        # Validar vehículo existe
        vehiculo = self.db.query(Vehiculo).filter(Vehiculo.id == schema.vehiculo_id).first()
        if not vehiculo:
            raise HTTPException(status_code=404, detail="Vehículo no encontrado")

        # Validar trabajador existe
        trabajador = self.db.query(User).filter(User.id == schema.trabajador_id).first()
        if not trabajador:
            raise HTTPException(status_code=404, detail="Trabajador no encontrado")

        # Validar ruta (opcional)
        if schema.ruta_id:
            ruta = self.db.query(RutaAsignacion).filter(RutaAsignacion.id == schema.ruta_id).first()
            if not ruta:
                raise HTTPException(status_code=404, detail="Ruta no encontrada")

        # Crear incidente
        incidente = Incidente(
            vehiculo_id=schema.vehiculo_id,
            ruta_id=schema.ruta_id,
            trabajador_id=schema.trabajador_id,
            tipo=schema.tipo,
            fecha=datetime.utcnow(),
            ubicacion=schema.ubicacion,
            descripcion=schema.descripcion,
            hay_danos=schema.hay_danos,
            hay_personas_afectadas=schema.hay_personas_afectadas,
            estado="reportado"
        )
        self.db.add(incidente)
        self.db.flush()

        # REGLA: Si hay daños o personas afectadas, puede generar avería
        if schema.generar_averia or schema.hay_danos or schema.hay_personas_afectadas:
            if schema.averia_categoria and schema.averia_componente:
                criticidad = schema.averia_criticidad or "alta"
                if schema.hay_personas_afectadas:
                    criticidad = "critica"

                averia = Averia(
                    vehiculo_id=schema.vehiculo_id,
                    ruta_id=schema.ruta_id,
                    trabajador_id=schema.trabajador_id,
                    categoria=schema.averia_categoria,
                    componente=schema.averia_componente,
                    descripcion=schema.averia_descripcion or f"Generada por incidente: {schema.descripcion}",
                    criticidad=criticidad,
                    fecha_reporte=datetime.utcnow(),
                    origen="incidente",
                    estado="reportada"
                )
                self.db.add(averia)
                self.db.flush()

                # Si avería es crítica, bloquear vehículo
                if criticidad.lower() == "critica":
                    vehiculo.estado = "bloqueado"

        self.db.commit()
        self.db.refresh(incidente)
        return incidente

    def get_incidente_by_id(self, incidente_id: int) -> Optional[Incidente]:
        """Obtener incidente por ID (activos solo)"""
        return self.db.query(Incidente).filter(
            Incidente.id == incidente_id,
            Incidente.fecha_baja.is_(None)  # Solo activos
        ).first()

    def get_all_incidentes(self) -> List[Incidente]:
        """Listar todos los incidentes activos"""
        return self.db.query(Incidente).filter(Incidente.fecha_baja.is_(None)).order_by(Incidente.fecha.desc()).all()

    def get_incidentes_by_vehiculo(self, vehiculo_id: int) -> List[Incidente]:
        """Listar incidentes de un vehículo"""
        return self.db.query(Incidente).filter(
            Incidente.vehiculo_id == vehiculo_id,
            Incidente.fecha_baja.is_(None)
        ).order_by(Incidente.fecha.desc()).all()

    def get_incidentes_by_tipo(self, tipo: str) -> List[Incidente]:
        """Listar incidentes por tipo"""
        return self.db.query(Incidente).filter(
            Incidente.tipo == tipo,
            Incidente.fecha_baja.is_(None)
        ).order_by(Incidente.fecha.desc()).all()

    def get_incidentes_by_estado(self, estado: str) -> List[Incidente]:
        """Listar incidentes por estado"""
        return self.db.query(Incidente).filter(
            Incidente.estado == estado,
            Incidente.fecha_baja.is_(None)
        ).order_by(Incidente.fecha.desc()).all()

    def get_incidentes_criticos(self) -> List[Incidente]:
        """Obtener incidentes críticos (con personas afectadas)"""
        return self.db.query(Incidente).filter(
            Incidente.hay_personas_afectadas == True,
            Incidente.fecha_baja.is_(None)
        ).order_by(Incidente.fecha.desc()).all()

    def update_incidente(self, incidente_id: int, schema: IncidenteUpdate, usuario_id: int) -> Incidente:
        """
        Actualizar incidente.

        Transiciones de estado:
        reportado → en_evaluacion → cerrado
        """
        incidente = self.get_incidente_by_id(incidente_id)
        if not incidente:
            raise HTTPException(status_code=404, detail="Incidente no encontrado")

        # Actualizar estado
        if schema.estado:
            estados_validos = ["reportado", "en_evaluacion", "cerrado"]
            if schema.estado not in estados_validos:
                raise HTTPException(status_code=400, detail=f"Estado inválido: {schema.estado}")
            incidente.estado = schema.estado

        # Actualizar descripción
        if schema.descripcion is not None:
            incidente.descripcion = schema.descripcion

        # Actualizar flags de daño
        if schema.hay_danos is not None:
            incidente.hay_danos = schema.hay_danos

        if schema.hay_personas_afectadas is not None:
            incidente.hay_personas_afectadas = schema.hay_personas_afectadas

        self.db.commit()
        self.db.refresh(incidente)
        return incidente

    def delete_incidente(self, incidente_id: int, usuario_id: int) -> Incidente:
        """Soft delete de incidente"""
        incidente = self.get_incidente_by_id(incidente_id)
        if not incidente:
            raise HTTPException(status_code=404, detail="Incidente no encontrado")

        incidente.fecha_baja = datetime.utcnow()
        incidente.usuario_baja = usuario_id
        self.db.commit()
        self.db.refresh(incidente)
        return incidente
