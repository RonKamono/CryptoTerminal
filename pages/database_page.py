import flet as ft
import os
import asyncio

class ControlPage:
    def __init__(self, page, cl, trading_bot=None):
        self.page = page
        self.cl = cl
        self.trading_bot = trading_bot
        self.db = None

    def build_view(self):

        first_column = ft.Column(

        )

        second_column = ft.Column(
            controls=[
                ft.Text(
                    'Text'
                )
            ]
        )

        third_column = ft.Column()

        return ft.Row(
            expand=True,
            controls=[first_column, second_column, third_column],
        )