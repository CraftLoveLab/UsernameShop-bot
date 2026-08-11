import json
import logging
import os

logger = logging.getLogger(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)


def _using_database():
    return bool(DATABASE_URL)


def init_stats():
    if not _using_database():
        logger.info("Stats: используется stats.json (DATABASE_URL не задан)")
        return

    import psycopg2

    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS product_views (
                    product_id TEXT PRIMARY KEY,
                    views INTEGER NOT NULL DEFAULT 0
                )
                """
            )
        conn.commit()

    _migrate_json_to_db()
    logger.info("Stats: используется PostgreSQL")


def _migrate_json_to_db():
    try:
        with open("stats.json", "r", encoding="utf-8") as file:
            stats = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return

    if not stats:
        return

    import psycopg2

    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            for product_id, views in stats.items():
                cur.execute(
                    """
                    INSERT INTO product_views (product_id, views)
                    VALUES (%s, %s)
                    ON CONFLICT (product_id) DO UPDATE
                    SET views = GREATEST(product_views.views, EXCLUDED.views)
                    """,
                    (product_id, views),
                )
        conn.commit()

    logger.info("Перенесено %s записей из stats.json в PostgreSQL", len(stats))


def load_stats():
    if _using_database():
        import psycopg2

        with psycopg2.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT product_id, views FROM product_views")
                return dict(cur.fetchall())

    try:
        with open("stats.json", "r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}


def increment_views(product_id):
    if _using_database():
        import psycopg2

        with psycopg2.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO product_views (product_id, views)
                    VALUES (%s, 1)
                    ON CONFLICT (product_id) DO UPDATE
                    SET views = product_views.views + 1
                    RETURNING views
                    """,
                    (product_id,),
                )
                views = cur.fetchone()[0]
            conn.commit()
            return views

    stats = load_stats()
    stats[product_id] = stats.get(product_id, 0) + 1
    with open("stats.json", "w", encoding="utf-8") as file:
        json.dump(stats, file, ensure_ascii=False, indent=4)
    return stats[product_id]
