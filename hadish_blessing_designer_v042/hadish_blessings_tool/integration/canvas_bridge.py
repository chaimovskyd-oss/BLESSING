class CanvasBridge:
    """Small integration layer.

    Standalone mode uses clipboard only.
    Plugin mode can pass any callable as on_insert_text.
    Example:
        panel = BlessingPanel(root, on_insert_text=my_app.add_text_to_canvas)
    """
    def __init__(self, on_insert_text=None):
        self.on_insert_text = on_insert_text

    def add_text(self, text: str):
        if self.on_insert_text:
            self.on_insert_text(text)
            return True
        return False
