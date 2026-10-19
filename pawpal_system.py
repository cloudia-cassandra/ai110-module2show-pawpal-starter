"""PawPal+ logic layer: backend classes for owners, pets, tasks, and scheduling."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional


@dataclass
class Task:
    """A single pet care activity, such as a walk, feeding, or medication."""

    title: str
    duration_minutes: int
    priority: str  # "low", "medium", or "high"
    preferred_time: Optional[str] = None  # e.g. "morning", "afternoon", "evening"
    frequency: str = "daily"  # "daily" or "weekly"
    completed: bool = False
    last_completed: Optional[date] = None
    pet_name: str = ""  # set by Pet.add_task so the plan can say which pet a task is for

    def priority_rank(self) -> int:
        """Return a number for sorting: low=1, medium=2, high=3."""
        pass

    def is_due_today(self, day: date) -> bool:
        """Return True if this task should happen on the given day (uses frequency and last_completed)."""
        pass

    def mark_complete(self, day: date) -> None:
        """Mark this task as done and remember the day it was completed."""
        pass


@dataclass
class Pet:
    """An animal being cared for, along with its care tasks."""

    name: str
    species: str  # "dog", "cat", or "other"
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Add a care task for this pet and tag it with this pet's name."""
        pass

    def remove_task(self, title: str) -> None:
        """Remove the task with the given title."""
        pass

    def edit_task(self, title: str, changes: dict) -> None:
        """Update fields on the task with the given title."""
        pass


@dataclass
class Owner:
    """The person using PawPal+ and the time they have for pet care."""

    name: str
    available_minutes: int
    day_start: str = "08:00"
    pets: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        """Attach a pet to this owner."""
        pass


@dataclass
class DailyPlan:
    """The scheduler's output: scheduled tasks, skipped tasks, and the reasons for each."""

    date: date
    entries: list[tuple[str, Task, str]] = field(default_factory=list)  # (start_time, task, reason)
    skipped: list[tuple[Task, str]] = field(default_factory=list)  # (task, reason)

    def add_entry(self, task: Task, start_time: str, reason: str) -> None:
        """Add a task to the plan at the given start time."""
        pass

    def skip(self, task: Task, reason: str) -> None:
        """Record a task that was left out of the plan and why."""
        pass

    def total_minutes(self) -> int:
        """Return the total minutes of all scheduled tasks."""
        pass

    def explain(self) -> str:
        """Return a readable summary of the plan and the reasoning behind it."""
        pass


class Scheduler:
    """Builds a daily plan from the owner's pets, tasks, and available time."""

    def __init__(self, owner: Owner, day: date) -> None:
        self.owner = owner
        self.date = day

    def collect_tasks(self) -> list[Task]:
        """Gather all tasks due today across the owner's pets."""
        pass

    def sort_tasks(self, tasks: list[Task]) -> list[Task]:
        """Order tasks by priority, then preferred time, then duration."""
        pass

    def generate_plan(self) -> DailyPlan:
        """Fit sorted tasks into the owner's available time and return the plan."""
        pass

    def detect_conflicts(self, plan: DailyPlan) -> list[str]:
        """Return warnings for any overlapping time slots in the plan."""
        pass
