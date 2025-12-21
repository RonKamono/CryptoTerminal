

class WindowFunctions:
    def __init__(self):
        pass

    def close_window(self, e):
        try:
            e.page.window.close()
        except Exception:
            pass