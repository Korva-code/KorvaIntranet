-- Agregar campo price_cost a movimientos_almacen
ALTER TABLE movimientos_almacen
    ADD COLUMN IF NOT EXISTS price_cost NUMERIC(18, 4);
