from __future__ import annotations

from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from datetime import datetime, timezone
from app.models.ruta_asignacion import RutaAsignacion
from app.models.vehiculo import Vehiculo
from app.models.user import User
from app.models.mantenimiento import Mantenimiento
from app.schemas.ruta_asignacion_schema import (
    RutaAsignacionCreate,
    RutaAsignacionUpdate,
    RutaAsignacionFinalizar,
    RutaAsignacionIniciar
)
from app.utils.pdf_generator import generar_pdf_ruta

class RutaService:
    def __init__(self, db: Session):
        self.db = db

    def get_ruta_by_id(self, ruta_id: int) -> RutaAsignacion:
        ruta = self.db.query(RutaAsignacion).filter(
            RutaAsignacion.id == ruta_id,
            RutaAsignacion.estado_ruta != "inactivo"
        ).first()
        if not ruta:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Asignación de ruta no encontrada."
            )
        return ruta

    def get_all_rutas(self) -> list[RutaAsignacion]:
        return self.db.query(RutaAsignacion).filter(RutaAsignacion.estado_ruta != "inactivo").all()

    def get_rutas_by_trabajador(self, trabajador_id: int) -> list[RutaAsignacion]:
        return self.db.query(RutaAsignacion).filter(
            RutaAsignacion.trabajador_id == trabajador_id,
            RutaAsignacion.estado_ruta != "inactivo"
        ).all()

    def create_ruta(self, schema: RutaAsignacionCreate) -> RutaAsignacion:
        # Rule 1: Buscar al usuario por trabajador_id.
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
        vehiculo = self.db.query(Vehiculo).filter(
            Vehiculo.id == schema.vehiculo_id,
            Vehiculo.estado != "inactivo"
        ).first()
        if not vehiculo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vehículo no encontrado."
            )

        # Si su estado es "asignado", "en_ruta" o "en_mantenimiento", lanzar HTTPException(400, "El vehículo no está disponible.")
        if vehiculo.estado in ["asignado", "en_ruta", "en_mantenimiento"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El vehículo no está disponible."
            )

        # Rule 4: Crear la ruta y actualizar automáticamente el estado del vehículo a "asignado"
        nueva_ruta = RutaAsignacion(
            vehiculo_id=schema.vehiculo_id,
            trabajador_id=schema.trabajador_id,
            origen=schema.origen,
            destino=schema.destino,
            fecha_salida=schema.fecha_salida,
            fecha_llegada_estimada=schema.fecha_llegada_estimada,
            estado_ruta="pendiente",  # Se inicializa como pendiente
            observaciones_salida=schema.observaciones_salida
        )
        
        # Actualizamos el estado del vehículo a "asignado"
        vehiculo.estado = "asignado"

        self.db.add(nueva_ruta)
        self.db.commit()
        self.db.refresh(nueva_ruta)
        return nueva_ruta

    def iniciar_ruta(self, ruta_id: int, schema: RutaAsignacionIniciar) -> RutaAsignacion:
        ruta = self.get_ruta_by_id(ruta_id)

        if ruta.estado_ruta != "pendiente":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Solo se puede iniciar una ruta pendiente."
            )
        
        # Validar que los checks sean True (doble validación)
        if not (schema.check_llantas and schema.check_frenos and schema.check_luces):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Todos los checks de inspección deben ser aprobados (True) para iniciar la ruta."
            )

        # Buscar el vehículo
        vehiculo = self.db.query(Vehiculo).filter(Vehiculo.id == ruta.vehiculo_id).first()
        if not vehiculo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vehículo no encontrado."
            )

        # Actualizar datos de inicio
        ruta.estado_ruta = "en_progreso"
        ruta.kilometraje_salida = schema.kilometraje_salida
        ruta.combustible_salida = schema.combustible_salida
        ruta.observaciones_salida = schema.observaciones_salida
        ruta.firma_trabajador = schema.firma_trabajador
        ruta.check_llantas = schema.check_llantas
        ruta.check_frenos = schema.check_frenos
        ruta.check_luces = schema.check_luces

        # Pasar vehículo a 'en_ruta'
        vehiculo.estado = "en_ruta"

        # Generar el PDF
        generar_pdf_ruta(ruta)

        self.db.commit()
        self.db.refresh(ruta)
        return ruta

    def finalize_ruta(self, ruta_id: int, schema: RutaAsignacionFinalizar) -> RutaAsignacion:
        ruta = self.get_ruta_by_id(ruta_id)

        if ruta.estado_ruta != "en_progreso":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Solo se puede finalizar una ruta en progreso."
            )
        
        # Actualizamos datos de llegada
        ruta.estado_ruta = "completada"
        ruta.kilometraje_llegada = schema.kilometraje_llegada
        ruta.combustible_llegada = schema.combustible_llegada
        ruta.observaciones_llegada = schema.observaciones_llegada

        # Cambiar el estado del vehículo asociado
        vehiculo = self.db.query(Vehiculo).filter(Vehiculo.id == ruta.vehiculo_id).first()
        if vehiculo:
            obs = (schema.observaciones_llegada or "").strip().lower()
            tiene_falla = False
            # Solo las observaciones que describen una incidencia envían el vehículo a mantenimiento.
            observaciones_sin_falla = {
                "ninguna",
                "ninguno",
                "ok",
                "todo ok",
                "llegada ok",
                "perfecto",
                "sin novedad",
                "sin novedades",
                "llegada sin novedad",
                "llegada sin novedades",
                "sin incidencia",
                "sin incidencias",
            }
            if obs and obs not in observaciones_sin_falla:
                tiene_falla = True
            
            if tiene_falla:
                vehiculo.estado = "en_mantenimiento"
                nuevo_mantenimiento = Mantenimiento(
                    vehiculo_id=ruta.vehiculo_id,
                    fecha_ingreso=datetime.now(timezone.utc),
                    descripcion_falla=schema.observaciones_llegada,
                    costo=0.0,
                    estado="en_taller"
                )
                self.db.add(nuevo_mantenimiento)
            else:
                vehiculo.estado = "disponible"

        self.db.commit()
        self.db.refresh(ruta)
        return ruta

    def update_estado_ruta(self, ruta_id: int, nuevo_estado: str) -> RutaAsignacion:
        ruta = self.get_ruta_by_id(ruta_id)
        ruta.estado_ruta = nuevo_estado

        vehiculo = self.db.query(Vehiculo).filter(Vehiculo.id == ruta.vehiculo_id).first()
        if vehiculo:
            if nuevo_estado == "completada":
                vehiculo.estado = "disponible"
            elif nuevo_estado == "en_progreso":
                vehiculo.estado = "en_ruta"
            elif nuevo_estado == "pendiente":
                vehiculo.estado = "asignado"
            elif nuevo_estado in ["cancelada"]:
                vehiculo.estado = "disponible"

        self.db.commit()
        self.db.refresh(ruta)
        return ruta

    def update_ruta(self, ruta_id: int, schema: RutaAsignacionUpdate) -> RutaAsignacion:
        ruta = self.get_ruta_by_id(ruta_id)

        campos_actualizables = (
            "origen", "destino", "fecha_salida", "fecha_llegada_estimada",
            "kilometraje_salida", "kilometraje_llegada", "combustible_salida",
            "combustible_llegada", "observaciones_salida", "observaciones_llegada",
            "firma_trabajador", "check_llantas", "check_frenos", "check_luces"
        )
        for campo in campos_actualizables:
            valor = getattr(schema, campo)
            if valor is not None:
                setattr(ruta, campo, valor)

        if schema.estado_ruta is not None:
            self.update_estado_ruta(ruta_id, schema.estado_ruta)
        else:
            self.db.commit()
            self.db.refresh(ruta)

        return ruta

    def delete_ruta(self, ruta_id: int, usuario_id: int) -> dict:
        ruta = self.get_ruta_by_id(ruta_id)
        if ruta.estado_ruta in ["pendiente", "en_progreso"]:
            vehiculo = self.db.query(Vehiculo).filter(Vehiculo.id == ruta.vehiculo_id).first()
            if vehiculo:
                vehiculo.estado = "disponible"

        ruta.estado_ruta = "inactivo"
        ruta.fecha_baja = datetime.now(timezone.utc)
        ruta.usuario_baja = usuario_id
        self.db.commit()
        return {"detail": "Ruta marcada como inactiva correctamente."}
