# KorvaIntranet — Arquitectura del Proyecto

> Flask 3.0 · PostgreSQL · Bootstrap 5.3 · Blueprint `main`

---

## Estructura de carpetas

```
KorvaIntranet/
├── app.py                        # Punto de entrada (debug=True, port=5000)
├── config.py                     # Configuración (DB, secret key)
│
├── app/
│   ├── __init__.py               # create_app(): Flask + SQLAlchemy + LoginManager + Blueprints
│   │
│   ├── models/                   # Modelos ORM (uno por módulo)
│   │   ├── __init__.py           # Re-exporta todos los modelos
│   │   ├── model_almacenes.py
│   │   ├── model_usuarios.py
│   │   ├── model_articulos.py
│   │   ├── model_socios_negocio.py
│   │   └── model_facturas.py
│   │
│   ├── main/                     # Blueprint principal
│   │   ├── __init__.py           # Define blueprint e importa todos los routers
│   │   ├── router_dashboard.py
│   │   ├── router_ventas_facturas.py
│   │   ├── router_compras_facturas.py
│   │   ├── router_articulos.py
│   │   ├── router_grupos_articulos.py
│   │   ├── router_socios_negocio.py
│   │   ├── router_usuarios.py
│   │   └── router_finanzas.py
│   │
│   └── auth/                     # Blueprint de autenticación
│       ├── __init__.py
│       └── routes.py             # /auth/login · /auth/logout
│
├── templates/
│   ├── maestras/
│   │   ├── base.html             # Layout madre (navbar, sidebar, CSS/JS globales)
│   │   ├── sidebar.html
│   │   └── header.html
│   └── main/
│       ├── dashboard.html
│       ├── ventas_facturas.html
│       ├── ventas_facturas_nueva.html
│       ├── compras_facturas.html
│       ├── compras_facturas_nueva.html
│       ├── articulos.html
│       ├── grupos_articulos.html
│       ├── socios_negocio.html
│       ├── admin_usuarios.html
│       ├── mi_perfil.html
│       └── placeholder.html
│
└── static/                       # CSS, JS, imágenes propios
```

---

## Modelos (`app/models/`)

### `model_almacenes.py`

| Clase | Tabla BD |
|---|---|
| `Warehouse` | `warehouses` |

**Campos**

| Campo | Tipo | Descripción |
|---|---|---|
| `whs_code` | String(2) PK | Código del almacén |
| `whs_name` | Text | Nombre |
| `street` | String(100) | Dirección |
| `is_nettable` | String(1) | Y/N |
| `is_drop_ship` | String(1) | Y/N |
| `allow_bin_locations` | String(1) | Y/N |

**Propiedades**

| Propiedad | Retorna |
|---|---|
| `code` | `whs_code` sin espacios |
| `name` | `whs_name` sin espacios |

---

### `model_usuarios.py`

| Clase | Tabla BD |
|---|---|
| `Perfil` | `w_perfil` |
| `Usuario` | `w_usuarios` |

#### `Perfil`

| Campo | Tipo | Descripción |
|---|---|---|
| `id_perfil` | Integer PK | |
| `descripcion` | String(256) | Nombre del perfil |
| `id_estado` | Integer | |
| `tipo_menu` | Integer | |

**Propiedades:** `nombre` → `descripcion` sin espacios

#### `Usuario` (hereda `UserMixin`)

| Campo | Tipo | Descripción |
|---|---|---|
| `id_usuario` | String(20) PK | |
| `nombres` | Text | |
| `contrasena` | Text | Contraseña plana |
| `id_perfil` | Integer | FK → `w_perfil` |
| `id_estado` | Integer | 1 = activo |
| `id_rol` | Integer | NOT NULL |
| `whs_code` | String(2) | FK → `warehouses` |
| `correo` | String(60) | |
| `ubicacion` | Text | Departamento |

**Relaciones**

| Relación | Apunta a | Descripción |
|---|---|---|
| `perfil_rel` | `Perfil` | Por `id_perfil` |
| `warehouse` | `Warehouse` | Por `whs_code` (TRIM) |

**Propiedades clave**

| Propiedad | Descripción |
|---|---|
| `is_active` | `id_estado == 1` |
| `is_admin` | `id_perfil == 1` o `id_rol == 1` |
| `full_name` | `nombres` en Title Case |
| `initials` | Iniciales (máx. 2) |
| `whs_name` | Nombre del almacén vía relación o fallback query |
| `perfil_nombre` | Nombre del perfil vía relación |

**Función:** `load_user(user_id)` — registrada en `login_manager.user_loader`

---

### `model_articulos.py`

| Clase | Tabla BD |
|---|---|
| `ItemGroup` | `items_group` |
| `ItemBarcode` | `items_barcode` |
| `Item` | `items` |

#### `ItemGroup`

| Campo | Tipo | Descripción |
|---|---|---|
| `item_group_code` | Integer PK | |
| `item_group_name` | String(50) | |
| `CostingCode` | String(10) | |

**Métodos:** `nombre` (property), `as_dict()`

#### `ItemBarcode`

| Campo | Tipo |
|---|---|
| `item_code` | Text PK |
| `item_barcode` | Text |

#### `Item`

| Campo | Tipo | Descripción |
|---|---|---|
| `item_code` | Text PK | |
| `item_name` | Text | |
| `frgn_name` | Text | Nombre extranjero |
| `itms_grp_cod` | Integer | FK → `items_group` |
| `itms_grp_nam` | String(100) | Cache del nombre del grupo |
| `invnt_item` | String(1) | Y/N inventariable |
| `sell_item` | String(1) | Y/N venta |
| `prchse_item` | String(1) | Y/N compra |
| `on_hand` | Numeric(18,6) | Stock disponible |
| `is_commited` | Numeric(18,6) | Comprometido |
| `on_order` | Numeric(18,6) | En pedido |
| `avg_price` | Numeric(18,6) | Precio promedio |
| `PriceAfterVAT` | Numeric(18,4) | Precio con IGV |
| `sal_unit_msr` | String(50) | Unidad de venta |
| `buy_unit_msr` | String(50) | Unidad de compra |
| `tax_code_ar` | String(20) | Código impuesto venta |
| `tax_code_ap` | String(20) | Código impuesto compra |
| `valid_for` | String(1) | Y/N activo |
| `frozen_for` | String(1) | Y/N bloqueado |
| `TipoBien` | Integer | |
| `create_date` | Date | |
| `update_date` | Date | |

**Relaciones**

| Relación | Apunta a |
|---|---|
| `grupo` | `ItemGroup` por `itms_grp_cod` |
| `barcode_obj` | `ItemBarcode` por `item_code` |

**Métodos:** `as_dict()`, `grupo_nombre`, `barcode`, `sal_unit`, `buy_unit`, `tax_ar`, `tax_ap`

---

### `model_socios_negocio.py`

| Clase | Tabla BD |
|---|---|
| `BusinessPartner` | `business_partners` |

| Campo | Tipo | Descripción |
|---|---|---|
| `card_code` | String(50) PK | Código del socio |
| `card_name` | String(255) | Nombre o razón social |
| `card_type` | String(20) | `2`=Cliente · `3`=Proveedor |
| `group_code` | String(10) | Grupo del socio |
| `federal_tax_id` | String(20) | RUC / DNI |
| `currency` | String(3) | Moneda preferida |
| `email` | Text | |
| `IsCredit` | Integer | Días crédito habilitados |
| `Creditday` | Integer | Días de crédito |
| `u_validc` | String(1) | Y/N válido |
| `u_vs_afprcp` | String(1) | Afecto a percepción |
| `u_bpp_bptd` | String(10) | Tipo documento |
| `u_bpp_bpno` | String(255) | Número documento |
| `u_bpp_bpap` | String(50) | Apellido paterno |
| `u_bpp_bptp` | String(10) | Tipo persona |
| `u_cl_estmig` | String(1) | Estado migración |
| `u_cl_resmig` | Text | Resultado migración |
| `u_cl_fecmig` | Date | Fecha migración |

**Métodos:** `tipo_label` (property), `as_dict()`

---

### `model_facturas.py`

| Clase | Tabla BD |
|---|---|
| `Invoice` | `invoice` |

| Campo | Tipo | Descripción |
|---|---|---|
| `invoice_id` | Integer PK | |
| `card_code` | Text | FK → `business_partners` |
| `doc_date` | Date | Fecha documento |
| `tax_date` | Date | Fecha impuesto |
| `doc_due_date` | Date | Fecha vencimiento |
| `doc_total` | Numeric(18,4) | Total del documento |
| `doc_currency` | Text | `SOL` / `USD` |
| `comments` | Text | Comentarios |
| `num_at_card` | Text | N° documento externo |
| `journal_memo` | Text | Referencia/diario |
| `invoice_type` | Text | Tipo comprobante |
| `invoice_serie` | Text | Serie |
| `invoice_wh` | Text | Almacén |
| `invoice_pos` | Integer | Posición correlativo |
| `user_code` | Text | Usuario que registró |
| `sunat_estado` | Text | Estado SUNAT |

**Relaciones:** `bp` → `BusinessPartner` por `card_code`

**Métodos:** `bp_name` (property), `as_dict()`

---

## Routers (`app/main/`)

### `router_dashboard.py`

| Método | URL | Función | Template |
|---|---|---|---|
| GET | `/` | `dashboard` | `main/dashboard.html` |
| GET | `/dashboard` | `dashboard` | `main/dashboard.html` |

---

### `router_ventas_facturas.py`

**Modelos usados:** `Warehouse` · `Item` · `BusinessPartner` · `Invoice` · `Usuario`

| Método | URL | Función | Descripción |
|---|---|---|---|
| GET | `/ventas/facturas` | `ventas_facturas` | Listado de facturas de venta (últimas 200) con drawer de detalle |
| GET | `/ventas/facturas/nueva` | `ventas_facturas_nueva` | Formulario nueva factura |
| POST | `/ventas/facturas/nueva` | `ventas_facturas_nueva` | Llama a `fn_invoice_inserta()` en PostgreSQL |
| GET | `/api/socios-ventas` | `api_socios_ventas` | JSON: socios tipo `2` con `federal_tax_id` |
| GET | `/api/invoice-series` | `api_invoice_series` | JSON: series disponibles por tipo+almacén |

**Parámetros POST nueva factura:**
`card_code`, `doc_date`, `tax_date`, `doc_due_date`, `doc_currency`, `comments`, `num_at_card`, `journal_memo`, `invoice_type`, `invoice_serie`, `invoice_wh`, `invoice_pos`, `invoice_user`, `items_json` (JSON serializado con las líneas de detalle)

---

### `router_compras_facturas.py`

**Modelos usados:** `Warehouse` · `Item` · `BusinessPartner` · `Usuario`

| Método | URL | Función | Descripción |
|---|---|---|---|
| GET | `/compras/facturas` | `compras_facturas` | Listado de facturas de compra (últimas 200) |
| GET | `/compras/facturas/nueva` | `compras_facturas_nueva` | Formulario nueva factura de compra |
| POST | `/compras/facturas/nueva` | `compras_facturas_nueva` | Llama a `fn_invoice_p_inserta()` en PostgreSQL |

---

### `router_articulos.py`

**Modelos usados:** `Item` · `ItemGroup`

| Método | URL | Función | Descripción |
|---|---|---|---|
| GET | `/maestras/articulos` | `articulos` | Listado de artículos con drawer edición |
| POST | `/maestras/articulos/nuevo` | `articulo_nuevo` | Crea nuevo artículo + barcodes |
| POST | `/maestras/articulos/<item_code>/editar` | `articulo_editar` | Actualiza artículo + barcodes |
| GET | `/api/articulos/<item_code>/barcodes` | `api_articulo_barcodes` | JSON: códigos de barra del artículo |
| GET | `/api/items-lista` | `api_items_lista` | JSON: lista simple `{item_code, item_name}` |
| GET | `/api/items-con-precio` | `api_items_con_precio` | JSON: artículos con precio ajustado por RUC del socio |

**Parámetro `api_items_con_precio`:** `?ruc=` RUC del socio. Aplica descuento si existe en `business_partners_discount_item`, sino usa `PriceAfterVAT`.

**Helpers internos:**

| Función | Descripción |
|---|---|
| `_parse_date(val)` | Convierte string `YYYY-MM-DD` a `date` |
| `_parse_num(val)` | Convierte string a `float`, `None` si vacío |
| `_apply_item_fields(item, form)` | Aplica todos los campos del form al objeto `Item` |
| `_save_barcodes(item_code, json)` | Borra y re-inserta barcodes en `items_barcode` |

---

### `router_grupos_articulos.py`

**Modelos usados:** `ItemGroup`

| Método | URL | Función | Descripción |
|---|---|---|---|
| GET | `/maestras/grupos` | `grupos_articulos` | Listado de grupos con JOIN a `costingcodes` |
| POST | `/maestras/grupos/nuevo` | `grupo_nuevo` | Crea nuevo grupo |
| POST | `/maestras/grupos/<grupo_code>/editar` | `grupo_editar` | Actualiza nombre y costing del grupo |

---

### `router_socios_negocio.py`

**Modelos usados:** `BusinessPartner`

| Método | URL | Función | Descripción |
|---|---|---|---|
| GET | `/maestras/socios` | `socios_negocio` | Listado de socios con JOINs a `anexo_tipo` y `business_partners_group` |
| POST | `/maestras/socios/nuevo` | `socio_nuevo` | Crea socio + direcciones + descuentos por ítem |
| POST | `/maestras/socios/<card_code>/editar` | `socio_editar` | Actualiza socio + direcciones + descuentos |
| GET | `/api/socios/<card_code>/direcciones` | `api_socio_direcciones` | JSON: direcciones del socio |
| GET | `/api/descuentos` | `api_descuentos` | JSON: descuentos por ítem para un RUC (`?ruc=`) |

**Helpers internos:**

| Función | Descripción |
|---|---|
| `_parse_date(val)` | Convierte string `YYYY-MM-DD` a `date` |
| `_apply_bp_fields(bp, form)` | Aplica todos los campos del form al objeto `BusinessPartner` |
| `_save_addresses(card_code, json)` | Borra y re-inserta en `business_partners_addresses` |
| `_save_descuentos(ruc, json)` | Borra y re-inserta en `business_partners_discount_item` |

---

### `router_usuarios.py`

**Modelos usados:** `Usuario` · `Warehouse` · `Perfil`

| Método | URL | Función | Descripción |
|---|---|---|---|
| GET | `/mi-perfil` | `mi_perfil` | Perfil del usuario actual |
| POST | `/mi-perfil/cambiar-contrasena` | `cambiar_contrasena` | Cambia contraseña del usuario actual |
| GET | `/admin/usuarios` | `admin_usuarios` | Listado de todos los usuarios del sistema |
| POST | `/admin/usuarios/<id_usuario>/editar` | `admin_editar_usuario` | Actualiza datos del usuario |

---

### `router_finanzas.py`

Rutas placeholder (sin lógica de negocio aún).

| Método | URL | Función |
|---|---|---|
| GET | `/ventas/boletas` | `ventas_boletas` |
| GET | `/finanzas/presupuesto` | `presupuesto` |
| GET | `/finanzas/gastos` | `gastos` |
| GET | `/finanzas/reportes` | `reportes_finanzas` |
| GET | `/configuracion/usuarios` | `usuarios` |
| GET | `/configuracion/sistema` | `sistema` |

---

## Flujo de una petición

```
Browser → GET /ventas/facturas/nueva
              │
              ▼
        app/main/__init__.py  (Blueprint 'main')
              │
              ▼
        router_ventas_facturas.py → ventas_facturas_nueva()
              │  consulta BD (Warehouse)
              ▼
        render_template('main/ventas_facturas_nueva.html')
              │  variables: warehouses, today
              ▼
        templates/maestras/base.html  (layout)
        templates/main/ventas_facturas_nueva.html  (content + JS)
              │
              ▼
        Browser renderiza la página
              │
              │  fetch('/api/socios-ventas')   ← AJAX al seleccionar socio
              ▼
        router_ventas_facturas.py → api_socios_ventas()
              │  SELECT FROM business_partners
              ▼
        jsonify([...])  → JS actualiza dropdown
              │
              │  fetch('/api/items-con-precio?ruc=...')
              ▼
        router_articulos.py → api_items_con_precio()
              │  SELECT con CASE precio/descuento
              ▼
        jsonify([...])  → JS carga lista de ítems con precios
              │
              │  POST /ventas/facturas/nueva  (submit form)
              ▼
        router_ventas_facturas.py → ventas_facturas_nueva() POST
              │  fn_invoice_inserta() en PostgreSQL
              ▼
        redirect → /ventas/facturas
```

---

## Convenciones del proyecto

| Concepto | Convención |
|---|---|
| Archivos de modelo | `model_<modulo>.py` en `app/models/` |
| Archivos de rutas | `router_<modulo>.py` en `app/main/` |
| APIs JSON | Prefijo `/api/` en la URL |
| Datos al cargar página | Solo los mínimos (ej. `warehouses`, `today`) vía `render_template` |
| Datos dinámicos | Siempre vía `fetch()` desde el browser → endpoints `/api/` |
| Guardado en BD | A través de stored functions PostgreSQL (`fn_*`) o SQLAlchemy ORM directo |
