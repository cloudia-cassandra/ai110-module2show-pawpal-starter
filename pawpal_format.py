"""Presentation helpers shared by the CLI (main.py) and the Streamlit app: emojis, colors, and tables.

Nothing here changes how tasks are scheduled; it only decides how they look.
"""

from __future__ import annotations

import os
import sys
from typing import TextIO

from tabulate import tabulate

from pawpal_system import DailyPlan, Scheduler, Task, to_hhmm, to_minutes

# The first group whose keyword appears in a task's title decides its icon.
# Emojis without a variation selector (U+FE0F) are used so terminal columns stay aligned.
TASK_ICONS = [
    (("meds", "medication", "medicine", "pill", "vet"), "💊"),
    (("walk", "run", "hike"), "🦮"),
    (("breakfast", "lunch", "dinner", "feed", "food", "meal", "snack"), "🍖"),
    (("bath", "shower"), "🛁"),
    (("brush", "groom", "nail", "teeth", "coat"), "🧼"),
    (("litter", "clean"), "🧹"),
    (("play", "toy", "puzzle", "train"), "🧸"),
]
DEFAULT_TASK_ICON = "🐾"
SPECIES_ICONS = {"dog": "🐶", "cat": "🐱"}
PRIORITY_ICONS = {"high": "🔴", "medium": "🟡", "low": "🟢"}
PRIORITY_COLORS = {"high": "red", "medium": "yellow", "low": "green"}

ANSI_CODES = {"red": "\033[31m", "green": "\033[32m", "yellow": "\033[33m", "cyan": "\033[36m", "bold": "\033[1m", "dim": "\033[2m"}
ANSI_RESET = "\033[0m"
TABLE_FORMAT = "rounded_outline"


def use_color(stream: TextIO = sys.stdout) -> bool:
    """Return True if output should be colored: only for a real terminal, and never when NO_COLOR is set."""
    return stream.isatty() and "NO_COLOR" not in os.environ


def paint(text: str, color: str, enabled: bool = True) -> str:
    """Wrap text in an ANSI color code (red, green, yellow, cyan, bold, dim), or return it unchanged if disabled."""
    return f"{ANSI_CODES[color]}{text}{ANSI_RESET}" if enabled else text


def task_icon(task: Task) -> str:
    """Return an emoji for the kind of task, guessed from keywords in its title (🐾 if none match)."""
    title = task.title.lower()
    for keywords, icon in TASK_ICONS:
        if any(keyword in title for keyword in keywords):
            return icon
    return DEFAULT_TASK_ICON


def species_icon(species: str) -> str:
    """Return 🐶 for dogs, 🐱 for cats, and 🐾 for anything else."""
    return SPECIES_ICONS.get(species, DEFAULT_TASK_ICON)


def priority_label(priority: str, color: bool = False) -> str:
    """Return a priority with its colored dot, e.g. "🔴 high"; red/yellow/green text when color is on."""
    return paint(f"{PRIORITY_ICONS[priority]} {priority}", PRIORITY_COLORS[priority], color)


def status_label(task: Task, scheduler: Scheduler, color: bool = False) -> str:
    """Return "✅ done <date>", "🔁 due <date>" for a future occurrence, or "⏳ to do"."""
    if task.completed:
        return paint(f"✅ done {task.last_completed:%b %d}", "green", color)
    if not task.is_due_today(scheduler.date):
        return paint(f"🔁 due {task.due_date:%b %d}", "cyan", color)
    return "⏳ to do"


def task_label(task: Task) -> str:
    """Return the task title with its icon, e.g. "💊 Heartworm meds"."""
    return f"{task_icon(task)} {task.title}"


def pet_label(scheduler: Scheduler, task: Task) -> str:
    """Return the task's pet name with a species icon, e.g. "🐶 Mochi"."""
    try:
        species = scheduler.owner.find_pet(task.pet_name).species
    except ValueError:
        species = ""
    return f"{species_icon(species)} {task.pet_name}"


def heading(text: str, color: bool = False) -> str:
    """Return a bold section heading with a blank line above it."""
    return "\n" + paint(text, "bold", color)


def task_table(scheduler: Scheduler, tasks: list[Task], color: bool = False) -> str:
    """Return a task list as a table: time, task, pet, minutes, priority, status."""
    if not tasks:
        return "  (none)"
    rows = [
        [
            scheduler.task_time(task) or "any time",
            task_label(task),
            pet_label(scheduler, task),
            task.duration_minutes,
            priority_label(task.priority, color),
            status_label(task, scheduler, color),
        ]
        for task in tasks
    ]
    return tabulate(rows, headers=["Time", "Task", "Pet", "Min", "Priority", "Status"], tablefmt=TABLE_FORMAT)


def plan_report(scheduler: Scheduler, plan: DailyPlan, color: bool = False) -> str:
    """Return a full plan: a summary line, the schedule table (clashes marked ⚠), skipped tasks, and warnings."""
    lines = [
        paint(
            f"📅 Plan for {plan.date:%A, %B %d}: {plan.total_minutes()} of "
            f"{scheduler.owner.available_minutes} min scheduled",
            "bold",
            color,
        )
    ]
    clashing = {id(task) for pair in scheduler.find_overlaps(plan) for _, _, task in pair}
    if plan.entries:
        rows = []
        for start, task, reason in plan.entries:
            when = f"{start}-{to_hhmm(to_minutes(start) + task.duration_minutes)}"
            if id(task) in clashing:
                when = paint(f"⚠ {when}", "yellow", color)
            rows.append([when, task_label(task), pet_label(scheduler, task), task.duration_minutes,
                         priority_label(task.priority, color), reason])
        lines.append(tabulate(rows, headers=["Time", "Task", "Pet", "Min", "Priority", "Why"], tablefmt=TABLE_FORMAT))
    else:
        lines.append("No tasks scheduled.")
    if plan.skipped:
        lines.append(paint(f"Didn't fit ({len(plan.skipped)}):", "bold", color))
        rows = [[task_label(task), pet_label(scheduler, task), priority_label(task.priority, color), paint(reason, "dim", color)]
                for task, reason in plan.skipped]
        lines.append(tabulate(rows, headers=["Task", "Pet", "Priority", "Reason"], tablefmt=TABLE_FORMAT))
    if plan.warnings:
        lines.append(paint(f"⚠ {len(plan.warnings)} warning{'s' if len(plan.warnings) != 1 else ''}:", "yellow", color))
        lines.extend(paint(f"  • {warning}", "yellow", color) for warning in plan.warnings)
    else:
        lines.append(paint("✅ No time clashes.", "green", color))
    return "\n".join(lines)


def moves_table(scheduler: Scheduler, moves: list[tuple[Task, str, str | None]], color: bool = False) -> str:
    """Return suggest_moves() output as a table: task, pet, current start, suggested start."""
    if not moves:
        return "  Nothing to move."
    rows = [
        [task_label(task), pet_label(scheduler, task), old, paint(new, "green", color) if new else paint("no free time today", "red", color)]
        for task, old, new in moves
    ]
    return tabulate(rows, headers=["Task", "Pet", "From", "To"], tablefmt=TABLE_FORMAT)


# Background tints for table cells in the Streamlit app. Semi-transparent, so they read well in light and dark themes.
CELL_TINTS = {
    "high": "rgba(255, 75, 75, 0.18)",
    "medium": "rgba(255, 190, 0, 0.20)",
    "low": "rgba(33, 195, 84, 0.18)",
    "done": "rgba(33, 195, 84, 0.18)",
    "due": "rgba(28, 131, 225, 0.18)",
}


def cell_style(value: object) -> str:
    """Return a CSS background for a priority or status cell ("🔴 high", "✅ done Oct 18", ...), or "" for none."""
    words = str(value).split()
    tint = CELL_TINTS.get(words[1]) if len(words) > 1 else None
    return f"background-color: {tint}" if tint else ""
