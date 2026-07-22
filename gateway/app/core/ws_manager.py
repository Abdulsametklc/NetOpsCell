from fastapi import WebSocket


class ConnectionManager:
    """JWT'den gelen user_id/role'e göre bağlantıları izler (ARCHITECTURE.md §5,
    Notification Hub). Aynı kullanıcının birden fazla sekmesi/cihazı olabilir,
    bu yüzden user_id başına bir set tutulur."""

    def __init__(self) -> None:
        self._by_user: dict[str, set[WebSocket]] = {}
        self._roles: dict[WebSocket, str] = {}

    async def connect(self, user_id: str, role: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self._by_user.setdefault(user_id, set()).add(websocket)
        self._roles[websocket] = role

    def disconnect(self, user_id: str, websocket: WebSocket) -> None:
        conns = self._by_user.get(user_id)
        if conns is not None:
            conns.discard(websocket)
            if not conns:
                self._by_user.pop(user_id, None)
        self._roles.pop(websocket, None)

    async def send_to_user(self, user_id: str, message: dict) -> None:
        for ws in list(self._by_user.get(user_id, ())):
            try:
                await ws.send_json(message)
            except Exception:  # noqa: BLE001 - kopuk soket, sessizce atla
                pass

    async def broadcast_to_roles(self, roles: set[str], message: dict) -> None:
        for ws, role in list(self._roles.items()):
            if role in roles:
                try:
                    await ws.send_json(message)
                except Exception:  # noqa: BLE001
                    pass


manager = ConnectionManager()
