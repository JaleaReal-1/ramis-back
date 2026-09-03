"""
Tests de integración para inspecciones dinámicas de vehículos.
Cubre FASE 3: Inspecciones y checklist dinámico.

NOTA: Los tests se enfocanen validar:
- Creación de inspecciones
- Cálculo automático de resultado
- Validación de criticidad
- Monotonía de kilometraje
- Integración con rutas
- RBAC
"""
import uuid
from datetime import datetime, timedelta
from typing import Optional
import pytest

from app.dependencies.auth_dependencies import get_current_user
from app.main import app
from app.models.user import User
from app.models.inspeccion import ChecklistItem


@pytest.fixture(autouse=True)
def override_auth(db_session):
    """Crear usuarios para los tests de inspecciones"""
    # Almacenero
    almacenero = User(
        nombre="Admin",
        apellidos="Principal",
        dni="12345678",
        cargo="Almacenero",
        email="almacenero@test.com",
        password="hashed_password",
        role="almacenero"
    )
    db_session.add(almacenero)

    # Trabajador (conductor)
    trabajador = User(
        nombre="Chofer",
        apellidos="Prueba",
        dni="87654321",
        cargo="Conductor",
        email="chofer@test.com",
        password="hashed_password",
        role="trabajador"
    )
    db_session.add(trabajador)
    db_session.commit()
    db_session.refresh(almacenero)
    db_session.refresh(trabajador)

    # Override auth para usar almacenero por defecto
    app.dependency_overrides[get_current_user] = lambda: almacenero

    yield almacenero, trabajador
    app.dependency_overrides.pop(get_current_user, None)


def _unique_dni() -> str:
    return str(uuid.uuid4().int)[:8]


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


def _ensure_checklist_items(db_session):
    """Asegurar que existen items de checklist en la BD"""
    existing_count = db_session.query(ChecklistItem).count()
    if existing_count == 0:
        # Insertar items de checklist
        items_data = [
            ("Frenos", "Seguridad", "critica", 1),
            ("Llantas", "Seguridad", "critica", 2),
            ("Luces principales", "Iluminación", "critica", 3),
            ("Nivel de Aceite", "Motor", "media", 4),
            ("Nivel de Refrigerante", "Motor", "media", 5),
            ("Espejos Retrovisores", "Carrocería", "baja", 6),
            ("Extintor de Emergencia", "Seguridad", "alta", 7),
            ("Botiquín de Primeros Auxilios", "Seguridad", "alta", 8),
            ("Cinturones de Seguridad", "Seguridad", "critica", 9),
        ]
        for nombre, categoria, criticidad, orden in items_data:
            item = ChecklistItem(
                nombre=nombre,
                categoria=categoria,
                criticidad=criticidad,
                orden=orden,
                activo=True
            )
            db_session.add(item)
        db_session.commit()


# ============================================================
# TEST 1: Listar items del checklist
# ============================================================

def test_listar_checklist_items(client, db_session, override_auth):
    """Verificar que los items del checklist se cargan"""
    _ensure_checklist_items(db_session)
    response = client.get("/api/inspecciones/checklist-items/")
    assert response.status_code == 200
    items = response.json()
    assert len(items) > 0
    # Validar que existen items críticos
    criticidades = [item["criticidad"] for item in items]
    assert "critica" in criticidades


# ============================================================
# TEST 2: Crear inspección SALIDA aprobada
# ============================================================

def test_crear_inspeccion_salida_aprobada(client, db_session, override_auth):
    """Crear una inspección de SALIDA completamente aprobada"""
    almacenero, trabajador = override_auth
    _ensure_checklist_items(db_session)

    vehiculo = _crear_vehiculo(client)

    # Obtener items del checklist
    checklist_response = client.get("/api/inspecciones/checklist-items/")
    checklist_items = checklist_response.json()
    assert len(checklist_items) > 0

    # Crear inspección con todos los items conformes
    detalles = [
        {"checklist_item_id": item["id"], "resultado_item": "conforme"}
        for item in checklist_items
    ]

    response = client.post(
        "/api/inspecciones/",
        json={
            "vehiculo_id": vehiculo["id"],
            "trabajador_id": trabajador.id,
            "tipo": "salida",
            "kilometraje": 1000.0,
            "combustible": "3/4",
            "observaciones": "Sin novedad",
            "detalles": detalles,
        },
    )
    assert response.status_code == 201
    inspeccion = response.json()
    assert inspeccion["resultado"] == "aprobada"
    assert inspeccion["tipo"] == "salida"
    assert inspeccion["kilometraje"] == 1000.0


# ============================================================
# TEST 3: Validar monotonía de kilometraje
# ============================================================

def test_validar_monotonia_kilometraje(client, db_session, override_auth):
    """
    Verificar que el kilometraje no puede decrecer.
    """
    almacenero, trabajador = override_auth
    _ensure_checklist_items(db_session)

    vehiculo = _crear_vehiculo(client)

    checklist_response = client.get("/api/inspecciones/checklist-items/")
    checklist_items = checklist_response.json()

    # Primera inspección con KM = 1000
    detalles = [
        {"checklist_item_id": item["id"], "resultado_item": "conforme"}
        for item in checklist_items
    ]

    resp1 = client.post(
        "/api/inspecciones/",
        json={
            "vehiculo_id": vehiculo["id"],
            "trabajador_id": trabajador.id,
            "tipo": "salida",
            "kilometraje": 1000.0,
            "combustible": "3/4",
            "detalles": detalles,
        },
    )
    assert resp1.status_code == 201

    # Intentar segunda inspección con KM menor = 900 (debe fallar)
    detalles_2 = [
        {"checklist_item_id": item["id"], "resultado_item": "conforme"}
        for item in checklist_items
    ]

    resp2 = client.post(
        "/api/inspecciones/",
        json={
            "vehiculo_id": vehiculo["id"],
            "trabajador_id": trabajador.id,
            "tipo": "llegada",
            "kilometraje": 900.0,  # Menor que 1000
            "combustible": "1/2",
            "detalles": detalles_2,
        },
    )
    assert resp2.status_code == 400
    assert "monotónico" in resp2.json()["detail"].lower()


# ============================================================
# TEST 4: Crear inspección con item crítico NO_CONFORME
# ============================================================

def test_crear_inspeccion_rechazada_critica(client, db_session, override_auth):
    """
    Crear inspección que resulte RECHAZADA por tener un item CRÍTICO NO_CONFORME.
    El vehículo debe quedar BLOQUEADO.
    """
    almacenero, trabajador = override_auth
    _ensure_checklist_items(db_session)

    vehiculo = _crear_vehiculo(client)

    checklist_response = client.get("/api/inspecciones/checklist-items/")
    checklist_items = checklist_response.json()

    # Encontrar un item crítico
    item_critico = None
    for item in checklist_items:
        if item["criticidad"].lower() == "critica":
            item_critico = item
            break

    assert item_critico is not None, "No se encontró item crítico en el checklist"

    # Crear detalles: el item crítico es NO_CONFORME, otros conformes
    detalles = []
    for item in checklist_items:
        if item["id"] == item_critico["id"]:
            detalles.append({"checklist_item_id": item["id"], "resultado_item": "no_conforme"})
        else:
            detalles.append({"checklist_item_id": item["id"], "resultado_item": "conforme"})

    response = client.post(
        "/api/inspecciones/",
        json={
            "vehiculo_id": vehiculo["id"],
            "trabajador_id": trabajador.id,
            "tipo": "salida",
            "kilometraje": 1500.0,
            "combustible": "lleno",
            "observaciones": "Item crítico con problemas",
            "detalles": detalles,
        },
    )
    assert response.status_code == 201
    inspeccion = response.json()
    assert inspeccion["resultado"] == "rechazada"

    # Verificar que el vehículo quedó BLOQUEADO
    vehiculo_updated = client.get(f"/api/vehiculos/{vehiculo['id']}")
    assert vehiculo_updated.status_code == 200
    assert vehiculo_updated.json()["estado"] == "bloqueado"


# ============================================================
# TEST 5: Listar inspecciones
# ============================================================

def test_listar_inspecciones(client, db_session, override_auth):
    """Listar todas las inspecciones"""
    almacenero, trabajador = override_auth
    _ensure_checklist_items(db_session)

    # Crear un vehículo e inspección
    vehiculo = _crear_vehiculo(client)
    checklist_response = client.get("/api/inspecciones/checklist-items/")
    checklist_items = checklist_response.json()

    detalles = [
        {"checklist_item_id": item["id"], "resultado_item": "conforme"}
        for item in checklist_items
    ]

    client.post(
        "/api/inspecciones/",
        json={
            "vehiculo_id": vehiculo["id"],
            "trabajador_id": trabajador.id,
            "tipo": "salida",
            "kilometraje": 1000.0,
            "combustible": "3/4",
            "detalles": detalles,
        },
    )

    # Listar
    response = client.get("/api/inspecciones/")
    assert response.status_code == 200
    inspecciones = response.json()
    assert len(inspecciones) > 0


# ============================================================
# TEST 6: Bloqueo de inicio de ruta si inspección rechazada
# ============================================================

def test_iniciar_ruta_rechaza_si_inspeccion_rechazada(client, db_session, override_auth):
    """
    Verificar que no se puede iniciar una ruta si la inspección SALIDA fue rechazada.
    """
    almacenero, trabajador = override_auth
    _ensure_checklist_items(db_session)

    vehiculo = _crear_vehiculo(client)

    # Crear ruta
    salida = datetime.utcnow()
    llegada = salida + timedelta(hours=2)

    ruta_response = client.post(
        "/api/rutas/",
        json={
            "vehiculo_id": vehiculo["id"],
            "trabajador_id": trabajador.id,
            "origen": "A",
            "destino": "B",
            "fecha_salida": salida.isoformat(),
            "fecha_llegada_estimada": llegada.isoformat(),
        },
    )
    assert ruta_response.status_code == 201
    ruta_id = ruta_response.json()["id"]

    # Crear inspección RECHAZADA
    checklist_response = client.get("/api/inspecciones/checklist-items/")
    checklist_items = checklist_response.json()

    # Obtener item crítico
    item_critico = next(
        (item for item in checklist_items if item["criticidad"].lower() == "critica"),
        None
    )
    assert item_critico is not None

    detalles = []
    for item in checklist_items:
        if item["id"] == item_critico["id"]:
            detalles.append({"checklist_item_id": item["id"], "resultado_item": "no_conforme"})
        else:
            detalles.append({"checklist_item_id": item["id"], "resultado_item": "conforme"})

    inspeccion_response = client.post(
        "/api/inspecciones/",
        json={
            "vehiculo_id": vehiculo["id"],
            "trabajador_id": trabajador.id,
            "tipo": "salida",
            "kilometraje": 2000.0,
            "combustible": "1/2",
            "detalles": detalles,
        },
    )
    assert inspeccion_response.status_code == 201
    assert inspeccion_response.json()["resultado"] == "rechazada"

    # Intentar iniciar ruta como trabajador
    app.dependency_overrides[get_current_user] = lambda: trabajador
    iniciar_response = client.patch(
        f"/api/rutas/{ruta_id}/iniciar",
        json={
            "firma_trabajador": "sig",
            "check_llantas": True,
            "check_frenos": True,
            "check_luces": True,
            "kilometraje_salida": 2000.0,
            "combustible_salida": "1/2",
        },
    )
    # Debe fallar porque la inspección SALIDA fue rechazada
    assert iniciar_response.status_code == 400
    assert "rechazada" in iniciar_response.json()["detail"].lower()


# ============================================================
# TEST 7: Integración - Inspección aprobada permite iniciar ruta
# ============================================================

def test_inspeccion_aprobada_permite_iniciar_ruta(client, db_session, override_auth):
    """
    Verificar que una inspección aprobada PERMITE iniciar la ruta.
    """
    almacenero, trabajador = override_auth
    _ensure_checklist_items(db_session)

    vehiculo = _crear_vehiculo(client)

    # Crear ruta
    salida = datetime.utcnow()
    llegada = salida + timedelta(hours=2)

    ruta_response = client.post(
        "/api/rutas/",
        json={
            "vehiculo_id": vehiculo["id"],
            "trabajador_id": trabajador.id,
            "origen": "Lima",
            "destino": "Arequipa",
            "fecha_salida": salida.isoformat(),
            "fecha_llegada_estimada": llegada.isoformat(),
        },
    )
    assert ruta_response.status_code == 201
    ruta_id = ruta_response.json()["id"]

    # Crear inspección APROBADA
    checklist_response = client.get("/api/inspecciones/checklist-items/")
    checklist_items = checklist_response.json()

    detalles = [
        {"checklist_item_id": item["id"], "resultado_item": "conforme"}
        for item in checklist_items
    ]

    inspeccion_response = client.post(
        "/api/inspecciones/",
        json={
            "vehiculo_id": vehiculo["id"],
            "trabajador_id": trabajador.id,
            "tipo": "salida",
            "kilometraje": 1000.0,
            "combustible": "lleno",
            "detalles": detalles,
        },
    )
    assert inspeccion_response.status_code == 201
    assert inspeccion_response.json()["resultado"] == "aprobada"

    # Iniciar ruta como trabajador
    app.dependency_overrides[get_current_user] = lambda: trabajador
    # Usar una firma base64 válida (PNG transparente de 1x1 pixel)
    valid_base64_sig = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
    iniciar_response = client.patch(
        f"/api/rutas/{ruta_id}/iniciar",
        json={
            "firma_trabajador": valid_base64_sig,
            "check_llantas": True,
            "check_frenos": True,
            "check_luces": True,
            "kilometraje_salida": 1000.0,
            "combustible_salida": "lleno",
        },
    )
    # Debe tener éxito
    assert iniciar_response.status_code == 200
    assert iniciar_response.json()["estado_ruta"] == "en_progreso"


# ============================================================
# TEST 8: Obtener detalle de inspección
# ============================================================

def test_obtener_detalle_inspeccion(client, db_session, override_auth):
    """Obtener detalle de una inspección con detalles de items"""
    almacenero, trabajador = override_auth
    _ensure_checklist_items(db_session)

    vehiculo = _crear_vehiculo(client)

    checklist_response = client.get("/api/inspecciones/checklist-items/")
    checklist_items = checklist_response.json()

    detalles = [
        {"checklist_item_id": item["id"], "resultado_item": "conforme"}
        for item in checklist_items
    ]

    # Crear inspección
    create_response = client.post(
        "/api/inspecciones/",
        json={
            "vehiculo_id": vehiculo["id"],
            "trabajador_id": trabajador.id,
            "tipo": "salida",
            "kilometraje": 1000.0,
            "combustible": "3/4",
            "detalles": detalles,
        },
    )
    assert create_response.status_code == 201
    inspeccion_id = create_response.json()["id"]

    # Obtener detalle
    detail_response = client.get(f"/api/inspecciones/{inspeccion_id}")
    assert detail_response.status_code == 200
    inspeccion = detail_response.json()
    assert inspeccion["id"] == inspeccion_id
    assert inspeccion["resultado"] == "aprobada"
    assert len(inspeccion["detalles"]) > 0
