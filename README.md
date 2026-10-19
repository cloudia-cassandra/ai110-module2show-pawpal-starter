# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.

## 🏗️ Implementation Summary

The scheduling logic lives in [`pawpal_system.py`](pawpal_system.py). It has five classes:

- **`Task`** is one care activity. It has a title, a duration, a priority (low/medium/high), an optional preferred part of the day, an optional fixed start time, a daily or weekly frequency, and whether it has been completed. It checks its own values when it is created and can tell whether it is due on a given day.
- **`Pet`** holds a pet's name, species, and list of tasks. It adds, finds, edits, and removes tasks, and tags each task with the pet's name.
- **`Owner`** holds the owner's name, how many minutes they have for pet care, when their day starts, and their pets. `get_all_tasks()` returns every pet's tasks in one list.
- **`Scheduler`** builds the plan. It gets tasks from `Owner.get_all_tasks()`, keeps the ones due today, and then:
  1. picks tasks in priority order until the owner's time runs out, and records why any task was skipped;
  2. places fixed-time tasks exactly at their time;
  3. places the rest one after another from the start of the day, waiting for their preferred part of the day (afternoon from 12:00, evening from 17:00) and moving past fixed-time tasks;
  4. warns about any overlapping tasks.
- **`DailyPlan`** is the result: scheduled tasks with start times and reasons, skipped tasks with reasons, and warnings. `explain()` turns it into readable text.

[`main.py`](main.py) is a terminal demo with one owner and two pets. The class diagram is in [`diagrams/uml.mmd`](diagrams/uml.mmd).

## 🖥️ Sample Output

Output of `python main.py` (one owner, two pets, tasks added out of order with two deliberate time clashes, 90 minutes available):

```
Unsorted (each pet's tasks in the order added):
  17:00     Puzzle toy      Mochi  medium  to do
  any time  Bath            Mochi  low     to do
  08:00     Heartworm meds  Mochi  high    to do
  07:30     Morning walk    Mochi  high    to do
  08:15     Breakfast       Mochi  high    to do
  08:15     Breakfast       Luna   high    to do
  12:00     Brush coat      Luna   medium  to do
  08:20     Litter box      Luna   medium  to do

Sorted by time:
  07:30     Morning walk    Mochi  high    to do
  08:00     Heartworm meds  Mochi  high    to do
  08:15     Breakfast       Mochi  high    to do
  08:15     Breakfast       Luna   high    to do
  08:20     Litter box      Luna   medium  to do
  12:00     Brush coat      Luna   medium  to do
  17:00     Puzzle toy      Mochi  medium  to do
  any time  Bath            Mochi  low     to do

Only Luna's tasks:
  08:15     Breakfast       Luna   high    to do
  12:00     Brush coat      Luna   medium  to do
  08:20     Litter box      Luna   medium  to do

Marked Heartworm meds done; next one (daily) is due 2026-10-19.

Completed tasks:
  08:00     Heartworm meds  Mochi  high    done 2026-10-18

Mochi's tasks still to do, sorted by time:
  07:30     Morning walk    Mochi  high    to do
  08:00     Heartworm meds  Mochi  high    due 2026-10-19
  08:15     Breakfast       Mochi  high    to do
  17:00     Puzzle toy      Mochi  medium  to do
  any time  Bath            Mochi  low     to do

============================================================
Today's Schedule for Jordan's pets
============================================================
Plan for 2026-10-18 (90 min scheduled)
  07:30-08:00  Morning walk for Mochi (30 min, high): high priority, prefers morning
  08:15-08:25  Breakfast for Mochi (10 min, high): high priority, fixed time
  08:15-08:25  Breakfast for Luna (10 min, high): high priority, fixed time
  08:20-08:25  Litter box for Luna (5 min, medium): medium priority, fixed time
  12:00-12:20  Brush coat for Luna (20 min, medium): medium priority, prefers afternoon
  17:00-17:15  Puzzle toy for Mochi (15 min, medium): medium priority, prefers evening
Skipped:
  Bath for Mochi: not enough time (45 min needed, 0 min left)
Warnings:
  Breakfast for Mochi (08:15-08:25) overlaps Breakfast for Luna (08:15-08:25); different pets
  Breakfast for Mochi (08:15-08:25) overlaps Litter box for Luna (08:20-08:25); different pets
  Breakfast for Luna (08:15-08:25) overlaps Litter box for Luna (08:20-08:25); both for Luna
```

## 🧪 Testing PawPal+

```bash
# Run the full test suite:
pytest

# Run with coverage:
pytest --cov
```

Sample test output:

```
# Paste your pytest output here
```

## 📐 Smarter Scheduling

Beyond building a basic plan, the `Scheduler` in [`pawpal_system.py`](pawpal_system.py) can sort, filter, repeat, and check tasks.

| Feature | Method(s) | Summary |
|---------|-----------|---------|
| Sorting | `Scheduler.sort_by_time()`, `Scheduler.task_time()`, `Scheduler.sort_tasks()` | Orders tasks by time of day, or by priority when choosing what fits |
| Filtering | `Scheduler.filter_tasks()`, `Scheduler.collect_tasks()` | Shows one pet's tasks and/or done or not-done tasks; keeps only tasks due today |
| Conflict detection | `Scheduler.detect_conflicts()` | Warns when tasks overlap, for the same pet or different pets |
| Recurring tasks | `Task.mark_complete()`, `Task.next_occurrence()`, `Scheduler.mark_task_complete()` | Completing a daily or weekly task creates the next one automatically |

### Sorting: `Scheduler.sort_by_time()`

Returns tasks ordered from earliest to latest. `Scheduler.task_time()` decides each task's time: its fixed `start_time` if it has one, otherwise the start of its preferred part of the day (morning = the owner's `day_start`, afternoon = 12:00, evening = 17:00). Times are converted from `"HH:MM"` to minutes before sorting, so `"8:00"` correctly comes before `"10:00"`. Tasks with no time go last, and tasks at the same time are ordered by priority, high first.

A second method, `Scheduler.sort_tasks()`, orders by priority (then preferred time, then shortest first). `generate_plan()` uses it to decide which tasks fit in the owner's available minutes.

### Filtering: `Scheduler.filter_tasks(pet_name=None, completed=None)`

Returns the owner's tasks, filtered only by the arguments you pass:

```python
scheduler.filter_tasks(pet_name="Luna")                   # only Luna's tasks
scheduler.filter_tasks(completed=False)                   # only tasks still to do
scheduler.filter_tasks(pet_name="Mochi", completed=True)  # Mochi's finished tasks
```

`Scheduler.collect_tasks()` is the filter the planner uses: it keeps only tasks due on the scheduler's date (see recurring tasks below).

### Conflict detection: `Scheduler.detect_conflicts(plan)`

Called at the end of `generate_plan()`. It sorts the plan by start time and checks every pair of tasks with `itertools.combinations`: if the later task starts before the earlier one ends, they overlap. Each warning names both tasks, their times, and whether they are for the same pet or different pets. It also warns about any task that runs past midnight. Back-to-back tasks (one ends at 08:05, the next starts at 08:05) are not conflicts.

It is deliberately lightweight: it returns warning messages instead of raising an error, and both conflicting tasks stay in the plan so the owner can decide. Flexible tasks are already placed around fixed-time tasks, so in practice warnings come from two fixed-time tasks that overlap. `Task` also rejects malformed fixed times such as `"8am"` when it is created, so a bad time can't crash the scheduler later.

### Recurring tasks: `Scheduler.mark_task_complete(pet_name, title)`

Marks a task done and adds its next occurrence to the same pet:

1. `Task.mark_complete(day)` sets `completed` and `last_completed`, then calls `Task.next_occurrence(day)`.
2. `next_occurrence` returns a copy of the task with the same details, not completed, and `due_date = day + timedelta(days=1)` for daily tasks or `day + timedelta(weeks=1)` for weekly tasks. `timedelta` handles month and year boundaries (10/30 + 1 week = 11/06).
3. `Task.is_due_today(day)` returns `True` only when the task isn't completed and its `due_date` has arrived, so tomorrow's copy stays out of today's plan.

Completed tasks stay in the pet's list as history. `Pet.find_task()` picks the open copy first, and `mark_task_complete` refuses to complete a task that isn't due yet, so completing twice in one day can't skip ahead.

## 📸 Demo Walkthrough

Describe your app in numbered steps so a reader can follow along without watching a video:

1. <!-- Describe this step -->
2. <!-- Describe this step -->
3. <!-- Describe this step -->
4. <!-- Describe this step -->
5. <!-- Add more steps as needed -->

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or link to a demo video here -->
