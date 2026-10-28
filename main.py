"""
Dog Care Planner
A command-line tool for dog carers to manage each dog's daily care routine.

Author: Jingwen Zhao
Subject: 52685 Creative Coding, Spring 2026
Tutorial: Sem09
"""

import json
import os
from datetime import datetime

# ---------- File paths used to persist data between runs ----------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DOGS_FILE = os.path.join(DATA_DIR, "dogs.json")
TASKS_FILE = os.path.join(DATA_DIR, "tasks.json")


class Dog:
    """
    Represents one dog currently in care.

    Holds both identity details (name, breed, age) and the care
    requirements (feeding times, walk length, medication) that are
    later used to automatically generate that dog's daily tasks.
    """

    def __init__(self, name, breed, age, notes="",
                 feeding_times=None, walk_minutes=30, medication=None,
                 photo=""):
        self.name = name
        self.breed = breed
        self.age = age
        self.notes = notes
        # feeding_times is a list of "HH:MM" strings, e.g. ["08:00", "18:00"]
        self.feeding_times = feeding_times if feeding_times else ["08:00", "18:00"]
        self.walk_minutes = walk_minutes
        # medication is a list of dicts: [{"drug": "...", "time": "HH:MM"}, ...]
        self.medication = medication if medication else []
        # photo is the filename of the dog's avatar, stored in uploads/
        self.photo = photo

    def to_dict(self):
        """Convert this Dog into a plain dictionary that JSON can store."""
        return {
            "name": self.name,
            "breed": self.breed,
            "age": self.age,
            "notes": self.notes,
            "feeding_times": self.feeding_times,
            "walk_minutes": self.walk_minutes,
            "medication": self.medication,
            "photo": self.photo,
        }

    @classmethod
    def from_dict(cls, data):
        """Reconstruct a Dog object from a dictionary loaded from disk."""
        return cls(
            name=data["name"],
            breed=data["breed"],
            age=data["age"],
            notes=data.get("notes", ""),
            feeding_times=data.get("feeding_times", ["08:00", "18:00"]),
            walk_minutes=data.get("walk_minutes", 30),
            medication=data.get("medication", []),
            photo=data.get("photo", ""),
        )


class Task:
    """
    A single care task generated for one dog on a specific day.

    category is one of: "feeding", "walking", "medication", "other".
    task_date is a string "YYYY-MM-DD" so tasks from different days
    can coexist in the same list.
    """

    def __init__(self, task_id, dog_name, description, time_slot,
                 category, task_date, completed=False, photo=""):
        self.task_id = task_id
        self.dog_name = dog_name
        self.description = description
        self.time_slot = time_slot
        self.category = category
        self.task_date = task_date
        self.completed = completed
        # photo is the filename of the check-in photo, stored in uploads/
        self.photo = photo

    def mark_done(self):
        """Flip this task's completed flag to True."""
        self.completed = True

    def to_dict(self):
        """Convert this Task into a JSON-serialisable dictionary."""
        return {
            "task_id": self.task_id,
            "dog_name": self.dog_name,
            "description": self.description,
            "time_slot": self.time_slot,
            "category": self.category,
            "task_date": self.task_date,
            "completed": self.completed,
            "photo": self.photo,
        }

    @classmethod
    def from_dict(cls, data):
        """Rebuild a Task object from a dictionary loaded from disk."""
        return cls(
            task_id=data["task_id"],
            dog_name=data["dog_name"],
            description=data["description"],
            time_slot=data["time_slot"],
            category=data["category"],
            task_date=data["task_date"],
            completed=data.get("completed", False),
            photo=data.get("photo", ""),
        )


class CarePlanner:
    """
    The main application.

    It owns the list of dogs and the list of tasks. On start it loads
    both from JSON files; every change is saved back to disk so the
    data survives when the program is closed.
    """

    def __init__(self):
        self.dogs = []
        self.tasks = []
        self._ensure_data_dir()
        self._load()

    # ---------- persistence ----------
    def _ensure_data_dir(self):
        """Create the data/ folder if it does not exist yet."""
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)

    def _load(self):
        """Read dogs.json and tasks.json from disk into memory."""
        if os.path.exists(DOGS_FILE):
            with open(DOGS_FILE, "r", encoding="utf-8") as f:
                raw_dogs = json.load(f)
                self.dogs = [Dog.from_dict(d) for d in raw_dogs]
        if os.path.exists(TASKS_FILE):
            with open(TASKS_FILE, "r", encoding="utf-8") as f:
                raw_tasks = json.load(f)
                self.tasks = [Task.from_dict(t) for t in raw_tasks]

    def _save(self):
        """Write the current dogs and tasks to JSON files."""
        with open(DOGS_FILE, "w", encoding="utf-8") as f:
            json.dump([d.to_dict() for d in self.dogs], f, indent=2)
        with open(TASKS_FILE, "w", encoding="utf-8") as f:
            json.dump([t.to_dict() for t in self.tasks], f, indent=2)

    # ---------- dog operations ----------
    def add_dog(self):
        """Ask the carer for dog details and append a new Dog to the list."""
        print("\n--- Add a new dog ---")
        name = input("Dog name: ").strip()
        # prevent two dogs with the same name from conflicting
        if any(d.name.lower() == name.lower() for d in self.dogs):
            print("A dog with this name already exists.")
            return

        breed = input("Breed: ").strip()
        age = input("Age (years): ").strip()
        notes = input("Special care notes (e.g. food allergy): ").strip()

        feed_input = input("Feeding times, comma separated [default: 08:00,18:00]: ").strip()
        if feed_input:
            feeding_times = [t.strip() for t in feed_input.split(",") if t.strip()]
        else:
            feeding_times = ["08:00", "18:00"]

        walk_input = input("Daily walk in minutes [default: 30]: ").strip()
        walk_minutes = int(walk_input) if walk_input.isdigit() else 30

        med_input = input("Medication, format 'drug@time' separated by ';', or leave blank: ").strip()
        medication = []
        if med_input:
            for item in med_input.split(";"):
                item = item.strip()
                if "@" in item:
                    drug, time = item.split("@", 1)
                    medication.append({"drug": drug.strip(), "time": time.strip()})

        dog = Dog(name, breed, age, notes, feeding_times, walk_minutes, medication)
        self.dogs.append(dog)
        self._save()
        print(f"Added {name} the {breed}.")

    def list_dogs(self):
        """Print a summary of every dog currently in care."""
        if not self.dogs:
            print("No dogs registered yet.")
            return
        print("\n--- Dogs in care ---")
        for i, d in enumerate(self.dogs, 1):
            print(f"{i}. {d.name} | {d.breed} | {d.age} years")
            if d.notes:
                print(f"   notes: {d.notes}")

    # ---------- task operations ----------
    def generate_daily_tasks(self):
        """
        Build today's task list from scratch based on each dog's care
        requirements. Any tasks previously generated for today are
        replaced, so the carer can safely re-run this.
        """
        today = datetime.now().strftime("%Y-%m-%d")
        # keep tasks from other days, drop today's so we can regenerate
        self.tasks = [t for t in self.tasks if t.task_date != today]

        if not self.dogs:
            print("No dogs registered. Add a dog first.")
            return

        # new task ids continue from the largest existing id
        next_id = max([t.task_id for t in self.tasks], default=0) + 1

        for dog in self.dogs:
            # one feeding task per feeding time
            for t in dog.feeding_times:
                self.tasks.append(Task(
                    task_id=next_id,
                    dog_name=dog.name,
                    description=f"Feed {dog.name}",
                    time_slot=t,
                    category="feeding",
                    task_date=today,
                ))
                next_id += 1

            # one walking task
            self.tasks.append(Task(
                task_id=next_id,
                dog_name=dog.name,
                description=f"Walk {dog.name} for {dog.walk_minutes} minutes",
                time_slot="15:00",
                category="walking",
                task_date=today,
            ))
            next_id += 1

            # one medication task per medication entry
            for med in dog.medication:
                self.tasks.append(Task(
                    task_id=next_id,
                    dog_name=dog.name,
                    description=f"Give {dog.name} {med['drug']}",
                    time_slot=med["time"],
                    category="medication",
                    task_date=today,
                ))
                next_id += 1

        self._save()
        count = sum(1 for t in self.tasks if t.task_date == today)
        print(f"Generated {count} tasks for today ({today}).")

    def list_today_tasks(self):
        """Print today's tasks sorted by time of day."""
        today = datetime.now().strftime("%Y-%m-%d")
        todays = [t for t in self.tasks if t.task_date == today]
        if not todays:
            print("No tasks for today yet. Choose option 3 to generate them.")
            return
        todays.sort(key=lambda t: t.time_slot)
        print(f"\n--- Today's tasks ({today}) ---")
        for t in todays:
            mark = "[x]" if t.completed else "[ ]"
            print(f"{mark} #{t.task_id} {t.time_slot} | {t.dog_name} | "
                  f"{t.description} ({t.category})")

    def complete_task(self):
        """Let the carer enter a task id and mark it as done."""
        today = datetime.now().strftime("%Y-%m-%d")
        self.list_today_tasks()
        choice = input("Enter the task number (#) to mark complete: ").strip()
        if not choice.isdigit():
            print("Please enter a number.")
            return
        task_id = int(choice)
        for t in self.tasks:
            if t.task_id == task_id and t.task_date == today:
                t.mark_done()
                self._save()
                print(f"Task #{task_id} marked as done.")
                return
        print("Task not found for today.")

    def daily_summary(self):
        """Show how many tasks are done, broken down by category."""
        today = datetime.now().strftime("%Y-%m-%d")
        todays = [t for t in self.tasks if t.task_date == today]
        if not todays:
            print("No tasks for today.")
            return
        done = sum(1 for t in todays if t.completed)
        total = len(todays)
        pct = int(done / total * 100) if total else 0
        print("\n--- Today's summary ---")
        print(f"Dogs in care: {len(self.dogs)}")
        print(f"Tasks total: {total}")
        print(f"Completed: {done} ({pct}%)")

        # group tasks by category to show progress per care type
        cats = {}
        for t in todays:
            cats.setdefault(t.category, {"done": 0, "total": 0})
            cats[t.category]["total"] += 1
            if t.completed:
                cats[t.category]["done"] += 1
        for cat, c in cats.items():
            print(f"  - {cat}: {c['done']}/{c['total']} done")

    # ---------- main loop ----------
    def run(self):
        """Print the menu repeatedly until the carer chooses to exit."""
        menu = """
=== Dog Care Planner ===
1. Add a dog
2. View all dogs
3. Generate today's care tasks
4. View today's tasks
5. Mark a task as complete
6. View today's summary
7. Exit
"""
        while True:
            print(menu)
            choice = input("Choose an option: ").strip()
            if choice == "1":
                self.add_dog()
            elif choice == "2":
                self.list_dogs()
            elif choice == "3":
                self.generate_daily_tasks()
            elif choice == "4":
                self.list_today_tasks()
            elif choice == "5":
                self.complete_task()
            elif choice == "6":
                self.daily_summary()
            elif choice == "7":
                self._save()
                print("Saving data. Goodbye!")
                break
            else:
                print("Invalid choice, try again.")


if __name__ == "__main__":
    app = CarePlanner()
    app.run()
