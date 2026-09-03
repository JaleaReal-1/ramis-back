from __future__ import annotations

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.core.validation_handler import request_validation_exception_handler
import os

from app.database.base import Base
from app.database.connection import engine, get_db
from app.models.user import User
import app.models  # noqa: F401
from app.security.hashing import Hash
from sqlalchemy.orm import Session

# -------------------------------
# IMPORTAR ROUTERS
# -------------------------------
from app.routers.auth_router import router as auth_router
from app.routers.almacen_articulo_router import router as almacen_articulo_router
from app.routers.almacen_prestamo import router as almacen_prestamo_router
from app.routers.almacen_devolucion import router as almacen_devolucion_router
from app.routers.vehiculo_router import router as vehiculo_router
from app.routers.ruta_router import router as ruta_router
from app.routers.mantenimiento_router import router as mantenimiento_router
from app.routers.inspeccion_router import router as inspeccion_router
from app.routers.averia_router import router as averia_router
from app.routers.incidente_router import router as incidente_router
@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = next(get_db())
    try:
        seed_admin_user(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title="🚀 RamisToolX API - Corporación Ramis SAC",
    description="""
    ## Sistema Integral de Gestión de Activos y Control de Adquisiciones
    
    API desarrollada para la optimización de procesos logísticos y de almacén. 
    Implementa estándares de **OpenAPI 3.0** y principios de la norma **ISO 25010**.

    ### 🛠️ Equipo de Desarrollo (Orbit):
    * **JxL** (Backend & Lead Developer)
    * **Dan** (Analista de Sistemas)
    * **Pawel** (QA & Testing)
    * **Rusbel** (DevOps & Dockerizacion)
    
    ### 🔑 Seguridad:
    Esta API utiliza **OAuth2** con **JWT (JSON Web Tokens)** para el control de acceso basado en roles.
    """,
    version="1.2.0",
    contact={
        "name": "Equipo Orbit - UPeU Juliaca",
        "url": "https://github.com/russbell456/ramissac",
    },
    lifespan=lifespan
)


app.add_exception_handler(
    RequestValidationError,
    request_validation_exception_handler,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # En producción poner el dominio específico
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Sistema"])
def root():
    return {
        "status": "Online",
        "project": "RamisToolX",
        "version": "1.2.0",
        "message": "Backend central operativo"
    }

FOLDERS = [
    "uploads/comprobantes",
    "uploads/ordenes_compra",
    "temp_files",
    "static/firmas",
    "static/generados",
    "static/templates"
]

for folder in FOLDERS:
    os.makedirs(folder, exist_ok=True)


app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


def seed_admin_user(db: Session):
    admin_email = "admin@example.com"
    existing = db.query(User).filter(User.email == admin_email).first()
    if not existing:
        admin_user = User(
            nombre="Admin",
            dni="00000000A",
            cargo="Administrador",
            apellidos="Principal",
            codigo_unico="ADMIN-ORBIT",
            email=admin_email,
            password=Hash.get_password_hash("admin123"),
            role="admin"
        )
        db.add(admin_user)
        db.commit()

        print("Usuario admin creado correctamente.")
    else:
        print("Usuario admin ya existe.")

app.include_router(almacen_devolucion_router)
app.include_router(almacen_articulo_router)
app.include_router(almacen_prestamo_router)
app.include_router(auth_router)
app.include_router(vehiculo_router)
app.include_router(ruta_router)
app.include_router(mantenimiento_router)
app.include_router(inspeccion_router)
app.include_router(averia_router)
app.include_router(incidente_router)
