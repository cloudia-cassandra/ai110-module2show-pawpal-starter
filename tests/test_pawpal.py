"""Tests for the PawPal+ logic layer."""

from datetime import date

import pytest

from pawpal_system import Owner, Pet, Scheduler, Task, to_minutes


def test_mark_complete_changes_task_status():
    task = Task("Morning walk", 30, "high")
    assert task.completed is False

    task.mark_complete(date(2026, 10, 18))

    assert task.completed is True
    assert task.last_completed == date(2026, 10, 18)


def test_add_task_increases_pet_task_count():
    pet = Pet("Mochi", "dog")
    assert len(pet.tasks) == 0

    pet.add_task(Task("Feeding", 10, "high"))

    assert len(pet.tasks) == 1
    assert pet.tasks[0].pet_name == "Mochi"


def make_owner_with_tasks():
    owner = Owner("Jordan", 120, day_start="07:30")
    mochi, luna = Pet("Mochi", "dog"), Pet("Luna", "cat")
    owner.add_pet(mochi)
    owner.add_pet(luna)
    mochi.add_task(Task("Puzzle toy", 15, "medium", preferred_time="evening"))
    mochi.add_task(Task("Bath", 45, "low"))
    luna.add_task(Task("Breakfast", 10, "high", start_time="08:15"))
    mochi.add_task(Task("Meds", 5, "high", start_time="8:00"))  # no leading zero on purpose
    luna.add_task(Task("Brush coat", 20, "medium", preferred_time="afternoon"))
    return owner


def test_sort_by_time_orders_tasks_earliest_first_with_untimed_last():
    scheduler = Scheduler(make_owner_with_tasks(), date(2026, 10, 18))

    ordered = scheduler.sort_by_time(scheduler.owner.get_all_tasks())

    assert [t.title for t in ordered] == ["Meds", "Breakfast", "Brush coat", "Puzzle toy", "Bath"]


def test_filter_tasks_by_pet_and_completion_status():
    scheduler = Scheduler(make_owner_with_tasks(), date(2026, 10, 18))
    scheduler.mark_task_complete("Luna", "Breakfast")

    assert {t.title for t in scheduler.filter_tasks(pet_name="Luna")} == {"Breakfast", "Brush coat"}
    assert [t.title for t in scheduler.filter_tasks(completed=True)] == ["Breakfast"]
    # Completing Breakfast adds tomorrow's Breakfast, which is not completed yet.
    assert [t.title for t in scheduler.filter_tasks(pet_name="Luna", completed=False)] == ["Brush coat", "Breakfast"]
    assert len(scheduler.filter_tasks()) == 6


def test_completing_daily_task_creates_next_one_due_tomorrow():
    today = date(2026, 10, 18)
    scheduler = Scheduler(make_owner_with_tasks(), today)

    next_task = scheduler.mark_task_complete("Luna", "Breakfast")

    assert next_task.due_date == date(2026, 10, 19)
    assert next_task.completed is False
    assert next_task.start_time == "08:15" and next_task.pet_name == "Luna"
    assert next_task in scheduler.owner.find_pet("Luna").tasks
    # Not due again today, but due tomorrow.
    assert "Breakfast" not in [t.title for t in scheduler.collect_tasks()]
    assert "Breakfast" in [t.title for t in Scheduler(scheduler.owner, date(2026, 10, 19)).collect_tasks()]


def test_completing_weekly_task_creates_next_one_due_in_seven_days():
    owner = Owner("Jordan", 60)
    pet = Pet("Mochi", "dog")
    owner.add_pet(pet)
    pet.add_task(Task("Bath", 45, "low", frequency="weekly"))

    next_task = Scheduler(owner, date(2026, 10, 30)).mark_task_complete("Mochi", "Bath")

    assert next_task.due_date == date(2026, 11, 6)  # crosses into a new month correctly
    assert not Scheduler(owner, date(2026, 11, 5)).collect_tasks()
    assert Scheduler(owner, date(2026, 11, 6)).collect_tasks() == [next_task]


def test_detect_conflicts_warns_about_same_and_different_pet_overlaps():
    owner = Owner("Jordan", 120)
    mochi, luna = Pet("Mochi", "dog"), Pet("Luna", "cat")
    owner.add_pet(mochi)
    owner.add_pet(luna)
    mochi.add_task(Task("Breakfast", 10, "high", start_time="08:15"))
    luna.add_task(Task("Breakfast", 10, "high", start_time="08:15"))
    luna.add_task(Task("Litter box", 5, "medium", start_time="08:20"))
    mochi.add_task(Task("Walk", 30, "high", start_time="09:00"))  # no clash

    plan = Scheduler(owner, date(2026, 10, 18)).generate_plan()

    assert len(plan.entries) == 4  # conflicting tasks stay in the plan
    assert len(plan.warnings) == 3
    assert any("different pets" in w for w in plan.warnings)
    assert any("both for Luna" in w for w in plan.warnings)
    assert not any("Walk" in w for w in plan.warnings)


def test_back_to_back_tasks_are_not_a_conflict():
    owner = Owner("Jordan", 60)
    pet = Pet("Mochi", "dog")
    owner.add_pet(pet)
    pet.add_task(Task("Meds", 5, "high", start_time="08:00"))
    pet.add_task(Task("Breakfast", 10, "high", start_time="08:05"))

    assert Scheduler(owner, date(2026, 10, 18)).generate_plan().warnings == []


def test_bad_start_time_is_rejected_up_front():
    with pytest.raises(ValueError):
        Task("Meds", 5, "high", start_time="8am")
    with pytest.raises(ValueError):
        Task("Meds", 5, "high", start_time="25:00")


def owner_with(*tasks, minutes=120, day_start="08:00"):
    """Return an owner with one pet, Mochi, who has the given tasks."""
    owner = Owner("Jordan", minutes, day_start=day_start)
    pet = Pet("Mochi", "dog")
    owner.add_pet(pet)
    for task in tasks:
        pet.add_task(task)
    return owner


def plan_times(plan):
    """Return {title: start_time} for every scheduled entry in a plan."""
    return {task.title: start for start, task, _ in plan.entries}


# --- Sorting correctness ---


def test_tasks_at_the_same_start_time_put_higher_priority_first():
    owner = owner_with(
        Task("Brush teeth", 5, "low", start_time="09:00"),
        Task("Meds", 5, "high", start_time="09:00"),
        Task("Breakfast", 10, "medium", start_time="09:00"),
    )
    scheduler = Scheduler(owner, date(2026, 10, 18))

    ordered = scheduler.sort_by_time(owner.get_all_tasks())

    assert [t.title for t in ordered] == ["Meds", "Breakfast", "Brush teeth"]


def test_sort_tasks_uses_priority_then_time_of_day_then_duration():
    owner = owner_with(
        Task("Evening walk", 30, "high", preferred_time="evening"),
        Task("Long play", 40, "medium"),
        Task("Morning walk", 30, "high", preferred_time="morning"),
        Task("Quick play", 10, "medium"),
        Task("Short morning walk", 15, "high", preferred_time="morning"),
    )
    scheduler = Scheduler(owner, date(2026, 10, 18))

    ordered = scheduler.sort_tasks(owner.get_all_tasks())

    assert [t.title for t in ordered] == [
        "Short morning walk", "Morning walk", "Evening walk", "Quick play", "Long play",
    ]


def test_priority_is_case_insensitive():
    task = Task("Meds", 5, "HIGH")

    assert task.priority == "high"
    assert task.priority_rank() == 3


# --- Building the plan ---


def test_owner_with_no_pets_gets_an_empty_plan():
    plan = Scheduler(Owner("Jordan", 60), date(2026, 10, 18)).generate_plan()

    assert plan.entries == [] and plan.skipped == [] and plan.warnings == []
    assert "No tasks scheduled." in plan.explain()


def test_pet_with_no_tasks_gets_an_empty_plan():
    plan = Scheduler(owner_with(), date(2026, 10, 18)).generate_plan()

    assert plan.entries == []
    assert plan.total_minutes() == 0


def test_task_that_exactly_fills_the_budget_is_scheduled():
    owner = owner_with(Task("Walk", 40, "high"), Task("Play", 20, "medium"), minutes=60)

    plan = Scheduler(owner, date(2026, 10, 18)).generate_plan()

    assert plan.total_minutes() == 60
    assert plan.skipped == []


def test_zero_budget_skips_every_task():
    owner = owner_with(Task("Walk", 30, "high"), Task("Meds", 5, "high"), minutes=0)

    plan = Scheduler(owner, date(2026, 10, 18)).generate_plan()

    assert plan.entries == []
    assert len(plan.skipped) == 2
    assert all("not enough time" in reason for _, reason in plan.skipped)


def test_big_high_priority_task_is_skipped_but_smaller_low_one_still_fits():
    owner = owner_with(Task("Long hike", 60, "high"), Task("Brush", 10, "low"), minutes=30)

    plan = Scheduler(owner, date(2026, 10, 18)).generate_plan()

    assert [t.title for _, t, _ in plan.entries] == ["Brush"]
    assert [t.title for t, _ in plan.skipped] == ["Long hike"]


# --- Placing tasks in time slots ---


def test_flexible_task_jumps_past_a_fixed_task_it_would_overlap():
    owner = owner_with(
        Task("Breakfast", 10, "high", start_time="08:15"),
        Task("Walk", 30, "high", preferred_time="morning"),
    )

    plan = Scheduler(owner, date(2026, 10, 18)).generate_plan()

    assert plan_times(plan) == {"Breakfast": "08:15", "Walk": "08:25"}
    assert plan.warnings == []


def test_afternoon_task_waits_until_noon():
    owner = owner_with(Task("Brush coat", 20, "medium", preferred_time="afternoon"))

    plan = Scheduler(owner, date(2026, 10, 18)).generate_plan()

    assert plan_times(plan) == {"Brush coat": "12:00"}


def test_plan_entries_are_in_chronological_order():
    plan = Scheduler(make_owner_with_tasks(), date(2026, 10, 18)).generate_plan()

    starts = [to_minutes(start) for start, _, _ in plan.entries]
    assert starts == sorted(starts)


# --- Recurrence logic ---


def test_completing_the_same_task_twice_in_one_day_is_rejected():
    owner = owner_with(Task("Feeding", 10, "high"))
    scheduler = Scheduler(owner, date(2026, 10, 18))
    scheduler.mark_task_complete("Mochi", "Feeding")

    with pytest.raises(ValueError):
        scheduler.mark_task_complete("Mochi", "Feeding")
    assert len(owner.find_pet("Mochi").tasks) == 2  # no extra occurrence was added


def test_overdue_task_is_still_planned_and_next_one_counts_from_completion():
    owner = owner_with(Task("Feeding", 10, "high", due_date=date(2026, 10, 15)))
    scheduler = Scheduler(owner, date(2026, 10, 18))

    assert [t.title for t in scheduler.collect_tasks()] == ["Feeding"]
    next_task = scheduler.mark_task_complete("Mochi", "Feeding")

    assert next_task.due_date == date(2026, 10, 19)  # not Oct 16


# --- Conflict detection ---


def test_two_tasks_at_the_exact_same_time_are_flagged():
    owner = owner_with(
        Task("Meds", 5, "high", start_time="08:00"),
        Task("Breakfast", 10, "high", start_time="08:00"),
    )

    plan = Scheduler(owner, date(2026, 10, 18)).generate_plan()

    assert len(plan.entries) == 2
    assert len(plan.warnings) == 1
    assert "Meds" in plan.warnings[0] and "Breakfast" in plan.warnings[0]
    assert "both for Mochi" in plan.warnings[0]


def test_three_overlapping_tasks_give_one_warning_per_pair():
    owner = owner_with(
        Task("Meds", 30, "high", start_time="08:00"),
        Task("Breakfast", 30, "high", start_time="08:10"),
        Task("Brush", 30, "high", start_time="08:20"),
    )

    plan = Scheduler(owner, date(2026, 10, 18)).generate_plan()

    assert len(plan.warnings) == 3


def test_task_ending_exactly_at_midnight_is_fine_but_one_past_is_flagged():
    on_time = owner_with(Task("Night walk", 30, "low", start_time="23:30"))
    too_late = owner_with(Task("Night walk", 31, "low", start_time="23:30"))

    assert Scheduler(on_time, date(2026, 10, 18)).generate_plan().warnings == []
    warnings = Scheduler(too_late, date(2026, 10, 18)).generate_plan().warnings
    assert len(warnings) == 1 and "past midnight" in warnings[0]


# --- Validation ---


def test_invalid_edit_leaves_task_unchanged():
    owner = owner_with(Task("Walk", 30, "high"))
    pet = owner.find_pet("Mochi")

    with pytest.raises(ValueError):
        pet.edit_task("Walk", {"priority": "urgent", "duration_minutes": 45})

    task = pet.find_task("Walk")
    assert task.priority == "high" and task.duration_minutes == 30
