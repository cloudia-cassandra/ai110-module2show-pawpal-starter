"""Tests for the PawPal+ logic layer."""

import json
from datetime import date

import pytest

from pawpal_system import Owner, Pet, Scheduler, Task, to_hhmm, to_minutes


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


def test_sort_by_priority_breaks_ties_by_time_of_day_then_duration():
    owner = owner_with(
        Task("Evening walk", 30, "high", preferred_time="evening"),
        Task("Long play", 40, "medium"),
        Task("Morning walk", 30, "high", preferred_time="morning"),
        Task("Quick play", 10, "medium"),
        Task("Short morning walk", 15, "high", preferred_time="morning"),
    )
    scheduler = Scheduler(owner, date(2026, 10, 18))

    ordered = scheduler.sort_by_priority(owner.get_all_tasks())

    assert [t.title for t in ordered] == [
        "Short morning walk", "Morning walk", "Evening walk", "Quick play", "Long play",
    ]


def test_sort_by_priority_puts_priority_first_then_clock_time():
    owner = owner_with(
        Task("Low early", 10, "low", start_time="06:00"),
        Task("High late", 10, "high", start_time="18:00"),
        Task("Medium noon", 10, "medium", start_time="12:00"),
        Task("High any time", 10, "high"),
        Task("High early", 10, "high", start_time="07:00"),
        Task("High morning", 10, "high", preferred_time="morning"),  # day starts 08:00
        day_start="08:00",
    )
    scheduler = Scheduler(owner, date(2026, 10, 18))

    ordered = scheduler.sort_by_priority(owner.get_all_tasks())

    # A fixed 07:00 task now comes before a flexible morning (08:00) task of the same priority,
    # and untimed tasks come last within their priority. Earlier low tasks never jump ahead.
    assert [t.title for t in ordered] == [
        "High early", "High morning", "High late", "High any time", "Medium noon", "Low early",
    ]


def test_tight_budget_keeps_the_earliest_task_within_the_same_priority():
    owner = owner_with(
        Task("Morning walk", 30, "high", preferred_time="morning"),  # 08:00
        Task("Meds", 5, "high", start_time="07:00"),
        minutes=30,
    )

    plan = Scheduler(owner, date(2026, 10, 18)).generate_plan()

    # Both are high priority; Meds is earlier in the day, so it is chosen first and the walk no longer fits.
    assert [t.title for _, t, _ in plan.entries] == ["Meds"]
    assert [t.title for t, _ in plan.skipped] == ["Morning walk"]


def test_priority_decides_what_is_skipped_regardless_of_time():
    owner = owner_with(
        Task("Early brush", 20, "low", start_time="07:00"),
        Task("Late meds", 20, "high", start_time="20:00"),
        Task("Noon play", 20, "medium", start_time="12:00"),
        minutes=40,
    )

    plan = Scheduler(owner, date(2026, 10, 18)).generate_plan()

    assert [t.title for _, t, _ in plan.entries] == ["Noon play", "Late meds"]  # shown in time order
    assert [t.title for t, _ in plan.skipped] == ["Early brush"]


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


def test_find_overlaps_returns_each_clashing_pair_earlier_task_first():
    owner = owner_with(
        Task("Walk", 30, "high", start_time="09:00"),
        Task("Breakfast", 10, "high", start_time="08:15"),
        Task("Meds", 5, "high", start_time="08:20"),
    )
    scheduler = Scheduler(owner, date(2026, 10, 18))

    overlaps = scheduler.find_overlaps(scheduler.generate_plan())

    assert [(a[2].title, b[2].title) for a, b in overlaps] == [("Breakfast", "Meds")]
    (a_start, a_end, _), (b_start, _, _) = overlaps[0]
    assert (to_hhmm(a_start), to_hhmm(a_end), to_hhmm(b_start)) == ("08:15", "08:25", "08:20")


# --- Next available slot and suggested moves ---


def plan_for(*tasks, minutes=240, day_start="08:00"):
    """Return (scheduler, plan) for one pet with the given tasks."""
    scheduler = Scheduler(owner_with(*tasks, minutes=minutes, day_start=day_start), date(2026, 10, 18))
    return scheduler, scheduler.generate_plan()


def test_next_slot_on_an_empty_plan_is_the_day_start():
    scheduler, plan = plan_for(day_start="07:30")

    assert scheduler.find_next_slot(plan, 30) == "07:30"


def test_next_slot_skips_gaps_that_are_too_small():
    scheduler, plan = plan_for(
        Task("Meds", 5, "high", start_time="08:00"),
        Task("Breakfast", 10, "high", start_time="08:15"),  # 08:05-08:15 is only a 10-minute gap
    )

    assert scheduler.find_next_slot(plan, 10) == "08:05"  # fits exactly
    assert scheduler.find_next_slot(plan, 15) == "08:25"  # too big for the gap


def test_next_slot_respects_earliest_and_overlapping_busy_times():
    scheduler, plan = plan_for(
        Task("Breakfast", 10, "high", start_time="08:15"),
        Task("Litter box", 15, "medium", start_time="08:20"),  # overlaps Breakfast; busy until 08:35
    )

    assert scheduler.find_next_slot(plan, 5, earliest="08:16") == "08:35"
    assert scheduler.find_next_slot(plan, 5, earliest="09:00") == "09:00"


def test_next_slot_can_ignore_the_task_being_moved():
    scheduler, plan = plan_for(Task("Breakfast", 10, "high", start_time="08:15"))
    breakfast = plan.entries[0][1]

    assert scheduler.find_next_slot(plan, 10, earliest="08:15") == "08:25"
    assert scheduler.find_next_slot(plan, 10, earliest="08:15", ignore=breakfast) == "08:15"


def test_next_slot_returns_none_when_nothing_fits_before_midnight():
    scheduler, plan = plan_for(Task("Night walk", 30, "low", start_time="23:30"))

    assert scheduler.find_next_slot(plan, 30, earliest="23:15") is None
    with pytest.raises(ValueError):
        scheduler.find_next_slot(plan, 0)


def test_suggest_moves_clears_every_clash_without_creating_new_ones():
    owner = Owner("Jordan", 120)
    mochi, luna = Pet("Mochi", "dog"), Pet("Luna", "cat")
    owner.add_pet(mochi)
    owner.add_pet(luna)
    mochi.add_task(Task("Breakfast", 10, "high", start_time="08:15"))
    luna.add_task(Task("Breakfast", 10, "high", start_time="08:15"))
    luna.add_task(Task("Litter box", 5, "medium", start_time="08:20"))
    scheduler = Scheduler(owner, date(2026, 10, 18))
    plan = scheduler.generate_plan()

    moves = scheduler.suggest_moves(plan)

    # Same priority and start: the second one moves. Medium Litter box moves rather than high Breakfast.
    assert [(t.title, t.pet_name, old, new) for t, old, new in moves] == [
        ("Breakfast", "Luna", "08:15", "08:25"),
        ("Litter box", "Luna", "08:20", "08:35"),
    ]
    # Applying the moves leaves a plan with no warnings.
    for task, _, new in moves:
        owner.find_pet(task.pet_name).edit_task(task.title, {"start_time": new})
    assert scheduler.generate_plan().warnings == []


def test_suggest_moves_moves_the_lower_priority_task_even_if_it_starts_first():
    scheduler, plan = plan_for(
        Task("Brush", 20, "low", start_time="08:00"),
        Task("Meds", 5, "high", start_time="08:10"),
    )

    assert [(t.title, old, new) for t, old, new in scheduler.suggest_moves(plan)] == [("Brush", "08:00", "08:15")]


def test_suggest_moves_is_empty_without_clashes_and_reports_none_when_day_is_full():
    scheduler, plan = plan_for(Task("Meds", 5, "high", start_time="08:00"))
    assert scheduler.suggest_moves(plan) == []

    scheduler, plan = plan_for(
        Task("Night walk", 30, "high", start_time="23:30"),
        Task("Night snack", 10, "low", start_time="23:40"),
    )
    assert [(t.title, new) for t, _, new in scheduler.suggest_moves(plan)] == [("Night snack", None)]


# --- Saving and loading (data.json) ---


def test_save_and_load_round_trip_keeps_pets_tasks_and_history(tmp_path):
    owner = make_owner_with_tasks()
    owner.find_pet("Mochi").add_task(Task("Bath", 45, "low", frequency="weekly"))  # duplicate title on purpose
    Scheduler(owner, date(2026, 10, 18)).mark_task_complete("Luna", "Breakfast")
    path = tmp_path / "data.json"

    owner.save_to_json(path)
    loaded = Owner.load_from_json(path)

    assert loaded == owner  # every field of every pet and task, including dates and completed history
    assert loaded.find_pet("Luna").find_task("Breakfast").due_date == date(2026, 10, 19)
    assert all(task.pet_name == pet.name for pet in loaded.pets for task in pet.tasks)


def test_loaded_owner_builds_the_same_plan(tmp_path):
    owner = make_owner_with_tasks()
    path = tmp_path / "data.json"
    owner.save_to_json(path)

    day = date(2026, 10, 18)
    original = Scheduler(owner, day).generate_plan()
    reloaded = Scheduler(Owner.load_from_json(path), day).generate_plan()

    assert reloaded.explain() == original.explain()


def test_saved_file_is_readable_json_with_iso_dates(tmp_path):
    owner = owner_with(Task("Feeding", 10, "high"))
    Scheduler(owner, date(2026, 10, 18)).mark_task_complete("Mochi", "Feeding")
    path = tmp_path / "data.json"

    owner.save_to_json(path)

    saved = json.loads(path.read_text())
    tasks = saved["owner"]["pets"][0]["tasks"]
    assert saved["version"] == 1
    assert tasks[0]["last_completed"] == "2026-10-18" and tasks[1]["due_date"] == "2026-10-19"
    assert "pet_name" not in tasks[0]
    assert [p.name for p in tmp_path.iterdir()] == ["data.json"]  # no temp file left behind


def test_owner_with_no_pets_round_trips(tmp_path):
    path = tmp_path / "data.json"
    Owner("Jordan", 60, day_start="07:00").save_to_json(path)

    assert Owner.load_from_json(path) == Owner("Jordan", 60, day_start="07:00")


def test_loading_a_missing_file_raises_file_not_found(tmp_path):
    with pytest.raises(FileNotFoundError):
        Owner.load_from_json(tmp_path / "data.json")


@pytest.mark.parametrize(
    "text",
    [
        "not json",
        '{"version": 99, "owner": {}}',  # unknown version
        '{"version": 1}',  # missing owner
        '{"version": 1, "owner": {"name": "J", "available_minutes": 60, "day_start": "08:00",'
        ' "pets": [{"name": "Mochi", "species": "dog", "tasks": [{"title": "Walk", "duration_minutes": 30,'
        ' "priority": "urgent"}]}]}}',  # invalid task value
        '{"version": 1, "owner": {"name": "J", "available_minutes": 60, "day_start": "08:00",'
        ' "pets": [{"name": "Mochi", "species": "dog", "tasks": [{"title": "Walk", "duration_minutes": 30,'
        ' "priority": "high", "colour": "red"}]}]}}',  # unknown task field
        '{"version": 1, "owner": {"name": "J", "available_minutes": 60, "day_start": "08:00",'
        ' "pets": [{"name": "Mochi", "species": "dog", "tasks": [{"title": "Walk", "duration_minutes": 30,'
        ' "priority": "high", "due_date": "tomorrow"}]}]}}',  # bad date
    ],
)
def test_loading_bad_data_raises_value_error(tmp_path, text):
    path = tmp_path / "data.json"
    path.write_text(text)

    with pytest.raises(ValueError, match="not valid PawPal\\+ data"):
        Owner.load_from_json(path)


# --- Anchored recurrence (weekly tasks keep their weekday) ---


@pytest.mark.parametrize(
    "due, done, expected",
    [
        (date(2026, 10, 17), date(2026, 10, 17), date(2026, 10, 24)),  # Saturday task done on time
        (date(2026, 10, 17), date(2026, 10, 19), date(2026, 10, 24)),  # done Monday: still Saturday, no drift
        (date(2026, 10, 17), date(2026, 10, 24), date(2026, 10, 31)),  # a week late: next is strictly after today
        (date(2026, 10, 17), date(2026, 11, 9), date(2026, 11, 14)),  # three weeks missed: one copy, no backlog
        (date(2026, 10, 17), date(2026, 10, 14), date(2026, 10, 24)),  # done early: not due twice that week
        (date(2026, 12, 27), date(2027, 1, 2), date(2027, 1, 3)),  # across a year boundary
        (None, date(2026, 10, 19), date(2026, 10, 26)),  # no due date yet: the first completion sets the weekday
    ],
)
def test_weekly_task_keeps_its_weekday(due, done, expected):
    task = Task("Bath", 45, "low", frequency="weekly", due_date=due)

    next_task = task.mark_complete(done)

    assert next_task.due_date == expected
    assert next_task.completed is False and next_task.last_completed is None


@pytest.mark.parametrize(
    "due, done, expected",
    [
        (date(2026, 10, 10), date(2026, 10, 18), date(2026, 10, 19)),  # overdue: due tomorrow, not a backlog
        (date(2026, 10, 19), date(2026, 10, 17), date(2026, 10, 20)),  # early: the day after its due date
        (date(2026, 12, 31), date(2026, 12, 31), date(2027, 1, 1)),
    ],
)
def test_daily_task_is_due_the_day_after_it_was_done_or_due(due, done, expected):
    assert Task("Feeding", 10, "high", due_date=due).mark_complete(done).due_date == expected


def test_late_weekly_task_comes_back_on_its_weekday_in_the_scheduler():
    owner = owner_with(Task("Bath", 45, "low", frequency="weekly", due_date=date(2026, 10, 17)))  # a Saturday

    next_task = Scheduler(owner, date(2026, 10, 19)).mark_task_complete("Mochi", "Bath")  # done Monday

    assert next_task.due_date == date(2026, 10, 24) and next_task.due_date.weekday() == 5
    assert not Scheduler(owner, date(2026, 10, 23)).collect_tasks()
    assert Scheduler(owner, date(2026, 10, 24)).collect_tasks() == [next_task]
