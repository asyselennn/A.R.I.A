# ARIA — Personal AI Assistant

**ARIA** is a personal AI assistant developed in Python, designed to combine conversational AI, persistent memory, voice interaction, a desktop command center, and local computer tools in a modular architecture.

The project started as a personal AI assistant and evolved into a fully interactive desktop application with both text and voice-based interaction.

## ✨ Features

- 🤖 **Conversational AI** — Natural-language interaction through an AI backend
- 🧠 **Persistent Memory** — Stores and retrieves selected information across sessions
- 💬 **Conversation History** — Session-based chat history and conversation management
- 🖥️ **Desktop GUI** — Custom-built command center interface
- 🎙️ **Neural Text-to-Speech** — Natural voice responses using Edge TTS
- 🎤 **Speech Recognition** — Converts spoken input into text
- 🔄 **Continuous Voice Mode** — Listen → transcribe → think → respond → speak → listen again
- 🛠️ **Local Tools** — Calculator, date/time, memory operations, and system information
- 🔐 **Security Layer** — Controlled handling of local actions and sensitive operations
- 📝 **Logging** — Application and error logging for debugging and development
- ⚙️ **Modular Architecture** — AI, memory, history, voice, GUI, tools, and security are separated into independent modules

## 🧠 Architecture

ARIA is designed around a modular architecture rather than a single large script.

```text
                    ┌─────────────────────┐
                    │       ARIA GUI      │
                    │   Command Center    │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │      AI Engine      │
                    │    ask_ai() core    │
                    └───────┬────┬────────┘
                            │    │
              ┌─────────────┘    └─────────────┐
              ▼                                ▼
       ┌──────────────┐                 ┌──────────────┐
       │    Memory    │                 │    Tools     │
       │ Persistence  │                 │ Local Actions│
       └──────────────┘                 └──────────────┘
              │                                │
              └─────────────┬──────────────────┘
                            ▼
                    ┌──────────────┐
                    │   Security   │
                    │    Layer     │
                    └──────────────┘

        Voice Input ──► Speech Recognition
        Voice Output ◄── Neural TTS
```

The core AI layer is separated from the GUI and voice layers, allowing different interfaces to use the same underlying AI, memory, history, tools, and security systems.

## 🎙️ Voice System

ARIA supports interactive voice conversations.

The voice pipeline follows:

```text
User Speech
     ↓
Microphone
     ↓
Speech Recognition
     ↓
AI Processing
     ↓
Response Generation
     ↓
Neural Text-to-Speech
     ↓
Audio Output
     ↓
Listen Again
```

Voice responses currently support Turkish and English neural voices.

## 🧠 Memory System

ARIA includes persistent memory so that selected information can remain available between conversations.

Memory operations include:

- Save information
- Search memory
- Forget information
- Clear memory

The system is designed so that memory functionality remains independent from the graphical interface and AI layer.

## 🛠️ Tools

ARIA can interact with local tools through the AI layer.

Current capabilities include:

- Calculator
- Date and time
- Memory search
- Memory save
- Memory deletion
- Basic system information

Natural-language requests can trigger supported tools automatically.

## 🖥️ Desktop Interface

ARIA includes a custom desktop command center designed specifically for the project.

The interface provides:

- Text conversation
- Voice interaction
- Voice Mode
- Session management
- Application status
- Memory interaction
- AI responses
- System controls

## 📁 Project Structure

```text
A.R.I.A/
│
├── gui.py            # Desktop graphical interface
├── voice.py          # Voice input/output system
├── ai.py             # AI interaction layer
├── memory.py         # Persistent memory
├── history.py        # Conversation and session management
├── tools.py          # Local tools
├── security.py       # Security and action controls
├── config.py         # Configuration
├── logger.py         # Logging
├── aria.py           # Main application entry point
├── ARIA.spec         # Application build configuration
├── requirements.txt  # Python dependencies
├── .gitignore        # Git exclusions
└── README.md         # Project documentation
```

## ⚙️ Technologies

- **Python**
- **AI API / Responses API**
- **Tkinter**
- **Edge TTS**
- **SpeechRecognition**
- **SoundDevice**
- **NumPy**
- **Miniaudio**
- **JSON-based persistence**
- **Git / GitHub**

## 🚀 Running ARIA

### Requirements

- Python 3.11+
- Compatible AI API key
- Microphone for voice interaction
- Speakers or headphones for voice output

### Installation

Clone the repository:

```bash
git clone https://github.com/asyselennn/A.R.I.A.git
cd A.R.I.A
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Configure the required environment variables locally.

**Do not commit API keys, `.env` files, or private memory data to the repository.**

### Run

For the desktop interface:

```bash
python gui.py
```

For the command-line interface:

```bash
python aria.py
```

## 🔐 Security & Privacy

ARIA is designed to keep sensitive configuration and personal data separate from the public source code.

Private information such as:

- API keys
- Environment variables
- Personal memory data
- Local generated files

should remain outside the public repository.

## 🎯 Project Goal

ARIA is an exploration of how a personal AI assistant can combine conversational intelligence with memory, voice interaction, local tools, and a dedicated user interface.

The long-term goal is to develop ARIA into a more capable personal intelligent system while keeping its architecture modular, understandable, and extensible.

## 🔮 Future Development

Possible future directions include:

- Improved voice recognition
- More natural conversational interaction
- Expanded local tool capabilities
- More advanced memory retrieval
- Additional automation
- Improved security and permission management
- Further GUI development

## 👩‍💻 Author

**Aydan Selen Yılmaz**

Engineering • Artificial Intelligence • Robotics

ARIA is an independently developed personal AI assistant project created as part of my exploration of artificial intelligence, software engineering, and intelligent systems.

---

⭐ If you find the project interesting, feel free to explore the source code and follow its development.
