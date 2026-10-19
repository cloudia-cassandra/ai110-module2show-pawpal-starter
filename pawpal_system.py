"""PawPal+ logic layer: backend classes for owners, pets, tasks, and scheduling."""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from datetime import date
from typing import Optional

PRIORITY_RANKS = {"low": 1, "medium": 2, "high": 3}
FREQUENCIES = ("daily", "weekly")
# Order used to place flexible tasks through the day; None (no preference) goes last.
TIME_OF_DAY_ORDER = {"morning": 0, "afternoon": 1, "evening": 2, None: 3}
# Earliest start for a flexible task with this preference ("morning" starts at the owner's day_start).
TIME_OF_DAY_START = {"afternoon": "12:00", "evening": "17:00"}


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

    def priority_rank(self) -> int:
        """Return a number for sorting: low=1, medium=2, high=3."""
        return PRIORITY_RANKS[self.priority]

    def is_due_today(self, day: date) -> bool:
        """Return True if this task should happen on the given day (uses frequency and last_completed)."""
        if self.last_completed is None:
            return True
        days_since = (day - self.last_completed).days
        if self.frequency == "daily":
            return days_since >= 1
        return days_since >= 7

    def mark_complete(self, day: date) -> None:
        """Mark this task as done and remember the day it was completed."""
        self.completed = True
        self.last_completed = day


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
        """Return the task with the given title, or raise ValueError if there isn't one."""
        for task in self.tasks:
            if task.title == title:
                return task
        raise ValueError(f"{self.name} has no task called {title!r}")

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
        updated = Task(**{**{f: getattr(task, f) for f in allowed}, **changes})
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

    def sort_tasks(self, tasks: list[Task]) -> list[Task]:
        """Order tasks by priority (high first), then preferred time, then duration (short first)."""
        return sorted(
            tasks,
            key=lambda t: (-t.priority_rank(), TIME_OF_DAY_ORDER[t.preferred_time], t.duration_minutes),
        )

    def generate_plan(self) -> DailyPlan:
        """Fit sorted tasks into the owner's available time and return the plan."""
        plan = DailyPlan(self.date)

        # 1. Choose tasks: highest priority first, until the time budget runs out.
        remaining = self.owner.available_minutes
        chosen: list[Task] = []
        for task in self.sort_tasks(self.collect_tasks()):
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
        busy = [(to_minutes(t.start_time), to_minutes(t.start_time) + t.duration_minutes) for t in fixed]
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
            moved = True
            while moved:
                moved = False
                for busy_start, busy_end in busy:
                    if cursor < busy_end and busy_start < cursor + task.duration_minutes:
                        cursor = busy_end
                        moved = True
            reason = f"{task.priority} priority"
            if task.preferred_time:
                reason += f", prefers {task.preferred_time}"
            plan.add_entry(task, to_hhmm(cursor), reason)
            cursor += task.duration_minutes

        plan.warnings = self.detect_conflicts(plan)
        return plan

    def detect_conflicts(self, plan: DailyPlan) -> list[str]:
        """Return warnings for any overlapping time slots in the plan."""
        warnings = []
        for i, (start_a, task_a, _) in enumerate(plan.entries):
            end_a = to_minutes(start_a) + task_a.duration_minutes
            for start_b, task_b, _ in plan.entries[i + 1:]:
                if to_minutes(start_b) < end_a:
                    warnings.append(
                        f"{task_a.title} for {task_a.pet_name} ({start_a}) overlaps "
                        f"{task_b.title} for {task_b.pet_name} ({start_b})"
                    )
        return warnings

    def mark_task_complete(self, pet_name: str, title: str) -> None:
        """Mark one pet's task as done for the scheduler's date."""
        self.owner.find_pet(pet_name).find_task(title).mark_complete(self.date)
