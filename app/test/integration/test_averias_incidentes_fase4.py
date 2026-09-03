"""
Tests de integración para Averías e Incidentes (FASE 4).
"""
import uuid
from datetime import datetime, timedelta
import pytest

from app.dependencies.auth_dependencies import get_current_user
from app.main import app
from app.models.user import User
from app.models.averia import Averia
from app.models.incidente import Incidente


@pytest.fixture(autouse=True)
def override_auth(db_session):
    """Crear usuarios para los tests"""
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

    app.dependency_overrides[get_current_user] = lambda: almacenero

    yield almacenero, trabajador
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
    assert response.status_code == 201
    return response.json()


def _crear_ruta(client, vehiculo_id: int, trabajador_id: int):
    salida = datetime.utcnow()
    llegada = salida + timedelta(hours=2)
    response = client.post(
        "/api/rutas/",
        json={
            "vehiculo_id": vehiculo_id,
            "trabajador_id": trabajador_id,
            "origen": "Lima",
            "destino": "Arequipa",
            "fecha_salida": salida.isoformat(),
            "fecha_llegada_estimada": llegada.isoformat(),
        },
    )
    assert response.status_code == 201
    return response.json()


# ============================================================
# TESTS DE AVERÍAS
# ============================================================

def test_crear_averia_simple(client, db_session, override_auth):
    """Crear avería simple de baja criticidad"""
    almacenero, trabajador = override_auth
    vehiculo = _crear_vehiculo(client)

    response = client.post(
        "/api/averias/",
        json={
            "vehiculo_id": vehiculo["id"],
            "categoria": "Eléctrico",
            "componente": "Batería",
            "descripcion": "Batería descargada",
            "criticidad": "baja",
            "origen": "operacion",
        },
    )
    assert response.status_code == 201
    averia = response.json()
    assert averia["estado"] == "reportada"
    assert averia["criticidad"] == "baja"


def test_crear_averia_critica_bloquea_vehiculo(client, db_session, override_auth):
    """Crear avería crítica bloquea el vehículo"""
    almacenero, trabajador = override_auth
    vehiculo = _crear_vehiculo(client)

    # Crear avería crítica
    response = client.post(
        "/api/averias/",
        json={
            "vehiculo_id": vehiculo["id"],
            "categoria": "Seguridad",
            "componente": "Frenos",
            "descripcion": "Frenos completamente inoperantes",
            "criticidad": "critica",
            "origen": "inspeccion_salida",
        },
    )
    assert response.status_code == 201
    averia = response.json()
    assert averia["criticidad"] == "critica"

    # Verificar que vehículo está bloqueado
    vehiculo_response = client.get(f"/api/vehiculos/{vehiculo['id']}")
    assert vehiculo_response.status_code == 200
    assert vehiculo_response.json()["estado"] == "bloqueado"


def test_listar_averias(client, db_session, override_auth):
    """Listar averías"""
    almacenero, trabajador = override_auth
    vehiculo = _crear_vehiculo(client)

    # Crear una avería
    client.post(
        "/api/averias/",
        json={
            "vehiculo_id": vehiculo["id"],
            "categoria": "Motor",
            "componente": "Cilindro",
            "descripcion": "Cilindro dañado",
            "criticidad": "media",
            "origen": "operacion",
        },
    )

    # Listar
    response = client.get("/api/averias/")
    assert response.status_code == 200
    averias = response.json()
    assert len(averias) > 0


def test_filtrar_averias_por_vehiculo(client, db_session, override_auth):
    """Filtrar averías por vehículo"""
    almacenero, trabajador = override_auth
    vehiculo1 = _crear_vehiculo(client)
    vehiculo2 = _crear_vehiculo(client)

    # Crear avería para vehículo 1
    client.post(
        "/api/averias/",
        json={
            "vehiculo_id": vehiculo1["id"],
            "categoria": "Motor",
            "componente": "Válvula",
            "descripcion": "Válvula gastada",
            "criticidad": "media",
            "origen": "operacion",
        },
    )

    # Listar avería de vehículo 1
    response = client.get(f"/api/averias/?vehiculo_id={vehiculo1['id']}")
    assert response.status_code == 200
    averias = response.json()
    assert all(a["vehiculo_id"] == vehiculo1["id"] for a in averias)


def test_actualizar_averia_cambiar_estado(client, db_session, override_auth):
    """Cambiar estado de avería: reportada → en_evaluacion"""
    almacenero, trabajador = override_auth
    vehiculo = _crear_vehiculo(client)

    # Crear avería
    create_response = client.post(
        "/api/averias/",
        json={
            "vehiculo_id": vehiculo["id"],
            "categoria": "Carrocería",
            "componente": "Puerta",
            "descripcion": "Puerta dañada",
            "criticidad": "baja",
            "origen": "operacion",
        },
    )
    averia_id = create_response.json()["id"]

    # Actualizar estado
    update_response = client.put(
        f"/api/averias/{averia_id}",
        json={
            "estado": "en_evaluacion",
        },
    )
    assert update_response.status_code == 200
    assert update_response.json()["estado"] == "en_evaluacion"


def test_averia_critica_resuelta_desbloquea_vehiculo(client, db_session, override_auth):
    """Avería crítica resuelta desbloquea vehículo si no hay otras críticas"""
    almacenero, trabajador = override_auth
    vehiculo = _crear_vehiculo(client)

    # Crear avería crítica
    create_response = client.post(
        "/api/averias/",
        json={
            "vehiculo_id": vehiculo["id"],
            "categoria": "Seguridad",
            "componente": "Frenos",
            "descripcion": "Frenos inoperantes",
            "criticidad": "critica",
            "origen": "inspeccion_salida",
        },
    )
    averia_id = create_response.json()["id"]

    # Verificar bloqueado
    vehiculo_response = client.get(f"/api/vehiculos/{vehiculo['id']}")
    assert vehiculo_response.json()["estado"] == "bloqueado"

    # Resolver avería
    client.put(
        f"/api/averias/{averia_id}",
        json={"estado": "resuelta"},
    )

    # Verificar desbloqueado
    vehiculo_response = client.get(f"/api/vehiculos/{vehiculo['id']}")
    assert vehiculo_response.json()["estado"] == "disponible"


# ============================================================
# TESTS DE INCIDENTES
# ============================================================

def test_crear_incidente_simple(client, db_session, override_auth):
    """Crear incidente simple"""
    almacenero, trabajador = override_auth
    vehiculo = _crear_vehiculo(client)

    response = client.post(
        "/api/incidentes/",
        json={
            "vehiculo_id": vehiculo["id"],
            "trabajador_id": trabajador.id,
            "tipo": "casi_accidente",
            "ubicacion": "Km 50, Panamericana Sur",
            "descripcion": "Freno de emergencia aplicado",
            "hay_danos": False,
            "hay_personas_afectadas": False,
        },
    )
    assert response.status_code == 201
    incidente = response.json()
    assert incidente["estado"] == "reportado"
    assert incidente["tipo"] == "casi_accidente"


def test_incidente_con_danos_genera_averia(client, db_session, override_auth):
    """Incidente con daños puede generar avería"""
    almacenero, trabajador = override_auth
    vehiculo = _crear_vehiculo(client)

    response = client.post(
        "/api/incidentes/",
        json={
            "vehiculo_id": vehiculo["id"],
            "trabajador_id": trabajador.id,
            "tipo": "colision",
            "ubicacion": "Km 100, Panamericana",
            "descripcion": "Colisión frontal",
            "hay_danos": True,
            "hay_personas_afectadas": False,
            "generar_averia": True,
            "averia_categoria": "Carrocería",
            "averia_componente": "Frontal",
            "averia_criticidad": "alta",
            "averia_descripcion": "Daño frontal por colisión",
        },
    )
    assert response.status_code == 201
    incidente = response.json()
    assert incidente["hay_danos"] == True

    # Verificar que se creó avería
    averias_response = client.get(f"/api/averias/?vehiculo_id={vehiculo['id']}")
    averias = averias_response.json()
    assert len(averias) > 0
    assert averias[0]["criticidad"] == "alta"


def test_incidente_con_personas_genera_averia_critica(client, db_session, override_auth):
    """Incidente con personas afectadas genera avería crítica y bloquea vehículo"""
    almacenero, trabajador = override_auth
    vehiculo = _crear_vehiculo(client)

    response = client.post(
        "/api/incidentes/",
        json={
            "vehiculo_id": vehiculo["id"],
            "trabajador_id": trabajador.id,
            "tipo": "volcadura",
            "ubicacion": "Km 200, Carretera Panamericana",
            "descripcion": "Volcadura con personas atrapadas",
            "hay_danos": True,
            "hay_personas_afectadas": True,
            "generar_averia": True,
            "averia_categoria": "Estructural",
            "averia_componente": "Chasis",
            "averia_descripcion": "Volcadura completa, daño total estructural",
        },
    )
    assert response.status_code == 201
    incidente = response.json()
    assert incidente["hay_personas_afectadas"] == True

    # Verificar que se creó avería crítica
    averias_response = client.get(f"/api/averias/?vehiculo_id={vehiculo['id']}")
    averias = averias_response.json()
    assert len(averias) > 0
    assert averias[0]["criticidad"] == "critica"

    # Verificar que vehículo está bloqueado
    vehiculo_response = client.get(f"/api/vehiculos/{vehiculo['id']}")
    assert vehiculo_response.json()["estado"] == "bloqueado"


def test_listar_incidentes(client, db_session, override_auth):
    """Listar incidentes"""
    almacenero, trabajador = override_auth
    vehiculo = _crear_vehiculo(client)

    # Crear incidente
    client.post(
        "/api/incidentes/",
        json={
            "vehiculo_id": vehiculo["id"],
            "trabajador_id": trabajador.id,
            "tipo": "impacto",
            "ubicacion": "Taller",
            "descripcion": "Impacto en estacionamiento",
            "hay_danos": True,
            "hay_personas_afectadas": False,
        },
    )

    # Listar
    response = client.get("/api/incidentes/")
    assert response.status_code == 200
    incidentes = response.json()
    assert len(incidentes) > 0


def test_actualizar_incidente_cambiar_estado(client, db_session, override_auth):
    """Cambiar estado de incidente: reportado → en_evaluacion → cerrado"""
    almacenero, trabajador = override_auth
    vehiculo = _crear_vehiculo(client)

    # Crear incidente
    create_response = client.post(
        "/api/incidentes/",
        json={
            "vehiculo_id": vehiculo["id"],
            "trabajador_id": trabajador.id,
            "tipo": "choque",
            "ubicacion": "Almacén",
            "descripcion": "Choque contra pared",
            "hay_danos": False,
            "hay_personas_afectadas": False,
        },
    )
    incidente_id = create_response.json()["id"]

    # Cambiar a en_evaluacion
    update1 = client.put(
        f"/api/incidentes/{incidente_id}",
        json={"estado": "en_evaluacion"},
    )
    assert update1.status_code == 200
    assert update1.json()["estado"] == "en_evaluacion"

    # Cambiar a cerrado
    update2 = client.put(
        f"/api/incidentes/{incidente_id}",
        json={"estado": "cerrado"},
    )
    assert update2.status_code == 200
    assert update2.json()["estado"] == "cerrado"


def test_historial_incidentes_por_vehiculo(client, db_session, override_auth):
    """Obtener historial de incidentes de un vehículo"""
    almacenero, trabajador = override_auth
    vehiculo = _crear_vehiculo(client)

    # Crear 2 incidentes
    for i in range(2):
        client.post(
            "/api/incidentes/",
            json={
                "vehiculo_id": vehiculo["id"],
                "trabajador_id": trabajador.id,
                "tipo": "casi_accidente",
                "ubicacion": f"Ubicación {i}",
                "descripcion": f"Incidente {i}",
                "hay_danos": False,
                "hay_personas_afectadas": False,
            },
        )

    # Obtener historial
    response = client.get(f"/api/incidentes/vehiculo/{vehiculo['id']}/historial")
    assert response.status_code == 200
    incidentes = response.json()
    assert len(incidentes) >= 2


def test_rbac_almacenero_puede_actualizar_averia(client, db_session, override_auth):
    """Solo almacenero puede actualizar avería"""
    almacenero, trabajador = override_auth
    vehiculo = _crear_vehiculo(client)

    # Crear avería como almacenero
    create_response = client.post(
        "/api/averias/",
        json={
            "vehiculo_id": vehiculo["id"],
            "categoria": "Motor",
            "componente": "Filtro",
            "descripcion": "Filtro obstruido",
            "criticidad": "baja",
            "origen": "mantenimiento",
        },
    )
    averia_id = create_response.json()["id"]

    # Trabajador intenta actualizar (debe fallar)
    app.dependency_overrides[get_current_user] = lambda: trabajador
    update_response = client.put(
        f"/api/averias/{averia_id}",
        json={"estado": "en_evaluacion"},
    )
    assert update_response.status_code == 403


def test_flujo_completo_averia_incidente(client, db_session, override_auth):
    """Flujo completo: Crear incidente → generar avería → resolver"""
    almacenero, trabajador = override_auth
    vehiculo = _crear_vehiculo(client)

    # 1. Crear incidente con avería
    incidente_response = client.post(
        "/api/incidentes/",
        json={
            "vehiculo_id": vehiculo["id"],
            "trabajador_id": trabajador.id,
            "tipo": "dano_estructural",
            "ubicacion": "Km 150",
            "descripcion": "Daño en lado derecho",
            "hay_danos": True,
            "hay_personas_afectadas": False,
            "generar_averia": True,
            "averia_categoria": "Carrocería",
            "averia_componente": "Lateral derecho",
            "averia_criticidad": "media",
            "averia_descripcion": "Golpe en lateral derecho",
        },
    )
    assert incidente_response.status_code == 201
    incidente_id = incidente_response.json()["id"]

    # 2. Verificar que avería fue creada
    averias_response = client.get(f"/api/averias/?vehiculo_id={vehiculo['id']}")
    averias = averias_response.json()
    assert len(averias) > 0
    averia_id = averias[0]["id"]
    assert averias[0]["criticidad"] == "media"

    # 3. Cambiar estado de avería: reportada → en_evaluacion
    client.put(
        f"/api/averias/{averia_id}",
        json={"estado": "en_evaluacion"},
    )

    # 4. Cambiar a programada
    client.put(
        f"/api/averias/{averia_id}",
        json={"estado": "programada"},
    )

    # 5. Cambiar a en_reparacion
    client.put(
        f"/api/averias/{averia_id}",
        json={"estado": "en_reparacion"},
    )

    # 6. Resolver avería
    resolve_response = client.put(
        f"/api/averias/{averia_id}",
        json={"estado": "resuelta"},
    )
    assert resolve_response.status_code == 200
    assert resolve_response.json()["estado"] == "resuelta"

    # 7. Cerrar incidente
    close_response = client.put(
        f"/api/incidentes/{incidente_id}",
        json={"estado": "cerrado"},
    )
    assert close_response.status_code == 200
    assert close_response.json()["estado"] == "cerrado"
