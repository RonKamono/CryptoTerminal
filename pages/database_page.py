import webbrowser

import flet as ft

class DatabasePage:
    def __init__(self, page, cl, database, trading_bot=None):
        self.page = page
        self.cl = cl
        self.trading_bot = trading_bot
        self.db = database
        self.users_count = len(self.db.get_active_users())
        self.users_all_info = []
        self.load_user_from_db()
        self._create_buttons_user()

        self.app_page = self._build_app_view()

# CREATE FUNCS
    def _create_buttons_user(self):

        self.users_buttons = []
        for i in range(self.users_count):
            username = self.users_all_info[i]['username'] or 'no_username'
            user_id = self.users_all_info[i]['user_id']
            button = ft.ElevatedButton(
                    text=f'{username} | {user_id}',
                    on_click= lambda e: webbrowser.open(f't.me/{username}'),
                    color=self.cl.text_primary,
                    bgcolor=self.cl.secondary_bg,
                    width=400,
                    height=80
                )

            self.users_buttons.append(button)


#LOAD FUNCS
    def load_user_from_db(self):
        self.users_all_info = self.db.get_active_users()
        return

#UPDATE FUNCS

#VIEW FUNCS
    def _build_app_view(self):

        first_column = ft.Column(
            controls=[
                ft.Container(
                    width=450,
                    height=900,
                    bgcolor=self.cl.secondary_bg,
                    border_radius=50,
                    padding=ft.padding.all(20),
                    content=ft.Column(
                        controls=[
                            ft.Text(
                                'Text'
                            )
                        ]
                    )
                )
            ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER
        )

        second_column = ft.Column(
            controls=[
                ft.Container(
                    width=600,
                    height=900,
                    bgcolor=self.cl.secondary_bg,
                    border_radius=50,
                    padding=ft.padding.all(20),
                    content=ft.Column(
                        controls=[

                        ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER
                    )
                )
            ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER
        )

        third_column = ft.Column(
            controls=[
                ft.Container(
                    width=450,
                    height=900,
                    bgcolor=self.cl.secondary_bg,
                    border_radius=50,
                    content=ft.Column(
                        controls=[
                            ft.Container(
                                content=ft.Text(f'Users: {self.users_count}',
                                                size=32,
                                                weight=ft.FontWeight.W_600,
                                                color=self.cl.text_primary),
                                alignment=ft.alignment.center
                            ),
                                ft.Container(
                                    width=430,
                                    height=800,
                                    padding=ft.padding.all(20),
                                    border_radius=50,
                                    bgcolor=self.cl.color_bg,
                                    content=ft.Column(
                                        spacing=10,
                                        scroll=ft.ScrollMode.AUTO,
                                        controls=self.users_buttons,
                                        alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER
                                    )
                                )
                        ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER
                    )
                )
            ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER
        )

        return ft.Row(
            expand=True,
            controls=[ft.Container(
                expand=True,
                padding=ft.padding.all(20),
                content = ft.Row(
                   controls=[
                       first_column, second_column, third_column
                   ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, spacing=50
                )
            )],
        alignment=ft.MainAxisAlignment.CENTER, vertical_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=50,
        )