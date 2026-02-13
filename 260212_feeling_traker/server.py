#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen

BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = BASE_DIR
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "mood_tracker.db"

HOST = os.getenv("MOOD_APP_HOST", "127.0.0.1")
PORT = int(os.getenv("MOOD_APP_PORT", "8765"))

MOODS = {
    "great": {"label": "아주 좋음", "score": 5, "emoji": "😁"},
    "good": {"label": "좋음", "score": 4, "emoji": "🙂"},
    "okay": {"label": "보통", "score": 3, "emoji": "😐"},
    "down": {"label": "우울", "score": 2, "emoji": "😔"},
    "bad": {"label": "힘듦", "score": 1, "emoji": "😣"},
}


@dataclass
class ChatReply:
    text: str
    source: str
    emotions: list[str]
    causes: list[str]
    actions: list[str]


def now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def parse_date(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%d")


def ensure_db() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS entries (
                date TEXT PRIMARY KEY,
                mood_id TEXT NOT NULL,
                score INTEGER NOT NULL,
                comment TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS app_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "INSERT OR IGNORE INTO app_meta(key, value) VALUES('started_at', ?)",
            (today_str(),),
        )
        conn.commit()


def db_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_started_at(conn: sqlite3.Connection) -> str:
    row = conn.execute("SELECT value FROM app_meta WHERE key='started_at'").fetchone()
    return row["value"] if row else today_str()


def save_entry(payload: dict[str, Any]) -> dict[str, Any]:
    date = payload.get("date", "").strip()
    mood_id = payload.get("moodId", "").strip()
    comment = (payload.get("comment") or "").strip()

    if not date:
        raise ValueError("date is required")
    parse_date(date)
    if mood_id not in MOODS:
        raise ValueError("invalid moodId")

    score = MOODS[mood_id]["score"]
    ts = now_iso()

    with db_conn() as conn:
        conn.execute(
            """
            INSERT INTO entries(date, mood_id, score, comment, created_at, updated_at)
            VALUES(?, ?, ?, ?, ?, ?)
            ON CONFLICT(date) DO UPDATE SET
              mood_id=excluded.mood_id,
              score=excluded.score,
              comment=excluded.comment,
              updated_at=excluded.updated_at
            """,
            (date, mood_id, score, comment, ts, ts),
        )
        conn.commit()

    return {"date": date, "moodId": mood_id, "score": score, "comment": comment}


def load_entries(date_from: str | None = None, date_to: str | None = None) -> list[dict[str, Any]]:
    query = "SELECT date, mood_id, score, comment, updated_at FROM entries"
    params: list[Any] = []
    conds: list[str] = []
    if date_from:
        conds.append("date >= ?")
        params.append(date_from)
    if date_to:
        conds.append("date <= ?")
        params.append(date_to)
    if conds:
        query += " WHERE " + " AND ".join(conds)
    query += " ORDER BY date ASC"

    with db_conn() as conn:
        rows = conn.execute(query, params).fetchall()

    return [
        {
            "date": r["date"],
            "moodId": r["mood_id"],
            "score": r["score"],
            "comment": r["comment"] or "",
            "updatedAt": r["updated_at"],
            "mood": MOODS.get(r["mood_id"], {}),
        }
        for r in rows
    ]


def summary_payload() -> dict[str, Any]:
    entries = load_entries()
    scores = [e["score"] for e in entries]
    avg = round(sum(scores) / len(scores), 2) if scores else 0.0

    today = datetime.now().date()
    week_start = today - timedelta(days=6)

    with db_conn() as conn:
        started_at = datetime.strptime(get_started_at(conn), "%Y-%m-%d").date()

    window_start = max(started_at, week_start)
    date_set = {e["date"] for e in entries}
    missing = []
    d = window_start
    while d <= today:
        key = d.strftime("%Y-%m-%d")
        if key not in date_set:
            missing.append(key)
        d += timedelta(days=1)

    notices = []
    if missing:
        notices.append(f"최근 관리 구간({window_start} ~ {today})에서 {len(missing)}일 기록이 비어 있습니다.")
    else:
        notices.append("최근 관리 구간 기록이 잘 채워져 있습니다.")

    low_streak = 0
    high_streak = 0
    for e in reversed(entries):
        if e["score"] <= 2:
            low_streak += 1
        else:
            break
    for e in reversed(entries):
        if e["score"] >= 4:
            high_streak += 1
        else:
            break
    if low_streak >= 3:
        notices.append("주의: 최근 낮은 기분이 연속됩니다. 수면/휴식/업무강도를 점검해보세요.")
    if high_streak >= 3:
        notices.append("응원: 최근 좋은 흐름이 지속됩니다. 현재 루틴을 유지해보세요.")

    trend = []
    for e in entries:
        trend.append({"date": e["date"], "score": e["score"], "moodId": e["moodId"]})

    return {
        "count": len(entries),
        "averageScore": avg,
        "notices": notices,
        "missingDates": missing,
        "trend": trend,
        "windowStart": str(window_start),
        "windowEnd": str(today),
    }


def save_chat(role: str, content: str) -> None:
    with db_conn() as conn:
        conn.execute(
            "INSERT INTO chat_messages(role, content, created_at) VALUES(?, ?, ?)",
            (role, content, now_iso()),
        )
        conn.commit()


def load_chat(limit: int = 80) -> list[dict[str, Any]]:
    with db_conn() as conn:
        rows = conn.execute(
            "SELECT role, content, created_at FROM chat_messages ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    rows = list(reversed(rows))
    return [{"role": r["role"], "content": r["content"], "createdAt": r["created_at"]} for r in rows]


def load_recent_dialog(limit: int = 16) -> list[dict[str, str]]:
    rows = load_chat(limit=limit)
    return [{"role": r["role"], "content": r["content"]} for r in rows if r.get("role") in {"user", "assistant"}]


def detect_emotions(text: str) -> list[str]:
    t = text.lower()
    rules = {
        "분노": ["화나", "짜증", "빡쳐", "열받", "분노", "angry", "annoy", "irritat"],
        "우울": ["우울", "무기력", "허무", "침울", "depress", "sad"],
        "불안": ["불안", "초조", "걱정", "압박", "anxious"],
        "피로": ["피곤", "지침", "지쳤", "수면부족", "tired", "exhaust"],
    }
    found = [name for name, kws in rules.items() if any(k in t for k in kws)]
    return found or ["중립"]


def detect_causes(text: str) -> list[str]:
    t = text.lower()
    rules = {
        "업무/마감 압박": ["마감", "일", "업무", "회의", "보고", "프로젝트"],
        "수면/컨디션": ["잠", "수면", "피곤", "컨디션", "두통"],
        "대인관계 갈등": ["싸웠", "갈등", "관계", "서운", "오해"],
        "건강/생활 리듬": ["운동", "건강", "식사", "생활", "루틴"],
    }
    found = [name for name, kws in rules.items() if any(k in t for k in kws)]
    return found or ["원인 정보 부족"]


def suggest_actions(emotions: list[str], causes: list[str]) -> list[str]:
    acts: list[str] = []
    if "분노" in emotions:
        acts.append("30초 복식호흡 후 지금 통제 가능한 행동 1개만 정하기")
    if "우울" in emotions or "피로" in emotions:
        acts.append("오늘 할 일 우선순위를 1개로 줄이고 회복 시간 20분 확보")
    if "불안" in emotions:
        acts.append("걱정 목록을 종이에 적고 즉시 실행 가능한 항목만 분리")
    if "업무/마감 압박" in causes:
        acts.append("마감 업무를 25분 단위로 쪼개 첫 블록만 시작")
    if "수면/컨디션" in causes:
        acts.append("오늘 취침 시간 고정 및 카페인 컷오프 시간 정하기")
    if not acts:
        acts.append("원인-감정-다음행동을 한 줄로 적어 패턴을 관찰하기")
    return acts[:3]


def local_calm_reply(message: str) -> ChatReply:
    msg = message.strip()
    emotions = detect_emotions(msg)
    causes = detect_causes(msg)
    actions = suggest_actions(emotions, causes)
    text = (
        f"지금 감정은 {', '.join(emotions)} 쪽으로 보여요. "
        f"원인 후보는 {', '.join(causes)} 입니다. "
        f"우선 '{actions[0]}'부터 해볼까요?"
    )
    return ChatReply(text=text, source="rule-based", emotions=emotions, causes=causes, actions=actions)


def try_openai_reply(message: str, history: list[dict[str, str]]) -> ChatReply | None:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None

    model = os.getenv("MOOD_CHAT_MODEL", "gpt-4o-mini")
    prompt = (
        "너는 감정 코치다. 사용자의 일상 대화에서 감정(분노/우울/불안/피로)과 원인 후보를 짚고,"
        " 짧고 실용적인 해결 액션 1~3개를 제시한다."
        " 응답은 반드시 JSON으로만 반환한다."
        " 포맷: {\"reply\":\"...\", \"emotions\":[...], \"causes\":[...], \"actions\":[...]}"
    )

    body = {
        "model": model,
        "messages": [{"role": "system", "content": prompt}] + history + [{"role": "user", "content": message}],
        "temperature": 0.4,
        "max_tokens": 260,
        "response_format": {"type": "json_object"},
    }

    req = Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(req, timeout=12) as resp:
            raw = resp.read().decode("utf-8")
        payload = json.loads(raw)
        raw_content = payload["choices"][0]["message"]["content"].strip()
        parsed = json.loads(raw_content)
        text = str(parsed.get("reply", "")).strip() or "지금 상태를 한 줄로 요약해볼게요. 핵심 원인부터 정리해봅시다."
        emotions = [str(x) for x in parsed.get("emotions", []) if str(x).strip()][:4] or detect_emotions(message)
        causes = [str(x) for x in parsed.get("causes", []) if str(x).strip()][:4] or detect_causes(message)
        actions = [str(x) for x in parsed.get("actions", []) if str(x).strip()][:3] or suggest_actions(emotions, causes)
        return ChatReply(text=text, source=f"openai:{model}", emotions=emotions, causes=causes, actions=actions)
    except Exception:
        return None


def chat_reply(message: str) -> ChatReply:
    history = load_recent_dialog(limit=12)
    online = try_openai_reply(message, history)
    if online:
        return online
    return local_calm_reply(message)


def chat_insights(limit: int = 40) -> dict[str, Any]:
    rows = [m for m in load_chat(limit=limit) if m["role"] == "user"]
    merged = " ".join(m["content"] for m in rows)
    emotions = detect_emotions(merged)
    causes = detect_causes(merged)
    actions = suggest_actions(emotions, causes)
    return {"emotions": emotions, "causes": causes, "actions": actions, "sampleSize": len(rows)}


class Handler(BaseHTTPRequestHandler):
    server_version = "MoodTracker/0.2"

    def log_message(self, fmt: str, *args: Any) -> None:
        return

    def _json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _serve_file(self, rel_path: str) -> None:
        target = (WEB_DIR / rel_path.lstrip("/")).resolve()
        if not str(target).startswith(str(WEB_DIR.resolve())):
            self.send_error(HTTPStatus.FORBIDDEN)
            return
        if not target.exists() or not target.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        content_type = "text/plain; charset=utf-8"
        if target.suffix == ".html":
            content_type = "text/html; charset=utf-8"
        elif target.suffix == ".css":
            content_type = "text/css; charset=utf-8"
        elif target.suffix == ".js":
            content_type = "application/javascript; charset=utf-8"
        elif target.suffix == ".png":
            content_type = "image/png"
        elif target.suffix == ".jpg" or target.suffix == ".jpeg":
            content_type = "image/jpeg"
        elif target.suffix == ".ico":
            content_type = "image/x-icon"

        data = target.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if path == "/api/health":
            self._json(200, {"ok": True, "time": now_iso()})
            return

        if path == "/api/entries":
            date_from = query.get("from", [None])[0]
            date_to = query.get("to", [None])[0]
            self._json(200, {"entries": load_entries(date_from, date_to)})
            return

        if path == "/api/entry":
            date = query.get("date", [""])[0]
            if not date:
                self._json(400, {"error": "date query required"})
                return
            items = [e for e in load_entries(date, date) if e["date"] == date]
            self._json(200, {"entry": items[0] if items else None})
            return

        if path == "/api/summary":
            self._json(200, summary_payload())
            return

        if path == "/api/chat/history":
            self._json(200, {"messages": load_chat()})
            return

        if path == "/api/chat/insights":
            self._json(200, chat_insights())
            return

        if path == "/" or path == "":
            self._serve_file("index.html")
            return

        self._serve_file(path)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path

        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length > 0 else b"{}"
        try:
            payload = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            self._json(400, {"error": "invalid json"})
            return

        if path == "/api/entry":
            try:
                saved = save_entry(payload)
                self._json(200, {"ok": True, "entry": saved})
            except ValueError as exc:
                self._json(400, {"error": str(exc)})
            return

        if path == "/api/chat":
            msg = (payload.get("message") or "").strip()
            if not msg:
                self._json(400, {"error": "message required"})
                return
            save_chat("user", msg)
            reply = chat_reply(msg)
            save_chat("assistant", reply.text)
            self._json(
                200,
                {
                    "ok": True,
                    "reply": reply.text,
                    "source": reply.source,
                    "analysis": {
                        "emotions": reply.emotions,
                        "causes": reply.causes,
                        "actions": reply.actions,
                    },
                },
            )
            return

        self._json(404, {"error": "not found"})


def main() -> None:
    ensure_db()
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"MoodTracker server running: http://{HOST}:{PORT}")
    print(f"DB: {DB_PATH}")
    server.serve_forever()


if __name__ == "__main__":
    main()
