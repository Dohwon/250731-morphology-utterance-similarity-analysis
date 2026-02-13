#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox
from tkinter import font as tkfont
from urllib.error import URLError
from urllib.request import Request, urlopen
import webbrowser

BASE_DIR = Path(__file__).resolve().parent
SETTINGS_PATH = BASE_DIR / "data" / "widget_settings.json"
API_BASE = os.getenv("MOOD_API_BASE", "http://127.0.0.1:8765")
ADMIN_URL = os.getenv("MOOD_ADMIN_URL", "http://127.0.0.1:8765")

MOODS = [
    ("great", "최고", "😁"),
    ("good", "좋음", "🙂"),
    ("okay", "보통", "😐"),
    ("down", "가라앉음", "😔"),
    ("bad", "나쁨", "😣"),
]


def pick_kr_font(size: int, weight: str = "normal") -> tuple[str, int, str]:
    candidates = [
        "Malgun Gothic",
        "맑은 고딕",
        "Noto Sans CJK KR",
        "Noto Sans KR",
        "NanumGothic",
        "Apple SD Gothic Neo",
        "Arial",
    ]
    available = set(tkfont.families())
    for family in candidates:
        if family in available:
            return (family, size, weight)
    return ("TkDefaultFont", size, weight)


class WidgetApp:
    def __init__(self, root: tk.Tk, *, debug_visible: bool = False, reset_position: bool = False):
        self.root = root
        self.debug_visible = debug_visible
        self.root.title("Mood Floating")
        self.root.overrideredirect(not debug_visible)
        self.root.attributes("-topmost", True)
        self.root.geometry("88x88+120+120")
        self.root.configure(bg="#111827")

        self.drag_x = 0
        self.drag_y = 0
        self.dragging = False
        self.pending_single_click: str | None = None

        self.icon_image: tk.PhotoImage | None = None
        self.quick_window: tk.Toplevel | None = None
        self.chat_window: tk.Toplevel | None = None
        self.chat_input: tk.Entry | None = None
        self.chat_log: tk.Text | None = None
        self.selected_mood_id: str | None = None

        self.base_font = pick_kr_font(10, "normal")
        self.bold_font = pick_kr_font(10, "bold")
        self.title_font = pick_kr_font(11, "bold")

        self.frame = tk.Frame(root, bg="#111827", bd=0, highlightthickness=0)
        self.frame.pack(fill=tk.BOTH, expand=True)

        self.icon_btn = tk.Button(
            self.frame,
            text="🙂",
            font=pick_kr_font(26),
            bg="#1f2937",
            fg="#f9fafb",
            activebackground="#334155",
            activeforeground="#f9fafb",
            bd=0,
            relief=tk.FLAT,
            highlightthickness=0,
            cursor="hand2",
        )
        self.icon_btn.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        self.icon_btn.bind("<ButtonPress-1>", self.on_press)
        self.icon_btn.bind("<B1-Motion>", self.on_drag)
        self.icon_btn.bind("<ButtonRelease-1>", self.on_release)
        self.icon_btn.bind("<Double-Button-1>", self.on_double_click)
        self.icon_btn.bind("<Button-3>", self.show_menu)

        self.menu = tk.Menu(self.root, tearoff=0)
        self.menu.add_command(label="관리화면 열기", command=lambda: webbrowser.open(ADMIN_URL))
        self.menu.add_command(label="아이콘 변경(PNG)", command=self.pick_icon)
        self.menu.add_command(label="위치 초기화", command=self.reset_widget_position)
        self.menu.add_command(label="숨기기(작업표시줄)", command=self.root.iconify)
        self.menu.add_separator()
        self.menu.add_command(label="종료", command=self.root.destroy)

        self.load_settings(reset_position=reset_position)
        self.root.after(120, self.force_show)

    def settings(self) -> dict:
        if SETTINGS_PATH.exists():
            try:
                return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    def save_settings(self, data: dict) -> None:
        SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        SETTINGS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def load_settings(self, *, reset_position: bool = False) -> None:
        s = self.settings()
        x = 120 if reset_position else int(s.get("x", 120))
        y = 120 if reset_position else int(s.get("y", 120))
        self.root.update_idletasks()
        sw = max(self.root.winfo_screenwidth(), 300)
        sh = max(self.root.winfo_screenheight(), 300)
        if x < 0 or x > sw - 88:
            x = 120
        if y < 0 or y > sh - 88:
            y = 120
        self.root.geometry(f"88x88+{x}+{y}")
        icon_path = s.get("iconPath")
        if icon_path and Path(icon_path).exists():
            self.apply_icon(icon_path)

    def force_show(self) -> None:
        self.root.deiconify()
        self.root.lift()
        if self.debug_visible:
            self.root.focus_force()
        self.root.attributes("-topmost", True)

    def reset_widget_position(self) -> None:
        self.root.geometry("88x88+120+120")
        s = self.settings()
        s["x"] = 120
        s["y"] = 120
        self.save_settings(s)

    def apply_icon(self, path: str) -> None:
        try:
            self.icon_image = tk.PhotoImage(file=path)
            self.icon_btn.configure(image=self.icon_image, text="")
        except Exception:
            messagebox.showwarning("아이콘", "PNG 아이콘만 지원됩니다.")

    def pick_icon(self) -> None:
        path = filedialog.askopenfilename(title="아이콘 PNG 선택", filetypes=[("PNG", "*.png")])
        if not path:
            return
        self.apply_icon(path)
        s = self.settings()
        s["iconPath"] = path
        self.save_settings(s)

    def on_press(self, event: tk.Event) -> None:
        self.drag_x = event.x
        self.drag_y = event.y
        self.dragging = False

    def on_drag(self, event: tk.Event) -> None:
        self.dragging = True
        self.cancel_single_click()
        x = self.root.winfo_x() + event.x - self.drag_x
        y = self.root.winfo_y() + event.y - self.drag_y
        self.root.geometry(f"+{x}+{y}")

    def on_release(self, _event: tk.Event) -> None:
        if self.dragging:
            s = self.settings()
            s["x"] = self.root.winfo_x()
            s["y"] = self.root.winfo_y()
            self.save_settings(s)
            self.dragging = False
            return
        self.cancel_single_click()
        self.pending_single_click = self.root.after(220, self.open_quick_entry)

    def on_double_click(self, _event: tk.Event) -> None:
        self.cancel_single_click()
        webbrowser.open(ADMIN_URL)

    def cancel_single_click(self) -> None:
        if self.pending_single_click:
            try:
                self.root.after_cancel(self.pending_single_click)
            except Exception:
                pass
            self.pending_single_click = None

    def show_menu(self, event: tk.Event) -> None:
        self.menu.tk_popup(event.x_root, event.y_root)

    def post_json(self, endpoint: str, payload: dict) -> dict:
        req = Request(
            f"{API_BASE}{endpoint}",
            method="POST",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urlopen(req, timeout=12) as resp:
            raw = resp.read().decode("utf-8")
            if resp.status != 200:
                raise RuntimeError(f"status={resp.status}")
            return json.loads(raw)

    def post_entry(self, mood_id: str) -> None:
        payload = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "moodId": mood_id,
            "comment": "",
        }
        self.post_json("/api/entry", payload)

    def post_chat(self, message: str) -> dict:
        return self.post_json("/api/chat", {"message": message})

    def open_quick_entry(self) -> None:
        self.pending_single_click = None
        if self.quick_window and self.quick_window.winfo_exists():
            self.quick_window.lift()
            self.quick_window.focus_force()
            return

        w = tk.Toplevel(self.root)
        self.quick_window = w
        w.title("빠른 기분 체크")
        w.geometry("360x210")
        w.configure(bg="#f8fafc")
        w.attributes("-topmost", True)
        w.resizable(False, False)
        w.protocol("WM_DELETE_WINDOW", self.close_quick_window)

        tk.Label(
            w,
            text="지금 기분 하나만 선택해 주세요",
            bg="#f8fafc",
            fg="#111827",
            font=self.title_font,
        ).pack(pady=(12, 8))

        mood_frame = tk.Frame(w, bg="#f8fafc")
        mood_frame.pack(pady=(0, 10))

        selected = tk.StringVar(value="")
        status = tk.Label(w, text="", bg="#f8fafc", fg="#047857", font=self.base_font)
        status.pack(pady=(0, 6))

        def select_mood(mid: str) -> None:
            selected.set(mid)
            self.selected_mood_id = mid
            status.config(text=f"선택됨: {next((m[1] for m in MOODS if m[0] == mid), mid)}")

        for mood_id, label, emoji in MOODS:
            card = tk.Button(
                mood_frame,
                text=f"{emoji}\n{label}",
                justify=tk.CENTER,
                width=6,
                height=3,
                bg="#ffffff",
                fg="#111827",
                activebackground="#e2e8f0",
                bd=1,
                relief=tk.SOLID,
                font=self.base_font,
                command=lambda mid=mood_id: select_mood(mid),
            )
            card.pack(side=tk.LEFT, padx=4)

        action = tk.Frame(w, bg="#f8fafc")
        action.pack(pady=(6, 8))

        def save_only() -> None:
            mood_id = selected.get()
            if not mood_id:
                status.config(text="기분을 먼저 선택해 주세요.", fg="#b45309")
                return
            try:
                self.post_entry(mood_id)
                status.config(text="저장 완료", fg="#047857")
            except URLError:
                status.config(text="서버 연결 실패 (start_server.sh 확인)", fg="#b45309")

        def save_and_open_chat() -> None:
            mood_id = selected.get()
            if not mood_id:
                status.config(text="기분을 먼저 선택해 주세요.", fg="#b45309")
                return
            try:
                self.post_entry(mood_id)
                status.config(text="저장 완료 - 채팅창 열기", fg="#047857")
                self.open_chat_window()
            except URLError:
                status.config(text="서버 연결 실패 (start_server.sh 확인)", fg="#b45309")

        tk.Button(
            action,
            text="저장",
            command=save_only,
            bg="#1d4ed8",
            fg="#ffffff",
            activebackground="#1e40af",
            activeforeground="#ffffff",
            bd=0,
            padx=12,
            pady=6,
            font=self.bold_font,
        ).pack(side=tk.LEFT, padx=4)

        tk.Button(
            action,
            text="저장 후 채팅",
            command=save_and_open_chat,
            bg="#0f766e",
            fg="#ffffff",
            activebackground="#115e59",
            activeforeground="#ffffff",
            bd=0,
            padx=12,
            pady=6,
            font=self.bold_font,
        ).pack(side=tk.LEFT, padx=4)

    def close_quick_window(self) -> None:
        if self.quick_window and self.quick_window.winfo_exists():
            self.quick_window.destroy()
        self.quick_window = None

    def open_chat_window(self) -> None:
        if self.chat_window and self.chat_window.winfo_exists():
            self.chat_window.lift()
            self.chat_window.focus_force()
            return

        w = tk.Toplevel(self.root)
        self.chat_window = w
        w.title("Calm Bot")
        w.geometry("420x420")
        w.configure(bg="#f8fafc")
        w.attributes("-topmost", True)
        w.protocol("WM_DELETE_WINDOW", self.close_chat_window)

        tk.Label(
            w,
            text="일상 대화 중 감정 신호를 함께 정리해드려요",
            bg="#f8fafc",
            fg="#111827",
            font=self.bold_font,
        ).pack(anchor="w", padx=12, pady=(10, 4))

        log = tk.Text(w, height=16, wrap="word", bg="#ffffff", fg="#111827", font=self.base_font)
        log.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 8))
        log.insert("end", "봇: 안녕하세요. 지금 가장 마음에 걸리는 한 가지를 말해 주세요.\n")
        log.configure(state=tk.DISABLED)
        self.chat_log = log

        bottom = tk.Frame(w, bg="#f8fafc")
        bottom.pack(fill=tk.X, padx=12, pady=(0, 12))

        entry = tk.Entry(bottom, font=self.base_font)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        self.chat_input = entry

        def send() -> None:
            if not self.chat_input or not self.chat_log:
                return
            msg = self.chat_input.get().strip()
            if not msg:
                return
            self.chat_input.delete(0, tk.END)
            self.append_chat("나", msg)
            try:
                resp = self.post_chat(msg)
                reply = resp.get("reply", "답변을 가져오지 못했습니다.")
                source = resp.get("source", "unknown")
                self.append_chat("봇", f"{reply}\n(모델: {source})")
                analysis = resp.get("analysis") or {}
                emotions = ", ".join(analysis.get("emotions", []))
                causes = ", ".join(analysis.get("causes", []))
                actions = analysis.get("actions", [])
                lines = []
                if emotions:
                    lines.append(f"감정: {emotions}")
                if causes:
                    lines.append(f"원인: {causes}")
                if actions:
                    lines.append("권장 행동: " + " / ".join(actions[:2]))
                if lines:
                    self.append_chat("분석", " | ".join(lines))
            except URLError:
                self.append_chat("봇", "서버 연결 실패입니다. server.py가 실행 중인지 확인해 주세요.")

        tk.Button(
            bottom,
            text="전송",
            command=send,
            bg="#1d4ed8",
            fg="#ffffff",
            activebackground="#1e40af",
            activeforeground="#ffffff",
            bd=0,
            padx=10,
            pady=6,
            font=self.bold_font,
        ).pack(side=tk.LEFT)

        w.bind("<Return>", lambda _e: send())

    def append_chat(self, speaker: str, message: str) -> None:
        if not self.chat_log:
            return
        self.chat_log.configure(state=tk.NORMAL)
        self.chat_log.insert("end", f"{speaker}: {message}\n")
        self.chat_log.see("end")
        self.chat_log.configure(state=tk.DISABLED)

    def close_chat_window(self) -> None:
        if self.chat_window and self.chat_window.winfo_exists():
            self.chat_window.destroy()
        self.chat_window = None
        self.chat_log = None
        self.chat_input = None


def main() -> None:
    parser = argparse.ArgumentParser(description="Mood tracker floating widget")
    parser.add_argument("--debug-visible", action="store_true", help="Show bordered window for visibility debugging")
    parser.add_argument("--reset-position", action="store_true", help="Reset widget position to default (120,120)")
    args = parser.parse_args()

    root = tk.Tk()
    _app = WidgetApp(root, debug_visible=args.debug_visible, reset_position=args.reset_position)
    root.mainloop()


if __name__ == "__main__":
    main()
