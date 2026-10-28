"""Seed realistic historical tasks for the last 14 days so the dashboard,
summary and calendar pages have something to show. Today's existing tasks
are left untouched."""
import json, os, random
from datetime import datetime, timedelta

random.seed(42)

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "data")

with open(os.path.join(DATA, "dogs.json"), "r", encoding="utf-8") as f:
    dogs = json.load(f)

with open(os.path.join(DATA, "tasks.json"), "r", encoding="utf-8") as f:
    tasks = json.load(f)

today = datetime.now().strftime("%Y-%m-%d")
existing_ids = [t["task_id"] for t in tasks]
next_id = max(existing_ids) + 1 if existing_ids else 1

# drop today's tasks for now (we keep them later)
old_today = [t for t in tasks if t["task_date"] == today]
historical = [t for t in tasks if t["task_date"] != today]

new_tasks = []
for days_ago in range(14, 0, -1):
    d = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")
    for dog in dogs:
        name = dog["name"]
        # feeding tasks
        for ft in dog.get("feeding_times", ["08:00", "18:00"]):
            new_tasks.append({
                "task_id": next_id, "dog_name": name,
                "description": f"Feed {name}", "time_slot": ft,
                "category": "feeding", "task_date": d,
                "completed": False, "photo": ""
            })
            next_id += 1
        # walk task
        walk_min = dog.get("walk_minutes", 30)
        new_tasks.append({
            "task_id": next_id, "dog_name": name,
            "description": f"Walk {name} for {walk_min} minutes",
            "time_slot": "15:00", "category": "walking", "task_date": d,
            "completed": False, "photo": ""
        })
        next_id += 1
        # medication
        for med in dog.get("medication", []):
            new_tasks.append({
                "task_id": next_id, "dog_name": name,
                "description": f"Give {name} {med['drug']}",
                "time_slot": med["time"], "category": "medication",
                "task_date": d, "completed": False, "photo": ""
            })
            next_id += 1

# randomly complete ~75% of historical tasks, with some days busier than others
for t in new_tasks:
    # vary completion rate by day: 55% - 95%
    day_factor = random.uniform(0.55, 0.95)
    t["completed"] = random.random() < day_factor

# combine: old historical + newly generated + today's
all_tasks = historical + new_tasks + old_today
all_tasks.sort(key=lambda x: (x["task_date"], x["time_slot"]))

with open(os.path.join(DATA, "tasks.json"), "w", encoding="utf-8") as f:
    json.dump(all_tasks, f, indent=2, ensure_ascii=False)

print(f"Seeded {len(new_tasks)} historical tasks across 14 days.")
print(f"Total tasks now: {len(all_tasks)}")
