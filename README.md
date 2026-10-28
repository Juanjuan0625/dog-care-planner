# Dog Care Planner

A web app for dog boarders / foster carers to manage daily care routines
(feeding, walking, medication), check off tasks, and review completion
history. Built with Python + Flask as a local web prototype.

## Quick start

```bash
pip install -r requirements.txt
python app.py
```

Then open http://127.0.0.1:5000 in your browser.

## Features

- **Dashboard** — today's completion rate, quick actions, your dogs, 7-day trend.
- **Dogs** — add / edit / delete dogs, view per-dog care info and task history.
- **Tasks** — daily check-off board with category filters (feeding / walking / medication).
- **History** — monthly calendar view, click any day to see its tasks.
- **Summary** — weekly / monthly completion rates, dog leaderboard, category breakdown.

## Project structure

```
dog_care_planner/
├── app.py              # Flask routes and request handling
├── main.py             # core Dog / Task classes and JSON storage
├── seed_data.py        # generates 14 days of demo history
├── requirements.txt
├── README.md
├── data/
│   ├── dogs.json       # dog records
│   └── tasks.json      # task records
├── templates/          
└── uploads/           
```

## Data model

- **Dog**: name, breed, age, notes, feeding_times[], walk_minutes, medication[].
- **Task**: task_id, dog_name, description, time_slot, category, task_date, completed, photo.

Data is persisted to local JSON files — no database needed.

## Reset demo data

To wipe everything and regenerate 14 days of sample history:

```bash
python seed_data.py
```

