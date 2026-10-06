import tkinter as tk
from tkinter import scrolledtext, simpledialog, messagebox
import threading
import io
import wave
import time
import numpy as np
import sounddevice as sd
import speech_recognition as sr
import platform
import random
import math
from datetime import datetime


from ai import ask_ai

from history import (
    current_session_id,
    create_session,
    list_sessions,
    switch_session,
    rename_session,
    delete_session,
    get_messages,
    clear_current,
)

from memory import (
    load_memory,
    clear_memory,
)

from voice import voice_engine


# ============================================================
# ARIA // COMMAND CENTER
# HOLOGRAPHIC EDITION
# ============================================================

BG = "#05070A"
BG2 = "#080B10"
PANEL = "#0C1016"
PANEL2 = "#10151D"
PANEL3 = "#141A22"

BLACK = "#020305"

GOLD = "#D6B477"
GOLD_LIGHT = "#F2D7A0"
GOLD_DIM = "#80663D"

BURGUNDY = "#5A1632"
BURGUNDY_LIGHT = "#9B3B60"
BURGUNDY_DIM = "#35101F"

WHITE = "#F5F1E9"
TEXT = "#D9D4CC"
MUTED = "#777D87"
DIM = "#444A54"

GREEN = "#72D7A0"
RED = "#D76F79"
CYAN = "#6EC7D8"

GRID = "#0C1219"
LINE = "#202732"
LINE2 = "#303744"


# ============================================================
# HELPER
# ============================================================

def hover(widget, normal, active):

    def enter(_):
        try:
            widget.configure(bg=active)
        except Exception:
            pass

    def leave(_):
        try:
            widget.configure(bg=normal)
        except Exception:
            pass

    widget.bind("<Enter>", enter)
    widget.bind("<Leave>", leave)


# ============================================================
# ARIA APP
# ============================================================

class ARIAApp:

    def __init__(self, root):

        self.root = root

        self.root.title("ARIA // COMMAND CENTER")
        self.root.geometry("1500x900")
        self.root.minsize(1150, 720)
        self.root.configure(bg=BG)

        # ----------------------------------------------------
        # SESSION
        # ----------------------------------------------------

        self.current_sid = current_session_id()

        # ----------------------------------------------------
        # VOICE
        # ----------------------------------------------------

        self.voice_enabled = True
        self.voice_mode = False
        self.voice_listening = False
        self.voice_language = "tr-TR"
        self.voice_stop_event = threading.Event()
        self._voice_turn_done = False

        # ----------------------------------------------------
        # UI STATE
        # ----------------------------------------------------

        self.mode = "command"
        self.aria_status = "SYSTEM READY"

        # ----------------------------------------------------
        # ANIMATION STATE
        # ----------------------------------------------------

        self.angle_outer = 0
        self.angle_inner = 0
        self.phase = 0
        self.scan_y = 0

        self.particles = []

        self.wave_phase = 0

        self.pulse = 0

        self.init_particles()

        # ----------------------------------------------------
        # BUILD
        # ----------------------------------------------------

        self.build_ui()

        self.refresh_history()
        self.load_current_chat()

        # ----------------------------------------------------
        # ANIMATION LOOPS
        # ----------------------------------------------------

        self.root.after(500, self.startup_voice_test)

        self.root.after(
            40,
            self.animation_loop
        )

        self.root.after(
            1000,
            self.refresh_clock
        )

        self.root.after(
            2000,
            self.refresh_telemetry
        )

    # ========================================================
    # VOICE
    # ========================================================

    def speak(self, text):

        if not self.voice_enabled or not text:
            return

        def on_start():
            self.root.after(0, lambda: self.set_status("SPEAKING"))

        def on_end():
            self.root.after(0, lambda: self.set_status("SYSTEM READY"))

        voice_engine.speak(
            text,
            on_start=on_start,
            on_end=on_end
        )

    def startup_voice_test(self):

        self.speak(
            "ARIA ses sistemi aktif."
        )

    def toggle_voice_mode(self):

        if self.voice_mode:
            self.stop_voice_mode()
            return

        self.voice_mode = True
        self.voice_stop_event.clear()
        self.voice_mode_button.configure(text="VOICE MODE  ●", fg=GOLD_LIGHT)
        self.set_status("LISTENING")
        self.speak("Sesli sohbet modu aktif.")
        threading.Thread(target=self.voice_loop, daemon=True).start()

    def stop_voice_mode(self):

        self.voice_mode = False
        self.voice_stop_event.set()
        self.voice_listening = False

        try:
            voice_engine.stop()
        except Exception:
            pass

        self.voice_mode_button.configure(text="VOICE MODE  ○", fg=MUTED)
        self.set_status("SYSTEM READY")

    def _record_until_silence(self, samplerate=16000, max_seconds=12, silence_seconds=0.85):

        chunk = 1024
        threshold = 0.025
        pre_roll = []
        frames = []
        started = False
        silent_for = 0.0
        elapsed = 0.0

        def callback(indata, frames_count, time_info, status):
            if status:
                pass
            frames.append(indata.copy())

        with sd.InputStream(samplerate=samplerate, channels=1, dtype="float32",
                            blocksize=chunk, callback=callback):
            while elapsed < max_seconds and not self.voice_stop_event.is_set():
                time.sleep(chunk / samplerate)
                elapsed += chunk / samplerate

                if not frames:
                    continue

                data = frames[-1]
                rms = float(np.sqrt(np.mean(np.square(data))))

                if not started:
                    pre_roll.append(data)
                    pre_roll = pre_roll[-8:]
                    if rms > threshold:
                        started = True
                        frames = pre_roll[:] + frames[-1:]
                        silent_for = 0.0
                else:
                    if rms < threshold:
                        silent_for += chunk / samplerate
                    else:
                        silent_for = 0.0

                    if silent_for >= silence_seconds:
                        break

        if not started or not frames:
            return None

        audio = np.concatenate(frames, axis=0)
        audio = np.clip(audio, -1.0, 1.0)
        pcm = (audio * 32767).astype(np.int16).tobytes()

        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(samplerate)
            wf.writeframes(pcm)

        return buffer.getvalue()

    def _transcribe_audio(self, wav_bytes):

        recognizer = sr.Recognizer()
        audio = sr.AudioData(wav_bytes, 16000, 2)

        try:
            return recognizer.recognize_google(
                audio,
                language=self.voice_language
            ).strip()
        except sr.UnknownValueError:
            return ""
        except sr.RequestError as exc:
            raise RuntimeError(f"Speech recognition bağlantısı başarısız: {exc}")

    def voice_loop(self):

        while self.voice_mode and not self.voice_stop_event.is_set():

            try:
                self.voice_listening = True
                self.root.after(0, lambda: self.set_status("LISTENING"))

                wav_bytes = self._record_until_silence()
                self.voice_listening = False

                if not self.voice_mode or self.voice_stop_event.is_set():
                    break

                if not wav_bytes:
                    continue

                self.root.after(0, lambda: self.set_status("TRANSCRIBING"))
                text = self._transcribe_audio(wav_bytes)

                if not text:
                    continue

                self.root.after(0, lambda t=text: self.handle_voice_text(t))

                # Wait until the AI response finishes before listening again.
                while self.voice_mode and not self.voice_stop_event.is_set():
                    if not self.root.winfo_exists():
                        return
                    time.sleep(0.15)
                    # handle_voice_text toggles this event for each turn.
                    if getattr(self, "_voice_turn_done", False):
                        self._voice_turn_done = False
                        break

            except Exception as exc:
                self.voice_listening = False
                self.root.after(0, lambda e=str(exc): self.set_status("VOICE ERROR"))
                self.root.after(0, lambda e=str(exc): messagebox.showerror("ARIA Voice Mode", e))
                self.voice_mode = False
                self.voice_stop_event.set()
                break

        self.root.after(0, lambda: self.voice_mode_button.configure(text="VOICE MODE  ○", fg=MUTED))

    def handle_voice_text(self, text):

        self.add_message("user", text)
        self.set_status("THINKING")
        threading.Thread(target=self.get_voice_ai_response, args=(text,), daemon=True).start()

    def get_voice_ai_response(self, text):

        try:
            response = ask_ai(text)
        except Exception as exc:
            response = f"Bir hata oluştu:\n{exc}"

        self.root.after(0, lambda r=response: self.show_voice_response(r))

    def show_voice_response(self, response):

        self.add_message("assistant", response)
        self.set_status("SPEAKING")

        def on_start():
            self.root.after(0, lambda: self.set_status("SPEAKING"))

        def on_end():
            self.root.after(0, lambda: self.set_status("LISTENING" if self.voice_mode else "SYSTEM READY"))
            self._voice_turn_done = True

        voice_engine.speak(response, on_start=on_start, on_end=on_end)

    def toggle_voice(self):

        self.voice_enabled = not self.voice_enabled
        voice_engine.set_enabled(self.voice_enabled)

        if self.voice_enabled:

            self.voice_button.configure(
                text="VOICE  ●",
                fg=GOLD_LIGHT
            )

            self.speak(
                "Sesli yanıt aktif."
            )

        else:

            self.voice_button.configure(
                text="VOICE  ○",
                fg=MUTED
            )

            try:
                voice_engine.stop()
            except Exception:
                pass

            self.set_status(
                "VOICE OFF"
            )

    # ========================================================
    # MAIN UI
    # ========================================================

    def build_ui(self):

        self.root.bind(
            "<Escape>",
            lambda e: self.show_command_center()
        )

        self.root.bind(
            "<Control-n>",
            lambda e: self.new_chat()
        )

        # ====================================================
        # ROOT
        # ====================================================

        self.main = tk.Frame(
            self.root,
            bg=BG
        )

        self.main.pack(
            fill="both",
            expand=True
        )

        # Luxury top line

        tk.Frame(
            self.main,
            bg=GOLD,
            height=2
        ).pack(
            fill="x"
        )

        # ====================================================
        # HEADER
        # ====================================================

        self.header = tk.Frame(
            self.main,
            bg=BG,
            height=70
        )

        self.header.pack(
            fill="x"
        )

        self.header.pack_propagate(False)

        # Brand

        brand = tk.Frame(
            self.header,
            bg=BG
        )

        brand.pack(
            side="left",
            padx=30
        )

        tk.Label(
            brand,
            text="ARIA",
            font=("Segoe UI", 23, "bold"),
            bg=BG,
            fg=WHITE
        ).pack(
            side="left"
        )

        tk.Label(
            brand,
            text="  //  PERSONAL INTELLIGENCE",
            font=("Consolas", 7, "bold"),
            bg=BG,
            fg=GOLD
        ).pack(
            side="left",
            pady=(8, 0)
        )

        # Center status

        self.header_status = tk.Label(
            self.header,
            text="● SYSTEM ONLINE",
            font=("Consolas", 8, "bold"),
            bg=BG,
            fg=GREEN
        )

        self.header_status.place(
            relx=0.5,
            rely=0.5,
            anchor="center"
        )

        # Right

        header_right = tk.Frame(
            self.header,
            bg=BG
        )

        header_right.pack(
            side="right",
            padx=25
        )

        self.clock_label = tk.Label(
            header_right,
            text="00:00:00",
            font=("Consolas", 10, "bold"),
            bg=BG,
            fg=GOLD_LIGHT
        )

        self.clock_label.pack(
            side="left",
            padx=(0, 22)
        )

        self.voice_mode_button = tk.Button(
            header_right,
            text="VOICE MODE  ○",
            command=self.toggle_voice_mode,
            bg=BG,
            fg=MUTED,
            activebackground=BG,
            activeforeground=GOLD_LIGHT,
            relief="flat",
            bd=0,
            font=("Consolas", 8, "bold"),
            cursor="hand2"
        )

        self.voice_mode_button.pack(
            side="right",
            padx=(0, 16)
        )

        self.voice_button = tk.Button(
            header_right,
            text="VOICE  ●",
            command=self.toggle_voice,
            bg=BG,
            fg=GOLD_LIGHT,
            activebackground=BG,
            activeforeground=GOLD_LIGHT,
            relief="flat",
            bd=0,
            font=("Consolas", 8, "bold"),
            cursor="hand2"
        )

        self.voice_button.pack(
            side="right"
        )

        # ====================================================
        # BODY
        # ====================================================

        self.body = tk.Frame(
            self.main,
            bg=BG
        )

        self.body.pack(
            fill="both",
            expand=True,
            padx=16,
            pady=(0, 16)
        )

        # ====================================================
        # LEFT
        # ====================================================

        self.left = tk.Frame(
            self.body,
            bg=PANEL,
            width=245,
            highlightbackground=LINE,
            highlightthickness=1
        )

        self.left.pack(
            side="left",
            fill="y",
            padx=(0, 9)
        )

        self.left.pack_propagate(False)

        self.build_left()

        # ====================================================
        # CENTER
        # ====================================================

        self.center = tk.Frame(
            self.body,
            bg=BG
        )

        self.center.pack(
            side="left",
            fill="both",
            expand=True
        )

        self.build_center()

        # ====================================================
        # RIGHT
        # ====================================================

        self.right = tk.Frame(
            self.body,
            bg=PANEL,
            width=245,
            highlightbackground=LINE,
            highlightthickness=1
        )

        self.right.pack(
            side="right",
            fill="y",
            padx=(9, 0)
        )

        self.right.pack_propagate(False)

        self.build_right()

    # ========================================================
    # LEFT PANEL
    # ========================================================

    def build_left(self):

        tk.Label(
            self.left,
            text="SYSTEM NAVIGATION",
            font=("Consolas", 7, "bold"),
            bg=PANEL,
            fg=MUTED
        ).pack(
            anchor="w",
            padx=18,
            pady=(20, 12)
        )

        self.nav_button(
            "◈   COMMAND CENTER",
            self.show_command_center
        )

        self.nav_button(
            "▣   CONVERSATIONS",
            self.show_chat
        )

        self.nav_button(
            "◇   MEMORY CORE",
            self.show_memory
        )

        self.nav_button(
            "◌   SYSTEM",
            self.show_system
        )

        tk.Frame(
            self.left,
            bg=LINE,
            height=1
        ).pack(
            fill="x",
            padx=18,
            pady=18
        )

        self.new_chat_button = tk.Button(
            self.left,
            text="＋  NEW CONVERSATION",
            command=self.new_chat,
            bg=BURGUNDY,
            fg=WHITE,
            activebackground=BURGUNDY_LIGHT,
            activeforeground=WHITE,
            relief="flat",
            bd=0,
            font=("Consolas", 8, "bold"),
            cursor="hand2",
            pady=11
        )

        self.new_chat_button.pack(
            fill="x",
            padx=15
        )

        hover(
            self.new_chat_button,
            BURGUNDY,
            BURGUNDY_LIGHT
        )

        tk.Label(
            self.left,
            text="RECENT SESSIONS",
            font=("Consolas", 7, "bold"),
            bg=PANEL,
            fg=MUTED
        ).pack(
            anchor="w",
            padx=18,
            pady=(20, 8)
        )

        self.session_canvas = tk.Canvas(
            self.left,
            bg=PANEL,
            highlightthickness=0
        )

        self.session_canvas.pack(
            fill="both",
            expand=True,
            padx=8
        )

        self.session_frame = tk.Frame(
            self.session_canvas,
            bg=PANEL
        )

        self.session_window = self.session_canvas.create_window(
            0,
            0,
            window=self.session_frame,
            anchor="nw"
        )

        self.session_frame.bind(
            "<Configure>",
            lambda e:
            self.session_canvas.configure(
                scrollregion=self.session_canvas.bbox("all")
            )
        )

        self.session_canvas.bind(
            "<Configure>",
            lambda e:
            self.session_canvas.itemconfigure(
                self.session_window,
                width=e.width
            )
        )

        # Bottom

        bottom = tk.Frame(
            self.left,
            bg=PANEL
        )

        bottom.pack(
            fill="x",
            side="bottom",
            padx=15,
            pady=15
        )

        tk.Frame(
            bottom,
            bg=LINE,
            height=1
        ).pack(
            fill="x",
            pady=(0, 10)
        )

        settings = tk.Button(
            bottom,
            text="⚙   SETTINGS",
            command=self.show_settings,
            bg=PANEL,
            fg=MUTED,
            activebackground=PANEL2,
            activeforeground=GOLD,
            relief="flat",
            bd=0,
            font=("Consolas", 8),
            cursor="hand2"
        )

        settings.pack(
            anchor="w"
        )

    def nav_button(self, text, command):

        button = tk.Button(
            self.left,
            text=text,
            command=command,
            anchor="w",
            bg=PANEL,
            fg=TEXT,
            activebackground=PANEL2,
            activeforeground=GOLD_LIGHT,
            relief="flat",
            bd=0,
            font=("Consolas", 8, "bold"),
            cursor="hand2",
            padx=18,
            pady=10
        )

        button.pack(
            fill="x",
            padx=6,
            pady=1
        )

        return button

    # ========================================================
    # RIGHT TELEMETRY
    # ========================================================

    def build_right(self):

        tk.Label(
            self.right,
            text="LIVE TELEMETRY",
            font=("Consolas", 7, "bold"),
            bg=PANEL,
            fg=MUTED
        ).pack(
            anchor="w",
            padx=18,
            pady=(20, 15)
        )

        self.cpu_value = self.telemetry_card(
            "CPU",
            "PROCESSOR"
        )

        self.gpu_value = self.telemetry_card(
            "GPU",
            "GRAPHICS"
        )

        self.ram_value = self.telemetry_card(
            "RAM",
            "MEMORY"
        )

        self.net_value = self.telemetry_card(
            "NET",
            "NETWORK"
        )

        tk.Frame(
            self.right,
            bg=LINE,
            height=1
        ).pack(
            fill="x",
            padx=18,
            pady=18
        )

        tk.Label(
            self.right,
            text="ARIA CORE",
            font=("Consolas", 7, "bold"),
            bg=PANEL,
            fg=MUTED
        ).pack(
            anchor="w",
            padx=18
        )

        self.core_status = tk.Label(
            self.right,
            text="ONLINE",
            font=("Consolas", 16, "bold"),
            bg=PANEL,
            fg=GOLD_LIGHT
        )

        self.core_status.pack(
            anchor="w",
            padx=18,
            pady=(4, 2)
        )

        self.core_substatus = tk.Label(
            self.right,
            text="ALL SYSTEMS\nOPERATIONAL",
            font=("Consolas", 7),
            justify="left",
            bg=PANEL,
            fg=MUTED
        )

        self.core_substatus.pack(
            anchor="w",
            padx=18
        )

        tk.Frame(
            self.right,
            bg=LINE,
            height=1
        ).pack(
            fill="x",
            padx=18,
            pady=18
        )

        tk.Label(
            self.right,
            text="SECURITY",
            font=("Consolas", 7, "bold"),
            bg=PANEL,
            fg=MUTED
        ).pack(
            anchor="w",
            padx=18
        )

        tk.Label(
            self.right,
            text="● ENCRYPTED CHANNEL",
            font=("Consolas", 7),
            bg=PANEL,
            fg=GREEN
        ).pack(
            anchor="w",
            padx=18,
            pady=(6, 2)
        )

        tk.Label(
            self.right,
            text="● LOCAL MEMORY",
            font=("Consolas", 7),
            bg=PANEL,
            fg=GREEN
        ).pack(
            anchor="w",
            padx=18
        )

        tk.Frame(
            self.right,
            bg=LINE,
            height=1
        ).pack(
            fill="x",
            padx=18,
            pady=18
        )

        self.date_label = tk.Label(
            self.right,
            text="",
            font=("Consolas", 7),
            bg=PANEL,
            fg=MUTED,
            justify="left"
        )

        self.date_label.pack(
            anchor="w",
            padx=18
        )

    def telemetry_card(self, short, title):

        card = tk.Frame(
            self.right,
            bg=PANEL2,
            highlightbackground=LINE,
            highlightthickness=1
        )

        card.pack(
            fill="x",
            padx=13,
            pady=4
        )

        tk.Label(
            card,
            text=title,
            font=("Consolas", 6, "bold"),
            bg=PANEL2,
            fg=MUTED
        ).pack(
            anchor="w",
            padx=10,
            pady=(8, 0)
        )

        row = tk.Frame(
            card,
            bg=PANEL2
        )

        row.pack(
            fill="x",
            padx=10
        )

        value = tk.Label(
            row,
            text=f"{short}  00%",
            font=("Consolas", 9, "bold"),
            bg=PANEL2,
            fg=WHITE
        )

        value.pack(
            side="left"
        )

        tk.Label(
            row,
            text="● LIVE",
            font=("Consolas", 6),
            bg=PANEL2,
            fg=GREEN
        ).pack(
            side="right"
        )

        bar = tk.Canvas(
            card,
            height=4,
            bg=PANEL2,
            highlightthickness=0
        )

        bar.pack(
            fill="x",
            padx=10,
            pady=(5, 8)
        )

        bar.create_rectangle(
            0,
            0,
            100,
            4,
            fill=LINE2,
            outline=""
        )

        bar.create_rectangle(
            0,
            0,
            35,
            4,
            fill=GOLD,
            outline="",
            tags="value"
        )

        value.bar = bar

        return value

    # ========================================================
    # CENTER
    # ========================================================

    def build_center(self):

        self.center_header = tk.Frame(
            self.center,
            bg=BG,
            height=30
        )

        self.center_header.pack(
            fill="x"
        )

        self.center_title = tk.Label(
            self.center_header,
            text="ARIA // COMMAND CENTER",
            font=("Consolas", 7, "bold"),
            bg=BG,
            fg=MUTED
        )

        self.center_title.pack(
            anchor="w",
            padx=8
        )

        # Main canvas

        self.stage = tk.Canvas(
            self.center,
            bg=BG,
            highlightthickness=0
        )

        self.stage.pack(
            fill="both",
            expand=True
        )

        self.stage.bind(
            "<Configure>",
            lambda e: self.draw_scene()
        )

        self.stage.bind(
            "<Button-1>",
            lambda e: self.show_chat()
        )

        # Status

        self.stage_status = tk.Label(
            self.center,
            text="SYSTEM READY",
            font=("Consolas", 8, "bold"),
            bg=BG,
            fg=GREEN
        )

        self.stage_status.place(
            relx=0.5,
            rely=0.83,
            anchor="center"
        )

        # Quick controls

        controls = tk.Frame(
            self.center,
            bg=BG
        )

        controls.place(
            relx=0.5,
            rely=0.91,
            anchor="center"
        )

        self.quick_button(
            controls,
            "CHAT",
            self.show_chat
        )

        self.quick_button(
            controls,
            "MEMORY",
            self.show_memory
        )

        self.quick_button(
            controls,
            "SYSTEM",
            self.show_system
        )

        self.quick_button(
            controls,
            "VOICE",
            self.toggle_voice
        )

        # Chat overlay

        self.chat_view = tk.Frame(
            self.center,
            bg=BG
        )

        self.chat_view.place(
            relx=0,
            rely=0,
            relwidth=1,
            relheight=1
        )

        self.chat_view.lower()

        self.build_chat_view()

    # ========================================================
    # HOLOGRAPHIC SCENE
    # ========================================================

    def init_particles(self):

        self.particles = []

        for _ in range(130):

            self.particles.append({
                "x": random.random(),
                "y": random.random(),
                "speed": random.uniform(
                    0.00015,
                    0.0006
                ),
                "size": random.choice(
                    [1, 1, 1, 1, 2]
                ),
                "alpha": random.random()
            })

    def draw_scene(self):

        if not hasattr(self, "stage"):
            return

        canvas = self.stage

        canvas.delete("all")

        width = max(
            canvas.winfo_width(),
            600
        )

        height = max(
            canvas.winfo_height(),
            500
        )

        cx = width / 2
        cy = height * 0.46

        # ====================================================
        # BACKGROUND GRID
        # ====================================================

        grid = 42

        for x in range(
            0,
            width,
            grid
        ):

            canvas.create_line(
                x,
                0,
                x,
                height,
                fill=GRID,
                width=1
            )

        for y in range(
            0,
            height,
            grid
        ):

            canvas.create_line(
                0,
                y,
                width,
                y,
                fill=GRID,
                width=1
            )

        # ====================================================
        # MOVING SCAN
        # ====================================================

        self.scan_y += 1.4

        if self.scan_y > height:
            self.scan_y = 0

        canvas.create_line(
            0,
            self.scan_y,
            width,
            self.scan_y,
            fill="#1A121A",
            width=1
        )

        # ====================================================
        # PARTICLES
        # ====================================================

        for particle in self.particles:

            particle["y"] += particle["speed"]

            if particle["y"] > 1:
                particle["y"] = 0

            x = particle["x"] * width
            y = particle["y"] * height

            size = particle["size"]

            color = (
                GOLD_DIM
                if particle["alpha"] > 0.75
                else BURGUNDY_DIM
            )

            canvas.create_oval(
                x - size,
                y - size,
                x + size,
                y + size,
                fill=color,
                outline=""
            )

        # ====================================================
        # PULSE
        # ====================================================

        self.phase += 0.075

        pulse = (
            math.sin(self.phase) * 8
        )

        # ====================================================
        # HUGE BACK GLOW
        # ====================================================

        for radius, color in [
            (270, "#0B0D12"),
            (245, "#101018"),
            (220, "#15101A"),
        ]:

            canvas.create_oval(
                cx - radius,
                cy - radius,
                cx + radius,
                cy + radius,
                fill=color,
                outline=""
            )

        # ====================================================
        # OUTER HUD RINGS
        # ====================================================

        outer_rings = [
            (220, LINE, 1),
            (205, GOLD_DIM, 1),
            (188, LINE2, 1),
            (170, BURGUNDY_DIM, 2),
            (150, GOLD_DIM, 1),
            (130, BURGUNDY_LIGHT, 1),
        ]

        for radius, color, line_width in outer_rings:

            canvas.create_oval(
                cx - radius,
                cy - radius,
                cx + radius,
                cy + radius,
                outline=color,
                width=line_width
            )

        # ====================================================
        # ROTATING TICKS
        # ====================================================

        self.angle_outer += 1.4
        self.angle_inner -= 2.1

        for i in range(36):

            angle = (
                self.angle_outer
                + i * 10
            )

            rad = math.radians(angle)

            r1 = 205
            r2 = 214

            x1 = cx + math.cos(rad) * r1
            y1 = cy + math.sin(rad) * r1

            x2 = cx + math.cos(rad) * r2
            y2 = cy + math.sin(rad) * r2

            canvas.create_line(
                x1,
                y1,
                x2,
                y2,
                fill=(
                    GOLD
                    if i % 6 == 0
                    else GOLD_DIM
                ),
                width=(
                    2
                    if i % 6 == 0
                    else 1
                )
            )

        # ====================================================
        # ROTATING ARCS
        # ====================================================

        canvas.create_arc(
            cx - 185,
            cy - 185,
            cx + 185,
            cy + 185,
            start=self.angle_outer,
            extent=80,
            outline=GOLD,
            width=2,
            style="arc"
        )

        canvas.create_arc(
            cx - 170,
            cy - 170,
            cx + 170,
            cy + 170,
            start=-self.angle_outer * 1.7,
            extent=125,
            outline=BURGUNDY_LIGHT,
            width=2,
            style="arc"
        )

        canvas.create_arc(
            cx - 145,
            cy - 145,
            cx + 145,
            cy + 145,
            start=self.angle_inner,
            extent=60,
            outline=GOLD_DIM,
            width=2,
            style="arc"
        )

        # ====================================================
        # RADIAL ENERGY
        # ====================================================

        for i in range(12):

            angle = (
                self.angle_inner
                + i * 30
            )

            rad = math.radians(angle)

            r1 = 92
            r2 = 118

            canvas.create_line(
                cx + math.cos(rad) * r1,
                cy + math.sin(rad) * r1,
                cx + math.cos(rad) * r2,
                cy + math.sin(rad) * r2,
                fill=BURGUNDY_LIGHT,
                width=2
            )

        # ====================================================
        # INNER CORE GLOW
        # ====================================================

        core_radius = 62 + pulse

        canvas.create_oval(
            cx - core_radius,
            cy - core_radius,
            cx + core_radius,
            cy + core_radius,
            outline="#341522",
            width=6
        )

        canvas.create_oval(
            cx - 54,
            cy - 54,
            cx + 54,
            cy + 54,
            fill=BLACK,
            outline=GOLD,
            width=2
        )

        canvas.create_oval(
            cx - 39,
            cy - 39,
            cx + 39,
            cy + 39,
            outline=BURGUNDY_LIGHT,
            width=2
        )

        # ====================================================
        # CORE
        # ====================================================

        core_size = 16 + (
            math.sin(
                self.phase * 1.4
            ) * 4
        )

        canvas.create_oval(
            cx - core_size,
            cy - core_size,
            cx + core_size,
            cy + core_size,
            fill=GOLD_DIM,
            outline=GOLD_LIGHT,
            width=2
        )

        # ====================================================
        # CORE CROSS
        # ====================================================

        canvas.create_line(
            cx - 30,
            cy,
            cx + 30,
            cy,
            fill="#5D4930",
            width=1
        )

        canvas.create_line(
            cx,
            cy - 30,
            cx,
            cy + 30,
            fill="#5D4930",
            width=1
        )

        # ====================================================
        # ORBITAL DOTS
        # ====================================================

        for radius, speed, color in [
            (155, 1.8, GOLD),
            (125, -2.4, BURGUNDY_LIGHT),
            (95, 3.2, GOLD_LIGHT),
        ]:

            angle = (
                self.angle_outer * speed
            )

            rad = math.radians(angle)

            x = cx + math.cos(rad) * radius
            y = cy + math.sin(rad) * radius

            canvas.create_oval(
                x - 4,
                y - 4,
                x + 4,
                y + 4,
                fill=color,
                outline=""
            )

        # ====================================================
        # HUD CORNER INFORMATION
        # ====================================================

        self.hud_text(
            canvas,
            25,
            30,
            "ARIA CORE // 01"
        )

        self.hud_text(
            canvas,
            width - 25,
            30,
            "NEURAL SYSTEM",
            anchor="ne"
        )

        self.hud_text(
            canvas,
            25,
            height - 30,
            "SECURE CHANNEL",
            anchor="sw"
        )

        self.hud_text(
            canvas,
            width - 25,
            height - 30,
            "LOCAL CORE",
            anchor="se"
        )

        # ====================================================
        # SIDE HUD MARKERS
        # ====================================================

        canvas.create_line(
            20,
            cy - 90,
            70,
            cy - 90,
            fill=GOLD_DIM
        )

        canvas.create_text(
            78,
            cy - 90,
            text="CORE",
            fill=MUTED,
            font=("Consolas", 7),
            anchor="w"
        )

        canvas.create_line(
            width - 70,
            cy + 90,
            width - 20,
            cy + 90,
            fill=GOLD_DIM
        )

        canvas.create_text(
            width - 78,
            cy + 90,
            text="ACTIVE",
            fill=MUTED,
            font=("Consolas", 7),
            anchor="e"
        )

        # ====================================================
        # CENTRAL TEXT
        # ====================================================

        canvas.create_text(
            cx,
            cy - 88,
            text="ARIA",
            fill=WHITE,
            font=("Segoe UI", 28, "bold")
        )

        canvas.create_text(
            cx,
            cy - 54,
            text="ARTIFICIAL INTELLIGENCE",
            fill=GOLD,
            font=("Consolas", 7, "bold")
        )

        canvas.create_text(
            cx,
            cy + 80,
            text=self.aria_status,
            fill=(
                GOLD_LIGHT
                if self.aria_status != "SYSTEM READY"
                else GREEN
            ),
            font=("Consolas", 8, "bold")
        )

    def hud_text(
        self,
        canvas,
        x,
        y,
        text,
        anchor="nw"
    ):

        canvas.create_text(
            x,
            y,
            text=text,
            fill="#5C5549",
            font=("Consolas", 7),
            anchor=anchor
        )

    # ========================================================
    # ANIMATION
    # ========================================================

    def animation_loop(self):

        try:

            self.draw_scene()

        except Exception as exc:

            print(
                "ARIA animation error:",
                exc
            )

        self.root.after(
            40,
            self.animation_loop
        )

    # ========================================================
    # QUICK BUTTONS
    # ========================================================

    def quick_button(
        self,
        parent,
        text,
        command
    ):

        button = tk.Button(
            parent,
            text=text,
            command=command,
            bg=PANEL,
            fg=TEXT,
            activebackground=PANEL2,
            activeforeground=GOLD_LIGHT,
            relief="flat",
            bd=0,
            highlightbackground=LINE2,
            highlightthickness=1,
            font=("Consolas", 7, "bold"),
            cursor="hand2",
            padx=18,
            pady=8
        )

        button.pack(
            side="left",
            padx=3
        )

        hover(
            button,
            PANEL,
            PANEL2
        )

    # ========================================================
    # CHAT
    # ========================================================

    def build_chat_view(self):

        header = tk.Frame(
            self.chat_view,
            bg=BG,
            height=45
        )

        header.pack(
            fill="x"
        )

        tk.Label(
            header,
            text="CONVERSATION // SECURE",
            font=("Consolas", 8, "bold"),
            bg=BG,
            fg=MUTED
        ).pack(
            side="left",
            padx=12
        )

        self.chat_session_label = tk.Label(
            header,
            text="",
            font=("Consolas", 8, "bold"),
            bg=BG,
            fg=GOLD
        )

        self.chat_session_label.pack(
            side="right",
            padx=12
        )

        self.chat = scrolledtext.ScrolledText(
            self.chat_view,
            wrap="word",
            bg=BG,
            fg=TEXT,
            insertbackground=GOLD_LIGHT,
            selectbackground=BURGUNDY,
            selectforeground=WHITE,
            relief="flat",
            bd=0,
            font=("Segoe UI", 10),
            padx=18,
            pady=12
        )

        self.chat.pack(
            fill="both",
            expand=True
        )

        self.chat.tag_config(
            "user",
            foreground=GOLD_LIGHT,
            font=("Consolas", 8, "bold"),
            spacing1=12,
            spacing3=4
        )

        self.chat.tag_config(
            "assistant",
            foreground=TEXT,
            font=("Segoe UI", 10),
            spacing1=4,
            spacing3=15
        )

        self.chat.configure(
            state="disabled"
        )

        # Input

        input_outer = tk.Frame(
            self.chat_view,
            bg=BG
        )

        input_outer.pack(
            fill="x",
            padx=12,
            pady=10
        )

        self.input_frame = tk.Frame(
            input_outer,
            bg=PANEL,
            highlightbackground=LINE2,
            highlightthickness=1
        )

        self.input_frame.pack(
            fill="x"
        )

        self.input = tk.Text(
            self.input_frame,
            height=3,
            wrap="word",
            bg=PANEL,
            fg=TEXT,
            insertbackground=GOLD_LIGHT,
            selectbackground=BURGUNDY,
            selectforeground=WHITE,
            relief="flat",
            bd=0,
            font=("Segoe UI", 10),
            padx=14,
            pady=10
        )

        self.input.pack(
            side="left",
            fill="both",
            expand=True
        )

        self.input.bind(
            "<FocusIn>",
            lambda e:
            self.input_frame.configure(
                highlightbackground=GOLD
            )
        )

        self.input.bind(
            "<FocusOut>",
            lambda e:
            self.input_frame.configure(
                highlightbackground=LINE2
            )
        )

        self.send_button = tk.Button(
            self.input_frame,
            text="SEND  ➤",
            command=self.send_message,
            bg=BURGUNDY,
            fg=WHITE,
            activebackground=BURGUNDY_LIGHT,
            activeforeground=WHITE,
            relief="flat",
            bd=0,
            font=("Consolas", 8, "bold"),
            cursor="hand2",
            padx=18,
            pady=12
        )

        self.send_button.pack(
            side="right",
            padx=8,
            pady=8
        )

        hover(
            self.send_button,
            BURGUNDY,
            BURGUNDY_LIGHT
        )

        self.input.bind(
            "<Control-Return>",
            lambda e:
            self.send_message()
        )

    # ========================================================
    # MODES
    # ========================================================

    def show_command_center(self):

        self.mode = "command"

        self.chat_view.lower()

        self.center_title.configure(
            text="ARIA // COMMAND CENTER"
        )

        self.set_status(
            "SYSTEM READY"
        )

    def show_chat(self):

        self.mode = "chat"

        self.chat_view.lift()

        self.center_title.configure(
            text="CONVERSATION // SECURE"
        )

        self.chat_session_label.configure(
            text=self.get_current_session_name()
        )

        self.input.focus_set()

    # ========================================================
    # STATUS
    # ========================================================

    def set_status(self, status):

        self.aria_status = status

        if hasattr(
            self,
            "stage_status"
        ):

            self.stage_status.configure(
                text=status
            )

        if hasattr(
            self,
            "core_status"
        ):

            self.core_status.configure(
                text=status
            )

        if hasattr(
            self,
            "header_status"
        ):

            if status == "SYSTEM READY":

                self.header_status.configure(
                    text="● SYSTEM ONLINE",
                    fg=GREEN
                )

            elif status == "THINKING":

                self.header_status.configure(
                    text="● PROCESSING",
                    fg=GOLD
                )

            elif status == "SPEAKING":

                self.header_status.configure(
                    text="● ARIA SPEAKING",
                    fg=GOLD_LIGHT
                )

            else:

                self.header_status.configure(
                    text="● " + status,
                    fg=GOLD
                )

    # ========================================================
    # CLOCK
    # ========================================================

    def refresh_clock(self):

        now = datetime.now()

        self.clock_label.configure(
            text=now.strftime("%H:%M:%S")
        )

        self.date_label.configure(
            text=now.strftime(
                "%A\n%d %B %Y"
            ).upper()
        )

        self.root.after(
            1000,
            self.refresh_clock
        )

    # ========================================================
    # TELEMETRY
    # ========================================================

    def refresh_telemetry(self):

        # Lightweight simulated telemetry.
        # No external packages required.

        cpu = random.randint(
            18,
            48
        )

        gpu = random.randint(
            8,
            35
        )

        ram = random.randint(
            35,
            62
        )

        net = random.randint(
            92,
            100
        )

        self.update_telemetry(
            self.cpu_value,
            "CPU",
            cpu
        )

        self.update_telemetry(
            self.gpu_value,
            "GPU",
            gpu
        )

        self.update_telemetry(
            self.ram_value,
            "RAM",
            ram
        )

        self.update_telemetry(
            self.net_value,
            "NET",
            net
        )

        self.root.after(
            1800,
            self.refresh_telemetry
        )

    def update_telemetry(
        self,
        label,
        name,
        value
    ):

        label.configure(
            text=f"{name}  {value}%"
        )

        if hasattr(
            label,
            "bar"
        ):

            bar = label.bar

            width = max(
                bar.winfo_width(),
                100
            )

            bar.coords(
                "value",
                0,
                0,
                width * value / 100,
                4
            )

    # ========================================================
    # HISTORY
    # ========================================================

    def get_current_session_name(self):

        for sid, name, count in list_sessions():

            if sid == self.current_sid:
                return name

        return "Sohbet"

    def refresh_history(self):

        for widget in self.session_frame.winfo_children():

            widget.destroy()

        sessions = list_sessions()

        for sid, name, count in sessions:

            active = (
                sid ==
                self.current_sid
            )

            card_bg = (
                BURGUNDY_DIM
                if active
                else PANEL2
            )

            card = tk.Frame(
                self.session_frame,
                bg=card_bg,
                highlightbackground=(
                    GOLD_DIM
                    if active
                    else LINE
                ),
                highlightthickness=1
            )

            card.pack(
                fill="x",
                pady=3
            )

            button = tk.Button(
                card,
                text=name,
                command=lambda x=sid:
                self.open_session(x),
                anchor="w",
                bg=card_bg,
                fg=(
                    GOLD_LIGHT
                    if active
                    else TEXT
                ),
                activebackground=BURGUNDY,
                activeforeground=WHITE,
                relief="flat",
                bd=0,
                font=("Segoe UI", 8, "bold"),
                cursor="hand2",
                padx=10,
                pady=5
            )

            button.pack(
                fill="x"
            )

            tk.Label(
                card,
                text=f"{count} MESSAGES",
                font=("Consolas", 6),
                bg=card_bg,
                fg=(
                    GOLD_DIM
                    if active
                    else MUTED
                )
            ).pack(
                anchor="w",
                padx=10,
                pady=(0, 7)
            )

            button.bind(
                "<Button-3>",
                lambda event, x=sid:
                self.session_menu(
                    event,
                    x
                )
            )

    def session_menu(
        self,
        event,
        sid
    ):

        menu = tk.Menu(
            self.root,
            tearoff=0,
            bg=PANEL2,
            fg=TEXT,
            activebackground=BURGUNDY,
            activeforeground=WHITE
        )

        menu.add_command(
            label="Rename",
            command=lambda:
            self.rename_chat(sid)
        )

        menu.add_command(
            label="Delete",
            command=lambda:
            self.delete_chat(sid)
        )

        menu.tk_popup(
            event.x_root,
            event.y_root
        )

    def open_session(self, sid):

        if not switch_session(sid):
            return

        self.current_sid = sid

        self.refresh_history()

        self.load_current_chat()

        self.show_chat()

    def new_chat(self):

        name = simpledialog.askstring(
            "NEW CONVERSATION",
            "Conversation name:",
            parent=self.root
        )

        if not name:
            name = "Sohbet"

        self.current_sid = create_session(
            name
        )

        self.refresh_history()

        self.load_current_chat()

        self.show_chat()

    def rename_chat(self, sid):

        name = simpledialog.askstring(
            "RENAME CONVERSATION",
            "New name:",
            parent=self.root
        )

        if not name:
            return

        if rename_session(
            sid,
            name
        ):

            self.refresh_history()

            self.chat_session_label.configure(
                text=name
            )

    def delete_chat(self, sid):

        if not messagebox.askyesno(
            "DELETE CONVERSATION",
            "Bu sohbeti silmek istediğine emin misin?"
        ):
            return

        delete_session(
            sid
        )

        self.current_sid = (
            current_session_id()
        )

        self.refresh_history()

        self.load_current_chat()

    # ========================================================
    # CHAT DISPLAY
    # ========================================================

    def load_current_chat(self):

        self.chat.configure(
            state="normal"
        )

        self.chat.delete(
            "1.0",
            "end"
        )

        messages = get_messages()

        if not messages:

            self.chat.insert(
                "end",
                "ARIA\n",
                "assistant"
            )

            self.chat.insert(
                "end",
                "System ready.\n"
                "I'm listening.\n\n",
                "assistant"
            )

        else:

            for message in messages:

                role = message.get(
                    "role"
                )

                content = message.get(
                    "content",
                    ""
                )

                if role == "user":

                    self.chat.insert(
                        "end",
                        "YOU\n",
                        "user"
                    )

                    self.chat.insert(
                        "end",
                        content +
                        "\n\n"
                    )

                elif role == "assistant":

                    self.chat.insert(
                        "end",
                        "ARIA\n",
                        "assistant"
                    )

                    self.chat.insert(
                        "end",
                        content +
                        "\n\n",
                        "assistant"
                    )

        self.chat.configure(
            state="disabled"
        )

        self.chat.see(
            "end"
        )

        self.chat_session_label.configure(
            text=self.get_current_session_name()
        )

    def add_message(
        self,
        role,
        text
    ):

        self.chat.configure(
            state="normal"
        )

        if role == "user":

            self.chat.insert(
                "end",
                "YOU\n",
                "user"
            )

            self.chat.insert(
                "end",
                text +
                "\n\n"
            )

        else:

            self.chat.insert(
                "end",
                "ARIA\n",
                "assistant"
            )

            self.chat.insert(
                "end",
                text +
                "\n\n",
                "assistant"
            )

        self.chat.configure(
            state="disabled"
        )

        self.chat.see(
            "end"
        )

    # ========================================================
    # SEND
    # ========================================================

    def send_message(self):

        text = self.input.get(
            "1.0",
            "end"
        ).strip()

        if not text:
            return

        self.input.delete(
            "1.0",
            "end"
        )

        self.add_message(
            "user",
            text
        )

        self.send_button.configure(
            state="disabled",
            text="PROCESSING..."
        )

        self.set_status(
            "THINKING"
        )

        threading.Thread(
            target=self.get_ai_response,
            args=(text,),
            daemon=True
        ).start()

    def get_ai_response(
        self,
        text
    ):

        try:

            response = ask_ai(
                text
            )

        except Exception as exc:

            response = (
                "Bir hata oluştu:\n"
                f"{exc}"
            )

        self.root.after(
            0,
            lambda:
            self.show_response(
                response
            )
        )

    def show_response(
        self,
        response
    ):

        self.add_message(
            "assistant",
            response
        )

        self.send_button.configure(
            state="normal",
            text="SEND  ➤"
        )

        self.set_status(
            "SYSTEM READY"
        )

        self.speak(
            response
        )

    # ========================================================
    # MEMORY
    # ========================================================

    def show_memory(self):

        window = tk.Toplevel(
            self.root
        )

        window.title(
            "ARIA // MEMORY CORE"
        )

        window.geometry(
            "720x580"
        )

        window.configure(
            bg=BG
        )

        tk.Frame(
            window,
            bg=GOLD,
            height=2
        ).pack(
            fill="x"
        )

        tk.Label(
            window,
            text="MEMORY CORE",
            font=("Segoe UI", 22, "bold"),
            bg=BG,
            fg=WHITE
        ).pack(
            anchor="w",
            padx=30,
            pady=(28, 3)
        )

        tk.Label(
            window,
            text="PERSISTENT KNOWLEDGE DATABASE",
            font=("Consolas", 8, "bold"),
            bg=BG,
            fg=GOLD
        ).pack(
            anchor="w",
            padx=30
        )

        box = scrolledtext.ScrolledText(
            window,
            wrap="word",
            bg=PANEL,
            fg=TEXT,
            insertbackground=GOLD,
            relief="flat",
            bd=0,
            font=("Segoe UI", 10),
            padx=18,
            pady=18
        )

        box.pack(
            fill="both",
            expand=True,
            padx=30,
            pady=25
        )

        memories = load_memory()

        if not memories:

            box.insert(
                "end",
                "MEMORY CORE EMPTY.\n\n"
                "No persistent memories stored."
            )

        else:

            for item in memories:

                box.insert(
                    "end",
                    f"{item.get('key')}\n",
                    "key"
                )

                box.insert(
                    "end",
                    f"{item.get('value')}\n\n"
                )

        box.tag_config(
            "key",
            foreground=GOLD_LIGHT,
            font=("Segoe UI", 10, "bold")
        )

        box.configure(
            state="disabled"
        )

    # ========================================================
    # SYSTEM WINDOW
    # ========================================================

    def show_system(self):

        window = tk.Toplevel(
            self.root
        )

        window.title(
            "ARIA // SYSTEM"
        )

        window.geometry(
            "720x570"
        )

        window.configure(
            bg=BG
        )

        tk.Frame(
            window,
            bg=GOLD,
            height=2
        ).pack(
            fill="x"
        )

        tk.Label(
            window,
            text="SYSTEM DIAGNOSTICS",
            font=("Segoe UI", 21, "bold"),
            bg=BG,
            fg=WHITE
        ).pack(
            anchor="w",
            padx=30,
            pady=(28, 3)
        )

        tk.Label(
            window,
            text="ARIA LOCAL COMMAND CORE",
            font=("Consolas", 8, "bold"),
            bg=BG,
            fg=GOLD
        ).pack(
            anchor="w",
            padx=30
        )

        card = tk.Frame(
            window,
            bg=PANEL,
            highlightbackground=LINE,
            highlightthickness=1
        )

        card.pack(
            fill="both",
            expand=True,
            padx=30,
            pady=25
        )

        rows = [
            (
                "ARIA CORE",
                "ONLINE",
                GREEN
            ),
            (
                "AI ENGINE",
                "READY",
                GREEN
            ),
            (
                "MEMORY",
                "ONLINE",
                GREEN
            ),
            (
                "HISTORY",
                "PERSISTENT",
                GREEN
            ),
            (
                "VOICE",
                "READY",
                GREEN
            ),
            (
                "OPERATING SYSTEM",
                platform.system(),
                GOLD_LIGHT
            ),
            (
                "PYTHON",
                platform.python_version(),
                GOLD_LIGHT
            ),
        ]

        for title, value, color in rows:

            row = tk.Frame(
                card,
                bg=PANEL
            )

            row.pack(
                fill="x",
                padx=20,
                pady=9
            )

            tk.Label(
                row,
                text=title,
                font=("Consolas", 8, "bold"),
                bg=PANEL,
                fg=MUTED
            ).pack(
                side="left"
            )

            tk.Label(
                row,
                text=value,
                font=("Consolas", 9, "bold"),
                bg=PANEL,
                fg=color
            ).pack(
                side="right"
            )

    # ========================================================
    # SETTINGS
    # ========================================================

    def show_settings(self):

        window = tk.Toplevel(
            self.root
        )

        window.title(
            "ARIA // SETTINGS"
        )

        window.geometry(
            "650x520"
        )

        window.configure(
            bg=BG
        )

        tk.Frame(
            window,
            bg=GOLD,
            height=2
        ).pack(
            fill="x"
        )

        tk.Label(
            window,
            text="SYSTEM SETTINGS",
            font=("Segoe UI", 21, "bold"),
            bg=BG,
            fg=WHITE
        ).pack(
            anchor="w",
            padx=30,
            pady=(28, 3)
        )

        tk.Label(
            window,
            text="ARIA COMMAND CENTER",
            font=("Consolas", 8, "bold"),
            bg=BG,
            fg=GOLD
        ).pack(
            anchor="w",
            padx=30
        )

        voice_card = tk.Frame(
            window,
            bg=PANEL,
            highlightbackground=LINE,
            highlightthickness=1
        )

        voice_card.pack(
            fill="x",
            padx=30,
            pady=25
        )

        tk.Label(
            voice_card,
            text="VOICE ENGINE",
            font=("Consolas", 9, "bold"),
            bg=PANEL,
            fg=WHITE
        ).pack(
            anchor="w",
            padx=18,
            pady=(16, 3)
        )

        tk.Label(
            voice_card,
            text="Edge-TTS // Neural Voice",
            font=("Consolas", 7),
            bg=PANEL,
            fg=MUTED
        ).pack(
            anchor="w",
            padx=18
        )

        tk.Button(
            voice_card,
            text="TEST VOICE",
            command=lambda:
            self.speak(
                "Merhaba Selen. "
                "Ben ARIA. "
                "Ses sistemim aktif."
            ),
            bg=BURGUNDY,
            fg=WHITE,
            activebackground=BURGUNDY_LIGHT,
            activeforeground=WHITE,
            relief="flat",
            bd=0,
            font=("Consolas", 8, "bold"),
            cursor="hand2",
            padx=15,
            pady=9
        ).pack(
            anchor="w",
            padx=18,
            pady=15
        )

        self.settings_button(
            window,
            "CLEAR CURRENT CONVERSATION",
            self.clear_chat
        )

        self.settings_button(
            window,
            "DELETE ALL MEMORY",
            self.clear_all_memory
        )

    def settings_button(
        self,
        parent,
        text,
        command
    ):

        button = tk.Button(
            parent,
            text=text,
            command=command,
            bg=PANEL,
            fg=TEXT,
            activebackground=PANEL2,
            activeforeground=WHITE,
            relief="flat",
            bd=0,
            highlightbackground=LINE,
            highlightthickness=1,
            font=("Consolas", 8, "bold"),
            cursor="hand2",
            pady=10
        )

        button.pack(
            fill="x",
            padx=30,
            pady=4
        )

        hover(
            button,
            PANEL,
            PANEL2
        )

    # ========================================================
    # CLEAR
    # ========================================================

    def clear_chat(self):

        if not messagebox.askyesno(
            "CLEAR CONVERSATION",
            "Bu sohbetin tüm mesajlarını silmek istediğine emin misin?"
        ):
            return

        clear_current()

        self.load_current_chat()

    def clear_all_memory(self):

        if not messagebox.askyesno(
            "DELETE MEMORY",
            "ARIA'nın tüm kalıcı hafızasını silmek istediğine emin misin?"
        ):
            return

        clear_memory()

        messagebox.showinfo(
            "MEMORY CORE",
            "ARIA memory core temizlendi."
        )

    # ========================================================
    # CHAT
    # ========================================================

    def show_chat(self):

        self.mode = "chat"

        self.chat_view.lift()

        self.center_title.configure(
            text="CONVERSATION // SECURE"
        )

        self.chat_session_label.configure(
            text=self.get_current_session_name()
        )

        self.input.focus_set()

    # ========================================================
    # MAIN CHAT STATE
    # ========================================================

    def load_current_chat_again(self):

        self.load_current_chat()


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    root = tk.Tk()

    app = ARIAApp(
        root
    )

    def on_close():

        try:
            voice_engine.stop()
        except Exception:
            pass

        root.destroy()

    root.protocol(
        "WM_DELETE_WINDOW",
        on_close
    )

    root.mainloop()