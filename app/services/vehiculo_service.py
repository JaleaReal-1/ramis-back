from __future__ import annotations

from sqlalchemy.orm import Session
from datetime import datetime, timezone
from fastapi import HTTPException, status
from app.models.vehiculo import Vehiculo
from app.schemas.vehiculo_schema import VehiculoCreate, VehiculoUpdate

class VehiculoService:
    def __init__(self, db: Session):
        self.db = db

    def get_vehiculo_by_id(self, vehiculo_id: int) -> Vehiculo:
        vehiculo = self.db.query(Vehiculo).filter(
            Vehiculo.id == vehiculo_id,
            Vehiculo.estado != "inactivo"
        ).first()
        if not vehiculo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vehículo no encontrado."
            )
        return vehiculo

    def get_all_vehiculos(self) -> list[Vehiculo]:
        return self.db.query(Vehiculo).filter(Vehiculo.estado != "inactivo").all()

    def create_vehiculo(self, schema: VehiculoCreate) -> Vehiculo:
        # Verificar si la placa ya está registrada
        existente = self.db.query(Vehiculo).filter(Vehiculo.placa == schema.placa).first()
        if existente:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La placa ya está registrada."
            )

        nuevo_vehiculo = Vehiculo(
            placa=schema.placa,
            marca=schema.marca,
            modelo=schema.modelo,
            capacidad_carga=schema.capacidad_carga,
            estado="disponible"
        )
        self.db.add(nuevo_vehiculo)
        self.db.commit()
        self.db.refresh(nuevo_vehiculo)
        return nuevo_vehiculo

    def update_vehiculo(self, vehiculo_id: int, schema: VehiculoUpdate) -> Vehiculo:
        vehiculo = self.get_vehiculo_by_id(vehiculo_id)

        if schema.placa is not None:
            # Verificar que la nueva placa no esté en uso por otro vehículo
            placa_existente = self.db.query(Vehiculo).filter(
                Vehiculo.placa == schema.placa,
                Vehiculo.id != vehiculo_id
            ).first()
            if placa_existente:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="La placa ya está en uso por otro vehículo."
                )
            vehiculo.placa = schema.placa

        if schema.marca is not None:
            vehiculo.marca = schema.marca
        if schema.modelo is not None:
            vehiculo.modelo = schema.modelo
        if schema.capacidad_carga is not None:
            vehiculo.capacidad_carga = schema.capacidad_carga
        self.db.commit()
        self.db.refresh(vehiculo)
        return vehiculo

    def delete_vehiculo(self, vehiculo_id: int, usuario_id: int) -> dict:
        vehiculo = self.get_vehiculo_by_id(vehiculo_id)
        vehiculo.estado = "inactivo"
        vehiculo.fecha_baja = datetime.now(timezone.utc)
        vehiculo.usuario_baja = usuario_id
        self.db.commit()
        return {"detail": "Vehículo marcado como inactivo correctamente."}
