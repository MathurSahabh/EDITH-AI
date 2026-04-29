class TasksRouter:
    def __init__(self, config):
        self.config = config

    def add_task(self, raw_text: str) -> str:
        return f"Task added (placeholder): {raw_text}"

    def list_tasks(self) -> str:
        return "Task list (placeholder)."

    def complete_task(self, raw_text: str) -> str:
        return f"Task completed (placeholder): {raw_text}"

    def delete_task(self, raw_text: str) -> str:
        return f"Task deleted (placeholder): {raw_text}"