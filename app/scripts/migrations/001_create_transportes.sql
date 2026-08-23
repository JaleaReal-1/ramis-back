-- Módulo de transportes: vehiculos, rutas_asignaciones, mantenimientos
-- Idempotente para PostgreSQL (contenedor ramissac_db).
-- El backend también las crea con Base.metadata.create_all al arrancar.

CREATE TABLE IF NOT EXISTS vehiculos (
    id SERIAL PRIMARY KEY,
    placa VARCHAR NOT NULL,
    marca VARCHAR NOT NULL,
    modelo VARCHAR NOT NULL,
    capacidad_carga FLOAT NOT NULL,
    estado VARCHAR NOT NULL DEFAULT 'disponible'
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_vehiculos_placa ON vehiculos (placa);
CREATE INDEX IF NOT EXISTS ix_vehiculos_id ON vehiculos (id);

CREATE TABLE IF NOT EXISTS rutas_asignaciones (
    id SERIAL PRIMARY KEY,
    vehiculo_id INTEGER NOT NULL REFERENCES vehiculos (id),
    trabajador_id INTEGER NOT NULL REFERENCES users (id),
    origen VARCHAR NOT NULL,
    destino VARCHAR NOT NULL,
    fecha_salida TIMESTAMP NOT NULL,
    fecha_llegada_estimada TIMESTAMP NOT NULL,
    estado_ruta VARCHAR NOT NULL DEFAULT 'pendiente',
    kilometraje_salida FLOAT,
    kilometraje_llegada FLOAT,
    combustible_salida VARCHAR,
    combustible_llegada VARCHAR,
    observaciones_salida VARCHAR,
    observaciones_llegada VARCHAR
);

CREATE INDEX IF NOT EXISTS ix_rutas_asignaciones_id ON rutas_asignaciones (id);

-- Compatibilidad con tablas creadas antes de agregar la inspección de seguridad.
ALTER TABLE rutas_asignaciones
    ADD COLUMN IF NOT EXISTS firma_trabajador VARCHAR,
    ADD COLUMN IF NOT EXISTS check_llantas BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS check_frenos BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS check_luces BOOLEAN DEFAULT FALSE;

CREATE TABLE IF NOT EXISTS mantenimientos (
    id SERIAL PRIMARY KEY,
    vehiculo_id INTEGER NOT NULL REFERENCES vehiculos (id),
    fecha_ingreso TIMESTAMP NOT NULL,
    descripcion_falla VARCHAR NOT NULL,
    costo FLOAT NOT NULL,
    estado VARCHAR NOT NULL DEFAULT 'en_taller'
);

CREATE INDEX IF NOT EXISTS ix_mantenimientos_id ON mantenimientos (id);
