import concurrent.futures
import flet as ft
import threading, time
import utils.webbrowser_open as wbb
import sys, os

from datetime import datetime
from parsing.coin_price_parcing import get_bybit_futures_price
from typing import Dict, List

class AppWindow:
    def __init__(self, page, cl, trading_bot=None):
        self.page = page
        self.cl = cl
        self.trading_bot = trading_bot
        self._stop_update = False
        self.db = None

        # Инициализация БД
        self._init_database()

        # Создаем UI элементы
        self._create_text_fields()
        self._create_buttons()
        self._create_position_containers()

        # Загружаем позиции из БД
        self._load_positions_from_db()

        # Собираем представление
        self.app_page = self._build_app_view()

        # Запускаем автообновление
        self._start_auto_update()

    def _init_database(self):
        """Инициализация подключения к базе данных"""
        try:
            # Добавляем путь к utils
            utils_path = os.path.join(os.path.dirname(__file__), '..', 'utils')
            if utils_path not in sys.path:
                sys.path.append(utils_path)

            from utils.database_logic import TradingDB
            self.db = TradingDB()
            print("✅ База данных инициализирована в AppWindow")
        except Exception as e:
            print(f"❌ Ошибка инициализации БД: {e}")
            self.db = None

    def _start_auto_update(self):
        """Запускает поток автоматического обновления"""

        def update_loop():
            while not self._stop_update:
                time.sleep(2)
                if self._stop_update:
                    break
                # Обновляем данные
                if self.page and self.db:
                    self._load_positions_from_db()

        thread = threading.Thread(target=update_loop, daemon=True)
        thread.start()

    def _create_text_field(self, **kwargs):
        """Создает стандартное текстовое поле"""
        defaults = {
            'height': 60,
            'width': 380,
            'value': '',
            'bgcolor': self.cl.color_bg,
            'border_radius': 16,
            'border_color': self.cl.secondary_bg,
            'text_align': ft.TextAlign.CENTER,
            'text_style': ft.TextStyle(
                color=self.cl.text_primary,
                size=16,
                weight=ft.FontWeight.W_500,
            ),
        }
        defaults.update(kwargs)
        return ft.TextField(**defaults)

    def _create_text_fields(self):
        """Создает все текстовые поля"""
        self.name_coin = self._create_text_field(value='')
        self.percentage_balance = self._create_text_field(value='10')
        self.cross = self._create_text_field(value='30')
        self.take_profit = self._create_text_field()
        self.stop_loss = self._create_text_field()
        self.type = self._create_text_field(value='LONG')

    def _create_buttons(self):
        """Создает кнопки"""
        button_style = {
            'disabled': False,
            'color': self.cl.text_primary,
            'bgcolor': self.cl.surface,
            'width': 190,
            'height': 40,
        }

        self.confirm_button = ft.ElevatedButton(
            text='Send Position',
            tooltip='Enter details',
            on_click=self.create_new_position,
            **button_style
        )

        self.get_button = ft.ElevatedButton(
            text='Delete Position',
            on_click=self.delete_positions,
            **button_style
        )

    def _create_position_containers(self):
        """Создает 8 контейнеров для позиций"""
        self.position_containers = []
        for i in range(8):
            container = ft.Container(
                width=350,
                height=190,
                bgcolor=self.cl.color_bg,
                border_radius=20,
                content=ft.Column(
                    controls=[
                        ft.Text(f'Позиция {i + 1}', color=self.cl.text_secondary),
                        ft.Text('Отсутствует', color=self.cl.text_secondary, size=12),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER
                )
            )
            self.position_containers.append(container)

    def _load_positions_from_db(self):
        """Загружает позиции из базы данных"""
        if not self.db:
            print("❌ БД не инициализирована")
            return

        try:
            # Получаем все позиции
            positions = self.db.get_all_positions(active_only=False)
            # Получаем цены
            price_cache = self._get_prices_parallel(positions)

            # Обновляем контейнеры
            for i in range(8):
                if i < len(positions):
                    pos = positions[i]
                    name = pos.get('name')
                    last_price = price_cache.get(name, 'N/A')
                    self._update_container_with_data(i, pos, last_price)
                else:
                    # Очищаем контейнер если позиции нет
                    self.position_containers[i].content = ft.Column(
                        controls=[
                            ft.Text(f'Позиция {i + 1}', color=self.cl.text_secondary),
                            ft.Text('Отсутствует', color=self.cl.text_secondary, size=12),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER
                    )
                    self.position_containers[i].bgcolor = self.cl.color_bg

            # Обновляем страницу
            if self.page:
                self.page.update()

        except Exception as e:
            print(f"❌ Ошибка загрузки позиций: {e}")
            import traceback
            traceback.print_exc()

    def _get_prices_parallel(self, positions: List[Dict]) -> Dict[str, str]:
        """Получает цены для всех монет параллельно"""
        price_cache = {}
        unique_coins = list(set(pos.get('name') for pos in positions if pos.get('name')))

        if not unique_coins:
            return price_cache

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_coin = {
                executor.submit(get_bybit_futures_price, coin): coin
                for coin in unique_coins
            }

            for future in concurrent.futures.as_completed(future_to_coin):
                coin = future_to_coin[future]
                try:
                    price_data = future.result()
                    if price_data['found']:
                        price_cache[coin] = price_data['last_price']
                    else:
                        price_cache[coin] = 'N/A'
                except:
                    price_cache[coin] = 'N/A'

        return price_cache

    def _update_container_with_data(self, index: int, position_data: Dict, last_price: str):
        """Обновляет контейнер с данными с проверкой TP/SL"""
        try:
            from utils.database_logic import TradingDB
            from utils.telegram_notifier import send_close_notification

            id = position_data.get('id')
            name = position_data.get('name')
            pos_type = position_data.get('pos_type')
            cross = position_data.get('cross')
            tp = position_data.get('take_profit')
            sl = position_data.get('stop_loss')
            percent = position_data.get('percent')
            entry_price = position_data.get('entry_price')
            is_active = position_data.get('is_active', True)
            close_reason = position_data.get('close_reason')

            # Работа с %
            balance_percent = 0
            if entry_price and last_price and cross and last_price != 'N/A':
                try:
                    entry = float(entry_price)
                    current = float(last_price)
                    leverage = float(cross)
                    if pos_type == 'short':
                        direction_multiplier = -1
                    else:
                        direction_multiplier = 1

                    price_change_pct = ((current - entry) / entry) * 100 * direction_multiplier

                    position_share = float(percent) / 100 if percent else 0.01
                    balance_percent = round(price_change_pct * leverage * position_share, 2)
                except Exception as e:
                    print(f"Ошибка расчёта: {e}")
                    balance_percent = 0

            # Проверяем TP/SL
            tp_hit = False
            sl_hit = False

            if is_active and last_price != 'N/A':
                try:
                    last_price_float = float(last_price)
                    tp_float = float(tp) if tp else None
                    sl_float = float(sl) if sl else None

                    if pos_type == "short":
                        tp_hit = tp_float and last_price_float <= tp_float
                        sl_hit = sl_float and last_price_float >= sl_float
                    else:  # long
                        tp_hit = tp_float and last_price_float >= tp_float
                        sl_hit = sl_float and last_price_float <= sl_float
                except Exception as e:
                    print(f"Ошибка проверки TP/SL: {e}")

            # Если сработал TP/SL - сохраняем в БД
            if is_active and (tp_hit or sl_hit):
                db = TradingDB()

                if tp_hit:
                    print(f'{id} - TP hit! Сохраняю в БД...')
                    new_close_reason = 'tp'
                    text_color = ft.Colors.GREEN_400

                else:
                    print(f'{id} - SL hit! Сохраняю в БД...')
                    new_close_reason = 'sl'
                    text_color = ft.Colors.RED_400

                # Сохраняем в БД
                try:
                    db.update_position(
                        position_id=id,
                        is_active=False,
                        close_reason=new_close_reason,
                        closed_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        final_pnl=balance_percent
                    )
                    print(f"✅ Позиция {id} сохранена в БД как неактивная")
                    is_active = False
                    close_reason = new_close_reason  # Обновляем причину закрытия

                    # Отправляем уведомление в Telegram
                    try:
                        close_data = {
                            'id': id,
                            'name': name,
                            'pos_type': pos_type,
                            'entry_price': entry_price,
                            'take_profit': tp,
                            'stop_loss': sl,
                            'close_reason': new_close_reason,
                            'final_pnl': balance_percent,
                            'closed_at': datetime.now().strftime('%m-%d %H:%M')
                        }
                        send_close_notification(close_data)
                        print(f"📢 Уведомление о закрытии {name} отправлено")
                    except Exception as e:
                        print(f"⚠️ Ошибка отправки уведомления: {e}")

                    # Уведомляем TradingBot о закрытии
                    if self.trading_bot and hasattr(self.trading_bot, 'remove_position'):
                        self.trading_bot.remove_position(id)

                except Exception as e:
                    print(f"❌ Ошибка сохранения в БД: {e}")

            # Определяем цвет и статус
            if not is_active:
                # Безопасная проверка close_reason
                if close_reason and 'tp' in str(close_reason).lower():
                    status = "TP HIT"
                    text_color = ft.Colors.GREEN_400
                elif close_reason and 'sl' in str(close_reason).lower():
                    status = "SL HIT"
                    text_color = ft.Colors.RED_400
                else:
                    status = "CLOSED"
                    text_color = ft.Colors.GREY_400
            else:
                if balance_percent > 0:
                    status = f"+{balance_percent}%"
                    text_color = ft.Colors.GREEN_400
                else:
                    status = f"{balance_percent}%"
                    text_color = ft.Colors.RED_400

            # Форматируем цены
            entry_display = str(entry_price) if entry_price else "N/A"
            current_display = last_price if last_price != 'N/A' else "N/A"
            tp_display = str(tp) if tp else "N/A"
            sl_display = str(sl) if sl else "N/A"

            # Работа с цветом для | pos_type
            type_color = ft.Colors.RED_400
            if pos_type.upper() == "LONG":
                type_color = ft.Colors.GREEN_400

            # Update container positions
            self.position_containers[index].content = ft.Column(
                controls=[
                    ft.Text(f"ID: {id} | {name.upper()}", color=self.cl.text_primary, size=16, weight=ft.FontWeight.W_600),
                    ft.Row(controls=[ft.Text(f"{pos_type.upper()}", color=type_color, size=15, weight=ft.FontWeight.W_600),
                                ft.Text(f'| CROSS: {cross} | PERCENT: {percent}%', color=self.cl.text_primary,
                                size=15, weight=ft.FontWeight.W_600)],
                                alignment=ft.MainAxisAlignment.CENTER),
                    ft.Text(f"Entry: {entry_display} | Current: {current_display}", color=self.cl.text_primary, size=14, weight=ft.FontWeight.W_600),
                    ft.Text(f"TP: {tp_display} | SL: {sl_display}", color=self.cl.text_primary, size=13, weight=ft.FontWeight.W_600),
                    ft.Text(f"{status}", color=text_color, size=14, weight=ft.FontWeight.W_700),
                    ft.Row(controls=[
                        ft.ElevatedButton(text='Bybit', color=self.cl.text_primary, width=70, bgcolor=self.cl.secondary_bg, on_click = lambda e: wbb.bybit_open(name)),
                        ft.ElevatedButton(text='Binance', color=self.cl.text_primary, width=70, bgcolor=self.cl.secondary_bg, on_click = lambda e: wbb.binance_open(name)),
                        ft.ElevatedButton(text='BingX', color=self.cl.text_primary,  width=70, bgcolor=self.cl.secondary_bg, on_click = lambda e: wbb.binx_open(name)),
                        ft.ElevatedButton(text='Mexc', color=self.cl.text_primary,  width=70, bgcolor=self.cl.secondary_bg, on_click = lambda e: wbb.mexc_open(name))
                    ], alignment=ft.MainAxisAlignment.CENTER)
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=5
            )
            self.position_containers[index].bgcolor = self.cl.color_bg

        except Exception as e:
            print(f"❌ Ошибка обновления контейнера {index}: {e}")
            import traceback
            traceback.print_exc()
            self.position_containers[index].content = ft.Column(
                controls=[
                    ft.Text(f"Позиция {index + 1}", color=self.cl.text_secondary),
                    ft.Text('Ошибка загрузки', color=self.cl.text_secondary, size=12),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER
            )

    def create_new_position(self, e):
        """Создает новую позицию"""
        if not self.db:
            print("❌ БД не инициализирована")
            return

        try:
            name = self.name_coin.value.strip().upper()
            percent = int(self.percentage_balance.value)
            cross = int(self.cross.value)
            tp = float(self.take_profit.value.replace(',', '.')) if self.take_profit.value else 0
            sl = float(self.stop_loss.value.replace(',', '.')) if self.stop_loss.value else 0
            pos_type = self.type.value.strip().lower()

            # Получаем текущую цену
            price_data = get_bybit_futures_price(coin=name)
            if not price_data['found']:
                print(f"❌ Не удалось получить цену для {name}")
                return

            entry_price = float(price_data['last_price'])

            # Добавляем в БД
            position_id = self.db.add_to_db(name, percent, cross, entry_price, tp, sl, pos_type)
            print(f"✅ Позиция {name} добавлена в БД (ID: {position_id})")

            # Обновляем UI
            self._load_positions_from_db()

            # Очищаем поля
            self.name_coin.value = ''
            self.take_profit.value = ''
            self.stop_loss.value = ''

            if self.page:
                self.page.update()

        except Exception as ex:
            print(f"❌ Ошибка создания позиции: {ex}")

    def delete_positions(self, e):
        """Удаляет позиции"""
        print("Удаление позиций")
        # TODO: реализовать удаление

    def _build_app_view(self):
        """Собирает представление приложения - центрируем Positions"""
        # Первая колонка с полями ввода
        first_column = ft.Column(
            expand=4,
            controls=[
                self._create_field_group('Coin Name', self.name_coin),
                self._create_field_group('Long/Short', self.type),
                self._create_field_group('Cross', self.cross),
                self._create_field_group('Percent balance', self.percentage_balance),
                self._create_field_group('Take Profit', self.take_profit),
                self._create_field_group('Stop Loss', self.stop_loss),
                ft.Row(
                    controls=[self.confirm_button, self.get_button],
                    alignment=ft.MainAxisAlignment.CENTER,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER
                )
            ],
            spacing=20,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER
        )

        # Вторая колонка с позициями - центрируем заголовок
        second_column = ft.Column(
            expand=5,
            controls=[
                ft.Container(
                    width=780,
                    height=920,
                    bgcolor=self.cl.secondary_bg,
                    border_radius=50,
                    padding=ft.padding.all(20),
                    content=ft.Column(
                        controls=[
                            # Центрируем заголовок
                            ft.Container(
                                content=ft.Text('Positions',
                                               size=32,
                                               weight=ft.FontWeight.W_600,
                                               color=self.cl.text_primary),
                                alignment=ft.alignment.center
                            ),
                            ft.Row(
                                controls=[
                                    ft.Column(
                                        controls=self.position_containers[:4],
                                        spacing=15,
                                        horizontal_alignment=ft.CrossAxisAlignment.CENTER
                                    ),
                                    ft.Column(
                                        controls=self.position_containers[4:],
                                        spacing=15,
                                        horizontal_alignment=ft.CrossAxisAlignment.CENTER
                                    )
                                ],
                                spacing=20,
                                alignment=ft.MainAxisAlignment.CENTER,
                                vertical_alignment=ft.CrossAxisAlignment.START
                            )
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=20
                    )
                )
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER
        )

        return ft.Row(
            expand=True,
            controls=[first_column, second_column],
            vertical_alignment=ft.CrossAxisAlignment.START
        )

    def _create_field_group(self, label, field):
        """Создает группу с меткой и полем ввода"""
        return ft.Container(
            ft.Column(
                controls=[
                    ft.Text(label, size=20, weight=ft.FontWeight.W_600, color=self.cl.text_primary),
                    field
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=10
            ),
            bgcolor=self.cl.surface,
            border_radius=30,
            width=400
        )

    def close_position(self, name):
        """Закрывает позицию и отправляет уведомление"""
        print(f"🔔 Закрытие позиции: {name}")

        try:
            from utils.telegram_notifier import send_close_notification

            if not self.db:
                print("❌ БД не инициализирована")
                return

            # Находим активную позицию по имени
            positions = self.db.get_all_positions(active_only=True)
            position_to_close = None

            for pos in positions:
                if pos.get('name') == name:
                    position_to_close = pos
                    break

            if not position_to_close:
                print(f"⚠️ Активная позиция {name} не найдена")
                return

            # Формируем данные для закрытия
            close_data = {
                'id': position_to_close.get('id'),
                'name': name,
                'pos_type': position_to_close.get('pos_type'),
                'entry_price': position_to_close.get('entry_price'),
                'take_profit': position_to_close.get('take_profit'),
                'stop_loss': position_to_close.get('stop_loss'),
                'close_reason': 'manual',  # или 'tp', 'sl' в зависимости от ситуации
                'final_pnl': 0,  # можно рассчитать
                'closed_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

            # Отправляем уведомление
            send_close_notification(close_data)
            print(f"📢 Уведомление о закрытии {name} отправлено")

        except Exception as e:
            print(f"⚠️ Ошибка закрытия позиции: {e}")