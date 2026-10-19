"""PawPal+ logic layer: backend classes for owners, pets, tasks, and scheduling."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field, fields, replace
from datetime import date, timedelta
from itertools import combinations
from pathlib import Path
from typing import Optional, Union

PRIORITY_RANKS = {"low": 1, "medium": 2, "high": 3}
FREQUENCIES = ("daily", "weekly")
# How far after completion the next occurrence of a recurring task is due.
RECURRENCE_GAP = {"daily": timedelta(days=1), "weekly": timedelta(weeks=1)}
# Order used to place flexible tasks through the day; None (no preference) goes last.
TIME_OF_DAY_ORDER = {"morning": 0, "afternoon": 1, "evening": 2, None: 3}
# Earliest start for a flexible task with this preference ("morning" starts at the owner's day_start).
TIME_OF_DAY_START = {"afternoon": "12:00", "evening": "17:00"}
# Bumped if the data.json layout ever changes, so old files can be recognized.
DATA_VERSION = 1
DATE_FIELDS = ("due_date", "last_completed")


def to_minutes(hhmm: str) -> int:
    """Convert a "HH:MM" string to minutes after midnight."""
    hours, minutes = hhmm.split(":")
    return int(hours) * 60 + int(minutes)


def to_hhmm(minutes: int) -> str:
    """Convert minutes after midnight to a "HH:MM" string."""
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


@dataclass
class Task:
    """A single pet care activity, such as a walk, feeding, or medication."""

    title: str
    duration_minutes: int
    priority: str  # "low", "medium", or "high"
    preferred_time: Optional[str] = None  # "morning", "afternoon", or "evening"
    start_time: Optional[str] = None  # fixed "HH:MM" time, e.g. meds at "08:00"
    frequency: str = "daily"  # "daily" or "weekly"
    due_date: Optional[date] = None  # None means due now; set on the next occurrence of a recurring task
    completed: bool = False
    last_completed: Optional[date] = None
    pet_name: str = ""  # set by Pet.add_task so the plan can say which pet a task is for

    def __post_init__(self) -> None:
        """Normalize priority and reject invalid priority, frequency, preferred_time, or duration."""
        self.priority = self.priority.lower()
        if self.priority not in PRIORITY_RANKS:
            raise ValueError(f"priority must be low, medium, or high, not {self.priority!r}")
        if self.frequency not in FREQUENCIES:
            raise ValueError(f"frequency must be daily or weekly, not {self.frequency!r}")
        if self.preferred_time not in TIME_OF_DAY_ORDER:
            raise ValueError(f"preferred_time must be morning, afternoon, or evening, not {self.preferred_time!r}")
        if self.duration_minutes <= 0:
            raise ValueError("duration_minutes must be greater than 0")
        if self.start_time is not None:
            # Check the format here so the scheduler never crashes on a bad time later.
            try:
                hours, minutes = (int(part) for part in self.start_time.split(":"))
            except ValueError:
                raise ValueError(f"start_time must look like HH:MM, not {self.start_time!r}") from None
            if not (0 <= hours < 24 and 0 <= minutes < 60):
                raise ValueError(f"start_time must be a real time of day, not {self.start_time!r}")

    def priority_rank(self) -> int:
        """Return a number for sorting: low=1, medium=2, high=3."""
        return PRIORITY_RANKS[self.priority]

    def is_due_today(self, day: date) -> bool:
        """Return True if this task is not done yet and its due date has arrived (or it has none)."""
        return not self.completed and (self.due_date is None or self.due_date <= day)

    def next_occurrence(self, day: date) -> Task:
        """Return a fresh copy of this task, due one day (daily) or one week (weekly) after the given day."""
        return replace(self, due_date=day + RECURRENCE_GAP[self.frequency], completed=False, last_completed=None)

    def mark_complete(self, day: date) -> Task:
        """Mark this task as done on the given day and return its next occurrence."""
        self.completed = True
        self.last_completed = day
        return self.next_occurrence(day)

    def to_dict(self) -> dict:
        """Return this task as JSON-ready data: dates become "YYYY-MM-DD" strings, pet_name is left out."""
        data = asdict(self)
        del data["pet_name"]  # rebuilt by Pet.add_task when loading
        for name in DATE_FIELDS:
            if data[name] is not None:
                data[name] = data[name].isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict) -> Task:
        """Build a task from to_dict() data; the usual validation runs, so bad saved values raise ValueError."""
        values = dict(data)
        for name in DATE_FIELDS:
            if values.get(name) is not None:
                values[name] = date.fromisoformat(values[name])
        return cls(**values)


@dataclass
class Pet:
    """An animal being cared for, along with its care tasks."""

    name: str
    species: str  # "dog", "cat", or "other"
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Add a care task for this pet and tag it with this pet's name."""
        task.pet_name = self.name
        self.tasks.append(task)

    def find_task(self, title: str) -> Task:
        """Return the task with the given title, preferring one not yet completed; raise ValueError if none."""
        matches = [task for task in self.tasks if task.title == title]
        if not matches:
            raise ValueError(f"{self.name} has no task called {title!r}")
        # Completed recurring tasks stay in the list as history, so pick the open occurrence first.
        return next((task for task in matches if not task.completed), matches[0])

    def remove_task(self, title: str) -> None:
        """Remove the task with the given title."""
        self.tasks.remove(self.find_task(title))

    def edit_task(self, title: str, changes: dict) -> None:
        """Update fields on the task with the given title."""
        task = self.find_task(title)
        allowed = {f.name for f in fields(Task)} - {"pet_name"}
        unknown = set(changes) - allowed
        if unknown:
            raise ValueError(f"cannot edit unknown task fields: {sorted(unknown)}")
        # Build a new Task so the same validation runs on the edited values.
        values = {name: getattr(task, name) for name in allowed}
        values.update(changes)
        updated = Task(**values)
        for name in allowed:
            setattr(task, name, getattr(updated, name))


@dataclass
class Owner:
    """The person using PawPal+ and the time they have for pet care."""

    name: str
    available_minutes: int
    day_start: str = "08:00"
    pets: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        """Attach a pet to this owner."""
        self.pets.append(pet)

    def find_pet(self, name: str) -> Pet:
        """Return the pet with the given name, or raise ValueError if there isn't one."""
        for pet in self.pets:
            if pet.name == name:
                return pet
        raise ValueError(f"{self.name} has no pet called {name!r}")

    def get_all_tasks(self) -> list[Task]:
        """Return every task across all of this owner's pets."""
        return [task for pet in self.pets for task in pet.tasks]

    def to_dict(self) -> dict:
        """Return the owner, their pets, and every task (including completed history) as JSON-ready data."""
        return {
            "name": self.name,
            "available_minutes": self.available_minutes,
            "day_start": self.day_start,
            "pets": [
                {"name": pet.name, "species": pet.species, "tasks": [task.to_dict() for task in pet.tasks]}
                for pet in self.pets
            ],
        }

    @classmethod
    def from_dict(cls, data: dict) -> Owner:
        """Rebuild an owner from to_dict() data, adding tasks through Pet.add_task so each knows its pet."""
        owner = cls(data["name"], data["available_minutes"], data["day_start"])
        for pet_data in data["pets"]:
            pet = Pet(pet_data["name"], pet_data["species"])
            for task_data in pet_data["tasks"]:
                pet.add_task(Task.from_dict(task_data))
            owner.add_pet(pet)
        return owner

    def save_to_json(self, path: Union[str, Path] = "data.json") -> None:
        """Save the owner, pets, and tasks to a JSON file."""
        path = Path(path)
        text = json.dumps({"version": DATA_VERSION, "owner": self.to_dict()}, indent=2)
        # Write to a temporary file first, then swap it in, so a crash mid-write can't leave a half-written file.
        temp = path.with_name(path.name + ".tmp")
        temp.write_text(text + "\n", encoding="utf-8")
        os.replace(temp, path)

    @classmethod
    def load_from_json(cls, path: Union[str, Path] = "data.json") -> Owner:
        """Load an owner saved by save_to_json.

        Raises FileNotFoundError if the file doesn't exist, and ValueError if it isn't valid PawPal+ data.
        """
        text = Path(path).read_text(encoding="utf-8")
        try:
            saved = json.loads(text)
            if saved.get("version") != DATA_VERSION:
                raise ValueError(f"unsupported data version {saved.get('version')!r}")
            return cls.from_dict(saved["owner"])
        except (json.JSONDecodeError, KeyError, TypeError, AttributeError, ValueError) as error:
            raise ValueError(f"{path} is not valid PawPal+ data: {error}") from error


@dataclass
class DailyPlan:
    """The scheduler's output: scheduled tasks, skipped tasks, and the reasons for each."""

    date: date
    entries: list[tuple[str, Task, str]] = field(default_factory=list)  # (start_time, task, reason)
    skipped: list[tuple[Task, str]] = field(default_factory=list)  # (task, reason)
    warnings: list[str] = field(default_factory=list)

    def add_entry(self, task: Task, start_time: str, reason: str) -> None:
        """Add a task to the plan at the given start time, keeping entries in time order."""
        self.entries.append((start_time, task, reason))
        self.entries.sort(key=lambda entry: to_minutes(entry[0]))

    def skip(self, task: Task, reason: str) -> None:
        """Record a task that was left out of the plan and why."""
        self.skipped.append((task, reason))

    def total_minutes(self) -> int:
        """Return the total minutes of all scheduled tasks."""
        return sum(task.duration_minutes for _, task, _ in self.entries)

    def explain(self) -> str:
        """Return a readable summary of the plan and the reasoning behind it."""
        lines = [f"Plan for {self.date.isoformat()} ({self.total_minutes()} min scheduled)"]
        if not self.entries:
            lines.append("  No tasks scheduled.")
        for start, task, reason in self.entries:
            end = to_hhmm(to_minutes(start) + task.duration_minutes)
            lines.append(
                f"  {start}-{end}  {task.title} for {task.pet_name} "
                f"({task.duration_minutes} min, {task.priority}): {reason}"
            )
        if self.skipped:
            lines.append("Skipped:")
            for task, reason in self.skipped:
                lines.append(f"  {task.title} for {task.pet_name}: {reason}")
        if self.warnings:
            lines.append("Warnings:")
            lines.extend(f"  {warning}" for warning in self.warnings)
        return "\n".join(lines)


class Scheduler:
    """Builds a daily plan from the owner's pets, tasks, and available time."""

    def __init__(self, owner: Owner, day: date) -> None:
        """Create a scheduler for one owner on one day."""
        self.owner = owner
        self.date = day

    def collect_tasks(self) -> list[Task]:
        """Gather all tasks due today across the owner's pets."""
        return [task for task in self.owner.get_all_tasks() if task.is_due_today(self.date)]

    def task_time(self, task: Task) -> Optional[str]:
        """Return the "HH:MM" a task is aimed at: its fixed time, else the start of its preferred part of the day."""
        if task.start_time:
            return task.start_time
        if task.preferred_time == "morning":
            return self.owner.day_start
        return TIME_OF_DAY_START.get(task.preferred_time)

    def task_minutes(self, task: Task) -> int:
        """Return task_time() as minutes after midnight, so "9:00" sorts before "10:00"; untimed tasks get 24:00."""
        when = self.task_time(task)
        return to_minutes(when) if when else 24 * 60

    def sort_by_priority(self, tasks: list[Task]) -> list[Task]:
        """Order tasks by priority (high first), then by time of day (earliest first, untimed last), then shortest first."""
        return sorted(tasks, key=lambda t: (-t.priority_rank(), self.task_minutes(t), t.duration_minutes))

    def sort_by_time(self, tasks: list[Task]) -> list[Task]:
        """Order tasks by time of day (earliest first); tasks with no time go last, higher priority first on ties."""
        return sorted(tasks, key=lambda t: (self.task_minutes(t), -t.priority_rank()))

    def filter_tasks(self, pet_name: Optional[str] = None, completed: Optional[bool] = None) -> list[Task]:
        """Return the owner's tasks, keeping only one pet's and/or only done or not-done ones when given."""
        return [
            task
            for task in self.owner.get_all_tasks()
            if (pet_name is None or task.pet_name == pet_name)
            and (completed is None or task.completed == completed)
        ]

    def generate_plan(self) -> DailyPlan:
        """Fit sorted tasks into the owner's available time and return the plan."""
        plan = DailyPlan(self.date)

        # 1. Choose tasks: highest priority first (earliest first within a priority), until the time budget runs out.
        remaining = self.owner.available_minutes
        chosen: list[Task] = []
        for task in self.sort_by_priority(self.collect_tasks()):
            if task.duration_minutes <= remaining:
                chosen.append(task)
                remaining -= task.duration_minutes
            else:
                plan.skip(
                    task,
                    f"not enough time ({task.duration_minutes} min needed, {remaining} min left)",
                )

        # 2. Place fixed-time tasks exactly where they belong.
        fixed = [t for t in chosen if t.start_time]
        busy = sorted((to_minutes(t.start_time), to_minutes(t.start_time) + t.duration_minutes) for t in fixed)
        for task in fixed:
            plan.add_entry(task, task.start_time, f"{task.priority} priority, fixed time")

        # 3. Place flexible tasks back to back from the start of the day, by time of day,
        #    waiting for their preferred part of the day and jumping past any fixed-time
        #    task they would overlap.
        flexible = [t for t in chosen if not t.start_time]
        flexible.sort(key=lambda t: (TIME_OF_DAY_ORDER[t.preferred_time], -t.priority_rank()))
        cursor = to_minutes(self.owner.day_start)
        for task in flexible:
            if task.preferred_time in TIME_OF_DAY_START:
                cursor = max(cursor, to_minutes(TIME_OF_DAY_START[task.preferred_time]))
            # busy is sorted by start, so one pass is enough: after jumping past a slot,
            # only later slots can still be in the way.
            for busy_start, busy_end in busy:
                if cursor < busy_end and busy_start < cursor + task.duration_minutes:
                    cursor = busy_end
            reason = f"{task.priority} priority"
            if task.preferred_time:
                reason += f", prefers {task.preferred_time}"
            plan.add_entry(task, to_hhmm(cursor), reason)
            cursor += task.duration_minutes

        plan.warnings = self.detect_conflicts(plan)
        return plan

    def plan_slots(self, plan: DailyPlan) -> list[tuple[int, int, Task]]:
        """Return each plan entry as (start, end, task) in minutes after midnight, sorted by start time."""
        return sorted(
            ((to_minutes(start), to_minutes(start) + task.duration_minutes, task) for start, task, _ in plan.entries),
            key=lambda slot: slot[0],
        )

    def find_overlaps(self, plan: DailyPlan) -> list[tuple[tuple[int, int, Task], tuple[int, int, Task]]]:
        """Return every pair of overlapping (start, end, task) slots in the plan, the earlier-starting one first."""
        # Check every pair once. Because the slots are sorted, the second task starts no earlier
        # than the first, so they overlap exactly when the second starts before the first ends.
        return [(a, b) for a, b in combinations(self.plan_slots(plan), 2) if b[0] < a[1]]

    def detect_conflicts(self, plan: DailyPlan) -> list[str]:
        """Return a warning for every pair of overlapping tasks (same or different pets) and any task past midnight."""
        warnings = []
        for (a_start, a_end, a), (b_start, b_end, b) in self.find_overlaps(plan):
            who = f"both for {a.pet_name}" if a.pet_name == b.pet_name else "different pets"
            warnings.append(
                f"{a.title} for {a.pet_name} ({to_hhmm(a_start)}-{to_hhmm(a_end)}) overlaps "
                f"{b.title} for {b.pet_name} ({to_hhmm(b_start)}-{to_hhmm(b_end)}); {who}"
            )
        for start, end, task in self.plan_slots(plan):
            if end > 24 * 60:
                warnings.append(f"{task.title} for {task.pet_name} runs past midnight (starts {to_hhmm(start)})")
        return warnings

    def _first_gap(self, busy: list[tuple[int, int]], duration: int, earliest: int) -> Optional[int]:
        """Return the earliest start (minutes) at or after earliest where duration fits between busy intervals."""
        cursor = earliest
        for busy_start, busy_end in sorted(busy):
            if busy_start >= cursor + duration:
                break  # the gap before this interval is big enough
            # Overlapping or touching: the gap can only start once this interval ends.
            cursor = max(cursor, busy_end)
        return cursor if cursor + duration <= 24 * 60 else None

    def find_next_slot(
        self, plan: DailyPlan, duration_minutes: int, earliest: Optional[str] = None, ignore: Optional[Task] = None
    ) -> Optional[str]:
        """Return the first "HH:MM" at or after earliest (default: day start) where a task this long fits
        without overlapping anything in the plan, or None if nothing fits before midnight.

        ignore leaves one task out of the busy times, so a task can look for a new slot for itself.
        """
        if duration_minutes <= 0:
            raise ValueError("duration_minutes must be greater than 0")
        busy = [(start, end) for start, end, task in self.plan_slots(plan) if task is not ignore]
        start = self._first_gap(busy, duration_minutes, to_minutes(earliest or self.owner.day_start))
        return None if start is None else to_hhmm(start)

    def suggest_moves(self, plan: DailyPlan) -> list[tuple[Task, str, Optional[str]]]:
        """Suggest new start times that clear every overlap in the plan, as (task, current start, new start).

        Clashes are resolved one at a time: the lower-priority task of the earliest clash (or, on a tie,
        the later one) moves to the next free slot at or after its current time. Each move accounts for
        earlier moves, so the suggestions never clash with each other. New start is None if no gap is left today.
        """
        slots = self.plan_slots(plan)
        moves = []
        while True:
            slots.sort(key=lambda slot: slot[0])
            clash = next(((a, b) for a, b in combinations(slots, 2) if b[0] < a[1]), None)
            if clash is None:
                return moves
            a, b = clash
            mover = a if a[2].priority_rank() < b[2].priority_rank() else b
            slots.remove(mover)
            start, _, task = mover
            # A moved task lands in a free gap, so it can't clash again; the loop ends after at most one move per task.
            new_start = self._first_gap([(s, e) for s, e, _ in slots], task.duration_minutes, start)
            moves.append((task, to_hhmm(start), None if new_start is None else to_hhmm(new_start)))
            if new_start is not None:
                slots.append((new_start, new_start + task.duration_minutes, task))

    def mark_task_complete(self, pet_name: str, title: str) -> Task:
        """Mark one pet's task done for the scheduler's date, add its next occurrence to the pet, and return it."""
        pet = self.owner.find_pet(pet_name)
        task = pet.find_task(title)
        if not task.is_due_today(self.date):
            raise ValueError(f"{title!r} for {pet_name} is not due on {self.date.isoformat()}")
        next_task = task.mark_complete(self.date)
        pet.add_task(next_task)
        return next_task
