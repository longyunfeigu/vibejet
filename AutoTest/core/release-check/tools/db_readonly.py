"""Runs inside a service pod (sent over stdin). Executes one SQL statement in a read-only
transaction using the pod's own database settings and prints the result as TSV.

argv: <base64 sql> <max rows>
"""
import asyncio
import base64
import os
import sys
from urllib.parse import quote

TIMEOUT_MS = 30000


def dsn():
    url = os.environ.get("DATABASE_URL", "")
    if url:
        scheme, rest = url.split("://", 1)
        return "postgresql://" + rest
    need = ("POSTGRES_HOST", "POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB")
    if not all(os.environ.get(k) for k in need):
        sys.exit("this pod has no DATABASE_URL or POSTGRES_* settings")
    e = os.environ
    return (f"postgresql://{quote(e['POSTGRES_USER'])}:{quote(e['POSTGRES_PASSWORD'])}"
            f"@{e['POSTGRES_HOST']}:{e.get('POSTGRES_PORT', '5432')}/{e['POSTGRES_DB']}")


def emit(columns, rows, limit):
    print("\t".join(columns))
    for row in rows[:limit]:
        print("\t".join("" if v is None else str(v).replace("\t", " ").replace("\n", " ") for v in row))
    if len(rows) > limit:
        print(f"... {len(rows) - limit} more rows not shown", file=sys.stderr)


def run_psycopg2(sql, limit):
    import psycopg2
    conn = psycopg2.connect(dsn(), options=f"-c statement_timeout={TIMEOUT_MS}")
    try:
        conn.set_session(readonly=True)
        with conn.cursor() as cur:
            cur.execute(sql)
            emit([d[0] for d in cur.description or []], cur.fetchmany(limit + 1), limit)
    finally:
        conn.rollback()
        conn.close()


async def run_asyncpg(sql, limit):
    import asyncpg
    conn = await asyncpg.connect(dsn(), server_settings={"statement_timeout": str(TIMEOUT_MS)})
    try:
        tx = conn.transaction(readonly=True)
        await tx.start()
        try:
            stmt = await conn.prepare(sql)
            rows = await stmt.fetch()
            emit([a.name for a in stmt.get_attributes()], [tuple(r) for r in rows], limit)
        finally:
            await tx.rollback()
    finally:
        await conn.close()


def main():
    sql = base64.b64decode(sys.argv[1]).decode()
    limit = int(sys.argv[2])
    try:
        import psycopg2  # noqa: F401
        run_psycopg2(sql, limit)
    except ImportError:
        asyncio.run(run_asyncpg(sql, limit))


main()
