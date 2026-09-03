import uuid
from datetime import datetime, timedelta
from typing import Optional
import pytest

from app.dependencies.auth_dependencies import get_current_user
from app.main import app
from app.models.user import User
from app.test.integration.test_inspecciones_fase3 import _ensure_checklist_items


@pytest.fixture(autouse=True)
def override_auth(db_session):
    # Crear un usuario almacenero para los flujos de gestión de transportes.
    user = User(
        nombre="Admin",
        apellidos="Principal",
        dni="12345678",
        cargo="Almacenero",
        email="admin@test.com",
        password="hashed_password",
        role="almacenero"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    
    app.dependency_overrides[get_current_user] = lambda: user
    yield user
    app.dependency_overrides.pop(get_current_user, None)


def _unique_dni() -> str:
    return str(uuid.uuid4().int)[:8]


def _register_trabajador(client):
    email = f"trab_{uuid.uuid4()}@test.com"
    response = client.post(
        "/auth/register",
        json={
            "nombre": "Chofer",
            "apellidos": "Prueba",
            "dni": _unique_dni(),
            "cargo": "Conductor",
            "email": email,
            "password": "12345678",
            "role": "trabajador",
        },
    )
    assert response.status_code == 201
    return response.json()


def _crear_vehiculo(client, placa: Optional[str] = None):
    placa = placa or f"T{uuid.uuid4().hex[:6].upper()}"
    response = client.post(
        "/api/vehiculos/",
        json={
            "placa": placa,
            "marca": "Volvo",
            "modelo": "FH16",
            "capacidad_carga": 20.5,
        },
    )
    assert response.status_code == 201
    return response.json()

def _crear_inspeccion_salida_aprobada(client, vehiculo_id, trabajador_id, db_session):
    _ensure_checklist_items(db_session)
    checklist_response = client.get("/api/inspecciones/checklist-items/")
    checklist_items = checklist_response.json()

    detalles = [
        {"checklist_item_id": item["id"], "resultado_item": "conforme"}
        for item in checklist_items
    ]

    response = client.post(
        "/api/inspecciones/",
        json={
            "vehiculo_id": vehiculo_id,
            "trabajador_id": trabajador_id,
            "tipo": "salida",
            "kilometraje": 100.0,
            "combustible": "lleno",
            "detalles": detalles,
        },
    )
    assert response.status_code == 201
    assert response.json()["resultado"] in ["aprobada", "aprobada_con_observaciones"]
    return response.json()


def _crear_inspeccion_post_mantenimiento_aprobada(client, vehiculo_id, trabajador_id, db_session):
    _ensure_checklist_items(db_session)
    checklist_response = client.get("/api/inspecciones/checklist-items/")
    checklist_items = checklist_response.json()

    detalles = [
        {"checklist_item_id": item["id"], "resultado_item": "conforme"}
        for item in checklist_items
    ]

    response = client.post(
        "/api/inspecciones/",
        json={
            "vehiculo_id": vehiculo_id,
            "trabajador_id": trabajador_id,
            "tipo": "post_mantenimiento",
            "kilometraje": 15000.0,
            "combustible": "lleno",
            "detalles": detalles,
        },
    )
    assert response.status_code == 201
    assert response.json()["resultado"] in ["aprobada", "aprobada_con_observaciones"]
    return response.json()


def test_listar_vehiculos_vacio(client):
    response = client.get("/api/vehiculos/")
    assert response.status_code == 200
    assert response.json() == []


def test_crud_vehiculo(client):
    creado = _crear_vehiculo(client, "ABC123")
    assert creado["placa"] == "ABC123"
    assert creado["estado"] == "disponible"

    listado = client.get("/api/vehiculos/")
    assert listado.status_code == 200
    assert any(v["id"] == creado["id"] for v in listado.json())

    detalle = client.get(f"/api/vehiculos/{creado['id']}")
    assert detalle.status_code == 200
    assert detalle.json()["marca"] == "Volvo"


def test_listar_rutas_y_crear_asignacion(client):
    vacio = client.get("/api/rutas/")
    assert vacio.status_code == 200
    assert vacio.json() == []

    vehiculo = _crear_vehiculo(client)
    trabajador = _register_trabajador(client)
    salida = datetime.utcnow()
    llegada = salida + timedelta(hours=4)

    # El esquema de creación ya no pide kilometraje ni gasolina de salida.
    response = client.post(
        "/api/rutas/",
        json={
            "vehiculo_id": vehiculo["id"],
            "trabajador_id": trabajador["id"],
            "origen": "Juliaca",
            "destino": "Puno",
            "fecha_salida": salida.isoformat(),
            "fecha_llegada_estimada": llegada.isoformat(),
            "observaciones_salida": "Sin novedad",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["estado_ruta"] == "pendiente"
    assert data["kilometraje_salida"] is None

    # Al crearse, el vehículo pasa a estar "asignado"
    vehiculo_asignado = client.get(f"/api/vehiculos/{vehiculo['id']}")
    assert vehiculo_asignado.json()["estado"] == "asignado"


def test_iniciar_ruta(client, db_session, override_auth):
    vehiculo = _crear_vehiculo(client)
    trabajador = _register_trabajador(client)
    salida = datetime.utcnow()
    llegada = salida + timedelta(hours=2)

    creada = client.post(
        "/api/rutas/",
        json={
            "vehiculo_id": vehiculo["id"],
            "trabajador_id": trabajador["id"],
            "origen": "A",
            "destino": "B",
            "fecha_salida": salida.isoformat(),
            "fecha_llegada_estimada": llegada.isoformat(),
        },
    )
    ruta_id = creada.json()["id"]

    # Traer el objeto del trabajador registrado de la BD usando db_session
    trabajador_user = db_session.query(User).filter(User.id == trabajador["id"]).first()

    # Intentar iniciar con algún check en False debe fallar (Pydantic ValidationError, retorna 400 por handler custom)
    app.dependency_overrides[get_current_user] = lambda: trabajador_user
    response_fallida = client.patch(
        f"/api/rutas/{ruta_id}/iniciar",
        json={
            "firma_trabajador": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
            "check_llantas": True,
            "check_frenos": False,
            "check_luces": True,
            "kilometraje_salida": 15000.0,
            "combustible_salida": "3/4"
        }
    )
    assert response_fallida.status_code == 400

    # Crear inspección de SALIDA aprobada (obligatoria para iniciar la ruta)
    _crear_inspeccion_salida_aprobada(client, vehiculo["id"], trabajador["id"], db_session)

    # Iniciar con todo correcto
    response_ok = client.patch(
        f"/api/rutas/{ruta_id}/iniciar",
        json={
            "firma_trabajador": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
            "check_llantas": True,
            "check_frenos": True,
            "check_luces": True,
            "kilometraje_salida": 15000.0,
            "combustible_salida": "3/4",
            "observaciones_salida": "Todo impecable"
        }
    )
    assert response_ok.status_code == 200
    data = response_ok.json()
    assert data["estado_ruta"] == "en_progreso"
    assert data["kilometraje_salida"] == 15000.0
    assert data["combustible_salida"] == "3/4"
    assert data["check_llantas"] is True

    # El vehículo pasa a estar 'en_ruta'
    app.dependency_overrides[get_current_user] = lambda: override_auth
    vehiculo_en_ruta = client.get(f"/api/vehiculos/{vehiculo['id']}")
    assert vehiculo_en_ruta.json()["estado"] == "en_ruta"


def test_finalizar_ruta_libera_vehiculo(client, db_session, override_auth):
    vehiculo = _crear_vehiculo(client)
    trabajador = _register_trabajador(client)
    salida = datetime.utcnow()
    llegada = salida + timedelta(hours=2)

    creada = client.post(
        "/api/rutas/",
        json={
            "vehiculo_id": vehiculo["id"],
            "trabajador_id": trabajador["id"],
            "origen": "A",
            "destino": "B",
            "fecha_salida": salida.isoformat(),
            "fecha_llegada_estimada": llegada.isoformat(),
        },
    )
    ruta_id = creada.json()["id"]

    # Crear inspección de SALIDA aprobada (obligatoria para iniciar la ruta)
    _crear_inspeccion_salida_aprobada(client, vehiculo["id"], trabajador["id"], db_session)

    trabajador_user = db_session.query(User).filter(User.id == trabajador["id"]).first()

    # Iniciar ruta primero (con rol de trabajador asignado)
    app.dependency_overrides[get_current_user] = lambda: trabajador_user
    client.patch(
        f"/api/rutas/{ruta_id}/iniciar",
        json={
            "firma_trabajador": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
            "check_llantas": True,
            "check_frenos": True,
            "check_luces": True,
            "kilometraje_salida": 100.0,
            "combustible_salida": "lleno",
        }
    )

    # Finalizar sin fallas ("Llegada ok") - restauramos la autenticación de administrador
    app.dependency_overrides[get_current_user] = lambda: override_auth
    fin = client.patch(
        f"/api/rutas/{ruta_id}/finalizar",
        json={
            "kilometraje_llegada": 180.0,
            "combustible_llegada": "1/2",
            "observaciones_llegada": "Llegada ok",
        },
    )
    assert fin.status_code == 200
    assert fin.json()["estado_ruta"] == "completada"
    assert fin.json()["kilometraje_llegada"] == 180.0

    vehiculo_libre = client.get(f"/api/vehiculos/{vehiculo['id']}")
    assert vehiculo_libre.json()["estado"] == "disponible"


def test_finalizar_ruta_con_falla_envia_a_mantenimiento(client, db_session, override_auth):
    vehiculo = _crear_vehiculo(client)
    trabajador = _register_trabajador(client)
    salida = datetime.utcnow()
    llegada = salida + timedelta(hours=2)

    creada = client.post(
        "/api/rutas/",
        json={
            "vehiculo_id": vehiculo["id"],
            "trabajador_id": trabajador["id"],
            "origen": "A",
            "destino": "B",
            "fecha_salida": salida.isoformat(),
            "fecha_llegada_estimada": llegada.isoformat(),
        },
    )
    ruta_id = creada.json()["id"]

    # Crear inspección de SALIDA aprobada (obligatoria para iniciar la ruta)
    _crear_inspeccion_salida_aprobada(client, vehiculo["id"], trabajador["id"], db_session)

    trabajador_user = db_session.query(User).filter(User.id == trabajador["id"]).first()

    # Iniciar ruta primero
    app.dependency_overrides[get_current_user] = lambda: trabajador_user
    client.patch(
        f"/api/rutas/{ruta_id}/iniciar",
        json={
            "firma_trabajador": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
            "check_llantas": True,
            "check_frenos": True,
            "check_luces": True,
            "kilometraje_salida": 100.0,
            "combustible_salida": "lleno",
        }
    )

    # Finalizar con falla real - restauramos la autenticación de administrador
    app.dependency_overrides[get_current_user] = lambda: override_auth
    fin = client.patch(
        f"/api/rutas/{ruta_id}/finalizar",
        json={
            "kilometraje_llegada": 180.0,
            "combustible_llegada": "1/2",
            "observaciones_llegada": "Problema grave con los frenos traseros",
        },
    )
    assert fin.status_code == 200
    assert fin.json()["estado_ruta"] == "completada"

    # El vehículo pasa a estar 'en_mantenimiento'
    vehiculo_manto = client.get(f"/api/vehiculos/{vehiculo['id']}")
    assert vehiculo_manto.json()["estado"] == "en_mantenimiento"

    # Verificar creación automática del registro de mantenimiento
    mantenimientos = client.get("/api/mantenimientos/")
    assert mantenimientos.status_code == 200
    assert len(mantenimientos.json()) == 1
    assert mantenimientos.json()[0]["vehiculo_id"] == vehiculo["id"]
    assert mantenimientos.json()[0]["descripcion"] == "Problema grave con los frenos traseros"
    assert mantenimientos.json()[0]["tipo_mantenimiento"] == "correctivo"
    assert mantenimientos.json()[0]["estado_ejecucion"] == "pendiente"


def test_listar_y_crear_mantenimiento(client):
    vacio = client.get("/api/mantenimientos/")
    assert vacio.status_code == 200
    assert vacio.json() == []

    vehiculo = _crear_vehiculo(client)
    # Registrar una avería para vincular el mantenimiento correctivo
    averia = client.post(
        "/api/averias/",
        json={
            "vehiculo_id": vehiculo["id"],
            "categoria": "Frenos",
            "componente": "Pastillas traseras",
            "descripcion": "Freno trasero desgastado",
            "criticidad": "media",
            "origen": "operacion",
        },
    )
    assert averia.status_code == 201
    averia_id = averia.json()["id"]

    response = client.post(
        "/api/mantenimientos/correctivo",
        json={
            "vehiculo_id": vehiculo["id"],
            "averia_id": averia_id,
            "descripcion": "Reemplazo de pastillas de freno trasero",
            "costo": 350.0,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["tipo_mantenimiento"] == "correctivo"
    assert data["estado_ejecucion"] == "pendiente"
    assert data["descripcion"] == "Reemplazo de pastillas de freno trasero"

    vehiculo_taller = client.get(f"/api/vehiculos/{vehiculo['id']}")
    assert vehiculo_taller.json()["estado"] == "en_mantenimiento"


def test_ruta_rechaza_usuario_sin_rol_trabajador(client):
    vehiculo = _crear_vehiculo(client)
    email = f"user_{uuid.uuid4()}@test.com"
    usuario = client.post(
        "/auth/register",
        json={
            "nombre": "Admin",
            "apellidos": "Fake",
            "dni": _unique_dni(),
            "cargo": "Admin",
            "email": email,
            "password": "12345678",
            "role": "admin",
        },
    )
    assert usuario.status_code == 201

    salida = datetime.utcnow()
    response = client.post(
        "/api/rutas/",
        json={
            "vehiculo_id": vehiculo["id"],
            "trabajador_id": usuario.json()["id"],
            "origen": "A",
            "destino": "B",
            "fecha_salida": salida.isoformat(),
            "fecha_llegada_estimada": (salida + timedelta(hours=1)).isoformat(),
        },
    )
    assert response.status_code == 403
    assert "trabajador" in response.json()["detail"].lower()


def test_iniciar_ruta_rechaza_usuario_distinto_o_no_trabajador(client, db_session):
    vehiculo = _crear_vehiculo(client)
    trabajador = _register_trabajador(client)
    salida = datetime.utcnow()
    llegada = salida + timedelta(hours=2)

    creada = client.post(
        "/api/rutas/",
        json={
            "vehiculo_id": vehiculo["id"],
            "trabajador_id": trabajador["id"],
            "origen": "A",
            "destino": "B",
            "fecha_salida": salida.isoformat(),
            "fecha_llegada_estimada": llegada.isoformat(),
        },
    )
    ruta_id = creada.json()["id"]

    # Registrar otro chofer (trabajador distinto)
    otro_chofer = _register_trabajador(client)
    
    otro_user = db_session.query(User).filter(User.id == otro_chofer["id"]).first()

    # Intentar iniciar con el otro trabajador debe retornar 403
    app.dependency_overrides[get_current_user] = lambda: otro_user
    response = client.patch(
        f"/api/rutas/{ruta_id}/iniciar",
        json={
            "firma_trabajador": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
            "check_llantas": True,
            "check_frenos": True,
            "check_luces": True,
            "kilometraje_salida": 15000.0,
            "combustible_salida": "3/4"
        }
    )
    assert response.status_code == 403
    assert "no tienes permiso" in response.json()["detail"].lower()


# ============================================================
# FASE 5: MANTENIMIENTO PREVENTIVO Y EJECUCIÓN
# ============================================================

def _crear_plan_mantenimiento(db_session, nombre="Plan Motor", intervalo_km=10000.0):
    from app.models.plan_mantenimiento import PlanMantenimiento, PlanMantenimientoDetalle
    plan = PlanMantenimiento(nombre=nombre, activo=True)
    db_session.add(plan)
    db_session.flush()
    detalle = PlanMantenimientoDetalle(
        plan_id=plan.id,
        actividad="Cambio de aceite",
        tipo_control="por_km",
        intervalo_km=intervalo_km,
        criticidad="media",
    )
    db_session.add(detalle)
    db_session.commit()
    db_session.refresh(plan)
    return plan


def test_crear_mantenimiento_preventivo_desde_plan(client, db_session):
    vehiculo = _crear_vehiculo(client)
    plan = _crear_plan_mantenimiento(db_session)

    response = client.post(
        "/api/mantenimientos/preventivo",
        json={
            "vehiculo_id": vehiculo["id"],
            "plan_mantenimiento_id": plan.id,
            "tipo_control": "por_km",
            "km_base": 10000.0,
            "descripcion": "Mantenimiento preventivo de motor",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["tipo_mantenimiento"] == "preventivo"
    assert data["plan_mantenimiento_id"] == plan.id
    assert data["estado_ejecucion"] == "pendiente"
    assert data["estado_mantenimiento"] == "NORMAL"


def test_estado_mantenimiento_vencido_por_km(client, db_session):
    vehiculo = _crear_vehiculo(client)
    plan = _crear_plan_mantenimiento(db_session, intervalo_km=1000.0)

    # Elevar el kilometraje del vehículo para simular que superó el KM base
    from app.models.vehiculo import Vehiculo
    v = db_session.query(Vehiculo).filter(Vehiculo.id == vehiculo["id"]).first()
    v.kilometraje_actual = 1500.0
    db_session.commit()

    # El vehículo ya superó el KM base (1000.0) -> VENCIDO
    response = client.post(
        "/api/mantenimientos/preventivo",
        json={
            "vehiculo_id": vehiculo["id"],
            "plan_mantenimiento_id": plan.id,
            "tipo_control": "por_km",
            "km_base": 1000.0,
            "descripcion": "Mantenimiento vencido por KM",
        },
    )
    assert response.status_code == 201
    assert response.json()["estado_mantenimiento"] == "VENCIDO"


def test_ejecutar_mantenimiento_requiere_inspeccion_post_mantenimiento(client, db_session):
    vehiculo = _crear_vehiculo(client)
    trabajador = _register_trabajador(client)

    # Crear avería y mantenimiento correctivo que bloquea el vehículo
    averia = client.post(
        "/api/averias/",
        json={
            "vehiculo_id": vehiculo["id"],
            "categoria": "Motor",
            "componente": "Sistema de enfriamiento",
            "descripcion": "Sobrecalentamiento del motor",
            "criticidad": "alta",
            "origen": "operacion",
        },
    )
    assert averia.status_code == 201

    mant = client.post(
        "/api/mantenimientos/correctivo",
        json={
            "vehiculo_id": vehiculo["id"],
            "averia_id": averia.json()["id"],
            "descripcion": "Cambio de termostato",
            "costo": 500.0,
        },
    )
    assert mant.status_code == 201
    mant_id = mant.json()["id"]

    # El vehículo debe quedar bloqueado en mantenimiento
    bloqueado = client.get(f"/api/vehiculos/{vehiculo['id']}")
    assert bloqueado.json()["estado"] == "en_mantenimiento"

    # Ejecutar el mantenimiento: NO libera el vehículo automáticamente.
    # Queda "observado" a la espera de una inspección POST_MANTENIMIENTO aprobada.
    ejecutado = client.patch(
        f"/api/mantenimientos/{mant_id}/ejecutar",
        json={
            "trabajador_id": trabajador["id"],
            "km_ejecucion": 15000.0,
            "horas_ejecucion": 8.0,
            "observaciones_ejecucion": "Termostato reemplazado correctamente",
        },
    )
    assert ejecutado.status_code == 200
    data = ejecutado.json()
    assert data["estado_ejecucion"] == "completado"
    assert data["km_ejecucion"] == 15000.0

    # Tras ejecutar, el vehículo queda en "observado" (no "disponible")
    observado = client.get(f"/api/vehiculos/{vehiculo['id']}")
    assert observado.json()["estado"] == "observado"
    assert observado.json()["kilometraje_actual"] == 15000.0

    # La avería vinculada queda resuelta
    averia_final = client.get(f"/api/averias/{averia.json()['id']}")
    assert averia_final.json()["estado"] == "resuelta"

    # Sin inspección POST_MANTENIMIENTO el vehículo NO puede operar (sigue "observado")
    ayuda = client.get(f"/api/mantenimientos/vehiculo/{vehiculo['id']}/historial")
    assert ayuda.status_code == 200
    assert len(ayuda.json()) == 1

    # La inspección POST_MANTENIMIENTO aprobada libera el vehículo a "disponible"
    _crear_inspeccion_post_mantenimiento_aprobada(client, vehiculo["id"], trabajador["id"], db_session)
    liberado = client.get(f"/api/vehiculos/{vehiculo['id']}")
    assert liberado.json()["estado"] == "disponible"


def _crear_inspeccion_post_mantenimiento_rechazada(client, vehiculo_id, trabajador_id, db_session):
    """Crear inspección POST_MANTENIMIENTO rechazada marcando un item crítico no conforme."""
    _ensure_checklist_items(db_session)
    checklist_items = client.get("/api/inspecciones/checklist-items/").json()

    detalles = [
        {"checklist_item_id": item["id"], "resultado_item": "conforme"}
        for item in checklist_items
    ]
    # Marcar el primer item crítico ("Frenos") como NO_CONFORME
    detalles[0]["resultado_item"] = "no_conforme"

    response = client.post(
        "/api/inspecciones/",
        json={
            "vehiculo_id": vehiculo_id,
            "trabajador_id": trabajador_id,
            "tipo": "post_mantenimiento",
            "kilometraje": 15000.0,
            "combustible": "lleno",
            "detalles": detalles,
        },
    )
    assert response.status_code == 201
    assert response.json()["resultado"] == "rechazada"
    return response.json()


def test_inspeccion_post_mantenimiento_rechazada_no_libera_vehiculo(client, db_session):
    vehiculo = _crear_vehiculo(client)
    trabajador = _register_trabajador(client)

    # Crear avería y mantenimiento correctivo que bloquea el vehículo
    averia = client.post(
        "/api/averias/",
        json={
            "vehiculo_id": vehiculo["id"],
            "categoria": "Motor",
            "componente": "Sistema de enfriamiento",
            "descripcion": "Sobrecalentamiento del motor",
            "criticidad": "alta",
            "origen": "operacion",
        },
    )
    assert averia.status_code == 201

    mant = client.post(
        "/api/mantenimientos/correctivo",
        json={
            "vehiculo_id": vehiculo["id"],
            "averia_id": averia.json()["id"],
            "descripcion": "Cambio de termostato",
            "costo": 500.0,
        },
    )
    assert mant.status_code == 201

    # Ejecutar el mantenimiento -> vehículo queda "observado"
    ejecutado = client.patch(
        f"/api/mantenimientos/{mant.json()['id']}/ejecutar",
        json={
            "trabajador_id": trabajador["id"],
            "km_ejecucion": 15000.0,
            "horas_ejecucion": 8.0,
            "observaciones_ejecucion": "Termostato reemplazado",
        },
    )
    assert ejecutado.status_code == 200
    observado = client.get(f"/api/vehiculos/{vehiculo['id']}")
    assert observado.json()["estado"] == "observado"

    # Inspección POST_MANTENIMIENTO RECHAZADA no libera el vehículo
    _crear_inspeccion_post_mantenimiento_rechazada(client, vehiculo["id"], trabajador["id"], db_session)
    aun_observado = client.get(f"/api/vehiculos/{vehiculo['id']}")
    assert aun_observado.json()["estado"] == "observado"


def test_historial_mantenimientos_por_vehiculo(client, db_session):
    vehiculo = _crear_vehiculo(client)
    plan = _crear_plan_mantenimiento(db_session)

    client.post(
        "/api/mantenimientos/preventivo",
        json={
            "vehiculo_id": vehiculo["id"],
            "plan_mantenimiento_id": plan.id,
            "tipo_control": "por_km",
            "km_base": 8000.0,
            "descripcion": "Mantenimiento programado",
        },
    )

    historial = client.get(f"/api/mantenimientos/vehiculo/{vehiculo['id']}/historial")
    assert historial.status_code == 200
    assert len(historial.json()) == 1
    assert historial.json()[0]["vehiculo_id"] == vehiculo["id"]
