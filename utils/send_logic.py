import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Optional, Tuple


class TradingDB:
    def __init__(self, db_name: str = 'trading.db'):
        """Инициализация базы данных"""
        # Определяем путь к базе данных
        self.db_path = os.path.join('C:\\DataBase', db_name)

        # Создаем директорию, если она не существует
        os.makedirs('C:\\DataBase', exist_ok=True)

        self.create_table()

    def create_table(self):
        """Создание таблицы для торговых позиций"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Основная таблица позиций - БЕЗ UNIQUE на name
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                percent INTEGER CHECK(percent >= 1 AND percent <= 100),
                take_profit REAL NOT NULL,
                stop_loss REAL NOT NULL,
                pos_type TEXT CHECK(pos_type IN ('long', 'short')) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,

                -- Проверки для логики
                CHECK(stop_loss >= 0),
                CHECK(take_profit >= 0),
                CHECK(stop_loss != take_profit)
            )
            ''')

            # Таблица для истории изменений
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS position_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                position_id INTEGER,
                name TEXT,
                percent INTEGER,
                take_profit REAL,
                stop_loss REAL,
                pos_type TEXT,
                changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (position_id) REFERENCES positions (id)
            )
            ''')

            # Таблица для логов операций
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS position_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                position_id INTEGER,
                action TEXT,
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (position_id) REFERENCES positions (id)
            )
            ''')

            conn.commit()

    def add_position(self,
                     name: str,
                     percent: int,
                     take_profit: float,
                     stop_loss: float,
                     pos_type: str) -> bool:
        """
        Добавление новой позиции
        """
        # Валидация входных данных
        if not self._validate_position(name, percent, take_profit, stop_loss, pos_type):
            return False

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute('''
                INSERT INTO positions (name, percent, take_profit, stop_loss, pos_type)
                VALUES (?, ?, ?, ?, ?)
                ''', (name, percent, take_profit, stop_loss, pos_type.lower()))

                position_id = cursor.lastrowid

                # Логируем создание
                self._log_action(position_id, "CREATE",
                                 f"Создана позиция: {name}, {pos_type}, TP: {take_profit}, SL: {stop_loss}")

                conn.commit()
                print(f"✅ Позиция '{name}' успешно добавлена (ID: {position_id})")
                print(f"📁 База данных: {self.db_path}")
                return True

        except sqlite3.IntegrityError as e:
            print(f"❌ Ошибка целостности данных: {e}")
            return False
        except Exception as e:
            print(f"❌ Ошибка при добавлении позиции: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _validate_position(self, name: str, percent: int,
                           take_profit: float, stop_loss: float,
                           pos_type: str) -> bool:
        """Валидация данных позиции"""
        print(f"\n🔍 ВАЛИДАЦИЯ данных:")
        print(f"  name: '{name}'")
        print(f"  percent: {percent}")
        print(f"  take_profit: {take_profit}")
        print(f"  stop_loss: {stop_loss}")
        print(f"  pos_type: '{pos_type}'")

        errors = []

        # Проверка имени (только буквы и пробелы)
        if not name.replace(' ', '').isalpha():
            errors.append("Имя должно содержать только буквы и пробелы")
            print(f"  ❌ Имя содержит не только буквы: '{name}'")

        # Проверка процента
        try:
            percent_int = int(percent)
            if not 1 <= percent_int <= 100:
                errors.append("Процент должен быть от 1 до 100")
                print(f"  ❌ Процент вне диапазона: {percent_int}")
        except (ValueError, TypeError):
            errors.append("Процент должен быть числом от 1 до 100")
            print(f"  ❌ Процент не число: {percent}")

        # Проверка типов позиций
        pos_type_lower = pos_type.lower()
        if pos_type_lower not in ['long', 'short']:
            errors.append("Тип позиции должен быть 'long' или 'short'")
            print(f"  ❌ Неверный тип позиции: '{pos_type}'")

        # Проверка уровней
        try:
            take_profit_float = float(take_profit)
            if take_profit_float <= 0:
                errors.append("Тейк-профит должен быть больше 0")
                print(f"  ❌ TP <= 0: {take_profit_float}")
        except (ValueError, TypeError):
            errors.append("Тейк-профит должен быть числом")
            print(f"  ❌ TP не число: {take_profit}")

        try:
            stop_loss_float = float(stop_loss)
            if stop_loss_float <= 0:
                errors.append("Стоп-лосс должен быть больше 0")
                print(f"  ❌ SL <= 0: {stop_loss_float}")
        except (ValueError, TypeError):
            errors.append("Стоп-лосс должен быть числом")
            print(f"  ❌ SL не число: {stop_loss}")

        # Логическая проверка для long/short
        try:
            tp = float(take_profit)
            sl = float(stop_loss)

            if pos_type_lower == 'long':
                if tp <= sl:
                    errors.append("Для long позиции: тейк-профит должен быть > стоп-лосса")
                    print(f"  ❌ Для LONG: TP ({tp}) <= SL ({sl})")
            else:  # short
                if tp >= sl:
                    errors.append("Для short позиции: тейк-профит должен быть < стоп-лосса")
                    print(f"  ❌ Для SHORT: TP ({tp}) >= SL ({sl})")
        except (ValueError, TypeError):
            print(f"  ⚠️ Пропущена логическая проверка из-за ошибок чисел")

        if errors:
            print("  ❌ Ошибки валидации:")
            for error in errors:
                print(f"     - {error}")
            return False

        print("  ✅ Валидация пройдена успешно")
        return True

    def get_all_positions(self, active_only: bool = False) -> List[Dict]:
        """Получение всех позиций"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                if active_only:
                    cursor.execute('''
                    SELECT * FROM positions 
                    WHERE is_active = 1 
                    ORDER BY created_at DESC
                    ''')
                else:
                    cursor.execute('SELECT * FROM positions ORDER BY created_at DESC')

                positions = [dict(row) for row in cursor.fetchall()]

                if positions:
                    status = "активных" if active_only else ""
                    print(f"\n📊 В базе {len(positions)} {status}позиций:")
                    for pos in positions:
                        print(f"  ID:{pos['id']} {pos['name']} {pos['pos_type']} {pos['percent']}%")
                else:
                    print("\n📭 База данных пустая")

                return positions

        except Exception as e:
            print(f"❌ Ошибка при получении позиций: {e}")
            import traceback
            traceback.print_exc()
            return []

    def get_position_by_name(self, name: str) -> Optional[Dict]:
        """Теперь возвращает список или первую позицию"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute('''
                SELECT * FROM positions 
                WHERE name = ? AND is_active = 1
                ORDER BY created_at DESC
                ''', (name,))

                rows = cursor.fetchall()
                if rows:
                    # Возвращаем первую позицию (последнюю созданную)
                    return dict(rows[0])
                return None

        except Exception as e:
            print(f"❌ Ошибка при поиске позиции: {e}")
            return None

    def get_all_positions_by_name(self, name: str) -> List[Dict]:
        """Новый метод: получить все позиции с определенным именем"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute('''
                SELECT * FROM positions 
                WHERE name = ? AND is_active = 1
                ORDER BY created_at DESC
                ''', (name,))

                return [dict(row) for row in cursor.fetchall()]

        except Exception as e:
            print(f"❌ Ошибка при поиске позиций по имени: {e}")
            return []

    def _log_action(self, position_id: int, action: str, details: str = ""):
        """Логирование действий"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                INSERT INTO position_logs (position_id, action, details)
                VALUES (?, ?, ?)
                ''', (position_id, action, details))
                conn.commit()
        except Exception as e:
            print(f"⚠️ Ошибка при логировании: {e}")


def get_actual_position():
    """
    Получает все актуальные позиции из базы данных
    """
    try:
        db = TradingDB('trading.db')
        positions = db.get_all_positions(active_only=True)

        if not positions:
            print("📭 Нет активных позиций в базе данных")
            return []

        print(f"✅ Найдено {len(positions)} активных позиций:")

        for i, pos in enumerate(positions, 1):
            print(f"\n{i}. ID: {pos['id']} - {pos['name']}")
            print(f"   Тип: {pos['pos_type'].upper()}")
            print(f"   Процент: {pos['percent']}%")
            print(f"   Take Profit: {pos['take_profit']}")
            print(f"   Stop Loss: {pos['stop_loss']}")
            print(f"   Создана: {pos['created_at']}")

        return positions

    except Exception as e:
        print(f"❌ Ошибка при получении позиций: {e}")
        import traceback
        traceback.print_exc()
        return []


def send_to_bot(name, percent, take_profit, stop_loss, pos_type):
    """
    Добавляет позицию в базу данных
    """
    try:
        print(f"\n🔍 ДЕБАГ: Получены данные:")
        print(f"  name: {name} (тип: {type(name)})")
        print(f"  percent: {percent} (тип: {type(percent)})")
        print(f"  take_profit: {take_profit} (тип: {type(take_profit)})")
        print(f"  stop_loss: {stop_loss} (тип: {type(stop_loss)})")
        print(f"  pos_type: {pos_type} (тип: {type(pos_type)})")

        # Преобразование типов
        try:
            percent_int = int(percent) if not isinstance(percent, int) else percent
            print(f"  percent после int(): {percent_int}")
        except Exception as e:
            print(f"  ❌ Ошибка преобразования percent в int: {e}")
            raise

        try:
            take_profit_float = float(take_profit) if not isinstance(take_profit, float) else take_profit
            print(f"  take_profit после float(): {take_profit_float}")
        except Exception as e:
            print(f"  ❌ Ошибка преобразования take_profit в float: {e}")
            raise

        try:
            stop_loss_float = float(stop_loss) if not isinstance(stop_loss, float) else stop_loss
            print(f"  stop_loss после float(): {stop_loss_float}")
        except Exception as e:
            print(f"  ❌ Ошибка преобразования stop_loss в float: {e}")
            raise

        db = TradingDB('trading.db')
        print(f"  🔍 База данных: {db.db_path}")

        success = db.add_position(name, percent_int, take_profit_float, stop_loss_float, pos_type)

        if success:
            print(f"\n✅ Позиция успешно добавлена:")
            print(f'Name: {name}')
            print(f'Percent Balance: {percent_int}%')
            print(f'Take Profit: {take_profit_float}')
            print(f'Stop Loss: {stop_loss_float}')
            print(f'Position Type: {pos_type}')
            return True
        else:
            print("❌ Не удалось добавить позицию в базу данных")
            print("   Возможные причины:")
            print("   1. Ошибка валидации данных")
            print("   2. Позиция с такими параметрами уже существует")
            print("   3. Проблема с базой данных")
            return False

    except ValueError as e:
        print(f"❌ Ошибка преобразования типов: {e}")
        import traceback
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False


# Пример использования
if __name__ == "__main__":
    # Тестирование соединения
    db = TradingDB('trading.db')
    print(f"📁 База данных создана по пути: {db.db_path}")

    # Пример добавления позиции
    success = db.add_position(
        name="Apple",
        percent=10,
        take_profit=150.0,
        stop_loss=140.0,
        pos_type="long"
    )

    # Получение всех позиций
    positions = db.get_all_positions()
    print(f"\nВсего позиций в базе: {len(positions)}")