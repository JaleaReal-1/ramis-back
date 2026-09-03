"""
Verificación RBAC: acceso del rol `admin` al módulo Transportes.

Confirma la corrección aplicada en vehiculo_router, averia_router,
incidente_router y mantenimiento_router (permitir 'admin'), y que
rutas/{id}/iniciar SIGA rechazando a 'admin' (regla de negocio:
solo el trabajador asignado puede iniciar su ruta).
"""
import uuid
import pytest

from app.dependencies.auth_dependencies import get_current_user
from app.main import app
from app.models.user import User


@pytest.fixture(autouse=True)
def override_admin(db_session):
    """Usuario administrador autenticado (rol = admin) para todos los tests."""
    admin = User(
        nombre="Admin",
        apellidos="Principal",
        dni="12345678",
        cargo="Administrador",
        email="admin@test.com",
        password="hashed_password",
        role="admin",
    )
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)

    app.dependency_overrides[get_current_user] = lambda: admin
    yield admin
    app.dependency_overrides.pop(get_current_user, None)


def _crear_vehiculo(client, placa: str = None):
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
    assert response.status_code == 201, response.text
    return response.json()


def _register_trabajador(client):
    email = f"trab_{uuid.uuid4()}@test.com"
    response = client.post(
        "/auth/register",
        json={
            "nombre": "Chofer",
            "apellidos": "Prueba",
            "dni": str(uuid.uuid4().int)[:8],
            "cargo": "Conductor",
            "email": email,
            "password": "12345678",
            "role": "trabajador",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _crear_ruta(client, vehiculo_id, trabajador_id):
    from datetime import datetime, timedelta

    response = client.post(
        "/api/rutas/",
        json={
            "origen": "Lima",
            "destino": "Juliaca",
            "fecha_salida": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
            "fecha_llegada_estimada": (datetime.utcnow() + timedelta(days=1)).isoformat(),
            "vehiculo_id": vehiculo_id,
            "trabajador_id": trabajador_id,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_admin_puede_listar_vehiculos(client):
    _crear_vehiculo(client)
    response = client.get("/api/vehiculos/")
    assert response.status_code == 200, response.text
    assert len(response.json()) == 1


def test_admin_puede_acceder_averias(client):
    response = client.get("/api/averias/")
    assert response.status_code == 200, response.text


def test_admin_puede_acceder_incidentes(client):
    response = client.get("/api/incidentes/")
    assert response.status_code == 200, response.text


def test_admin_puede_acceder_mantenimientos(client):
    response = client.get("/api/mantenimientos/")
    assert response.status_code == 200, response.text


def test_admin_puede_acceder_inspecciones(client):
    response = client.get("/api/inspecciones/")
    assert response.status_code == 200, response.text


def test_admin_puede_listar_rutas(client):
    response = client.get("/api/rutas/")
    assert response.status_code == 200, response.text


def test_admin_puede_crear_vehiculo(client):
    vehiculo = _crear_vehiculo(client)
    assert vehiculo["placa"]


def test_admin_puede_crear_ruta(client):
    vehiculo = _crear_vehiculo(client)
    trabajador = _register_trabajador(client)
    ruta = _crear_ruta(client, vehiculo["id"], trabajador["id"])
    assert ruta["id"]


def test_admin_puede_crear_averia_y_incidente(client):
    vehiculo = _crear_vehiculo(client)
    trabajador = _register_trabajador(client)
    averia = client.post(
        "/api/averias/",
        json={
            "vehiculo_id": vehiculo["id"],
            "categoria": "Motor",
            "componente": "Termostato",
            "descripcion": "Sobrecalentamiento",
            "criticidad": "alta",
            "origen": "operacion",
        },
    )
    assert averia.status_code == 201, averia.text

    incidente = client.post(
        "/api/incidentes/",
        json={
            "vehiculo_id": vehiculo["id"],
            "trabajador_id": trabajador["id"],
            "tipo": "casi_accidente",
            "ubicacion": "Carretera Central km 40",
            "descripcion": "Frenada brusca por obstáculo",
            "fecha_incidente": "2026-01-01T10:00:00",
        },
    )
    assert incidente.status_code == 201, incidente.text


def test_rutas_iniciar_rechaza_admin_y_exige_trabajador_asignado(client):
    """Regla de negocio: solo el trabajador asignado puede iniciar la ruta."""
    vehiculo = _crear_vehiculo(client)
    trabajador = _register_trabajador(client)
    ruta = _crear_ruta(client, vehiculo["id"], trabajador["id"])

    # El admin (autenticado en el fixture) intenta iniciar la ruta -> 403
    response = client.patch(
        f"/api/rutas/{ruta['id']}/iniciar",
        json={
            "firma_trabajador": "base64firma",
            "check_llantas": True,
            "check_frenos": True,
            "check_luces": True,
            "kilometraje_salida": 100.0,
            "combustible_salida": "lleno",
        },
    )
    assert response.status_code == 403, response.text
