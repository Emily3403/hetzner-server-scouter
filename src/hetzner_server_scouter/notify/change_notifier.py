from hetzner_server_scouter.notify.models import ServerChange


class ChangeNotifier:
    changes: list[ServerChange]

    def __init__(self) -> None:
        self.changes = []

    def new_change(self, change: ServerChange) -> None:
        self.changes.append(change)

    def notify_about_changes(self) -> None:
        pass
