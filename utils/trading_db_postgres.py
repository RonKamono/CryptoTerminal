import os
from typing import List, Dict, Optional
from datetime import datetime

import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()


class TradingDBPostgres:
    def __init__(self):
        self.conn = psycopg2.connect(
            os.getenv("DATABASE_URL"),
            cursor_factory=RealDictCursor
        )

    # -------------------------
    # CREATE
    # -------------------------
    def add_to_db(
        self,
        name: str,
        percent: int,
        cross_margin: Optional[int],
        entry_price: float,
        take_profit: float,
        stop_loss: float,
        pos_type: str
    ) -> Optional[int]:
        try:
            with self.conn:
                with self.conn.cursor() as cur:
                    cur.execute(
                        """
                        insert into positions
                        (name, percent, cross_margin, entry_price, take_profit, stop_loss, pos_type, is_active)
                        values (%s, %s, %s, %s, %s, %s, %s, true)
                        returning id
                        """,
                        (
                            name,
                            percent,
                            cross_margin,
                            entry_price,
                            take_profit,
                            stop_loss,
                            pos_type
                        )
                    )
                    position_id = cur.fetchone()["id"]

                    # history
                    cur.execute(
                        """
                        insert into position_history
                        (position_id, name, percent, cross_margin, entry_price, take_profit, stop_loss, pos_type)
                        values (%s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            position_id,
                            name,
                            percent,
                            cross_margin,
                            entry_price,
                            take_profit,
                            stop_loss,
                            pos_type
                        )
                    )

                    # logs
                    cur.execute(
                        """
                        insert into position_logs (position_id, action, details)
                        values (%s, %s, %s)
                        """,
                        (
                            position_id,
                            "CREATE",
                            f"Created position {name}"
                        )
                    )

                    return position_id

        except Exception as e:
            print(f"❌ PostgreSQL error (add): {e}")
            return None

    # -------------------------
    # READ
    # -------------------------
    def get_all_positions(self, active_only: bool = True) -> List[Dict]:
        try:
            with self.conn.cursor() as cur:
                if active_only:
                    cur.execute(
                        """
                        select *
                        from positions
                        where is_active = true
                        order by created_at desc
                        """
                    )
                else:
                    cur.execute(
                        """
                        select *
                        from positions
                        order by is_active desc, created_at desc
                        """
                    )

                rows = cur.fetchall()
                return rows

        except Exception as e:
            print(f"❌ PostgreSQL error (get_all): {e}")
            return []

    # -------------------------
    # UPDATE
    # -------------------------
    def update_position(self, position_id: int, **kwargs) -> bool:
        allowed_fields = [
            "name",
            "percent",
            "cross_margin",
            "take_profit",
            "stop_loss",
            "pos_type",
            "is_active",
            "close_reason",
            "closed_at",
            "final_pnl"
        ]

        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}

        if not updates:
            return False

        try:
            with self.conn:
                with self.conn.cursor() as cur:
                    set_clause = ", ".join([f"{k} = %s" for k in updates.keys()])
                    query = f"""
                        update positions
                        set {set_clause},
                            updated_at = now()
                        where id = %s
                    """

                    cur.execute(query, list(updates.values()) + [position_id])

                    cur.execute(
                        """
                        insert into position_logs (position_id, action, details)
                        values (%s, %s, %s)
                        """,
                        (position_id, "UPDATE", f"Fields: {', '.join(updates.keys())}")
                    )

                    return True

        except Exception as e:
            print(f"❌ PostgreSQL error (update): {e}")
            return False

    # -------------------------
    # CLOSE POSITION
    # -------------------------
    def close_position(self, position_id: int, close_reason: str, final_pnl: float) -> bool:
        try:
            with self.conn:
                with self.conn.cursor() as cur:
                    cur.execute(
                        """
                        update positions
                        set is_active = false,
                            close_reason = %s,
                            closed_at = now(),
                            final_pnl = %s,
                            updated_at = now()
                        where id = %s
                        """,
                        (close_reason, final_pnl, position_id)
                    )

                    cur.execute(
                        """
                        insert into position_logs (position_id, action, details)
                        values (%s, %s, %s)
                        """,
                        (
                            position_id,
                            "CLOSE",
                            f"Reason: {close_reason}, PnL: {final_pnl}%"
                        )
                    )

                    return True

        except Exception as e:
            print(f"❌ PostgreSQL error (close): {e}")
            return False

    # -------------------------
    # DELETE
    # -------------------------
    def delete_position(self, position_id: int) -> bool:
        try:
            with self.conn:
                with self.conn.cursor() as cur:
                    cur.execute("delete from positions where id = %s", (position_id,))
                    return True
        except Exception as e:
            print(f"❌ PostgreSQL error (delete): {e}")
            return False
