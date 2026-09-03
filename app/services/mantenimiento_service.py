from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.mantenimiento import Mantenimiento
from app.models.vehiculo import Vehiculo
from app.models.averia import Averia
from app.models.plan_mantenimiento import PlanMantenimiento
from app.models.user import User
from app.models.inspeccion import Inspeccion
from app.schemas.mantenimiento_schema import (
    MantenimientoCorrectivoCreate,
    MantenimientoPreventivoCreate,
    MantenimientoUpdate,
    MantenimientoEjecutar,
)


class MantenimientoService:
    def __init__(self, db: Session):
        self.db = db

    # CREAR MANTENIMIENTO CORRECTIVO (vinculado a avería)
    def create_mantenimiento_correctivo(
        self, schema: MantenimientoCorrectivoCreate, usuario_id: int
    ) -> Mantenimiento:
        """Crear mantenimiento correctivo vinculado a una avería."""
        # Validar vehículo
        vehiculo = self.db.query(Vehiculo).filter(
            Vehiculo.id == schema.vehiculo_id, Vehiculo.fecha_baja.is_(None)
        ).first()
        if not vehiculo:
            raise HTTPException(status_code=404, detail="Vehículo no encontrado")

        # Validar avería
        averia = self.db.query(Averia).filter(
            Averia.id == schema.averia_id, Averia.fecha_baja.is_(None)
        ).first()
        if not averia:
            raise HTTPException(status_code=404, detail="Avería no encontrada")

        # Validar que la avería pertenece al vehículo
        if averia.vehiculo_id != schema.vehiculo_id:
            raise HTTPException(status_code=400, detail="La avería no pertenece al vehículo especificado")

        # Crear mantenimiento
        mant = Mantenimiento(
            vehiculo_id=schema.vehiculo_id,
            tipo_mantenimiento="correctivo",
            averia_id=schema.averia_id,
            descripcion=schema.descripcion,
            costo=schema.costo,
            estado_mantenimiento="NORMAL",
            estado_ejecucion="pendiente",
            fecha_registro=datetime.utcnow(),
            km_registro=vehiculo.kilometraje_actual,
            horas_registro=0.0,
        )

        vehiculo.estado = "en_mantenimiento"

        self.db.add(mant)
        self.db.flush()
        self.db.commit()
        self.db.refresh(mant)
        return mant

    # CREAR MANTENIMIENTO PREVENTIVO (desde plan)
    def create_mantenimiento_preventivo(
        self, schema: MantenimientoPreventivoCreate, usuario_id: int
    ) -> Mantenimiento:
        """Crear mantenimiento preventivo desde plan."""
        # Validar vehículo
        vehiculo = self.db.query(Vehiculo).filter(
            Vehiculo.id == schema.vehiculo_id, Vehiculo.fecha_baja.is_(None)
        ).first()
        if not vehiculo:
            raise HTTPException(status_code=404, detail="Vehículo no encontrado")

        # Validar plan
        plan = self.db.query(PlanMantenimiento).filter(
            PlanMantenimiento.id == schema.plan_mantenimiento_id,
            PlanMantenimiento.fecha_baja.is_(None),
        ).first()
        if not plan:
            raise HTTPException(status_code=404, detail="Plan de mantenimiento no encontrado")

        # Determinar estado mantenimiento
        estado_mant = self._calcular_estado_mantenimiento(
            vehiculo, schema.tipo_control, schema.km_base, schema.fecha_base, schema.horas_base
        )

        mant = Mantenimiento(
            vehiculo_id=schema.vehiculo_id,
            tipo_mantenimiento="preventivo",
            plan_mantenimiento_id=schema.plan_mantenimiento_id,
            descripcion=schema.descripcion,
            costo=0.0,
            estado_mantenimiento=estado_mant,
            estado_ejecucion="pendiente",
            fecha_registro=datetime.utcnow(),
            km_registro=vehiculo.kilometraje_actual,
            horas_registro=0.0,
            km_base=schema.km_base,
            fecha_base=schema.fecha_base,
            horas_base=schema.horas_base,
            tipo_control=schema.tipo_control,
        )

        self.db.add(mant)
        self.db.flush()
        self.db.commit()
        self.db.refresh(mant)
        return mant

    # EJECUTAR MANTENIMIENTO
    def ejecutar_mantenimiento(
        self, mantenimiento_id: int, schema: MantenimientoEjecutar, usuario_id: int
    ) -> Mantenimiento:
        """Registrar ejecución del mantenimiento. actualizar KM del vehículo y liberarlo."""
        mant = self.get_mantenimiento_by_id(mantenimiento_id)
        if not mant:
            raise HTTPException(status_code=404, detail="Mantenimiento no encontrado")

        # Validar trabajador
        trabajador = self.db.query(User).filter(User.id == schema.trabajador_id).first()
        if not trabajador:
            raise HTTPException(status_code=404, detail="Trabajador no encontrado")

        # Actualizar campos de ejecución
        mant.fecha_ejecucion = datetime.utcnow()
        mant.km_ejecucion = schema.km_ejecucion
        mant.horas_ejecucion = schema.horas_ejecucion
        mant.trabajador_id = schema.trabajador_id
        mant.observaciones_ejecucion = schema.observaciones_ejecucion
        mant.estado_ejecucion = "completado"

        vehiculo = self.db.query(Vehiculo).filter(
            Vehiculo.id == mant.vehiculo_id
        ).first()
        if vehiculo and schema.km_ejecucion > vehiculo.kilometraje_actual:
            vehiculo.kilometraje_actual = schema.km_ejecucion
        if vehiculo and vehiculo.estado == "en_mantenimiento":
            vehiculo.estado = "observado"  # Requiere inspección POST_MANTENIMIENTO para volver a "disponible"
        if mant.averia_id:
            averia = self.db.query(Averia).filter(Averia.id == mant.averia_id).first()
            if averia and averia.estado not in ["resuelta", "cancelada"]:
                averia.estado = "resuelta"

        self.db.flush()
        self.db.commit()
        self.db.refresh(mant)
        return mant

    # OBTENER MANTENIMIENTO
    def get_mantenimiento_by_id(self, mantenimiento_id: int) -> Mantenimiento:
        """Obtener mantenimiento por ID (activo)"""
        return self.db.query(Mantenimiento).filter(
            Mantenimiento.id == mantenimiento_id, Mantenimiento.fecha_baja.is_(None)
        ).first()

    # LISTAR MANTENIMIENTOS
    def get_all_mantenimientos(self) -> list[Mantenimiento]:
        """Listar todos los mantenimientos activos"""
        return self.db.query(Mantenimiento).filter(
            Mantenimiento.fecha_baja.is_(None)
        ).order_by(Mantenimiento.fecha_registro.desc()).all()

    def get_mantenimientos_by_vehiculo(self, vehiculo_id: int) -> list[Mantenimiento]:
        """Obtener mantenimientos de un vehículo"""
        return self.db.query(Mantenimiento).filter(
            Mantenimiento.vehiculo_id == vehiculo_id,
            Mantenimiento.fecha_baja.is_(None),
        ).order_by(Mantenimiento.fecha_registro.desc()).all()

    def get_mantenimientos_by_tipo(self, tipo: str) -> list[Mantenimiento]:
        """Filtrar mantenimientos por tipo (correctivo, preventivo)"""
        return self.db.query(Mantenimiento).filter(
            Mantenimiento.tipo_mantenimiento == tipo,
            Mantenimiento.fecha_baja.is_(None),
        ).all()

    def get_mantenimientos_by_estado(self, estado: str) -> list[Mantenimiento]:
        """Filtrar mantenimientos por estado (NORMAL, PROXIMO, VENCIDO)"""
        return self.db.query(Mantenimiento).filter(
            Mantenimiento.estado_mantenimiento == estado,
            Mantenimiento.fecha_baja.is_(None),
        ).all()

    def get_mantenimientos_vencidos(self) -> list[Mantenimiento]:
        """Obtener todos los mantenimientos VENCIDOS"""
        return self.db.query(Mantenimiento).filter(
            Mantenimiento.estado_mantenimiento == "VENCIDO",
            Mantenimiento.fecha_baja.is_(None),
        ).all()

    # ACTUALIZAR MANTENIMIENTO
    def update_mantenimiento(
        self, mantenimiento_id: int, schema: MantenimientoUpdate, usuario_id: int
    ) -> Mantenimiento:
        """Actualizar descripción, costo, observaciones"""
        mant = self.get_mantenimiento_by_id(mantenimiento_id)
        if not mant:
            raise HTTPException(status_code=404, detail="Mantenimiento no encontrado")

        if schema.descripcion:
            mant.descripcion = schema.descripcion
        if schema.costo is not None:
            mant.costo = schema.costo
        if schema.observaciones_ejecucion:
            mant.observaciones_ejecucion = schema.observaciones_ejecucion

        self.db.flush()
        self.db.commit()
        self.db.refresh(mant)
        return mant

    # ELIMINAR MANTENIMIENTO (soft delete)
    def delete_mantenimiento(self, mantenimiento_id: int, usuario_id: int) -> None:
        """Soft delete de mantenimiento"""
        mant = self.get_mantenimiento_by_id(mantenimiento_id)
        if not mant:
            raise HTTPException(status_code=404, detail="Mantenimiento no encontrado")

        mant.fecha_baja = datetime.utcnow()
        mant.usuario_baja = usuario_id
        self.db.flush()
        self.db.commit()

    # UTILIDADES INTERNAS
    def _calcular_estado_mantenimiento(
        self,
        vehiculo: Vehiculo,
        tipo_control: str,
        km_base: float = None,
        fecha_base: datetime = None,
        horas_base: float = None,
    ) -> str:
        """Calcular si mantenimiento está NORMAL, PROXIMO o VENCIDO."""
        if tipo_control == "por_km" and km_base:
            if vehiculo.kilometraje_actual >= km_base:
                return "VENCIDO"
            if vehiculo.kilometraje_actual >= km_base * 0.8:
                return "PROXIMO"

        elif tipo_control == "por_fecha" and fecha_base:
            ahora = datetime.utcnow()
            if ahora >= fecha_base:
                return "VENCIDO"
            dias_diff = (fecha_base - ahora).days
            if dias_diff <= 7:
                return "PROXIMO"

        elif tipo_control == "mixto":
            vencido_km = km_base and vehiculo.kilometraje_actual >= km_base
            vencido_fecha = fecha_base and datetime.utcnow() >= fecha_base
            if vencido_km or vencido_fecha:
                return "VENCIDO"

            proximo_km = km_base and vehiculo.kilometraje_actual >= km_base * 0.8
            proximo_fecha = (
                fecha_base
                and (fecha_base - datetime.utcnow()).days <= 7
            )
            if proximo_km or proximo_fecha:
                return "PROXIMO"

        return "NORMAL"

    def require_post_inspeccion_mantenimiento(self, vehiculo_id: int) -> bool:
        """Verificar si requiere inspección POST_MANTENIMIENTO aprobada."""
        # Buscar mantenimiento reciente completado
        mantenimiento_reciente = self.db.query(Mantenimiento).filter(
            Mantenimiento.vehiculo_id == vehiculo_id,
            Mantenimiento.estado_ejecucion == "completado",
            Mantenimiento.fecha_baja.is_(None),
        ).order_by(Mantenimiento.fecha_ejecucion.desc()).first()

        if not mantenimiento_reciente:
            return False

        # Buscar inspección POST_MANTENIMIENTO aprobada POSTERIOR a ejecución
        inspeccion_post = self.db.query(Inspeccion).filter(
            Inspeccion.vehiculo_id == vehiculo_id,
            Inspeccion.tipo == "post_mantenimiento",
            Inspeccion.resultado == "aprobada",
            Inspeccion.fecha > mantenimiento_reciente.fecha_ejecucion,
        ).first()

        # Retorna True si NO tiene inspección POST_MANTENIMIENTO aprobada
        return inspeccion_post is None

    def can_vehicle_operate_after_maintenance(self, vehiculo_id: int) -> bool:
        """Verificar si vehículo puede operar después de mantenimiento."""
        return not self.require_post_inspeccion_mantenimiento(vehiculo_id)
