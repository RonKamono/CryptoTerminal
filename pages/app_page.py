### Import libs
import flet as ft

###import func/my libs



class AppWindow:
    def __init__(self, cl):

        self.name_coin = ft.TextField(
            height=60,
            width=380,
            value='',
            bgcolor=cl.color_bg,
            border_radius=16,
            border_color=cl.secondary_bg,
            text_align=ft.TextAlign.CENTER,
            text_style=ft.TextStyle(
                color=cl.text_primary,  # Цвет введенного текста
                size=16,
                weight=ft.FontWeight.W_500,
            ),
                        )

        self.percentage_balance = ft.TextField(
            height=60,
            width=380,
            value='',
            bgcolor=cl.color_bg,
            border_radius=16,
            border_color=cl.secondary_bg,
            text_align=ft.TextAlign.CENTER,
            text_style=ft.TextStyle(
                color=cl.text_primary,  # Цвет введенного текста
                size=16,
                weight=ft.FontWeight.W_500,
            ),

                        )

        self.take_profit = ft.TextField(
            height=60,
            width=380,
            value='',
            bgcolor=cl.color_bg,
            border_radius=16,
            border_color=cl.secondary_bg,
            text_align=ft.TextAlign.CENTER,
            text_style=ft.TextStyle(
                color=cl.text_primary,  # Цвет введенного текста
                size=16,
                weight=ft.FontWeight.W_500,
            ),
                        )

        self.stop_loss = ft.TextField(
            height=60,
            width=380,
            value='',
            bgcolor=cl.color_bg,
            border_radius=16,
            border_color=cl.secondary_bg,
            text_align=ft.TextAlign.CENTER,
            text_style=ft.TextStyle(
                color=cl.text_primary,  # Цвет введенного текста
                size=16,
                weight=ft.FontWeight.W_500,
            ),
                        )

        self.type = ft.TextField(
            height=60,
            width=380,
            value='',
            bgcolor=cl.color_bg,
            border_radius=16,
            border_color=cl.secondary_bg,
            text_align=ft.TextAlign.CENTER,
            text_style=ft.TextStyle(
                color=cl.text_primary,  # Цвет введенного текста
                size=16,
                weight=ft.FontWeight.W_500,
            ),
                        )

        self.confirm_button = ft.ElevatedButton(text='Send', disabled=False,
          tooltip='Enter details',
          color=cl.text_primary,
          bgcolor=cl.surface,
          width=400, height=40,
          on_click=lambda e: self.send_info(e)
                        )
        self.get_button = ft.ElevatedButton(text='Get Position', disabled=False,
          tooltip='Enter details',
          color=cl.text_primary,
          bgcolor=cl.surface,
          width=400, height=40,
          on_click=lambda e: self.get_info_position(e)
                        )

        ###app view
        self.app_page = ft.Column(
            expand=True,
            controls=[
                ft.Container(
                    ft.Column(
                        controls=[
                            ft.Text('Coin Name',
                                    size=20,
                                    weight=ft.FontWeight.W_600,
                                    color=cl.text_primary
                                    ),
                            self.name_coin
                        ], alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=10
                    ),
                    bgcolor=cl.surface,
                    border_radius=30,
                    width=400
                ),
                ft.Container(
                    ft.Column(
                        controls=[
                            ft.Text('Percent balance',
                                    size=20,
                                    weight=ft.FontWeight.W_600,
                                    color=cl.text_primary
                                    ),
                            self.percentage_balance
                        ], alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=10
                    ),
                    bgcolor=cl.surface,
                    border_radius=30,
                    width=400

                ),
                ft.Container(
                    ft.Column(
                        controls=[
                            ft.Text('Take Profit',
                                    size=20,
                                    weight=ft.FontWeight.W_600,
                                    color=cl.text_primary
                                    ),
                            self.take_profit
                        ], alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=10
                    ),
                    bgcolor=cl.surface,
                    border_radius=30,
                    width=400

                ),
                ft.Container(
                    ft.Column(
                        controls=[
                            ft.Text('Stop Loss',
                                    size=20,
                                    weight=ft.FontWeight.W_600,
                                    color=cl.text_primary
                                    ),
                            self.stop_loss
                        ], alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=10
                    ),
                    bgcolor=cl.surface,
                    border_radius=30,
                    width=400

                ),
                ft.Container(
                    ft.Column(
                        controls=[
                            ft.Text('Long/Short',
                                    size=20,
                                    weight=ft.FontWeight.W_600,
                                    color=cl.text_primary
                                    ),
                            self.type
                        ], alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=10
                    ),
                    bgcolor=cl.surface,
                    border_radius=30,
                    width=400

                ),
                ft.Column(
                    controls=[
                        self.confirm_button,
                        self.get_button,
                    ], alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER
                ),
            ], spacing=20,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.CENTER
        )

    def send_info(self, e):
        from utils.send_logic import send_to_bot
        name = self.name_coin.value.strip()
        percent_str = self.percentage_balance.value.strip()
        take_profit_str = self.take_profit.value.strip()
        stop_loss_str = self.stop_loss.value.strip()
        pos_type = self.type.value.strip()

        # Преобразование типов
        percent = int(percent_str)  # строка -> целое число
        take_profit = float(take_profit_str.replace(',', '.'))  # строка -> дробное число
        stop_loss = float(stop_loss_str.replace(',', '.'))  # строка -> дробное число

        send_to_bot(name, percent, take_profit, stop_loss, pos_type)

    def get_info_position(self, e):
        import pandas as pd
        from utils.send_logic import TradingDB
        db = TradingDB()
        positions = db.get_all_positions()

        if not positions:
            print("📭 Нет активных позиций")
            return

        # Создаем DataFrame для красивого вывода
        df = pd.DataFrame(positions)

        # Выбираем нужные колонки
        display_cols = ['name', 'pos_type', 'percent', 'take_profit', 'stop_loss', 'created_at']
        df_display = df[display_cols].copy()

        # Переименовываем колонки для лучшего отображения
        df_display.columns = ['Название', 'Тип', '%', 'TP', 'SL', 'Дата']

        # Форматируем дату
        df_display['Дата'] = df_display['Дата'].str[:19]

        print("\n" + "=" * 80)
        print("ТАБЛИЦА ПОЗИЦИЙ")
        print("=" * 80)
        print(df_display.to_string(index=False))
        print("=" * 80)
