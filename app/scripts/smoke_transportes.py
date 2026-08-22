"""Smoke contra el backend en Docker (http://localhost:8000)."""
from __future__ import annotations

import sys
import uuid
from datetime import datetime, timedelta

import httpx

BASE = "http://localhost:8000"


def _fail(msg: str, response: httpx.Response | None = None) -> None:
    extra = ""
    if response is not None:
        extra = f" [{response.status_code}] {response.text}"
    print(f"FAIL: {msg}{extra}")
    sys.exit(1)


def main() -> None:
    with httpx.Client(timeout=15.0) as client:
        root = client.get(f"{BASE}/")
        if root.status_code != 200:
            _fail("Backend no responde en /", root)

        vehiculos = client.get(f"{BASE}/api/vehiculos/")
        if vehiculos.status_code != 200:
            _fail("GET /api/vehiculos", vehiculos)

        placa = f"SM{uuid.uuid4().hex[:5].upper()}"
        creado = client.post(
            f"{BASE}/api/vehiculos/",
            json={
                "placa": placa,
                "marca": "Scania",
                "modelo": "R450",
                "capacidad_carga": 18.0,
            },
        )
        if creado.status_code != 201:
            _fail("POST /api/vehiculos", creado)

        rutas = client.get(f"{BASE}/api/rutas/")
        if rutas.status_code != 200:
            _fail("GET /api/rutas", rutas)

        mant = client.get(f"{BASE}/api/mantenimientos/")
        if mant.status_code != 200:
            _fail("GET /api/mantenimientos", mant)

        dni = str(uuid.uuid4().int)[:8]
        trabajador = client.post(
            f"{BASE}/auth/register",
            json={
                "nombre": "Smoke",
                "apellidos": "Chofer",
                "dni": dni,
                "cargo": "Conductor",
                "email": f"smoke_{uuid.uuid4()}@test.com",
                "password": "12345678",
                "role": "trabajador",
            },
        )
        if trabajador.status_code != 201:
            _fail("POST /auth/register trabajador", trabajador)

        salida = datetime.utcnow()
        ruta = client.post(
            f"{BASE}/api/rutas/",
            json={
                "vehiculo_id": creado.json()["id"],
                "trabajador_id": trabajador.json()["id"],
                "origen": "Juliaca",
                "destino": "Arequipa",
                "fecha_salida": salida.isoformat(),
                "fecha_llegada_estimada": (salida + timedelta(hours=6)).isoformat(),
                "kilometraje_salida": 42000.0,
                "combustible_salida": "lleno",
                "observaciones_salida": "Smoke test",
            },
        )
        if ruta.status_code != 201:
            _fail("POST /api/rutas", ruta)

        vehiculo2 = client.post(
            f"{BASE}/api/vehiculos/",
            json={
                "placa": f"MN{uuid.uuid4().hex[:5].upper()}",
                "marca": "Mercedes",
                "modelo": "Actros",
                "capacidad_carga": 15.0,
            },
        )
        if vehiculo2.status_code != 201:
            _fail("POST segundo vehiculo", vehiculo2)

        mantenimiento = client.post(
            f"{BASE}/api/mantenimientos/",
            json={
                "vehiculo_id": vehiculo2.json()["id"],
                "fecha_ingreso": datetime.utcnow().isoformat(),
                "descripcion_falla": "Cambio de aceite",
                "costo": 120.0,
            },
        )
        if mantenimiento.status_code != 201:
            _fail("POST /api/mantenimientos", mantenimiento)

    print("OK: /api/vehiculos, /api/rutas y /api/mantenimientos responden.")


if __name__ == "__main__":
    main()
