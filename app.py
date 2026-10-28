"""
Dog Care Planner — Web version (Flask)

Same project as main.py (the command-line version), but served as a small
website in the browser. It reuses the Dog and Task classes from main.py
and reads/writes the same JSON files, so both versions share one dataset.

Run with:
    python app.py
Then open http://127.0.0.1:5000 in your browser.
"""

import json
import os
from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash
from werkzeug.utils import secure_filename

# Reuse the data classes from the command-line version.
from main import Dog, Task

app = Flask(__name__)
app.secret_key = "dog-care-planner-local-dev"

# ---------- paths ----------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DOGS_FILE = os.path.join(DATA_DIR, "dogs.json")
TASKS_FILE = os.path.join(DATA_DIR, "tasks.json")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# only allow image uploads
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def is_valid_time(t):
    """Check that a string is a valid HH:MM time."""
    try:
        h, m = t.split(":")
        h, m = int(h), int(m)
        return 0 <= h <= 23 and 0 <= m <= 59
    except (ValueError, AttributeError):
        return False


# ---------- data loading / saving ----------
def load_dogs():
    if not os.path.exists(DOGS_FILE):
        return []
    with open(DOGS_FILE, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return [Dog.from_dict(d) for d in raw]


def save_dogs(dogs):
    with open(DOGS_FILE, "w", encoding="utf-8") as f:
        json.dump([d.to_dict() for d in dogs], f, indent=2)


def load_tasks():
    if not os.path.exists(TASKS_FILE):
        return []
    with open(TASKS_FILE, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return [Task.from_dict(t) for t in raw]


def save_tasks(tasks):
    with open(TASKS_FILE, "w", encoding="utf-8") as f:
        json.dump([t.to_dict() for t in tasks], f, indent=2)


# ---------- serve uploaded images ----------
@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_DIR, filename)


# ---------- pages ----------
@app.route("/")
def dashboard():
    """Landing dashboard: today's status at a glance."""
    from datetime import timedelta
    today = datetime.now().strftime("%Y-%m-%d")
    tasks = load_tasks()
    dogs = load_dogs()

    todays = [t for t in tasks if t.task_date == today]
    done = sum(1 for t in todays if t.completed)
    total = len(todays)
    pct = int(done/total*100) if total else 0

    # last 7 days mini bars
    week = []
    for i in range(6, -1, -1):
        d = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        day_tasks = [t for t in tasks if t.task_date == d]
        dd = sum(1 for t in day_tasks if t.completed)
        dt = len(day_tasks)
        week.append({"date": d, "done": dd, "total": dt,
                     "pct": int(dd/dt*100) if dt else 0})

    return render_template("dashboard.html",
                           today=today, dogs=dogs,
                           done=done, total=total, pct=pct, week=week)


@app.route("/tasks")
def tasks_today():
    """Home page: today's tasks and completion summary."""
    today = datetime.now().strftime("%Y-%m-%d")
    tasks = load_tasks()
    todays = [t for t in tasks if t.task_date == today]
    todays.sort(key=lambda t: t.time_slot)

    # optional category filter
    category = request.args.get("category", "")
    if category:
        todays = [t for t in todays if t.category == category]

    done = sum(1 for t in todays if t.completed)
    total = len(todays)
    pct = int(done / total * 100) if total else 0

    # build a 7-day completion summary for the stats panel
    from datetime import timedelta
    week = []
    for i in range(6, -1, -1):
        d = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        day_tasks = [t for t in tasks if t.task_date == d]
        day_done = sum(1 for t in day_tasks if t.completed)
        day_total = len(day_tasks)
        day_pct = int(day_done / day_total * 100) if day_total else 0
        week.append({"date": d, "done": day_done, "total": day_total, "pct": day_pct})

    return render_template("index.html",
                           today=today,
                           tasks=todays,
                           done=done,
                           total=total,
                           pct=pct,
                           week=week,
                           category=category)


@app.route("/generate")
def generate():
    """Rebuild today's tasks from every dog's care requirements."""
    today = datetime.now().strftime("%Y-%m-%d")
    dogs = load_dogs()
    tasks = load_tasks()
    tasks = [t for t in tasks if t.task_date != today]

    next_id = max([t.task_id for t in tasks], default=0) + 1

    for dog in dogs:
        for t in dog.feeding_times:
            tasks.append(Task(next_id, dog.name, f"Feed {dog.name}",
                              t, "feeding", today))
            next_id += 1
        tasks.append(Task(next_id, dog.name,
                          f"Walk {dog.name} for {dog.walk_minutes} minutes",
                          "15:00", "walking", today))
        next_id += 1
        for med in dog.medication:
            tasks.append(Task(next_id, dog.name,
                              f"Give {dog.name} {med['drug']}",
                              med["time"], "medication", today))
            next_id += 1

    save_tasks(tasks)
    return redirect(url_for("tasks_today"))


@app.route("/checkin/<int:task_id>", methods=["POST"])
def checkin(task_id):
    """Mark a task done, optionally attaching a check-in photo."""
    photo_filename = ""
    if "photo" in request.files:
        f = request.files["photo"]
        if f and f.filename and allowed_file(f.filename):
            # prefix with task id so names stay unique
            safe = secure_filename(f.filename)
            photo_filename = f"task_{task_id}_{safe}"
            f.save(os.path.join(UPLOAD_DIR, photo_filename))

    tasks = load_tasks()
    for t in tasks:
        if t.task_id == task_id:
            t.mark_done()
            if photo_filename:
                t.photo = photo_filename
            break
    save_tasks(tasks)
    return redirect(url_for("tasks_today"))


@app.route("/dogs")
def dogs_page():
    """Show every dog currently in care."""
    dogs = load_dogs()
    return render_template("dogs.html", dogs=dogs)


@app.route("/dog/<dog_name>")
def dog_detail(dog_name):
    """Single dog detail page: info, photo, and all their tasks."""
    from datetime import timedelta
    dogs = load_dogs()
    dog = next((d for d in dogs if d.name == dog_name), None)
    if not dog:
        return redirect(url_for("dogs_page"))

    tasks = load_tasks()
    dog_tasks = [t for t in tasks if t.dog_name == dog_name]
    dog_tasks.sort(key=lambda t: (t.task_date, t.time_slot), reverse=True)

    # optional: filter by a specific date
    selected_date = request.args.get("date", "")
    if selected_date:
        tasks_for_view = [t for t in dog_tasks if t.task_date == selected_date]
        show_all = True
        count_other = 0
    else:
        # by default only show recent 7 days; ?all=1 shows everything
        show_all = request.args.get("all") == "1"
        if not show_all:
            from datetime import timedelta
            cutoff = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
            tasks_for_view = [t for t in dog_tasks if t.task_date >= cutoff]
            count_other = len(dog_tasks) - len(tasks_for_view)
        else:
            tasks_for_view = dog_tasks
            count_other = 0

    done = sum(1 for t in dog_tasks if t.completed)
    total = len(dog_tasks)
    pct = int(done / total * 100) if total else 0

    # streak: consecutive days with at least one completed task for this dog
    streak = 0
    cursor = datetime.now()
    def dog_has_completed(day):
        ds = day.strftime("%Y-%m-%d")
        return any(t.dog_name == dog_name and t.task_date == ds and t.completed for t in tasks)
    if not dog_has_completed(cursor):
        cursor = cursor - timedelta(days=1)
    while dog_has_completed(cursor):
        streak += 1
        cursor = cursor - timedelta(days=1)

    return render_template("dog_detail.html",
                           dog=dog, tasks=tasks_for_view,
                           done=done, total=total, pct=pct, streak=streak,
                           show_all=show_all, count_other=count_other,
                           selected_date=selected_date)


@app.route("/upload_photo/<dog_name>", methods=["POST"])
def upload_dog_photo(dog_name):
    """Upload or replace a dog's avatar photo."""
    if "photo" not in request.files:
        return redirect(url_for("dog_detail", dog_name=dog_name))
    f = request.files["photo"]
    if not f or not f.filename or not allowed_file(f.filename):
        return redirect(url_for("dog_detail", dog_name=dog_name))

    safe = secure_filename(f.filename)
    filename = f"dog_{dog_name}_{safe}"
    f.save(os.path.join(UPLOAD_DIR, filename))

    dogs = load_dogs()
    for d in dogs:
        if d.name == dog_name:
            d.photo = filename
            break
    save_dogs(dogs)
    flash("Photo updated.", "success")
    return redirect(url_for("dog_detail", dog_name=dog_name))


@app.route("/dog/<dog_name>/edit", methods=["GET", "POST"])
def edit_dog(dog_name):
    """Edit an existing dog's details."""
    dogs = load_dogs()
    dog = next((d for d in dogs if d.name == dog_name), None)
    if not dog:
        flash("Dog not found.", "error")
        return redirect(url_for("dogs_page"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        breed = request.form.get("breed", "").strip()
        age_raw = request.form.get("age", "").strip()
        notes = request.form.get("notes", "").strip()
        breakfast = request.form.get("breakfast_time", "08:00").strip()
        dinner = request.form.get("dinner_time", "18:00").strip()
        walk_raw = request.form.get("walk_minutes", "30").strip()
        med_name = request.form.get("med_name", "").strip()
        med_time = request.form.get("med_time", "").strip()

        errors = []
        if not name:
            errors.append("Name is required.")
        elif len(name) < 2 or len(name) > 30:
            errors.append("Name must be between 2 and 30 characters.")
        elif any(d.name.lower() == name.lower() and d.name != dog_name for d in dogs):
            errors.append(f"A dog named '{name}' already exists.")
        if not breed:
            errors.append("Breed is required.")
        elif len(breed) > 50:
            errors.append("Breed must be at most 50 characters.")
        age = None
        if not age_raw:
            errors.append("Age is required.")
        elif not age_raw.isdigit():
            errors.append("Age must be a whole number.")
        else:
            age = int(age_raw)
            if age < 1 or age > 15:
                errors.append("Age must be between 1 and 15.")
        if len(notes) > 200:
            errors.append("Notes must be at most 200 characters.")

        feeding_times = [t for t in [breakfast, dinner] if t and is_valid_time(t)]
        if not feeding_times:
            errors.append("Pick at least one valid feeding time.")

        walk_minutes = int(walk_raw) if walk_raw.isdigit() else 30

        medication = []
        if med_name:
            if not med_time or not is_valid_time(med_time):
                errors.append("Pick a valid time for the medication.")
            else:
                medication = [{"drug": med_name, "time": med_time}]

        if errors:
            old = {"name": name, "breed": breed, "age": age_raw, "notes": notes,
                   "breakfast_time": breakfast, "dinner_time": dinner,
                   "walk_minutes": walk_raw, "med_name": med_name, "med_time": med_time}
            return render_template("edit_dog.html", dog=dog, errors=errors, old=old)

        # optional new photo
        photo_filename = dog.photo
        if "photo" in request.files:
            f = request.files["photo"]
            if f and f.filename and allowed_file(f.filename):
                safe = secure_filename(f.filename)
                photo_filename = f"dog_{name}_{safe}"
                f.save(os.path.join(UPLOAD_DIR, photo_filename))

        # if the dog was renamed, update its tasks too
        renamed = name != dog_name
        old_name = dog.name
        dog.name = name
        dog.breed = breed
        dog.age = age
        dog.notes = notes
        dog.feeding_times = feeding_times
        dog.walk_minutes = walk_minutes
        dog.medication = medication
        dog.photo = photo_filename
        save_dogs(dogs)

        if renamed:
            tasks = load_tasks()
            for t in tasks:
                if t.dog_name == old_name:
                    t.dog_name = name
            save_tasks(tasks)

        flash(f"{name} updated.", "success")
        return redirect(url_for("dog_detail", dog_name=name))

    # pre-fill the form with the dog's current values
    old = {"name": dog.name, "breed": dog.breed, "age": str(dog.age),
           "notes": dog.notes, "walk_minutes": str(dog.walk_minutes),
           "breakfast_time": dog.feeding_times[0] if dog.feeding_times else "08:00",
           "dinner_time": dog.feeding_times[1] if len(dog.feeding_times) > 1 else "18:00",
           "med_name": dog.medication[0]["drug"] if dog.medication else "",
           "med_time": dog.medication[0]["time"] if dog.medication else ""}
    return render_template("edit_dog.html", dog=dog, errors=[], old=old)


@app.route("/dog/<dog_name>/delete", methods=["POST"])
def delete_dog(dog_name):
    """Delete a dog and all of its tasks."""
    dogs = load_dogs()
    dogs = [d for d in dogs if d.name != dog_name]
    save_dogs(dogs)

    tasks = load_tasks()
    tasks = [t for t in tasks if t.dog_name != dog_name]
    save_tasks(tasks)

    flash(f"{dog_name} removed.", "success")
    return redirect(url_for("dogs_page"))


@app.route("/uncheck/<int:task_id>")
def uncheck(task_id):
    """Undo a completed task (set it back to pending)."""
    tasks = load_tasks()
    for t in tasks:
        if t.task_id == task_id:
            t.completed = False
            t.photo = ""
            break
    save_tasks(tasks)
    return redirect(request.referrer or url_for("tasks_today"))


@app.route("/add_dog", methods=["GET", "POST"])
def add_dog():
    """Show the add-dog form (GET) and accept its submission (POST)."""
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        breed = request.form.get("breed", "").strip()
        age_raw = request.form.get("age", "").strip()
        notes = request.form.get("notes", "").strip()
        breakfast = request.form.get("breakfast_time", "08:00").strip()
        dinner = request.form.get("dinner_time", "18:00").strip()
        walk_raw = request.form.get("walk_minutes", "30").strip()
        med_name = request.form.get("med_name", "").strip()
        med_time = request.form.get("med_time", "").strip()

        errors = []
        if not name:
            errors.append("Name is required.")
        elif len(name) < 2 or len(name) > 30:
            errors.append("Name must be between 2 and 30 characters.")
        elif any(d.name.lower() == name.lower() for d in load_dogs()):
            errors.append(f"A dog named '{name}' already exists.")
        if not breed:
            errors.append("Breed is required.")
        elif len(breed) > 50:
            errors.append("Breed must be at most 50 characters.")
        age = None
        if not age_raw:
            errors.append("Age is required.")
        elif not age_raw.isdigit():
            errors.append("Age must be a whole number.")
        else:
            age = int(age_raw)
            if age < 1 or age > 15:
                errors.append("Age must be between 1 and 15.")
        if len(notes) > 200:
            errors.append("Notes must be at most 200 characters.")

        feeding_times = [t for t in [breakfast, dinner] if t and is_valid_time(t)]
        if not feeding_times:
            errors.append("Pick at least one valid feeding time.")

        walk_minutes = int(walk_raw) if walk_raw.isdigit() else 30

        medication = []
        if med_name:
            if not med_time or not is_valid_time(med_time):
                errors.append("Pick a valid time for the medication.")
            else:
                medication = [{"drug": med_name, "time": med_time}]

        if errors:
            old = {"name": name, "breed": breed, "age": age_raw, "notes": notes,
                   "breakfast_time": breakfast, "dinner_time": dinner,
                   "walk_minutes": walk_raw, "med_name": med_name, "med_time": med_time}
            return render_template("add_dog.html", errors=errors, old=old)

        photo_filename = ""
        if "photo" in request.files:
            f = request.files["photo"]
            if f and f.filename and allowed_file(f.filename):
                safe = secure_filename(f.filename)
                photo_filename = f"dog_{name}_{safe}"
                f.save(os.path.join(UPLOAD_DIR, photo_filename))

        dogs = load_dogs()
        dogs.append(Dog(name, breed, age, notes,
                        feeding_times, walk_minutes, medication,
                        photo=photo_filename))
        save_dogs(dogs)
        return redirect(url_for("dog_detail", dog_name=name))

    return render_template("add_dog.html", errors=[], old={})


@app.route("/history")
def history():
    """Show tasks for a chosen date (defaults to today), with a mini month calendar on top."""
    from calendar import monthrange
    date_str = request.args.get("date", datetime.now().strftime("%Y-%m-%d"))
    tasks = load_tasks()
    day_tasks = [t for t in tasks if t.task_date == date_str]
    day_tasks.sort(key=lambda t: t.time_slot)

    done = sum(1 for t in day_tasks if t.completed)
    total = len(day_tasks)
    pct = int(done / total * 100) if total else 0

    # collect all dates that have tasks, for a small date picker
    all_dates = sorted({t.task_date for t in tasks}, reverse=True)

    # --- build mini month calendar on top of the page ---
    by_date = {}
    for t in tasks:
        by_date.setdefault(t.task_date, {"done": 0, "total": 0})
        by_date[t.task_date]["total"] += 1
        if t.completed:
            by_date[t.task_date]["done"] += 1

    # which month are we showing? use the selected date's month
    y, m, _ = [int(x) for x in date_str.split("-")]
    first_weekday = datetime(y, m, 1).weekday()
    days_in_month = monthrange(y, m)[1]
    cells = [None] * first_weekday
    for d in range(1, days_in_month + 1):
        ds = f"{y:04d}-{m:02d}-{d:02d}"
        info = by_date.get(ds, {"done": 0, "total": 0})
        cells.append({"date": ds, "day": d,
                      "done": info["done"], "total": info["total"],
                      "pct": int(info["done"]/info["total"]*100) if info["total"] else 0})
    while len(cells) % 7 != 0:
        cells.append(None)

    today_str = datetime.now().strftime("%Y-%m-%d")

    return render_template("history.html",
                           date=date_str,
                           tasks=day_tasks,
                           done=done, total=total, pct=pct,
                           all_dates=all_dates,
                           cells=cells, year=y, month=m, today_str=today_str)


@app.route("/calendar")
def calendar():
    """Show a monthly calendar with completion summary per day."""
    from calendar import monthrange
    today = datetime.now()
    year = request.args.get("year", today.year, type=int)
    month = request.args.get("month", today.month, type=int)

    tasks = load_tasks()
    by_date = {}
    for t in tasks:
        by_date.setdefault(t.task_date, {"done": 0, "total": 0})
        by_date[t.task_date]["total"] += 1
        if t.completed:
            by_date[t.task_date]["done"] += 1

    first_weekday = datetime(year, month, 1).weekday()
    days_in_month = monthrange(year, month)[1]
    cells = [None] * first_weekday
    for d in range(1, days_in_month + 1):
        ds = f"{year:04d}-{month:02d}-{d:02d}"
        info = by_date.get(ds, {"done": 0, "total": 0})
        cells.append({"date": ds, "day": d,
                      "done": info["done"], "total": info["total"],
                      "pct": int(info["done"]/info["total"]*100) if info["total"] else 0})
    while len(cells) % 7 != 0:
        cells.append(None)

    prev_m = month - 1; prev_y = year
    if prev_m < 1: prev_m = 12; prev_y -= 1
    next_m = month + 1; next_y = year
    if next_m > 12: next_m = 1; next_y += 1

    today_str = today.strftime("%Y-%m-%d")
    return render_template("calendar.html",
                           year=year, month=month,
                           cells=cells, today_str=today_str,
                           prev_y=prev_y, prev_m=prev_m,
                           next_y=next_y, next_m=next_m)


@app.route("/category/<cat>")
def category_detail(cat):
    """Show all historical tasks of one category (across all days and dogs)."""
    tasks = load_tasks()
    cat_tasks = [t for t in tasks if t.category == cat]
    cat_tasks.sort(key=lambda t: (t.task_date, t.time_slot), reverse=True)
    done = sum(1 for t in cat_tasks if t.completed)
    total = len(cat_tasks)
    pct = int(done/total*100) if total else 0
    return render_template("category.html",
                           cat=cat, tasks=cat_tasks,
                           done=done, total=total, pct=pct)


@app.route("/summary")
def summary():
    """Weekly and monthly summary: completion rates, dog leaderboard, category breakdown."""
    from datetime import timedelta
    tasks = load_tasks()
    dogs = load_dogs()

    # ---- last 7 days (week) ----
    week = []
    for i in range(6, -1, -1):
        d = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        day_tasks = [t for t in tasks if t.task_date == d]
        done = sum(1 for t in day_tasks if t.completed)
        total = len(day_tasks)
        pct = int(done/total*100) if total else 0
        week.append({"date": d, "done": done, "total": total, "pct": pct})
    week_done = sum(w["done"] for w in week)
    week_total = sum(w["total"] for w in week)
    week_pct = int(week_done/week_total*100) if week_total else 0

    # ---- current month ----
    today = datetime.now()
    month_prefix = today.strftime("%Y-%m")
    month_tasks = [t for t in tasks if t.task_date.startswith(month_prefix)]
    month_done = sum(1 for t in month_tasks if t.completed)
    month_total = len(month_tasks)
    month_pct = int(month_done/month_total*100) if month_total else 0
    # per-day mini grid for the month
    month_days = []
    for i in range(1, today.day + 1):
        ds = f"{month_prefix}-{i:02d}"
        day_tasks = [t for t in tasks if t.task_date == ds]
        done = sum(1 for t in day_tasks if t.completed)
        total = len(day_tasks)
        pct = int(done/total*100) if total else 0
        month_days.append({"date": ds, "day": i, "done": done, "total": total, "pct": pct})

    # ---- per-dog leaderboard ----
    dog_stats = []
    for d in dogs:
        d_tasks = [t for t in tasks if t.dog_name == d.name]
        done = sum(1 for t in d_tasks if t.completed)
        total = len(d_tasks)
        pct = int(done/total*100) if total else 0
        # streak: consecutive days (ending today or yesterday) with >=1 completed task
        streak = 0
        cursor = datetime.now()
        # if today has no completed task yet, streak can still count up to yesterday
        def has_completed(day):
            ds = day.strftime("%Y-%m-%d")
            return any(t.task_date == ds and t.completed for t in tasks)
        if not has_completed(cursor):
            cursor = cursor - timedelta(days=1)
        while has_completed(cursor):
            streak += 1
            cursor = cursor - timedelta(days=1)
        dog_stats.append({"name": d.name, "done": done, "total": total,
                          "pct": pct, "streak": streak})
    dog_stats.sort(key=lambda x: x["pct"], reverse=True)

    # ---- per-category breakdown ----
    cats = {}
    for t in tasks:
        cats.setdefault(t.category, {"done": 0, "total": 0})
        cats[t.category]["total"] += 1
        if t.completed:
            cats[t.category]["done"] += 1
    cat_stats = []
    for c, v in cats.items():
        pct = int(v["done"]/v["total"]*100) if v["total"] else 0
        cat_stats.append({"category": c, "done": v["done"], "total": v["total"], "pct": pct})
    cat_stats.sort(key=lambda x: x["pct"])

    return render_template("summary.html",
                           week=week, week_done=week_done, week_total=week_total, week_pct=week_pct,
                           month_pct=month_pct, month_done=month_done, month_total=month_total,
                           month_days=month_days,
                           dog_stats=dog_stats, cat_stats=cat_stats)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
