from __future__ import annotations

from sqlalchemy.orm import Session
from datetime import datetime, timezone
from fastapi import HTTPException, status
from app.models.mantenimiento import Mantenimiento
from app.models.vehiculo import Vehiculo
from app.schemas.mantenimiento_schema import MantenimientoCreate, MantenimientoUpdate

class MantenimientoService:
    def __init__(self, db: Session):
        self.db = db

    def get_mantenimiento_by_id(self, mantenimiento_id: int) -> Mantenimiento:
        mantenimiento = self.db.query(Mantenimiento).filter(
            Mantenimiento.id == mantenimiento_id,
            Mantenimiento.estado != "inactivo"
        ).first()
        if not mantenimiento:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Registro de mantenimiento no encontrado."
            )
        return mantenimiento

    def get_all_mantenimientos(self) -> list[Mantenimiento]:
        return self.db.query(Mantenimiento).filter(Mantenimiento.estado != "inactivo").all()

    def create_mantenimiento(self, schema: MantenimientoCreate) -> Mantenimiento:
        # Verificar que el vehículo exista
        vehiculo = self.db.query(Vehiculo).filter(
            Vehiculo.id == schema.vehiculo_id,
            Vehiculo.estado != "inactivo"
        ).first()
        if not vehiculo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vehículo no encontrado."
            )

        # Si el vehículo ya está en mantenimiento o en ruta, lanzar una advertencia/error de negocio
        if vehiculo.estado == "en_ruta":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se puede enviar a mantenimiento un vehículo que está actualmente en ruta."
            )

        # Crear registro de mantenimiento
        nuevo_mantenimiento = Mantenimiento(
            vehiculo_id=schema.vehiculo_id,
            fecha_ingreso=schema.fecha_ingreso,
            descripcion_falla=schema.descripcion_falla,
            costo=schema.costo,
            estado="en_taller"
        )

        # Cambiar estado del vehículo a "en_mantenimiento"
        vehiculo.estado = "en_mantenimiento"

        self.db.add(nuevo_mantenimiento)
        self.db.commit()
        self.db.refresh(nuevo_mantenimiento)
        return nuevo_mantenimiento

    def update_mantenimiento(self, mantenimiento_id: int, schema: MantenimientoUpdate) -> Mantenimiento:
        mantenimiento = self.get_mantenimiento_by_id(mantenimiento_id)

        if schema.fecha_ingreso is not None:
            mantenimiento.fecha_ingreso = schema.fecha_ingreso
        if schema.descripcion_falla is not None:
            mantenimiento.descripcion_falla = schema.descripcion_falla
        if schema.costo is not None:
            mantenimiento.costo = schema.costo

        if schema.estado is not None:
            mantenimiento.estado = schema.estado
            # Si el mantenimiento se completa, el vehículo vuelve a estar disponible
            if schema.estado == "completado":
                vehiculo = self.db.query(Vehiculo).filter(Vehiculo.id == mantenimiento.vehiculo_id).first()
                if vehiculo:
                    vehiculo.estado = "disponible"

        self.db.commit()
        self.db.refresh(mantenimiento)
        return mantenimiento

    def delete_mantenimiento(self, mantenimiento_id: int, usuario_id: int) -> dict:
        mantenimiento = self.get_mantenimiento_by_id(mantenimiento_id)
        mantenimiento.estado = "inactivo"
        mantenimiento.fecha_baja = datetime.now(timezone.utc)
        mantenimiento.usuario_baja = usuario_id
        self.db.commit()
        return {"detail": "Mantenimiento marcado como inactivo correctamente."}
