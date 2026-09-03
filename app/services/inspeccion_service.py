from __future__ import annotations

from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from datetime import datetime, timezone
from app.models.inspeccion import Inspeccion, InspeccionDetalle, ChecklistItem
from app.models.vehiculo import Vehiculo
from app.models.user import User
from app.schemas.inspeccion_schema import (
    InspeccionCreate,
    InspeccionUpdate,
    InspeccionResponse,
)


class InspeccionService:
    """
    Servicio de negocio para inspecciones dinámicas de vehículos.

    Responsabilidades:
    - Crear inspecciones con detalles dinámicos
    - Calcular resultado automático (aprobada/con_observaciones/rechazada)
    - Validar criticidad y bloquear vehículos si hay items críticos NO_CONFORME
    - Mantener monotonía de kilometraje
    - Consultar inspecciones
    """

    def __init__(self, db: Session):
        self.db = db

    def get_inspeccion_by_id(self, inspeccion_id: int) -> Inspeccion:
        """Obtener inspección por ID"""
        inspeccion = self.db.query(Inspeccion).filter(
            Inspeccion.id == inspeccion_id
        ).first()
        if not inspeccion:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Inspección no encontrada."
            )
        return inspeccion

    def get_all_inspecciones(self) -> list[Inspeccion]:
        """Listar todas las inspecciones"""
        return self.db.query(Inspeccion).order_by(Inspeccion.fecha.desc()).all()

    def get_inspecciones_by_vehiculo(self, vehiculo_id: int) -> list[Inspeccion]:
        """Obtener inspecciones de un vehículo específico"""
        vehiculo = self.db.query(Vehiculo).filter(Vehiculo.id == vehiculo_id).first()
        if not vehiculo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vehículo no encontrado."
            )
        return self.db.query(Inspeccion).filter(
            Inspeccion.vehiculo_id == vehiculo_id
        ).order_by(Inspeccion.fecha.desc()).all()

    def get_inspecciones_by_ruta(self, ruta_id: int) -> list[Inspeccion]:
        """Obtener inspecciones de una ruta específica"""
        return self.db.query(Inspeccion).filter(
            Inspeccion.ruta_id == ruta_id
        ).order_by(Inspeccion.fecha.desc()).all()

    def get_ultima_inspeccion_by_vehiculo(self, vehiculo_id: int) -> Inspeccion | None:
        """Obtener la última inspección de un vehículo"""
        return self.db.query(Inspeccion).filter(
            Inspeccion.vehiculo_id == vehiculo_id
        ).order_by(Inspeccion.fecha.desc()).first()

    def _validar_kilometraje(
        self, vehiculo_id: int, nuevo_kilometraje: float
    ) -> None:
        """
        REGLA: Monotonía de kilometraje.
        El nuevo kilometraje no puede ser menor que el último válido conocido.
        """
        vehiculo = self.db.query(Vehiculo).filter(
            Vehiculo.id == vehiculo_id
        ).first()
        if not vehiculo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vehículo no encontrado."
            )

        # El vehículo tiene un kilometraje_actual que se mantiene actualizado
        # No puede haber un nuevo kilom etraje menor que el actual
        if nuevo_kilometraje < vehiculo.kilometraje_actual:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Kilometraje inválido: no puede ser menor que el actual ({vehiculo.kilometraje_actual}). "
                    f"El kilometraje debe ser monotónico creciente."
                )
            )

    def _validar_usuario(self, trabajador_id: int) -> User:
        """Validar que el usuario existe y es trabajador"""
        trabajador = self.db.query(User).filter(User.id == trabajador_id).first()
        if not trabajador:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Trabajador no encontrado."
            )
        return trabajador

    def _procesar_detalles_inspeccion(
        self,
        inspeccion_id: int,
        detalles_schema: list,
    ) -> tuple[str, bool]:
        """
        Procesar detalles dinámicos de inspección y calcular resultado.

        Retorna:
        - resultado: "aprobada", "aprobada_con_observaciones", "rechazada"
        - hay_critica_no_conforme: True si existe un item crítico con resultado NO_CONFORME

        REGLAS:
        - Si cualquier item CRÍTICO está NO_CONFORME => RECHAZADA + bloquear vehículo
        - Si algún item está OBSERVADO => aprobada_con_observaciones
        - Si todos están CONFORME o NO_APLICA => APROBADA
        """
        hay_observaciones = False
        hay_critica_no_conforme = False

        for detalle_data in detalles_schema:
            checklist_item = self.db.query(ChecklistItem).filter(
                ChecklistItem.id == detalle_data.checklist_item_id
            ).first()
            if not checklist_item:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Checklist item {detalle_data.checklist_item_id} no encontrado."
                )

            resultado_item = detalle_data.resultado_item.lower()

            # Validar que sea un valor válido
            if resultado_item not in ["conforme", "observado", "no_conforme", "no_aplica"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Resultado inválido para item {checklist_item.nombre}: {resultado_item}"
                )

            # Detectar observaciones
            if resultado_item == "observado":
                hay_observaciones = True

            # REGLA CRÍTICA: Si un item CRÍTICO está NO_CONFORME, rechazar
            if (
                resultado_item == "no_conforme"
                and checklist_item.criticidad.lower() == "critica"
            ):
                hay_critica_no_conforme = True

            # Guardar detalle
            detalle = InspeccionDetalle(
                inspeccion_id=inspeccion_id,
                checklist_item_id=detalle_data.checklist_item_id,
                resultado_item=resultado_item,
            )
            self.db.add(detalle)

        # Determinar resultado general
        if hay_critica_no_conforme:
            resultado_general = "rechazada"
        elif hay_observaciones:
            resultado_general = "aprobada_con_observaciones"
        else:
            resultado_general = "aprobada"

        self.db.flush()  # Flushar cambios antes de retornar
        return resultado_general, hay_critica_no_conforme

    def create_inspeccion(self, schema: InspeccionCreate) -> InspeccionResponse:
        """
        Crear inspección con detalles dinámicos.

        FLUJO:
        1. Validar vehículo existe
        2. Validar trabajador existe
        3. Validar monotonía de kilometraje
        4. Crear inspeccion
        5. Procesar detalles y calcular resultado
        6. Si hay item crítico NO_CONFORME: bloquear vehículo
        7. Actualizar kilometraje del vehículo
        """
        # 1. Validar vehículo
        vehiculo = self.db.query(Vehiculo).filter(
            Vehiculo.id == schema.vehiculo_id
        ).first()
        if not vehiculo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vehículo no encontrado."
            )

        # 2. Validar trabajador
        self._validar_usuario(schema.trabajador_id)

        # 3. Validar monotonía de kilometraje
        self._validar_kilometraje(schema.vehiculo_id, schema.kilometraje)

        # 4. Crear inspección (resultado será actualizado después)
        nueva_inspeccion = Inspeccion(
            vehiculo_id=schema.vehiculo_id,
            ruta_id=schema.ruta_id,
            trabajador_id=schema.trabajador_id,
            tipo=schema.tipo.lower(),
            fecha=datetime.now(timezone.utc),
            kilometraje=schema.kilometraje,
            combustible=schema.combustible,
            firma=schema.firma,
            resultado="pendiente",  # Será actualizado
            observaciones=schema.observaciones,
        )
        self.db.add(nueva_inspeccion)
        self.db.flush()

        # 5. Procesar detalles y calcular resultado
        resultado_general, hay_critica_no_conforme = self._procesar_detalles_inspeccion(
            nueva_inspeccion.id,
            schema.detalles,
        )
        nueva_inspeccion.resultado = resultado_general

        # 6. Si hay item crítico NO_CONFORME: bloquear vehículo
        if hay_critica_no_conforme:
            if schema.tipo.lower() == "salida":
                # Si es inspección de SALIDA y rechazada, NO permitir que inicie la ruta
                # El vehículo queda BLOQUEADO hasta resolver
                vehiculo.estado = "bloqueado"
            else:
                # Para otras inspecciones, marcar como observado
                vehiculo.estado = "observado"
        elif (
            schema.tipo.lower() == "post_mantenimiento"
            and resultado_general in ("aprobada", "aprobada_con_observaciones")
            and vehiculo.estado == "observado"
        ):
            # POST_MANTENIMIENTO aprobada libera el vehículo que estaba en "observado"
            # tras finalizar su mantenimiento correctivo.
            vehiculo.estado = "disponible"

        # 7. Actualizar kilometraje del vehículo (es monotónico, ya validado)
        vehiculo.kilometraje_actual = schema.kilometraje

        self.db.commit()
        self.db.refresh(nueva_inspeccion)
        return nueva_inspeccion

    def update_inspeccion(
        self, inspeccion_id: int, schema: InspeccionUpdate
    ) -> InspeccionResponse:
        """Actualizar observaciones de inspección (operación limitada)"""
        inspeccion = self.get_inspeccion_by_id(inspeccion_id)

        if schema.observaciones is not None:
            inspeccion.observaciones = schema.observaciones

        self.db.commit()
        self.db.refresh(inspeccion)
        return inspeccion

    def delete_inspeccion(self, inspeccion_id: int, usuario_id: int) -> dict:
        """
        Soft delete de inspección (marca como inactiva pero mantiene histórico).
        En este caso, simplemente eliminamos en cascada (los detalles se eliminarán).
        """
        inspeccion = self.get_inspeccion_by_id(inspeccion_id)

        # Eliminar en cascada (los detalles se eliminan automáticamente)
        self.db.delete(inspeccion)
        self.db.commit()

        return {"detail": "Inspección eliminada correctamente."}

    def validar_inspeccion_salida_aprobada(self, vehiculo_id: int) -> bool:
        """
        REGLA: Antes de iniciar la ruta, debe existir una inspección SALIDA aprobada.

        Retorna True si existe una inspección SALIDA con resultado "aprobada" o "aprobada_con_observaciones".
        Retorna False si la última inspección SALIDA fue "rechazada" o si no existe.
        """
        ultima_inspeccion_salida = self.db.query(Inspeccion).filter(
            Inspeccion.vehiculo_id == vehiculo_id,
            Inspeccion.tipo == "salida",
        ).order_by(Inspeccion.fecha.desc()).first()

        if not ultima_inspeccion_salida:
            return False

        return ultima_inspeccion_salida.resultado in [
            "aprobada",
            "aprobada_con_observaciones",
        ]
