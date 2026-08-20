from __future__ import annotations

from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.ruta_asignacion import RutaAsignacion
from app.models.vehiculo import Vehiculo
from app.models.user import User
from app.schemas.ruta_asignacion_schema import RutaAsignacionCreate, RutaAsignacionUpdate, RutaAsignacionFinalizar

class RutaService:
    def __init__(self, db: Session):
        self.db = db

    def get_ruta_by_id(self, ruta_id: int) -> RutaAsignacion:
        ruta = self.db.query(RutaAsignacion).filter(RutaAsignacion.id == ruta_id).first()
        if not ruta:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Asignación de ruta no encontrada."
            )
        return ruta

    def get_all_rutas(self) -> list[RutaAsignacion]:
        return self.db.query(RutaAsignacion).all()

    def create_ruta(self, schema: RutaAsignacionCreate) -> RutaAsignacion:
        # Rule 1: Buscar al usuario por trabajador_id.
        # Si no existe o su role no es exactamente "trabajador", lanzar HTTPException(status_code=403, detail="El usuario no tiene el rol de trabajador.")
        usuario = self.db.query(User).filter(User.id == schema.trabajador_id).first()
        if not usuario or usuario.role != "trabajador":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="El usuario no tiene el rol de trabajador."
            )

        # Rule 2: Verificar si el trabajador ya tiene una ruta con estado_ruta == "en_progreso"
        ruta_activa = self.db.query(RutaAsignacion).filter(
            RutaAsignacion.trabajador_id == schema.trabajador_id,
            RutaAsignacion.estado_ruta == "en_progreso"
        ).first()
        if ruta_activa:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El trabajador ya está en una ruta activa."
            )

        # Rule 3: Buscar el vehículo por vehiculo_id
        vehiculo = self.db.query(Vehiculo).filter(Vehiculo.id == schema.vehiculo_id).first()
        if not vehiculo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vehículo no encontrado."
            )

        # Si su estado es "en_ruta" o "en_mantenimiento", lanzar HTTPException(400, "El vehículo no está disponible.")
        if vehiculo.estado in ["en_ruta", "en_mantenimiento"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El vehículo no está disponible."
            )

        # Rule 4: Crear la ruta y actualizar automáticamente el estado del vehículo a "en_ruta"
        nueva_ruta = RutaAsignacion(
            vehiculo_id=schema.vehiculo_id,
            trabajador_id=schema.trabajador_id,
            origen=schema.origen,
            destino=schema.destino,
            fecha_salida=schema.fecha_salida,
            fecha_llegada_estimada=schema.fecha_llegada_estimada,
            estado_ruta="pendiente",  # Se inicializa como pendiente
            kilometraje_salida=schema.kilometraje_salida,
            combustible_salida=schema.combustible_salida,
            observaciones_salida=schema.observaciones_salida
        )
        
        # Actualizamos el estado del vehículo a "en_ruta"
        vehiculo.estado = "en_ruta"

        self.db.add(nueva_ruta)
        self.db.commit()
        self.db.refresh(nueva_ruta)
        return nueva_ruta

    def finalize_ruta(self, ruta_id: int, schema: RutaAsignacionFinalizar) -> RutaAsignacion:
        ruta = self.get_ruta_by_id(ruta_id)
        
        # Actualizamos datos de llegada
        ruta.estado_ruta = "completada"
        ruta.kilometraje_llegada = schema.kilometraje_llegada
        ruta.combustible_llegada = schema.combustible_llegada
        ruta.observaciones_llegada = schema.observaciones_llegada

        # Cambiar el estado del vehículo asociado a "disponible"
        vehiculo = self.db.query(Vehiculo).filter(Vehiculo.id == ruta.vehiculo_id).first()
        if vehiculo:
            vehiculo.estado = "disponible"

        self.db.commit()
        self.db.refresh(ruta)
        return ruta

    def update_estado_ruta(self, ruta_id: int, nuevo_estado: str) -> RutaAsignacion:
        ruta = self.get_ruta_by_id(ruta_id)
        ruta.estado_ruta = nuevo_estado

        if nuevo_estado == "completada":
            vehiculo = self.db.query(Vehiculo).filter(Vehiculo.id == ruta.vehiculo_id).first()
            if vehiculo:
                vehiculo.estado = "disponible"
        elif nuevo_estado == "en_progreso":
            vehiculo = self.db.query(Vehiculo).filter(Vehiculo.id == ruta.vehiculo_id).first()
            if vehiculo:
                vehiculo.estado = "en_ruta"
        elif nuevo_estado in ["cancelada", "pendiente"]:
            vehiculo = self.db.query(Vehiculo).filter(Vehiculo.id == ruta.vehiculo_id).first()
            if vehiculo:
                vehiculo.estado = "disponible"

        self.db.commit()
        self.db.refresh(ruta)
        return ruta

    def update_ruta(self, ruta_id: int, schema: RutaAsignacionUpdate) -> RutaAsignacion:
        ruta = self.get_ruta_by_id(ruta_id)

        if schema.origen is not None:
            ruta.origen = schema.origen
        if schema.destino is not None:
            ruta.destino = schema.destino
        if schema.fecha_salida is not None:
            ruta.fecha_salida = schema.fecha_salida
        if schema.fecha_llegada_estimada is not None:
            ruta.fecha_llegada_estimada = schema.fecha_llegada_estimada
        
        if schema.kilometraje_salida is not None:
            ruta.kilometraje_salida = schema.kilometraje_salida
        if schema.kilometraje_llegada is not None:
            ruta.kilometraje_llegada = schema.kilometraje_llegada
        if schema.combustible_salida is not None:
            ruta.combustible_salida = schema.combustible_salida
        if schema.combustible_llegada is not None:
            ruta.combustible_llegada = schema.combustible_llegada
        if schema.observaciones_salida is not None:
            ruta.observaciones_salida = schema.observaciones_salida
        if schema.observaciones_llegada is not None:
            ruta.observaciones_llegada = schema.observaciones_llegada

        if schema.estado_ruta is not None:
            self.update_estado_ruta(ruta_id, schema.estado_ruta)
        else:
            self.db.commit()
            self.db.refresh(ruta)

        return ruta

    def delete_ruta(self, ruta_id: int) -> dict:
        ruta = self.get_ruta_by_id(ruta_id)
        if ruta.estado_ruta in ["pendiente", "en_progreso"]:
            vehiculo = self.db.query(Vehiculo).filter(Vehiculo.id == ruta.vehiculo_id).first()
            if vehiculo:
                vehiculo.estado = "disponible"

        self.db.delete(ruta)
        self.db.commit()
        return {"detail": "Asignación de ruta eliminada correctamente."}
