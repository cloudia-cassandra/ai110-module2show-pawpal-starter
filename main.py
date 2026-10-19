"""Demo script: build a sample owner with two pets, then sort, filter, and schedule their tasks."""

from dataclasses import replace
from datetime import date

from pawpal_format import heading, moves_table, paint, plan_report, task_label, task_table, use_color
from pawpal_system import Owner, Pet, Scheduler, Task

DEMO_DAY = date(2026, 10, 18)  # fixed so the output is the same every run
COLOR = use_color()  # colors only in a real terminal; set NO_COLOR=1 to turn them off


def print_tasks(title: str, scheduler: Scheduler, tasks: list[Task]) -> None:
    """Print a bold heading and the tasks as a table."""
    print(heading(title, COLOR))
    print(task_table(scheduler, tasks, COLOR))


def banner(title: str) -> None:
    """Print a section banner."""
    print()
    print(paint("═" * 60, "cyan", COLOR))
    print(paint(f"  {title}", "bold", COLOR))
    print(paint("═" * 60, "cyan", COLOR))


def main() -> None:
    owner = Owner(name="Jordan", available_minutes=90, day_start="07:30")

    mochi = Pet(name="Mochi", species="dog")
    luna = Pet(name="Luna", species="cat")
    owner.add_pet(mochi)
    owner.add_pet(luna)

    # Added out of time order on purpose, to show sort_by_time() working.
    mochi.add_task(Task("Puzzle toy", 15, "medium", preferred_time="evening"))
    luna.add_task(Task("Breakfast", 10, "high", start_time="08:15"))
    mochi.add_task(Task("Bath", 45, "low", frequency="weekly"))
    luna.add_task(Task("Brush coat", 20, "medium", preferred_time="afternoon"))
    mochi.add_task(Task("Heartworm meds", 5, "high", start_time="08:00"))
    mochi.add_task(Task("Morning walk", 30, "high", preferred_time="morning"))
    # Where priority and time disagree, to show sort_by_priority() differing from sort_by_time():
    mochi.add_task(Task("Brush teeth", 5, "low", start_time="07:00"))  # earliest task, but low priority
    luna.add_task(Task("Evening meds", 5, "high", start_time="20:00"))  # latest task, but high priority
    # Deliberate clashes, to show conflict warnings:
    mochi.add_task(Task("Breakfast", 10, "high", start_time="08:15"))  # same time as Luna's breakfast
    luna.add_task(Task("Litter box", 5, "medium", start_time="08:20"))  # during Luna's own breakfast

    scheduler = Scheduler(owner, DEMO_DAY)

    print_tasks("Unsorted (each pet's tasks in the order added):", scheduler, owner.get_all_tasks())
    print_tasks("Sorted by time:", scheduler, scheduler.sort_by_time(owner.get_all_tasks()))
    print_tasks("Sorted by priority, then time:", scheduler, scheduler.sort_by_priority(owner.get_all_tasks()))
    print_tasks("Only Luna's tasks:", scheduler, scheduler.filter_tasks(pet_name="Luna"))

    # Completing a recurring task automatically adds its next occurrence.
    next_meds = scheduler.mark_task_complete("Mochi", "Heartworm meds")
    print(paint(
        f"\n✅ Marked Heartworm meds done; next one ({next_meds.frequency}) is due {next_meds.due_date:%a %b %d}.",
        "green", COLOR,
    ))
    print_tasks("Completed tasks:", scheduler, scheduler.filter_tasks(completed=True))
    print_tasks(
        "Mochi's tasks still to do, sorted by time:",
        scheduler,
        scheduler.sort_by_time(scheduler.filter_tasks(pet_name="Mochi", completed=False)),
    )

    planner = Scheduler(owner, DEMO_DAY)
    plan = planner.generate_plan()
    banner(f"Today's Schedule for {owner.name}'s pets")
    print(plan_report(planner, plan, COLOR))

    # Next available slot: new times that clear every clash without creating new ones.
    print(heading("💡 Suggested fix for the clashes:", COLOR))
    print(moves_table(planner, planner.suggest_moves(plan), COLOR))
    print(f"🕒 Next free 20-minute slot after 09:00: {planner.find_next_slot(plan, 20, earliest='09:00')}")

    # Priority-based scheduling on a tight day: tasks are chosen by priority, earliest first within a priority.
    tight = Scheduler(replace(owner, available_minutes=25), DEMO_DAY)
    banner("Tight day: same tasks, only 25 minutes")
    print(paint("Choosing order (priority, then time):", "bold", COLOR))
    for rank, task in enumerate(tight.sort_by_priority(tight.collect_tasks()), start=1):
        print(f"  {rank}. {task_label(task)} ({task.pet_name}, {task.priority})")
    print(plan_report(tight, tight.generate_plan(), COLOR))

if __name__ == "__main__":
    main()
