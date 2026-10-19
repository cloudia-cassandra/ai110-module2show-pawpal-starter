"""Tests for the PawPal+ logic layer."""

from datetime import date

import pytest

from pawpal_system import Owner, Pet, Scheduler, Task


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
