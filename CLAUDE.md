# Game Review Analyzer

## Project Overview
Portfolio project for a game-industry AI/analytics role. Scrapes
multi-language Google Play reviews of NBA 2K26 MyTEAM Mobile
(com.t2ksports.myteam2k26v2), analyzes them per-review with an
LLM (sentiment, topics, localization issues, summary), and presents
results in a Streamlit dashboard. Includes a human-labelled
calibration experiment (accuracy v1 -> v2 via prompt iteration).

The user communicates in Chinese; reply in Chinese. The user handles
DeepSeek registration, game selection, and human labelling; Claude
Code writes and runs the code. See DEVELOPMENT_PLAN.md for milestones.

## Tech Stack
- Python 3.14 (venv)
- google-play-scraper — review collection (needs access to Google Play;
  may require a proxy in China)
- pandas, plotly, Streamlit
- LLM: DeepSeek API via the openai-compatible client
  (base_url https://api.deepseek.com, model deepseek-chat, temperature=0)
- tenacity for retries, python-dotenv for secrets

## Project Structure
src/
  scraper.py    # fetch en/es/pt/fr/zh-TW reviews -> data/reviews_raw.csv
  prompts.py    # all prompts centralized (few-shot iteration happens here)
  analyzer.py   # per-review LLM analysis, checkpoint/resume, JSON output
app.py          # Streamlit dashboard
data/           # CSVs, gitignored
docs/calibration.md  # human-label calibration results

## Coding Standards
- Structured JSON output from the LLM; strip markdown fences before parsing
- Checkpoint every 20 reviews (resume without re-paying for done rows)
- API key only via .env (DEEPSEEK_API_KEY); never commit .env or data/

## Local Development
- Activate venv: venv\Scripts\Activate.ps1
- Run scraper: python src/scraper.py
- Run analysis: python src/analyzer.py (from src/)
- Dashboard: streamlit run app.py (http://localhost:8501)
