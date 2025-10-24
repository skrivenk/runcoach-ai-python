# Run Coach AI

**Run Coach AI** is a smart, AI-powered running assistant that helps you plan, analyze, and optimize your workouts.  
It combines performance tracking, adaptive training plans, and AI-driven recommendations — all in a modern, calendar-based desktop app.

---

## Features

- **Calendar-Based Interface** – Visualize and manage training weeks and months easily.  
- **Workout Management** – Add, edit, and categorize runs by type, distance, pace, and time.  
- **AI Recalculation Engine** – Automatically adjusts your training plan based on completed or missed runs.  
- **GPX & Strava Integration (Planned)** – Import run data directly or sync from Strava.  
- **Local Database** – All data is stored locally for privacy and offline use.  
- **Cloud Sync (Future)** – Optional integration with a Flask + PostgreSQL backend for syncing data.  
- **OpenAI Integration (Future)** – Personalized training feedback and AI-based recommendations.

---

## Tech Stack

| Component | Technology |
|------------|-------------|
| Language | Python 3.11+ |
| Framework | PyQt |
| AI Engine | OpenAI GPT API |
| Database | SQLite |
| Version Control | Git + GitHub |
| Optional Backend | Flask + PostgreSQL |

---

## Installation

### 1. Clone the Repository
```bash
git clone https://github.com/<your-username>/runcoach-ai.git
cd runcoach-ai
```

### 2. Create and Activate a Virtual Environment
```bash
python -m venv venv
source venv/bin/activate   # macOS/Linux
venv\Scripts\activate      # Windows
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Set Up Environment Variables
Create a `.env` file in the project root:
```bash
OPENAI_API_KEY=your_api_key_here
```

---

## Usage

Run the app:
```bash
python main.py
```

- Click on days to add or edit workouts  
- View your weekly training summary  
- Recalculate future weeks using the AI module  

---

## Roadmap

- [x] Core calendar and workout management  
- [x] AI recalculation engine  
- [ ] Strava / GPX import  
- [ ] OpenAI training advisor  
- [ ] Performance analytics dashboard  
- [ ] Cloud synchronization  
- [ ] Mobile companion app  

---

## Contact

**Author:** Sergei Krivenkov  
**Portfolio:** [https://sergeik.com](https://sergeik.com)  
**LinkedIn:** [https://linkedin.com/in/skrivenkov](https://linkedin.com/in/skrivenkov)

---
