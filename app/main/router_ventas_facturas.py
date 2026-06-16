import json
from datetime import date, datetime
from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import text
from app.main import main
from app import db


@main.route('/ventas/facturas')
@login_required
def ventas_facturas():
    socios_rows = db.session.execute(text(
        "SELECT * FROM business_partners_lista_tipo('2')"
    )).fetchall()
    from app.models import Usuario
    usuarios   = Usuario.query.order_by(Usuario.nombres).all()
    today      = date.today().isoformat()

    fact_rows = db.session.execute(text("""
        SELECT
            i.invoice_id,
            i.card_code,
            COALESCE(bp.card_name, i.card_code)           AS bp_name,
            i.invoice_type,
            i.invoice_serie,
            i.invoice_number,
            i.doc_date,
            i.tax_date,
            i.doc_due_date,
            i.doc_currency,
            i.doc_total,
            i.invoice_wh,
            TRIM(COALESCE(w.whs_name, i.invoice_wh, ''))  AS whs_name,
            i.user_code,
            COALESCE(u.nombres, i.user_code, '')           AS user_nombres,
            i.comments,
            i.num_at_card,
            i.journal_memo,
            i.sunat_estado,
            i.sunat_a4,
            i.sunat_ticket,
            COALESCE(i.sunat_hash, '') AS sunat_hash,
            COALESCE(i.sunat_xml,  '') AS sunat_xml,
            COALESCE(i.sunat_cdr,  '') AS sunat_cdr
        FROM invoice i
        LEFT JOIN business_partners bp ON bp.card_code = i.card_code
        LEFT JOIN warehouses w ON TRIM(w.whs_code) = TRIM(i.invoice_wh)
        LEFT JOIN w_usuarios u ON u.id_usuario = i.user_code
        ORDER BY i.invoice_id DESC
        LIMIT 200
    """)).fetchall()

    inv_ids = [r[0] for r in fact_rows]
    det_by_inv = {}
    if inv_ids:
        for r in db.session.execute(text("""
            SELECT invoice_id, item_code, quantity, price_after_vat,
                   tax_code, warehouse_code, costing_code, costing_code2, costing_code3
            FROM invoice_item
            WHERE invoice_id = ANY(:ids)
            ORDER BY invoice_id
        """), {'ids': inv_ids}).fetchall():
            det_by_inv.setdefault(r[0], []).append({
                'item_code':       r[1] or '',
                'quantity':        float(r[2]) if r[2] is not None else 0,
                'price_after_vat': float(r[3]) if r[3] is not None else 0,
                'tax_code':        r[4] or '',
                'warehouse_code':  r[5] or '',
                'costing_code':    r[6] or '',
                'costing_code2':   r[7] or '',
                'costing_code3':   r[8] or '',
            })

    def _dt(v): return v.isoformat() if v else ''
    facturas_list = [{
        'invoice_id':     r[0],
        'card_code':      r[1] or '',
        'bp_name':        r[2] or '',
        'invoice_type':   r[3] or '',
        'invoice_serie':  r[4] or '',
        'invoice_number': r[5],
        'doc_date':       _dt(r[6]),
        'tax_date':       _dt(r[7]),
        'doc_due_date':   _dt(r[8]),
        'doc_currency':   r[9] or '',
        'doc_total':      float(r[10]) if r[10] is not None else None,
        'invoice_wh':     r[11] or '',
        'whs_name':       r[12] or '',
        'user_code':      r[13] or '',
        'user_nombres':   r[14] or '',
        'comments':       r[15] or '',
        'num_at_card':    r[16] or '',
        'journal_memo':   r[17] or '',
        'sunat_estado':   r[18] or '',
        'sunat_a4':       r[19] or '',
        'sunat_ticket':   r[20] or '',
        'sunat_hash':     r[21] or '',
        'sunat_xml':      r[22] or '',
        'sunat_cdr':      r[23] or '',
        'items':          det_by_inv.get(r[0], []),
    } for r in fact_rows]

    facturas_json    = json.dumps(facturas_list, ensure_ascii=False)
    socios_json_data = json.dumps([{
        'card_code':      r[0] or '',
        'card_name':      r[1] or '',
        'card_type':      r[2] or '',
        'group_code':     r[3] or '',
        'federal_tax_id': r[4] or '',
        'currency':       r[5] or '',
        'email':          r[6] or '',
        'IsCredit':       r[7],
        'Creditday':      r[8],
    } for r in socios_rows], ensure_ascii=False)
    return render_template('main/ventas_facturas.html', title='Facturas de Venta',
                           section='Ventas', page='Facturas',
                           fact_rows=fact_rows, usuarios=usuarios, today=today,
                           facturas_json=facturas_json,
                           socios_json_data=socios_json_data)


def _num_a_letras(monto: float) -> str:
    """Convierte un número a letras en español (para el importe total del comprobante)."""
    UNIDADES = ['', 'UN', 'DOS', 'TRES', 'CUATRO', 'CINCO', 'SEIS', 'SIETE',
                'OCHO', 'NUEVE', 'DIEZ', 'ONCE', 'DOCE', 'TRECE', 'CATORCE',
                'QUINCE', 'DIECISÉIS', 'DIECISIETE', 'DIECIOCHO', 'DIECINUEVE']
    DECENAS  = ['', 'DIEZ', 'VEINTE', 'TREINTA', 'CUARENTA', 'CINCUENTA',
                'SESENTA', 'SETENTA', 'OCHENTA', 'NOVENTA']
    CENTENAS = ['', 'CIENTO', 'DOSCIENTOS', 'TRESCIENTOS', 'CUATROCIENTOS',
                'QUINIENTOS', 'SEISCIENTOS', 'SETECIENTOS', 'OCHOCIENTOS', 'NOVECIENTOS']

    def _cientos(n):
        if n == 0:   return ''
        if n == 100: return 'CIEN'
        c = CENTENAS[n // 100]
        r = n % 100
        if r == 0:   return c
        if n < 100:  c = ''
        if r < 20:   return (c + ' ' if c else '') + UNIDADES[r]
        d = DECENAS[r // 10]
        u = UNIDADES[r % 10]
        txt = (c + ' ' if c else '') + d
        if u: txt += ' Y ' + u
        return txt

    entero    = int(monto)
    centavos  = round((monto - entero) * 100)
    if entero == 0:
        return f'CERO Y {centavos:02d}/100'
    if entero < 1000:
        letras = _cientos(entero)
    elif entero < 1_000_000:
        miles = entero // 1000
        resto = entero % 1000
        letras = ('UN MIL' if miles == 1 else _cientos(miles) + ' MIL')
        if resto: letras += ' ' + _cientos(resto)
    else:
        mils = entero // 1_000_000
        resto = entero % 1_000_000
        letras = ('UN MILLÓN' if mils == 1 else _cientos(mils) + ' MILLONES')
        if resto >= 1000:
            miles = resto // 1000
            letras += ' ' + ('MIL' if miles == 1 else _cientos(miles) + ' MIL')
            resto = resto % 1000
        if resto: letras += ' ' + _cientos(resto)
    return f'{letras} Y {centavos:02d}/100'


@main.route('/ventas/facturas/<int:invoice_id>/imprimir')
@login_required
def ventas_facturas_imprimir(invoice_id):
    row = db.session.execute(text("""
        SELECT
            i.invoice_id,
            COALESCE(i.invoice_serie::TEXT, '')        AS serie,
            COALESCE(i.invoice_number::TEXT, '')       AS numero,
            i.invoice_type,
            i.doc_date,
            i.doc_due_date,
            i.doc_currency,
            COALESCE(i.doc_total, 0)                   AS doc_total,
            COALESCE(i.comments, '')                   AS comments,
            COALESCE(i.num_at_card, '')                AS num_at_card,
            -- cliente
            COALESCE(bp.card_name, i.card_code, '')   AS bp_name,
            COALESCE(bp.federal_tax_id, '')            AS federal_tax_id,
            COALESCE(
                (SELECT TRIM(COALESCE(street,'')) ||
                        CASE WHEN COALESCE(street_no,'') <> ''
                             THEN ' ' || street_no ELSE '' END
                 FROM business_partners_addresses
                 WHERE bp_code = i.card_code LIMIT 1),
                ''
            )                                          AS direccion,
            -- tipo documento (descripción real de invoice_type)
            COALESCE(tp.invoice_type, '')              AS tipo_desc
        FROM invoice i
        LEFT JOIN business_partners bp ON bp.card_code = i.card_code
        LEFT JOIN invoice_type tp ON (
            tp.idtype::TEXT = i.invoice_type
            OR tp.invoice_type = i.invoice_type
        )
        WHERE i.invoice_id = :id
        LIMIT 1
    """), {'id': invoice_id}).fetchone()

    if not row:
        return 'Factura no encontrada', 404

    items_rows = db.session.execute(text("""
        SELECT
            ii.item_code,
            COALESCE(NULLIF(TRIM(it.item_name),''), ii.item_code, '') AS descripcion,
            COALESCE(ii.quantity, 0)                                   AS quantity,
            COALESCE(ii.price_after_vat, 0)                           AS price_after_vat,
            COALESCE(ii.tax_code, '')                                  AS tax_code,
            COALESCE(it.sal_unit_msr, 'ZZ')                           AS unidad
        FROM invoice_item ii
        LEFT JOIN items it ON it.item_code = ii.item_code
        WHERE ii.invoice_id = :id
        ORDER BY ii.item_code
    """), {'id': invoice_id}).fetchall()

    IGV_RATE = 0.18
    items    = []
    op_grav  = 0.0
    op_exo   = 0.0
    op_ina   = 0.0

    for r in items_rows:
        qty   = float(r[2] or 0)
        pav   = float(r[3] or 0)            # price including VAT
        tc    = (r[4] or '').strip().upper()
        if tc in ('IGV', 'IVA', '10', 'GRAVADO', ''):
            val_unit = pav / (1 + IGV_RATE)
            op_grav += qty * val_unit
            afect    = 'Gravado'
        elif tc in ('EXO', 'EXONERADO', '20'):
            val_unit = pav
            op_exo  += qty * pav
            afect    = 'Exonerado'
        else:
            val_unit = pav
            op_ina  += qty * pav
            afect    = 'Inafecto'

        items.append({
            'item_code':  r[0] or '',
            'descripcion': r[1] or '',
            'unidad':      r[5] or 'UNIDAD',
            'quantity':    qty,
            'val_unit':    val_unit,
            'importe':     qty * pav,
            'afect':       afect,
        })

    igv      = round(op_grav * IGV_RATE, 2)
    op_grav  = round(op_grav, 2)
    op_exo   = round(op_exo,  2)
    op_ina   = round(op_ina,  2)
    total    = float(row[7] or 0)

    serie      = str(row[1]).strip()
    tipo_desc  = (str(row[13]) if row[13] else '').strip().upper()
    # Fallback por serie si la tabla no devuelve descripción
    if not tipo_desc:
        tipo_desc = ('BOLETA DE VENTA ELECTRÓNICA'
                     if serie.upper().startswith('B')
                     else 'FACTURA ELECTRÓNICA')
    tipo_label = tipo_desc
    moneda_label = 'DÓLARES' if (row[6] or '').upper() == 'USD' else 'SOLES'
    moneda_sym   = '$'       if (row[6] or '').upper() == 'USD' else 'S/'

    monto_letras = _num_a_letras(total) + ' ' + moneda_label

    return render_template('main/factura_imprimir.html',
        inv       = row,
        serie     = serie,
        numero    = str(row[2]).strip().zfill(7),
        tipo_label= tipo_label,
        moneda_label = moneda_label,
        moneda_sym   = moneda_sym,
        items     = items,
        op_grav   = op_grav,
        op_exo    = op_exo,
        op_ina    = op_ina,
        igv       = igv,
        total     = total,
        monto_letras = monto_letras,
    )


@main.route('/ventas/facturas/nueva', methods=['GET', 'POST'])
@login_required
def ventas_facturas_nueva():
    if request.method == 'POST':
        def _fmt_date(s):
            try:
                return datetime.strptime(s.strip(), '%Y-%m-%d').strftime('%Y-%m-%d') if s.strip() else ''
            except ValueError:
                return s.strip()

        card_code     = request.form.get('card_code',     '').strip()
        doc_date      = _fmt_date(request.form.get('doc_date',     ''))
        tax_date      = _fmt_date(request.form.get('tax_date',     ''))
        doc_due_date  = _fmt_date(request.form.get('doc_due_date', ''))
        doc_currency  = request.form.get('doc_currency',  'SOL').strip()
        comments      = request.form.get('comments',      '').strip()
        num_at_card   = request.form.get('num_at_card',   '').strip()
        journal_memo  = request.form.get('journal_memo',  '').strip()
        invoice_type  = request.form.get('invoice_type',  '').strip()
        invoice_serie = request.form.get('invoice_serie', '').strip()
        invoice_wh    = request.form.get('invoice_wh',    '').strip()
        inv_pos_str   = request.form.get('invoice_pos',    '').strip()
        invoice_pos   = int(inv_pos_str) if inv_pos_str.isdigit() else None
        # invoice_type ahora trae el idtype numérico; úsalo directamente
        inv_idt_str    = request.form.get('invoice_idtype', invoice_type).strip()
        invoice_idtype = int(inv_idt_str) if inv_idt_str.isdigit() else None
        p_user        = str(request.form.get('invoice_user', '').strip() or current_user.id_usuario)
        items_str     = request.form.get('items_json', '[]').strip()

        try:
            items_list = json.loads(items_str)
        except Exception:
            flash('Error en el detalle de ítems.', 'danger')
            return redirect(url_for('main.ventas_facturas'))

        if not card_code:
            flash('El Socio de Negocio es obligatorio.', 'danger')
            return redirect(url_for('main.ventas_facturas'))
        if not items_list:
            flash('Debe agregar al menos un ítem en el detalle.', 'warning')
            return redirect(url_for('main.ventas_facturas'))

        doc_total = sum(
            float(i.get('price_after_vat', 0)) * float(i.get('quantity', 0))
            for i in items_list
        )

        items_for_db = [{
            'ItemCode':      i.get('item_code', ''),
            'Quantity':      float(i.get('quantity', 0)),
            'PriceAfterVAT': float(i.get('price_after_vat', 0)),
            'TaxCode':       i.get('tax_code', ''),
            'WarehouseCode': i.get('warehouse_code', ''),
            'CostingCode':   i.get('costing_code', ''),
            'CostingCode2':  i.get('costing_code2', ''),
            'CostingCode3':  i.get('costing_code3', ''),
        } for i in items_list]

        try:
            row = db.session.execute(text("""
                SELECT success, message, correlativo, invoiceid
                FROM fn_invoice_inserta(
                    :p_card_code,
                    CAST(:p_doc_date     AS DATE),
                    CAST(:p_tax_date     AS DATE),
                    CAST(:p_doc_due_date AS DATE),
                    :p_doc_total,
                    :p_doc_currency,
                    :p_comments,
                    :p_num_at_card,
                    :p_journal_memo,
                    :p_invoice_type,
                    :p_invoice_serie,
                    :p_invoice_wh,
                    :p_invoice_pos,
                    :p_user,
                    :p_idtype,
                    CAST(:p_items AS jsonb)
                )
            """), {
                'p_card_code':     card_code,
                'p_doc_date':      doc_date,
                'p_tax_date':      tax_date,
                'p_doc_due_date':  doc_due_date,
                'p_doc_total':     doc_total,
                'p_doc_currency':  doc_currency,
                'p_comments':      comments,
                'p_num_at_card':   num_at_card,
                'p_journal_memo':  journal_memo,
                'p_invoice_type':  invoice_type,
                'p_invoice_serie': invoice_serie,
                'p_invoice_wh':    invoice_wh,
                'p_invoice_pos':   invoice_pos,
                'p_idtype':        invoice_idtype,
                'p_user':          p_user,
                'p_items':         json.dumps(items_for_db),
            }).fetchone()

            if row and row[0]:
                db.session.commit()
                # Registrar movimientos de salida en el kardex
                try:
                    from app.main.router_almacen_kardex import registrar_movimientos_venta
                    registrar_movimientos_venta(
                        invoice_id   = row[3],
                        card_code    = card_code,
                        invoice_type = str(invoice_idtype) if invoice_idtype else invoice_type,
                        id_tipo      = invoice_idtype,
                        doc_date     = doc_date,
                        invoice_wh   = invoice_wh,
                        items_list   = items_list,
                        user_code    = p_user,
                    )
                    db.session.commit()
                except Exception as e_mov:
                    db.session.rollback()
                    flash(f'Advertencia Kardex: {e_mov}', 'warning')
                flash(f'Factura {row[2]} registrada correctamente (ID: {row[3]}).', 'success')
                return redirect(url_for('main.ventas_facturas'))
            else:
                db.session.rollback()
                flash(row[1] if row else 'La función no devolvió confirmación.', 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Error al registrar: {e}', 'danger')

        return redirect(url_for('main.ventas_facturas'))

    from app.models import Usuario
    usuarios = Usuario.query.order_by(Usuario.nombres).all()
    today = date.today().isoformat()
    return render_template('main/ventas_facturas_nueva.html',
                           title='Nueva Factura de Venta',
                           section='Ventas', page='Nueva Factura',
                           today=today, usuarios=usuarios)


@main.route('/ventas/facturas/<int:invoice_id>/editar', methods=['POST'])
@login_required
def ventas_facturas_editar(invoice_id):
    def _fmt(s):
        try:
            return datetime.strptime(s.strip(), '%Y-%m-%d').strftime('%Y-%m-%d') if s and s.strip() else None
        except ValueError:
            return None

    card_code    = request.form.get('card_code',    '').strip()
    doc_date     = _fmt(request.form.get('doc_date',    ''))
    tax_date     = _fmt(request.form.get('tax_date',    ''))
    doc_due_date = _fmt(request.form.get('doc_due_date', ''))
    doc_currency = request.form.get('doc_currency', 'SOL').strip()
    comments     = request.form.get('comments',     '').strip()
    num_at_card  = request.form.get('num_at_card',  '').strip()
    journal_memo = request.form.get('journal_memo', '').strip()
    invoice_wh   = request.form.get('invoice_wh',   '').strip()
    p_user       = str(request.form.get('invoice_user', '').strip() or current_user.id_usuario)
    items_str    = request.form.get('items_json', '[]').strip()

    try:
        items_list = json.loads(items_str)
    except Exception:
        flash('Error en el detalle de ítems.', 'danger')
        return redirect(url_for('main.ventas_facturas'))

    doc_total = sum(
        float(i.get('price_after_vat', 0)) * float(i.get('quantity', 0))
        for i in items_list
    )

    try:
        # Leer idtype antes de actualizar (no se modifica en el editor)
        inv_row = db.session.execute(text(
            "SELECT idtype, invoice_type FROM invoice WHERE invoice_id = :id"
        ), {'id': invoice_id}).fetchone()
        invoice_idtype = (inv_row[0]) if inv_row else None
        # invoice_type en movimientos_almacen guarda el código numérico (idtype)
        invoice_type   = str(invoice_idtype) if invoice_idtype else ((inv_row[1] or '') if inv_row else '')

        db.session.execute(text("""
            UPDATE invoice SET
                card_code    = :card_code,
                doc_date     = CAST(:doc_date     AS DATE),
                tax_date     = CAST(:tax_date     AS DATE),
                doc_due_date = CAST(:doc_due_date AS DATE),
                doc_currency = :doc_currency,
                doc_total    = :doc_total,
                comments     = :comments,
                num_at_card  = :num_at_card,
                journal_memo = :journal_memo,
                invoice_wh   = :invoice_wh,
                user_code    = :user_code
            WHERE invoice_id = :invoice_id
        """), {
            'card_code':    card_code,
            'doc_date':     doc_date,
            'tax_date':     tax_date,
            'doc_due_date': doc_due_date,
            'doc_currency': doc_currency,
            'doc_total':    round(doc_total, 2),
            'comments':     comments,
            'num_at_card':  num_at_card,
            'journal_memo': journal_memo,
            'invoice_wh':   invoice_wh,
            'user_code':    p_user,
            'invoice_id':   invoice_id,
        })

        db.session.execute(text(
            "DELETE FROM invoice_item WHERE invoice_id = :id"
        ), {'id': invoice_id})

        for it in items_list:
            db.session.execute(text("""
                INSERT INTO invoice_item
                    (invoice_id, item_code, quantity, price_after_vat,
                     tax_code, warehouse_code, costing_code, costing_code2, costing_code3)
                VALUES
                    (:invoice_id, :item_code, :quantity, :price_after_vat,
                     :tax_code, :warehouse_code, :costing_code, :costing_code2, :costing_code3)
            """), {
                'invoice_id':      invoice_id,
                'item_code':       it.get('item_code', ''),
                'quantity':        float(it.get('quantity', 0)),
                'price_after_vat': float(it.get('price_after_vat', 0)),
                'tax_code':        it.get('tax_code', ''),
                'warehouse_code':  it.get('warehouse_code', ''),
                'costing_code':    it.get('costing_code', ''),
                'costing_code2':   it.get('costing_code2', ''),
                'costing_code3':   it.get('costing_code3', ''),
            })

        db.session.commit()

        # Sincronizar movimientos de salida en el kardex
        try:
            from app.main.router_almacen_kardex import sincronizar_movimientos_venta
            sincronizar_movimientos_venta(
                invoice_id   = invoice_id,
                card_code    = card_code,
                invoice_type = invoice_type,
                id_tipo      = invoice_idtype,
                doc_date     = doc_date,
                invoice_wh   = invoice_wh,
                items_list   = items_list,
                user_code    = p_user,
            )
            db.session.commit()
        except Exception as e_mov:
            db.session.rollback()
            flash(f'Advertencia Kardex: {e_mov}', 'warning')

        flash(f'Factura #{invoice_id} actualizada correctamente.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al actualizar: {e}', 'danger')

    return redirect(url_for('main.ventas_facturas'))


@main.route('/api/socios-ventas')
#@login_required
def api_socios_ventas():
    rows = db.session.execute(text(
        "SELECT * FROM business_partners_lista_tipo('2')"
    )).fetchall()
    result = [{
        'card_code':      r[0] or '',
        'card_name':      r[1] or '',
        'card_type':      r[2] or '',
        'group_code':     r[3] or '',
        'federal_tax_id': r[4] or '',
        'currency':       r[5] or '',
        'email':          r[6] or '',
        'IsCredit':       r[7],
        'Creditday':      r[8],
    } for r in rows]
    print(f'[api_socios_ventas] {len(result)} registros | primero: {result[0] if result else None}')
    return jsonify(result)




@main.route('/api/invoice-types')
@login_required
def api_invoice_types():
    rows = db.session.execute(text(
        "SELECT * FROM invoice_type_lista(1)"
    )).fetchall()
    return jsonify([{'idtype': r[0] or '', 'invoice_type': r[1] or ''} for r in rows])


@main.route('/api/warehouses')
@login_required
def api_warehouses():
    rows = db.session.execute(text(
        "SELECT * FROM warehouses_lista('')"
    )).fetchall()
    result = [{
        'whs_code': r[0] or '',
        'whs_name': r[1] or '',
    } for r in rows]
    return jsonify(result)


@main.route('/api/invoice-series')
@login_required
def api_invoice_series():
    invoice_wh = request.args.get('invoice_wh', '').strip()
    idtype     = request.args.get('idtype',     '').strip()
    rows = db.session.execute(text(
        "SELECT * FROM invoce_doc_number_lista(:whs, :idtype)"
    ), {'whs': invoice_wh, 'idtype': idtype}).fetchall()
    return jsonify([{
        'invoice_type':  r[0] or '',
        'invoice_serie': r[1] or '',
        'invoice_pos':   r[2],
    } for r in rows])
