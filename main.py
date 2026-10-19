"""Demo script: build a sample owner with two pets, then sort, filter, and schedule their tasks."""

from dataclasses import replace
from datetime import date

from pawpal_system import Owner, Pet, Scheduler, Task

DEMO_DAY = date(2026, 10, 18)  # fixed so the output is the same every run


def print_tasks(heading: str, scheduler: Scheduler, tasks: list[Task]) -> None:
    """Print a heading and one aligned line per task."""
    print(f"\n{heading}")
    if not tasks:
        print("  (none)")
    for task in tasks:
        when = scheduler.task_time(task) or "any time"
        if task.completed:
            status = f"done {task.last_completed.isoformat()}"
        else:
            status = f"due {task.due_date.isoformat()}" if task.due_date else "to do"
        print(f"  {when:<9} {task.title:<15} {task.pet_name:<6} {task.priority:<7} {status}")


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
    print(f"\nMarked Heartworm meds done; next one ({next_meds.frequency}) is due {next_meds.due_date.isoformat()}.")
    print_tasks("Completed tasks:", scheduler, scheduler.filter_tasks(completed=True))
    print_tasks(
        "Mochi's tasks still to do, sorted by time:",
        scheduler,
        scheduler.sort_by_time(scheduler.filter_tasks(pet_name="Mochi", completed=False)),
    )

    planner = Scheduler(owner, DEMO_DAY)
    plan = planner.generate_plan()
    print()
    print("=" * 60)
    print(f"Today's Schedule for {owner.name}'s pets")
    print("=" * 60)
    print(plan.explain())

    # Next available slot: new times that clear every clash without creating new ones.
    print("\nSuggested fix for the clashes:")
    for task, old_start, new_start in planner.suggest_moves(plan):
        print(f"  Move {task.title} for {task.pet_name} from {old_start} to {new_start or '(no free time left today)'}")
    print(f"Next free 20-minute slot after 09:00: {planner.find_next_slot(plan, 20, earliest='09:00')}")

    # Priority-based scheduling on a tight day: tasks are chosen by priority, earliest first within a priority.
    tight_plan = Scheduler(replace(owner, available_minutes=25), DEMO_DAY).generate_plan()
    print()
    print("=" * 60)
    print("Tight day: same tasks, only 25 minutes")
    print("=" * 60)
    print("Choosing order:", ", ".join(
        f"{t.title} ({t.pet_name}, {t.priority})" for t in planner.sort_by_priority(planner.collect_tasks())
    ))
    print(tight_plan.explain())


if __name__ == "__main__":
    main()
