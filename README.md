# Noah (Zem Labs) — MVP

Daily, focused audio briefings based on your interests, in your chosen voice, language, and duration.

## Prereqs
- Python 3.10+
- `ffmpeg` installed:
  - macOS: `brew install ffmpeg`
  - Ubuntu/Debian: `sudo apt-get update && sudo apt-get install ffmpeg`
  - Windows: install ffmpeg and add to PATH.

## Setup
```bash
git clone <this-folder> noah-mvp
cd noah-mvp
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
cp .env.example .env
# Open .env and paste your keys (never commit them)
# Put your Zem Labs logo at assets/logo.png
streamlit run app.py