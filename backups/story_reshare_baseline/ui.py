from __future__ import annotations

import json
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, scrolledtext, simpledialog, ttk

from .client import InstagramStoryReshareClient


class InstagramStoryReshareApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Instagram Story Reshare")
        self.geometry("980x760")
        self.minsize(860, 680)

        default_session_path = InstagramStoryReshareClient._resolve_session_path("sessions/instagram_session.json")
        self.session_path_var = tk.StringVar(value=str(default_session_path))
        self.username_var = tk.StringVar()
        self.password_var = tk.StringVar()
        self.sessionid_var = tk.StringVar()
        self.story_identifier_var = tk.StringVar()
        self.mention_original_var = tk.BooleanVar(value=True)
        self.use_default_payload_var = tk.BooleanVar(value=True)

        self._build_layout()

    def _build_layout(self) -> None:
        container = ttk.Frame(self)
        container.pack(fill="both", expand=True)
        container.columnconfigure(0, weight=1)
        container.rowconfigure(0, weight=1)

        canvas = tk.Canvas(container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        root = ttk.Frame(canvas, padding=16)
        root.columnconfigure(0, weight=1)
        root.rowconfigure(4, weight=1)

        window_id = canvas.create_window((0, 0), window=root, anchor="nw")

        def on_frame_configure(_event=None) -> None:
            canvas.configure(scrollregion=canvas.bbox("all"))

        def on_canvas_configure(event) -> None:
            canvas.itemconfigure(window_id, width=event.width)

        root.bind("<Configure>", on_frame_configure)
        canvas.bind("<Configure>", on_canvas_configure)

        def _on_mousewheel(event) -> None:
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        auth = ttk.LabelFrame(root, text="Autenticación", padding=12)
        auth.grid(row=0, column=0, sticky="ew")
        auth.columnconfigure(1, weight=1)

        ttk.Label(auth, text="Session file").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=4)
        ttk.Entry(auth, textvariable=self.session_path_var).grid(row=0, column=1, sticky="ew", pady=4)

        ttk.Label(auth, text="Username").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=4)
        ttk.Entry(auth, textvariable=self.username_var).grid(row=1, column=1, sticky="ew", pady=4)

        ttk.Label(auth, text="Password").grid(row=2, column=0, sticky="w", padx=(0, 8), pady=4)
        ttk.Entry(auth, textvariable=self.password_var, show="*").grid(row=2, column=1, sticky="ew", pady=4)

        ttk.Label(auth, text="Sessionid").grid(row=3, column=0, sticky="w", padx=(0, 8), pady=4)
        ttk.Entry(auth, textvariable=self.sessionid_var).grid(row=3, column=1, sticky="ew", pady=4)

        story = ttk.LabelFrame(root, text="Historia", padding=12)
        story.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        story.columnconfigure(1, weight=1)

        ttk.Label(story, text="Story URL o PK").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=4)
        ttk.Entry(story, textvariable=self.story_identifier_var).grid(row=0, column=1, sticky="ew", pady=4)

        ttk.Checkbutton(
            story,
            text="Mencionar al autor original en la nueva story",
            variable=self.mention_original_var,
        ).grid(row=1, column=1, sticky="w", pady=4)

        extra = ttk.LabelFrame(root, text="Payload", padding=12)
        extra.grid(row=2, column=0, sticky="nsew", pady=(12, 0))
        extra.columnconfigure(0, weight=1)
        extra.rowconfigure(1, weight=1)

        ttk.Checkbutton(
            extra,
            text="Usar payload por defecto según tipo de media",
            variable=self.use_default_payload_var,
        ).grid(row=0, column=0, sticky="w", pady=(0, 8))

        self.extra_json = scrolledtext.ScrolledText(extra, height=8, wrap="word")
        self.extra_json.insert("1.0", '{\n  "source_type": "4"\n}\n')
        self.extra_json.grid(row=1, column=0, sticky="nsew")

        buttons = ttk.Frame(root)
        buttons.grid(row=3, column=0, sticky="ew", pady=(12, 0))
        buttons.columnconfigure(4, weight=1)

        ttk.Button(buttons, text="Info de sesión", command=self.show_session_info).grid(row=0, column=0, padx=(0, 8))
        ttk.Button(buttons, text="Inspeccionar story", command=self.inspect_story).grid(row=0, column=1, padx=(0, 8))
        ttk.Button(buttons, text="Compartir story", command=self.share_story).grid(row=0, column=2, padx=(0, 8))
        ttk.Button(buttons, text="Ejecutar todo", command=self.run_all).grid(row=0, column=3, padx=(0, 8))

        output_frame = ttk.LabelFrame(root, text="Salida", padding=12)
        output_frame.grid(row=4, column=0, sticky="nsew", pady=(12, 0))
        output_frame.columnconfigure(0, weight=1)
        output_frame.rowconfigure(0, weight=1)

        self.output = scrolledtext.ScrolledText(output_frame, wrap="word", height=18)
        self.output.grid(row=0, column=0, sticky="nsew")

    def _append_output(self, title: str, payload: object) -> None:
        self.output.insert("end", f"{title}\n")
        if isinstance(payload, str):
            self.output.insert("end", payload)
        else:
            self.output.insert("end", json.dumps(payload, indent=2, ensure_ascii=False))
        self.output.insert("end", "\n\n")
        self.output.see("end")

    def _clear_output(self) -> None:
        self.output.delete("1.0", "end")

    def _make_client(self) -> InstagramStoryReshareClient:
        return InstagramStoryReshareClient(
            session_path=self.session_path_var.get().strip(),
            logger=lambda msg: self.after(0, self._append_output, "Log", msg),
        )

    def _run_task(self, title: str, task) -> None:
        self._clear_output()

        def worker() -> None:
            try:
                result = task()
                self.after(0, self._append_output, title, result)
            except Exception as exc:
                self.after(0, self._append_output, "Error", str(exc))
                self.after(0, messagebox.showerror, "Instagram Story Reshare", str(exc))

        threading.Thread(target=worker, daemon=True).start()

    def _run_pipeline(self, title: str, task) -> None:
        self._clear_output()

        def worker() -> None:
            try:
                result = task()
                if result is not None:
                    self.after(0, self._append_output, title, result)
            except Exception as exc:
                self.after(0, self._append_output, "Error", str(exc))
                self.after(0, messagebox.showerror, "Instagram Story Reshare", str(exc))

        threading.Thread(target=worker, daemon=True).start()

    def _login(self, client: InstagramStoryReshareClient) -> None:
        def prompt(label: str) -> str:
            answer = simpledialog.askstring("Instagram verification", f"Ingresá {label}", parent=self)
            return (answer or "").strip()

        client.login(
            username=self.username_var.get().strip() or None,
            password=self.password_var.get() or None,
            sessionid=self.sessionid_var.get().strip() or None,
            verification_code_handler=prompt,
        )

    def inspect_story(self) -> None:
        def task():
            client = self._make_client()
            self._login(client)
            return client.inspect_story(self.story_identifier_var.get().strip())

        self._run_task("Story metadata", task)

    def share_story(self) -> None:
        def task():
            client = self._make_client()
            self._login(client)
            story_metadata = client.inspect_story(self.story_identifier_var.get().strip())
            self.after(0, self._append_output, "Story metadata", story_metadata)
            extra = self._resolve_payload(client, story_metadata["media_type"])
            result = client.repost_story(
                self.story_identifier_var.get().strip(),
                mention_original_author=self.mention_original_var.get(),
                extra_story_config=extra,
            )
            return result.to_dict()

        self._run_task("Share result", task)

    def show_session_info(self) -> None:
        def task():
            client = self._make_client()
            self._login(client)
            return client.export_runtime_metadata()

        self._run_task("Session info", task)

    def run_all(self) -> None:
        def task():
            client = self._make_client()
            self._login(client)
            session_info = client.export_runtime_metadata()
            self.after(0, self._append_output, "Session info", session_info)

            story_metadata = client.inspect_story(self.story_identifier_var.get().strip())
            self.after(0, self._append_output, "Story metadata", story_metadata)

            extra = self._resolve_payload(client, story_metadata["media_type"])
            result = client.repost_story(
                self.story_identifier_var.get().strip(),
                mention_original_author=self.mention_original_var.get(),
                extra_story_config=extra,
            )
            self.after(0, self._append_output, "Share result", result.to_dict())
            return None

        self._run_pipeline("Run all", task)

    def _resolve_payload(self, client: InstagramStoryReshareClient, media_type: int) -> dict:
        payload = client.parse_extra_story_config(self.extra_json.get("1.0", "end"))
        if self.use_default_payload_var.get():
            default_payload = client.default_story_payload_for_media(media_type)
            payload = self._deep_merge(default_payload, payload)
            self.after(0, self._append_output, "Payload usado", payload)
        return payload

    def _deep_merge(self, base: dict, override: dict) -> dict:
        merged = dict(base)
        for key, value in override.items():
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key] = self._deep_merge(merged[key], value)
            else:
                merged[key] = value
        return merged


def main() -> None:
    app = InstagramStoryReshareApp()
    app.mainloop()


if __name__ == "__main__":
    main()
