-- Ejecutar una sola vez.
-- Agrega columna imagen a la tabla gastos para almacenar el nombre del archivo.
ALTER TABLE gastos
    ADD COLUMN IF NOT EXISTS imagen TEXT;
