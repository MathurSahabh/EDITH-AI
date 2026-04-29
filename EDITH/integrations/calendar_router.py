class CalendarRouter:
    def __init__(self, config):
        self.config = config

    def connect(self, provider: str) -> str:
        return f"Calendar connect for {provider} is set up placeholder."

    def create_meeting(self, raw_text: str) -> str:
        return f"Meeting parsed/created (placeholder): {raw_text}"

    def list_today(self) -> str:
        return "Today's meetings (placeholder)."