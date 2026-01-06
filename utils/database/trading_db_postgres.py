import os
import logging
import psycopg2
from psycopg2.pool import SimpleConnectionPool
from psycopg2.extras import RealDictCursor
# ==========================
# LOGGER
# ==========================
logger = logging.getLogger(__name__)


class TradingDBPostgres:
    _pool: SimpleConnectionPool | None = None

    def __init__(self):
        if self.__class__._pool is None:
            logger.info("Initializing PostgreSQL connection pool")

            self.__class__._pool = SimpleConnectionPool(
                minconn=1,
                maxconn=5,
                dsn=os.getenv("DATABASE_URL"),
                cursor_factory=RealDictCursor
            )


    # ==========================
    # CONNECTION
    # ==========================

    def _get_conn(self):
        if self._pool is None:
            raise RuntimeError("PostgreSQL pool is not initialized")

        return self._pool.getconn()

    def _put_conn(self, conn):
        if self._pool and conn:
            self._pool.putconn(conn)

    # ==========================
    # POSITIONS
    # ==========================

    def get_all_positions(self, active_only=True):
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT *
                    FROM positions
                    WHERE is_active = true
                    ORDER BY created_at DESC
                """ if active_only else """
                    SELECT *
                    FROM positions
                    ORDER BY is_active DESC, created_at DESC
                """)
                rows = cur.fetchall()
                logger.info("Fetched %d positions", len(rows))
                return rows
        except Exception:
            logger.exception("Failed to fetch positions")
            return []
        finally:
            self._put_conn(conn)

    def add_to_db(
        self,
        name,
        percent,
        cross_margin,
        entry_price,
        take_profit,
        stop_loss,
        pos_type
    ):
        logger.info(
            "Adding position | %s %s entry=%s TP=%s SL=%s",
            name, pos_type, entry_price, take_profit, stop_loss
        )

        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO positions (
                            name,
                            percent,
                            cross_margin,
                            entry_price,
                            take_profit,
                            stop_loss,
                            pos_type,
                            is_active
                        )
                        VALUES (%s,%s,%s,%s,%s,%s,%s,true)
                        RETURNING id
                    """, (
                        name,
                        percent,
                        cross_margin,
                        entry_price,
                        take_profit,
                        stop_loss,
                        pos_type
                    ))

                    position_id = cur.fetchone()["id"]
                    conn.commit()

                    logger.info("Position created | id=%s", position_id)
                    return position_id

        except Exception:
            logger.exception("Failed to add position")
            raise

    def delete_position(self, position_id: int) -> bool:
        logger.info("Deleting position | id=%s", position_id)

        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "DELETE FROM positions WHERE id = %s",
                        (position_id,)
                    )

                conn.commit()

            logger.info("Position deleted | id=%s", position_id)
            return True

        except Exception:
            logger.exception("Failed to delete position | id=%s", position_id)
            return False

    # ==========================
    # BOT USERS
    # ==========================
    def add_user(self, user_id, username, first_name, last_name):
        logger.debug("Upserting user | id=%s username=%s", user_id, username)

        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO bot_users (
                            user_id,
                            username,
                            first_name,
                            last_name,
                            is_active
                        )
                        VALUES (%s,%s,%s,%s,true)
                        ON CONFLICT (user_id) DO UPDATE
                        SET
                            username = EXCLUDED.username,
                            first_name = EXCLUDED.first_name,
                            last_name = EXCLUDED.last_name,
                            is_active = true
                    """, (
                        user_id,
                        username,
                        first_name,
                        last_name
                    ))

                conn.commit()

            logger.info("User saved | id=%s", user_id)

        except Exception:
            logger.exception("Failed to add/update user | id=%s", user_id)

    def get_active_users(self):
        logger.debug("Fetching active bot users")
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT
                        user_id,
                        username,
                        first_name,
                        last_name,
                        created_at
                    FROM bot_users
                    WHERE is_active = true
                    ORDER BY created_at DESC
                """)

                users = cur.fetchall()  # список dict

                logger.info("Fetched %d active users", len(users))
                return users

        except Exception:
            logger.exception("Failed to fetch active users")
            return []


