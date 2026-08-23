from __future__ import annotations
from app.services.auditoria_service import (
    AuditoriaService
)
from sqlalchemy.orm import Session
from app.repositories.user_repository import UserRepository
from app.models.user import User
from app.core.security import hash_password, verify_password

class AuthService:
    def __init__(self, db: Session):
        self.db = db  #
        self.user_repo = UserRepository(db)

    def register_user(self, nombre: str, apellidos: str, dni: str, cargo: str | None, email: str, password: str, role: str = "user"):
        if self.user_repo.get_by_email(email):
            raise ValueError("El email ya está registrado")
        
        hashed_password = hash_password(password)
        user = User(
            nombre=nombre,
            apellidos=apellidos,
            dni=dni,
            cargo=cargo,
            email=email,
            password=hashed_password,
            role=role
        )
        return self.user_repo.create_user(user)

    def authenticate_user(self, email: str, password: str):
        user = self.user_repo.get_by_email(email)
        if not user or not verify_password(password, user.password):
            return None
        return user


    def obtener_trabajadores(self):
        return self.db.query(User).filter(
            User.role.in_(["trabajador", "almacenero"])
        ).all()
    def actualizar_usuario(
        self,
        user_id: int,
        nombre: str,
        apellidos: str,
        dni: str,
        cargo: str | None,
        email: str,
        usuario_auditoria: int
    ):

        user = (
            self.user_repo.get_by_id(
                user_id
            )
        )

        if not user:
            raise ValueError(
                "Usuario no encontrado"
            )

        user.nombre = nombre
        user.apellidos = apellidos
        user.dni = dni
        user.cargo = cargo
        user.email = email

        user = (
            self.user_repo.update_user(
                user
            )
        )

        AuditoriaService(
            self.db
        ).registrar(
            usuario_id=usuario_auditoria,
            accion="EDITAR_USUARIO",
            entidad="users",
            entidad_id=user.id,
            descripcion=(
                f"Se actualizó el usuario "
                f"{user.email}"
            )
        )

        return user
        

