import asyncio
import os
import tempfile

import edge_tts

from ai import AIError, ask_ai
from history import clear_current, create_session, list_sessions
from memory import (
    add_or_update_memory,
    clear_memory,
    delete_memory,
    format_memory,
    search_memory,
)
from tools import REGISTRY


HELP = """
ARIA komutları

  yardım                 Bu menüyü gösterir
  hafıza                 Kalıcı hafızayı gösterir
  ara <kelime>           Hafızada arama yapar
  hatırla anahtar: değer Bilgiyi manuel kaydeder
  unut <kelime>          Eşleşen hafızayı siler
  hafızayı temizle       Tüm kalıcı hafızayı siler
  geçmişi temizle        Mevcut sohbet geçmişini siler
  yeni sohbet            Yeni sohbet oturumu açar
  sohbetler              Sohbet oturumlarını listeler
  araçlar                Kullanılabilir araçları gösterir
  durum                  ARIA durumunu gösterir
  çıkış                  Programdan çıkar

Normal cümleleri doğrudan yazabilirsin. ARIA uygun aracı kendisi seçebilir.
"""


def speak(text: str) -> None:
    """ARIA'nın cevabını seslendirir."""

    # Türkçe karakterlere göre basit dil tespiti
    turkish_chars = "çğıöşüÇĞİÖŞÜ"

    if any(char in text for char in turkish_chars):
        voice = "tr-TR-EmelNeural"
    else:
        voice = "en-US-AriaNeural"

    # Geçici MP3 dosyası oluştur
    with tempfile.NamedTemporaryFile(
        suffix=".mp3",
        delete=False
    ) as temp_file:
        audio_path = temp_file.name

    async def generate_voice():
        communicate = edge_tts.Communicate(
            text,
            voice
        )
        await communicate.save(audio_path)

    try:
        asyncio.run(generate_voice())

        # Windows'ta sesi otomatik oynat
        os.startfile(audio_path)

    except Exception as exc:
        print(f"\n🔊 Ses hatası: {exc}")


def main() -> None:
    print("\n🤖 ARIA hazır. 'yardım' yazarak komutları görebilirsin.\n")

    while True:
        try:
            user = input("Sen > ").strip()

        except (KeyboardInterrupt, EOFError):
            print("\nARIA > Görüşürüz. 👋")
            break

        if not user:
            continue

        command = user.casefold()

        if command in {"çıkış", "exit", "quit"}:
            print("ARIA > Görüşürüz. 👋")
            break

        if command in {"yardım", "help"}:
            print(HELP)
            continue

        if command == "hafıza":
            print("\n" + format_memory() + "\n")
            continue

        if command.startswith("ara "):
            results = search_memory(user[4:])

            print(
                "\n"
                + (
                    format_memory(results)
                    if results
                    else "Eşleşme bulunamadı."
                )
                + "\n"
            )
            continue

        if command.startswith("hatırla "):
            raw = user[8:].strip()

            if ":" not in raw:
                print("ARIA > Format: hatırla anahtar: değer")
                continue

            key, value = raw.split(":", 1)

            try:
                add_or_update_memory(key, value)
                print("ARIA > Tamam, bunu hafızaya aldım. 🧠")

            except ValueError as exc:
                print(f"ARIA > {exc}")

            continue

        if command.startswith("unut "):
            query = user[5:].strip()
            removed = delete_memory(query)

            print(f"ARIA > {removed} hafıza kaydı silindi.")
            continue

        if command == "hafızayı temizle":
            clear_memory()
            print("ARIA > Kalıcı hafıza temizlendi.")
            continue

        if command == "geçmişi temizle":
            clear_current()
            print("ARIA > Mevcut sohbet geçmişi temizlendi.")
            continue

        if command == "yeni sohbet":
            sid = create_session("Sohbet")
            print(f"ARIA > Yeni sohbet başlatıldı: {sid}")
            continue

        if command == "sohbetler":
            for sid, name, count in list_sessions():
                print(f"- {sid} | {name} | {count} mesaj")
            continue

        if command == "araçlar":
            print("\n".join(f"- {name}" for name in REGISTRY))
            continue

        if command == "durum":
            print(
                "ARIA > Core: hazır | "
                "Hafıza: hazır | "
                "History: hazır | "
                "Tools: hazır | "
                "AI: hazır | "
                "Voice: hazır"
            )
            continue

        try:
            print("ARIA > düşünüyor...", end="\r")

            answer = ask_ai(user)

            print("ARIA > " + answer)

            # ARIA artık cevabını sesli söylüyor
            speak(answer)

        except AIError as exc:
            print(f"ARIA > API hatası: {exc}")

        except Exception as exc:
            print(f"ARIA > Beklenmeyen hata: {exc}")


if __name__ == "__main__":
    main()
