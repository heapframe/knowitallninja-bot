# KnowItAll Ninja — Quiz Automation Bot
> [!NOTE]
> **Archived:** I've finished secondary schooling and can no longer provide updates to this tool.

A browser automation tool that scrapes, caches, and replays quiz answers on the [KnowItAll Ninja](https://www.knowitallninja.com) e-learning platform, with a secondary mode for automated daily XP reward farming via cron.

---

## Overview

This project reverse-engineers the LearnDash / WPProQuiz quiz engine running on a WordPress LMS platform and automates the full quiz lifecycle using Playwright. It handles multiple question types, persists answers locally, and mimics human behaviour with randomised timing to avoid detection.

Two scripts cover two distinct use cases:

| Script | Purpose |
|---|---|
| `scraperbot.py` | Full course scraper — discovers all quizzes, scrapes correct answers on first attempt, caches them, then replays with 100% accuracy |
| `daily20xp.py` | Lightweight daily runner — does the minimum quiz activity to unlock the platform's daily XP reward, then exits (designed for cron) |

---

## Technical Highlights

- **Browser automation** via Playwright (sync API, Chromium) — no headless mode, real browser instance to avoid bot detection
- **Answer caching** using Python `pickle` — 127 quiz answer sets cached to disk, keyed by quiz slug
- **Multi-question-type support:**
  - Multiple choice (label text matching)
  - Fill-in-the-blank / cloze (textbox fill + `input` event dispatch)
  - Drag-and-drop / sort / matrix (DOM `appendChild` into drop zones via `page.evaluate()`)
- **Reverse-engineered quiz engine** — studied the platform's minified WPProQuiz JS source (`main.js`) to understand how `checkAnswers` AJAX requests are formed and validated
- **Scrape-then-replay architecture** — deliberately fails each quiz once to expose correct answers in the DOM, scrapes them, then immediately replays with a perfect score
- **Human-like delay simulation** — configurable `timeBetweenQuestions`, `timeBetweenQuizzes`, and randomised jitter to stay under anti-farming thresholds
- **Speed run mode** — reduces all delays by a configurable factor for bulk scraping runs
- **Credential model** with Pydantic v2 validation
- **Course deduplication** — `recentcourses.txt` tracks completed courses across sessions, cycling back when all are exhausted
- **Graceful degradation** — per-course failure counters, 404 detection, timeout handling

---

## Stack

| | |
|---|---|
| **Language** | Python 3.14 |
| **Browser automation** | Playwright 1.58 |
| **Data validation** | Pydantic v2 |
| **Serialisation** | Python `pickle` |
| **Target platform** | WordPress + LearnDash LMS + WPProQuiz |
| **Deployment** | cron (Linux server) |

---

## Setup

```bash
# Clone and enter the repo
git clone <repo-url>
cd knowitallninja

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright's Chromium browser
playwright install chromium

# Add your credentials
# Edit login.json — replace the placeholder values with your username and password
```

`login.json` ships with a placeholder that the scripts detect at runtime, prompting you interactively if credentials are missing.

---

## Usage

**Step 1 — Scrape and cache all quiz answers:**

```bash
python scraperbot.py
```

This will discover every quiz across all courses, scrape correct answers for any not yet cached, and replay them for a 100% score. Already-cached quizzes are replayed directly without a scrape pass. + You can run this after the first pass for a maxxed out score on everything, obliterating everyone else on the leaderboard

**Step 2 — Run the daily XP farmer:**

```bash
python daily20xp.py
```

Or schedule it via cron:

```cron
0 8 * * * cd /path/to/knowitallninja && venv/bin/python daily20xp.py
```

The script checks for claimable daily rewards before each quiz — as soon as both reward buttons are available, it claims them and exits immediately.

---

## Project Structure

```
knowitallninja/
├── scraperbot.py          # Full course scraper and answer replayer
├── daily20xp.py           # Daily XP farmer (cron-ready)
├── login.json             # Credentials (replace placeholder before use)
├── requirements.txt       # Python dependencies
├── recentcourses.txt      # Runtime state — tracks completed courses
└── answers/               # Cached answer files (one .pckl per quiz slug)
```

---

## How It Works

```
Login → Discover course URLs
         └─ For each course → derive quiz URL from lesson URL
              └─ Quiz cached?
                   ├─ YES → load .pckl → replay answers → submit
                   └─ NO  → submit empty → scrape correct answers from DOM
                             → save to .pckl → replay answers → submit
```

The platform reveals correct answers in the DOM after quiz submission. The bot targets `wpProQuiz_answerCorrectIncomplete` elements for multiple-choice and `ld-quiz__cloze-results--correct-answer` spans for fill-in-the-blank, using injected JavaScript via `page.evaluate()`.

---

## Skills Demonstrated

- Web scraping and browser automation at scale
- Reverse engineering a third-party JavaScript quiz engine
- DOM manipulation via injected JS in an automated browser context
- Designing a cache layer for scraped data
- Scheduling and running automation on a Linux server via cron
- Mimicking human interaction patterns to avoid bot detection
- Clean separation of concerns across two purpose-built scripts
