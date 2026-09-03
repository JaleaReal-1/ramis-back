-- Evolución integral del Módulo de Transportes
ALTER TABLE vehiculos ADD COLUMN IF NOT EXISTS kilometraje_actual FLOAT NOT NULL DEFAULT 0.0;

CREATE TABLE IF NOT EXISTS checklist_items (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR NOT NULL,
    categoria VARCHAR NOT NULL,
    criticidad VARCHAR NOT NULL, -- baja, media, alta, critica
    orden INTEGER NOT NULL DEFAULT 0,
    activo BOOLEAN NOT NULL DEFAULT TRUE
);
CREATE INDEX IF NOT EXISTS ix_checklist_items_id ON checklist_items (id);

CREATE TABLE IF NOT EXISTS inspecciones (
    id SERIAL PRIMARY KEY,
    vehiculo_id INTEGER NOT NULL REFERENCES vehiculos (id),
    ruta_id INTEGER REFERENCES rutas_asignaciones (id),
    trabajador_id INTEGER NOT NULL REFERENCES users (id),
    tipo VARCHAR NOT NULL, -- salida, llegada, extraordinaria, post_accidente, post_mantenimiento
    fecha TIMESTAMP NOT NULL,
    kilometraje FLOAT NOT NULL,
    combustible VARCHAR NOT NULL,
    firma VARCHAR,
    resultado VARCHAR NOT NULL, -- aprobada, aprobada_con_observaciones, rechazada
    observaciones VARCHAR
);
CREATE INDEX IF NOT EXISTS ix_inspecciones_id ON inspecciones (id);

CREATE TABLE IF NOT EXISTS inspeccion_detalles (
    id SERIAL PRIMARY KEY,
    inspeccion_id INTEGER NOT NULL REFERENCES inspecciones (id) ON DELETE CASCADE,
    checklist_item_id INTEGER NOT NULL REFERENCES checklist_items (id),
    resultado_item VARCHAR NOT NULL -- conforme, observado, no_conforme, no_aplica
);
CREATE INDEX IF NOT EXISTS ix_inspeccion_detalles_id ON inspeccion_detalles (id);

CREATE TABLE IF NOT EXISTS averias (
    id SERIAL PRIMARY KEY,
    vehiculo_id INTEGER NOT NULL REFERENCES vehiculos (id),
    ruta_id INTEGER REFERENCES rutas_asignaciones (id),
    trabajador_id INTEGER REFERENCES users (id),
    inspeccion_id INTEGER REFERENCES inspecciones (id),
    categoria VARCHAR NOT NULL,
    componente VARCHAR NOT NULL,
    descripcion VARCHAR NOT NULL,
    criticidad VARCHAR NOT NULL, -- baja, media, alta, critica
    fecha_reporte TIMESTAMP NOT NULL,
    kilometraje FLOAT,
    estado VARCHAR NOT NULL DEFAULT 'reportada', -- reportada, en_evaluacion, programada, en_reparacion, resuelta, cerrada
    origen VARCHAR NOT NULL, -- inspeccion_salida, operacion, inspeccion_llegada, mantenimiento
    fecha_baja TIMESTAMP,
    usuario_baja INTEGER REFERENCES users (id)
);
CREATE INDEX IF NOT EXISTS ix_averias_id ON averias (id);

CREATE TABLE IF NOT EXISTS incidentes (
    id SERIAL PRIMARY KEY,
    vehiculo_id INTEGER NOT NULL REFERENCES vehiculos (id),
    ruta_id INTEGER REFERENCES rutas_asignaciones (id),
    trabajador_id INTEGER NOT NULL REFERENCES users (id),
    tipo VARCHAR NOT NULL, -- colision, choque, volcadura, impacto, dano_estructural, casi_accidente, otro
    fecha TIMESTAMP NOT NULL,
    ubicacion VARCHAR NOT NULL,
    descripcion VARCHAR NOT NULL,
    hay_danos BOOLEAN NOT NULL DEFAULT FALSE,
    hay_personas_afectadas BOOLEAN NOT NULL DEFAULT FALSE,
    estado VARCHAR NOT NULL DEFAULT 'reportado', -- reportado, en_evaluacion, cerrado
    fecha_baja TIMESTAMP,
    usuario_baja INTEGER REFERENCES users (id)
);
CREATE INDEX IF NOT EXISTS ix_incidentes_id ON incidentes (id);

CREATE TABLE IF NOT EXISTS planes_mantenimiento (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR NOT NULL,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    fecha_baja TIMESTAMP,
    usuario_baja INTEGER REFERENCES users (id)
);
CREATE INDEX IF NOT EXISTS ix_planes_mantenimiento_id ON planes_mantenimiento (id);

CREATE TABLE IF NOT EXISTS plan_mantenimiento_detalles (
    id SERIAL PRIMARY KEY,
    plan_id INTEGER NOT NULL REFERENCES planes_mantenimiento (id) ON DELETE CASCADE,
    actividad VARCHAR NOT NULL,
    descripcion VARCHAR,
    tipo_control VARCHAR NOT NULL, -- por_km, por_fecha, por_horas, mixto
    intervalo_km FLOAT,
    intervalo_dias INTEGER,
    intervalo_horas FLOAT,
    alerta_previa_km FLOAT,
    alerta_previa_dias INTEGER,
    criticidad VARCHAR NOT NULL, -- baja, media, alta, critica
    activo BOOLEAN NOT NULL DEFAULT TRUE
);
CREATE INDEX IF NOT EXISTS ix_plan_mantenimiento_detalles_id ON plan_mantenimiento_detalles (id);

ALTER TABLE mantenimientos ADD COLUMN IF NOT EXISTS averia_id INTEGER REFERENCES averias (id);
ALTER TABLE mantenimientos ADD COLUMN IF NOT EXISTS plan_mantenimiento_id INTEGER REFERENCES planes_mantenimiento (id);

CREATE TABLE IF NOT EXISTS registros_combustible (
    id SERIAL PRIMARY KEY,
    vehiculo_id INTEGER NOT NULL REFERENCES vehiculos (id),
    trabajador_id INTEGER NOT NULL REFERENCES users (id),
    fecha TIMESTAMP NOT NULL,
    kilometraje FLOAT NOT NULL,
    nivel_anterior VARCHAR NOT NULL,
    litros FLOAT NOT NULL,
    nivel_posterior VARCHAR NOT NULL,
    tipo_combustible VARCHAR NOT NULL,
    costo FLOAT NOT NULL DEFAULT 0.0,
    observaciones VARCHAR,
    fecha_baja TIMESTAMP,
    usuario_baja INTEGER REFERENCES users (id)
);
CREATE INDEX IF NOT EXISTS ix_registros_combustible_id ON registros_combustible (id);

INSERT INTO checklist_items (nombre, categoria, criticidad, orden, activo) VALUES
('Frenos', 'Seguridad', 'critica', 1, TRUE),
('Llantas', 'Seguridad', 'critica', 2, TRUE),
('Luces principales', 'Iluminación', 'critica', 3, TRUE),
('Nivel de Aceite', 'Motor', 'media', 4, TRUE),
('Nivel de Refrigerante', 'Motor', 'media', 5, TRUE),
('Espejos Retrovisores', 'Carrocería', 'baja', 6, TRUE),
('Extintor de Emergencia', 'Seguridad', 'alta', 7, TRUE),
('Botiquín de Primeros Auxilios', 'Seguridad', 'alta', 8, TRUE),
('Cinturones de Seguridad', 'Seguridad', 'critica', 9, TRUE)
ON CONFLICT DO NOTHING;
