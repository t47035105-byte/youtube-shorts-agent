from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .pipeline import produce


API_ROOT = "https://api.telegram.org"
ERROR_DETAIL_LIMIT = 1400


def parse_command(text: str) -> tuple[str, str]:
    stripped = (text or "").strip()
    if not stripped.startswith("/"):
        return "", ""
    command, _, argument = stripped.partition(" ")
    return command.split("@", 1)[0].lower(), argument.strip()


def safe_error_detail(exc: Exception) -> str:
    detail = str(exc).strip() or repr(exc)
    for secret_name in ("TELEGRAM_BOT_TOKEN", "GEMINI_API_KEY", "ELEVENLABS_API_KEY", "OPENAI_API_KEY"):
        secret = os.environ.get(secret_name, "")
        if secret:
            detail = detail.replace(secret, "[secret]")
    detail = " ".join(detail.split())
    return detail[:ERROR_DETAIL_LIMIT]


class TelegramAgent:
    def __init__(self) -> None:
        self.token = os.environ["TELEGRAM_BOT_TOKEN"]
        allowed = os.environ.get("TELEGRAM_ALLOWED_CHAT_ID", "").strip()
        username = os.environ.get("TELEGRAM_ALLOWED_USERNAME", "").strip().lstrip("@").lower()
        if not allowed and not username:
            raise RuntimeError("TELEGRAM_ALLOWED_CHAT_ID or TELEGRAM_ALLOWED_USERNAME is required")
        self.allowed_chat_id = int(allowed) if allowed else None
        self.allowed_username = username or None
        self.state_file = Path(os.environ.get("TELEGRAM_OFFSET_FILE", "state/telegram_offset.txt"))

    def _call(self, method: str, **kwargs: Any) -> dict[str, Any]:
        import requests
        response = requests.post(f"{API_ROOT}/bot{self.token}/{method}", timeout=180, **kwargs)
        response.raise_for_status()
        payload = response.json()
        if not payload.get("ok"):
            raise RuntimeError(f"Telegram {method} failed")
        return payload

    def send_text(self, chat_id: int, text: str) -> None:
        self._call("sendMessage", data={"chat_id": chat_id, "text": text[:4000], "disable_web_page_preview": True})

    def send_video(self, chat_id: int, path: Path, caption: str) -> None:
        with path.open("rb") as handle:
            self._call("sendVideo", data={"chat_id": chat_id, "caption": caption[:1024], "supports_streaming": True}, files={"video": (path.name, handle, "video/mp4")})

    def offset(self) -> int:
        if not self.state_file.exists():
            return 0
        try:
            return int(self.state_file.read_text(encoding="utf-8").strip() or 0)
        except ValueError:
            return 0

    def save_offset(self, value: int) -> None:
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(str(value), encoding="utf-8")

    def updates(self) -> list[dict[str, Any]]:
        # Long-poll briefly so a scheduled run does not miss a command that arrives
        # just as the job starts.
        payload = self._call("getUpdates", data={"offset": self.offset(), "timeout": 10, "limit": 100})
        return payload.get("result", [])

    def allowed(self, update: dict[str, Any]) -> bool:
        message = update.get("message") or {}
        chat_id = int((message.get("chat") or {}).get("id", 0))
        sender_username = str((message.get("from") or {}).get("username", "")).lower()
        if not chat_id:
            return False
        if self.allowed_chat_id is not None and chat_id != self.allowed_chat_id:
            return False
        if self.allowed_username is not None and sender_username != self.allowed_username:
            return False
        return True

    def handle(self, update: dict[str, Any]) -> bool:
        message = update.get("message") or {}
        chat_id = int((message.get("chat") or {}).get("id", 0))
        if not self.allowed(update):
            return False
        command, argument = parse_command(message.get("text", ""))
        if command in {"/start", "/help"}:
            self.send_text(chat_id, "명령어: /make 만들고 싶은 쇼츠 주제\n예: /make 배달앱 구독료, 누구에게 이득일까")
            return False
        if command == "/status":
            self.send_text(chat_id, "에이전트 정상 작동 중입니다.")
            return False
        if command != "/make" or not argument:
            return False

        self.send_text(chat_id, f"제작을 시작합니다.\n주제: {argument}\n완성되면 영상과 근거를 함께 보낼게요.")
        try:
            video, metadata = produce(argument)
            plan = json.loads(metadata.read_text(encoding="utf-8"))
            source_lines = [f"- {item['title']}: {item['url']}" for item in plan.get("sources", [])]
            caption = f"{plan['title']}\n#{' #'.join(plan['hashtags'])}"
            self.send_video(chat_id, video, caption)
            if source_lines:
                self.send_text(chat_id, "확인한 출처\n" + "\n".join(source_lines))
            return True
        except Exception as exc:
            detail = safe_error_detail(exc)
            self.send_text(chat_id, f"제작 중 오류가 발생했습니다.\n{type(exc).__name__}: {detail}")
            raise


def poll_once() -> int:
    agent = TelegramAgent()
    max_jobs = max(1, int(os.environ.get("MAX_JOBS_PER_RUN", "1")))
    jobs = 0
    for update in agent.updates():
        error: Exception | None = None
        made = False
        try:
            made = agent.handle(update)
        except Exception as exc:
            error = exc
        finally:
            # Advance every Telegram update exactly once; count only real /make jobs.
            agent.save_offset(int(update["update_id"]) + 1)
        if made:
            jobs += 1
        if error is not None:
            raise error
        if jobs >= max_jobs:
            break
    return jobs


if __name__ == "__main__":
    poll_once()
