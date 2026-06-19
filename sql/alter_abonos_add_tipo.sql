-- Agregar columna tipo a la tabla abonos
-- 1 = Ingreso, 2 = Salida
ALTER TABLE abonos
    ADD COLUMN IF NOT EXISTS tipo INTEGER DEFAULT 1;
