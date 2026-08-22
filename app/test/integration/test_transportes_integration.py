import uuid
from datetime import datetime, timedelta
from typing import Optional


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


def test_iniciar_ruta(client):
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

    # Intentar iniciar con algún check en False debe fallar (Pydantic ValidationError, retorna 400 por handler custom)
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
    vehiculo_en_ruta = client.get(f"/api/vehiculos/{vehiculo['id']}")
    assert vehiculo_en_ruta.json()["estado"] == "en_ruta"


def test_finalizar_ruta_libera_vehiculo(client):
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

    # Iniciar ruta primero
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

    # Finalizar sin fallas ("Llegada ok")
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


def test_finalizar_ruta_con_falla_envia_a_mantenimiento(client):
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

    # Iniciar ruta primero
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

    # Finalizar con falla real
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
    assert mantenimientos.json()[0]["descripcion_falla"] == "Problema grave con los frenos traseros"
    assert mantenimientos.json()[0]["estado"] == "en_taller"


def test_listar_y_crear_mantenimiento(client):
    vacio = client.get("/api/mantenimientos/")
    assert vacio.status_code == 200
    assert vacio.json() == []

    vehiculo = _crear_vehiculo(client)
    response = client.post(
        "/api/mantenimientos/",
        json={
            "vehiculo_id": vehiculo["id"],
            "fecha_ingreso": datetime.utcnow().isoformat(),
            "descripcion_falla": "Freno trasero",
            "costo": 350.0,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["estado"] == "en_taller"
    assert data["descripcion_falla"] == "Freno trasero"

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
