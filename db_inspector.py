"""
Utilidad para inspeccionar la base de datos PostgreSQL (Render).
Uso:  python db_inspector.py
"""

import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv(
    'DATABASE_URL',
    'postgresql+psycopg2://bdkorvase_user:jb6UhJKDX207xRDSUtXbPVhJbu2sffvY'
    '@dpg-d711pftm5p6s738q952g-a.ohio-postgres.render.com:5432/bdkorvase'
)


def _parse_dsn(url: str) -> dict:
    """Convierte DATABASE_URL de SQLAlchemy al formato psycopg2."""
    url = url.replace('postgresql+psycopg2://', '').replace('postgresql://', '')
    userpass, rest = url.split('@', 1)
    user, password = userpass.split(':', 1)
    hostport_db    = rest.split('/', 1)
    hostport       = hostport_db[0]
    database       = hostport_db[1] if len(hostport_db) > 1 else ''
    if ':' in hostport:
        host, port = hostport.rsplit(':', 1)
    else:
        host, port = hostport, '5432'
    return dict(dbname=database, user=user, password=password, host=host, port=port)


def get_connection():
    dsn = _parse_dsn(DB_URL)
    try:
        return psycopg2.connect(**dsn)
    except Exception as e:
        print(f"[ERROR] No se pudo conectar: {e}")
        raise SystemExit(1)


def list_tables(conn) -> list[str]:
    cur = conn.cursor()
    cur.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")
    return [r[0] for r in cur.fetchall()]


def describe_table(conn, table: str) -> list:
    cur = conn.cursor()
    cur.execute("""
        SELECT column_name, data_type, character_maximum_length, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_name = %s
        ORDER BY ordinal_position
    """, (table,))
    return cur.fetchall()


def count_rows(conn, table: str) -> int:
    cur = conn.cursor()
    cur.execute(f'SELECT COUNT(*) FROM "{table}"')
    return cur.fetchone()[0]


def print_table(conn, table: str, limit: int = 20):
    cur = conn.cursor()
    cur.execute(f'SELECT * FROM "{table}" LIMIT {limit}')
    rows  = cur.fetchall()
    cols  = [d[0] for d in cur.description]
    if not rows:
        print("  (Sin datos)")
        return
    widths = [max(len(str(c)), max(len(str(r[i])) for r in rows)) for i, c in enumerate(cols)]
    sep    = '+' + '+'.join('-' * (w + 2) for w in widths) + '+'
    hdr    = '|' + '|'.join(f' {c:<{widths[i]}} ' for i, c in enumerate(cols)) + '|'
    print(sep); print(hdr); print(sep)
    for row in rows:
        print('|' + '|'.join(f' {str(v):<{widths[i]}} ' for i, v in enumerate(row)) + '|')
    print(sep)


def main():
    conn   = get_connection()
    tables = list_tables(conn)

    print(f"\n{'═'*60}")
    print(f"  DB Inspector  ·  Render PostgreSQL  ·  bdkorvase")
    print(f"{'═'*60}")
    print(f"  Tablas: {len(tables)}\n")

    for table in tables:
        cols = describe_table(conn, table)
        try:
            rows = count_rows(conn, table)
        except Exception:
            rows = '?'
        print(f"  ┌─ {table}  ({rows} filas)")
        for col in cols:
            nn   = ' NOT NULL' if col[3] == 'NO' else ''
            size = f'({col[2]})' if col[2] else ''
            dflt = f' DEFAULT {col[4]}' if col[4] else ''
            print(f"  │   {col[0]:<28} {col[1]}{size}{nn}{dflt}")
        print()

    while True:
        print("Opciones:")
        print("  [1] Ver contenido de una tabla")
        print("  [2] Ejecutar SQL personalizado")
        print("  [0] Salir")
        opt = input("\nOpción: ").strip()

        if opt == '0':
            break
        elif opt == '1':
            t = input("Nombre de tabla: ").strip()
            if t in tables:
                print_table(conn, t)
            else:
                print(f"[!] Tabla '{t}' no existe.")
        elif opt == '2':
            sql = input("SQL> ").strip()
            try:
                cur = conn.cursor()
                cur.execute(sql)
                if cur.description:
                    cols = [d[0] for d in cur.description]
                    print('\t'.join(cols))
                    for row in cur.fetchall():
                        print('\t'.join(str(v) for v in row))
                else:
                    conn.commit()
                    print(f"OK — {cur.rowcount} filas afectadas.")
            except Exception as e:
                conn.rollback()
                print(f"[ERROR] {e}")

    conn.close()
    print("Conexión cerrada.")


if __name__ == '__main__':
    main()
