import asyncio
import os
import tempfile
import threading

import edge_tts
import miniaudio
import numpy as np
import sounddevice as sd


# ============================================================
# ARIA // VOICE ENGINE
# EDGE-TTS + MINIAUDIO + SOUNDDEVICE
# ============================================================

class VoiceEngine:

    # ========================================================
    # VOICES
    # ========================================================

    TR_VOICE = "tr-TR-EmelNeural"
    EN_VOICE = "en-US-AriaNeural"

    # ========================================================
    # VOICE SETTINGS
    # ========================================================

    # Daha hızlı ve doğal konuşma
    TR_RATE = "+18%"
    EN_RATE = "+12%"

    # Biraz daha canlı / net ton
    TR_PITCH = "+2Hz"
    EN_PITCH = "+1Hz"

    # Ses seviyesi
    VOLUME = "+0%"

    # Windows Realtek Speakers
    OUTPUT_DEVICE = 3

    def __init__(self):

        self.enabled = True
        self.speaking = False

        self._lock = threading.Lock()
        self._generation = 0

        self._current_file = None

    # ========================================================
    # LANGUAGE DETECTION
    # ========================================================

    def detect_voice(self, text):

        text_lower = text.lower()

        # Türkçe karakter kontrolü
        turkish_characters = "çğıöşü"

        if any(
            char in text_lower
            for char in turkish_characters
        ):
            return self.TR_VOICE

        # Türkçe kelimeler
        turkish_words = {
            "ben",
            "sen",
            "biz",
            "siz",
            "bir",
            "bu",
            "şu",
            "ve",
            "ama",
            "için",
            "ile",
            "nasıl",
            "neden",
            "hangi",
            "ne",
            "kim",
            "merhaba",
            "tamam",
            "evet",
            "hayır",
            "artık",
            "sistem",
            "aktif",
            "hazır",
            "bugün",
            "yarın",
            "şimdi",
            "olan",
            "olarak",
            "çok",
            "daha",
            "var",
            "yok",
            "söyle",
            "bana",
            "senin",
            "benim",
            "çünkü",
            "fakat",
            "ancak",
            "değil",
            "oldu",
            "olacak",
            "ediyorum",
            "edebilir",
            "edebilirim",
        }

        words = {
            word.strip(
                ".,!?;:()[]{}\"'"
            )
            for word in text_lower.split()
        }

        if words.intersection(turkish_words):
            return self.TR_VOICE

        return self.EN_VOICE

    # ========================================================
    # VOICE PARAMETERS
    # ========================================================

    def get_voice_parameters(self, voice):

        if voice == self.TR_VOICE:

            return {
                "rate": self.TR_RATE,
                "pitch": self.TR_PITCH,
                "volume": self.VOLUME,
            }

        return {
            "rate": self.EN_RATE,
            "pitch": self.EN_PITCH,
            "volume": self.VOLUME,
        }

    # ========================================================
    # SPEAK
    # ========================================================

    def speak(
        self,
        text,
        on_start=None,
        on_end=None
    ):

        if not self.enabled:
            return

        if not text:
            return

        text = text.strip()

        if not text:
            return

        # Yeni konuşma için generation artır
        with self._lock:

            self._generation += 1

            generation = self._generation

        # Önce mevcut konuşmayı durdur
        self.stop(
            delete_file=True,
            increment_generation=False
        )

        # Ayrı thread
        thread = threading.Thread(
            target=self._speak_worker,
            args=(
                text,
                generation,
                on_start,
                on_end
            ),
            daemon=True
        )

        thread.start()

    # ========================================================
    # WORKER
    # ========================================================

    def _speak_worker(
        self,
        text,
        generation,
        on_start,
        on_end
    ):

        audio_path = None

        try:

            # ------------------------------------------------
            # SELECT VOICE
            # ------------------------------------------------

            voice = self.detect_voice(
                text
            )

            parameters = self.get_voice_parameters(
                voice
            )

            print(
                f"[VOICE] Using: {voice}"
            )

            print(
                f"[VOICE] Rate: {parameters['rate']} | "
                f"Pitch: {parameters['pitch']}"
            )

            # ------------------------------------------------
            # CREATE TEMP FILE
            # ------------------------------------------------

            fd, audio_path = tempfile.mkstemp(
                prefix="aria_voice_",
                suffix=".mp3"
            )

            os.close(fd)

            # ------------------------------------------------
            # EDGE TTS
            # ------------------------------------------------

            async def generate_audio():

                communicate = edge_tts.Communicate(
                    text=text,
                    voice=voice,
                    rate=parameters["rate"],
                    pitch=parameters["pitch"],
                    volume=parameters["volume"],
                )

                await communicate.save(
                    audio_path
                )

            asyncio.run(
                generate_audio()
            )

            # ------------------------------------------------
            # CHECK CURRENT GENERATION
            # ------------------------------------------------

            if not self._is_current(
                generation
            ):

                self._safe_delete(
                    audio_path
                )

                return

            # ------------------------------------------------
            # DECODE AUDIO
            # ------------------------------------------------

            decoded = miniaudio.decode_file(
                audio_path,
                output_format=miniaudio.SampleFormat.SIGNED16
            )

            sample_rate = decoded.sample_rate
            channels = decoded.nchannels

            # ------------------------------------------------
            # CONVERT TO NUMPY
            # ------------------------------------------------

            audio = np.frombuffer(
                decoded.samples,
                dtype=np.int16
            )

            audio = (
                audio.astype(
                    np.float32
                )
                / 32768.0
            )

            # ------------------------------------------------
            # FIX CHANNEL SHAPE
            # ------------------------------------------------

            if channels > 1:

                audio = audio.reshape(
                    -1,
                    channels
                )

            # ------------------------------------------------
            # UPDATE STATUS
            # ------------------------------------------------

            with self._lock:

                self._current_file = audio_path
                self.speaking = True

            # ------------------------------------------------
            # CALLBACK
            # ------------------------------------------------

            if on_start:

                try:

                    on_start()

                except Exception as exc:

                    print(
                        "[VOICE] on_start error:",
                        exc
                    )

            # ------------------------------------------------
            # PLAY
            # ------------------------------------------------

            print(
                f"[VOICE] Playing "
                f"{sample_rate} Hz / "
                f"{channels} channel(s)"
            )

            sd.play(
                audio,
                samplerate=sample_rate,
                device=self.OUTPUT_DEVICE,
                blocking=True
            )

        except Exception as exc:

            print(
                "[VOICE] ERROR:",
                repr(exc)
            )

        finally:

            # ------------------------------------------------
            # STOP AUDIO
            # ------------------------------------------------

            try:

                sd.stop()

            except Exception:
                pass

            # ------------------------------------------------
            # UPDATE STATE
            # ------------------------------------------------

            with self._lock:

                is_current = (
                    generation
                    == self._generation
                )

                if self._current_file == audio_path:

                    self._current_file = None

                if is_current:

                    self.speaking = False

            # ------------------------------------------------
            # DELETE TEMP FILE
            # ------------------------------------------------

            self._safe_delete(
                audio_path
            )

            # ------------------------------------------------
            # CALLBACK
            # ------------------------------------------------

            if (
                is_current
                and on_end
            ):

                try:

                    on_end()

                except Exception as exc:

                    print(
                        "[VOICE] on_end error:",
                        exc
                    )

    # ========================================================
    # STOP
    # ========================================================

    def stop(
        self,
        delete_file=True,
        increment_generation=True
    ):

        if increment_generation:

            with self._lock:

                self._generation += 1

        try:

            sd.stop()

        except Exception:
            pass

        with self._lock:

            audio_path = self._current_file

            self._current_file = None
            self.speaking = False

        if delete_file:

            self._safe_delete(
                audio_path
            )

    # ========================================================
    # ENABLE / DISABLE
    # ========================================================

    def set_enabled(
        self,
        enabled
    ):

        self.enabled = enabled

        if not enabled:

            self.stop()

    # ========================================================
    # STATUS
    # ========================================================

    def is_speaking(self):

        with self._lock:

            return self.speaking

    # ========================================================
    # GENERATION
    # ========================================================

    def _is_current(
        self,
        generation
    ):

        with self._lock:

            return (
                generation
                == self._generation
                and self.enabled
            )

    # ========================================================
    # FILE CLEANUP
    # ========================================================

    @staticmethod
    def _safe_delete(
        path
    ):

        if not path:
            return

        try:

            if os.path.exists(path):

                os.remove(
                    path
                )

        except Exception:
            pass


# ============================================================
# GLOBAL VOICE ENGINE
# ============================================================

voice_engine = VoiceEngine()