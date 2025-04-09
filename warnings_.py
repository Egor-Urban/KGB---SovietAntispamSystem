import os
import json
import logging
from config import STANDART_COUNT

logger = logging.getLogger(__name__)

class WarningManager:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self._data = self._load()

    def _load(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Ошибка загрузки warning-файла: {e}")
        return {}

    def _save(self):
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(self._data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            logger.error(f"Ошибка сохранения warning-файла: {e}")

    def get_user(self, user_id: int) -> dict:
        uid = str(user_id)
        return self._data.get(uid, {
            "username": "unknown",
            "banned": False,
            "messages": [],
            "count": 0,
            "max_warnings": STANDART_COUNT
        })

    def log_violation(self, user_id: int, username: str, message: str) -> int:
        uid = str(user_id)
        user_data = self._data.setdefault(uid, self.get_user(user_id))
        user_data["username"] = username or "unknown"
        user_data["messages"].append(message)
        user_data["count"] = user_data.get("count", 0) + 1
        self._save()
        return user_data["count"]

    def reset_count(self, user_id: int):
        if str(user_id) in self._data:
            self._data[str(user_id)]["count"] = 0
            self._save()

    def is_banned(self, user_id: int) -> bool:
        return self._data.get(str(user_id), {}).get("banned", False)

    def ban_user(self, user_id: int):
        self._data[str(user_id)]["banned"] = True
        self._save()

    def get_warning_status(self, user_id: int) -> tuple[int, int]:
        user = self.get_user(user_id)
        return user.get("count", 0), user.get("max_warnings", STANDART_COUNT)

    def unban_user(self, user_id: int):
        if str(user_id) in self._data:
            self._data[str(user_id)]["banned"] = False
            self._save()

    def get_logs(self) -> dict:
        return self._data
