from pathlib import Path
import os


# Minimal .env loader so the project stays dependency-free.
def _load_dotenv() -> None:
    env_file = Path(__file__).resolve().parent / ".env"
    if not env_file.exists():
        return

    for raw in env_file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()

        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")

        os.environ.setdefault(key, value)


_load_dotenv()


# Project root
ROOT = Path(__file__).resolve().parent


# Persistent user data
# These files live outside the PyInstaller application,
# so rebuilding/updating ARIA will not delete conversations or memory.
APP_DATA_DIR = Path(os.getenv("LOCALAPPDATA", Path.home())) / "ARIA"
APP_DATA_DIR.mkdir(parents=True, exist_ok=True)

DATA_DIR = APP_DATA_DIR


# ARIA data files
MEMORY_FILE = DATA_DIR / "aria_memory.json"
HISTORY_FILE = DATA_DIR / "aria_history.json"
LOG_FILE = DATA_DIR / "aria.log"


# AI configuration
API_URL = os.getenv(
    "AI_API_URL",
    "https://api.openai.com/v1/responses"
)

MODEL = os.getenv(
    "AI_MODEL",
    "gpt-4o-mini"
)

API_KEY = os.getenv(
    "OPENAI_API_KEY",
    ""
)


# Application limits
API_TIMEOUT = int(
    os.getenv("ARIA_API_TIMEOUT", "60")
)

MAX_RETRIES = int(
    os.getenv("ARIA_MAX_RETRIES", "3")
)

MAX_HISTORY_MESSAGES = int(
    os.getenv("ARIA_MAX_HISTORY_MESSAGES", "30")
)

MAX_TOOL_ROUNDS = int(
    os.getenv("ARIA_MAX_TOOL_ROUNDS", "5")
)

MAX_MEMORY_RESULTS = int(
    os.getenv("ARIA_MAX_MEMORY_RESULTS", "8")
)


# ARIA personality / system instructions
SYSTEM_PROMPT = """Sen ARIA adlı kişisel bir yapay zeka asistanısın.
Kullanıcıyla Türkçe veya İngilizce konuşabilirsin; kullanıcının dilini takip et.
Kısa ama yeterli, doğal ve yardımcı cevaplar ver.
Hesaplama, tarih-saat veya hafıza işlemleri için uygun araçları kullan.
Kullanıcının açıkça istemediği hassas bilgileri kalıcı hafızaya kaydetme.
Şifre, API anahtarı, kimlik doğrulama bilgisi, finansal bilgi veya benzeri sırları hafızaya kaydetme.
Dosya silme, sistem değiştirme, program çalıştırma gibi tehlikeli yerel işlemler için araç sunulmadığını bil.
"""
