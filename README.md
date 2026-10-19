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

## ✨ Features

Each feature below is implemented in [`pawpal_system.py`](pawpal_system.py) and covered by tests in [`tests/test_pawpal.py`](tests/test_pawpal.py).

**Planning the day**
- **Priority-first time budgeting:** `generate_plan()` goes through due tasks from high to low priority (ties: morning → afternoon → evening → no preference, then shortest first) and adds each one that still fits in the owner's available minutes. Tasks that don't fit are listed as skipped with the minutes needed and the minutes left. This is a greedy approach: it never removes a task it already chose, so a large high-priority task can be skipped while a smaller low-priority one still fits.
- **Fixed-time tasks:** a task with a `start_time` (for example, meds at 08:00) is placed at exactly that time.
- **Time-of-day placement:** flexible tasks are placed back to back from the owner's day start. A task that prefers afternoon or evening waits until 12:00 or 17:00, and any task that would overlap a fixed-time task moves to right after it.
- **Explained plans:** every scheduled task has a reason ("high priority, prefers morning"), and `DailyPlan.explain()` prints the whole plan, skipped tasks and warnings as text.

**Sorting and filtering**
- **Sorting by time:** `sort_by_time()` orders tasks by fixed time, or by the start of their preferred part of the day. Times are compared in minutes, so `"8:00"` comes before `"10:00"`. Tasks at the same time put higher priority first, and tasks with no time go last.
- **Sorting by priority:** `sort_tasks()` orders tasks high → low, used to decide what fits in the time budget.
- **Filtering:** `filter_tasks(pet_name, completed)` shows one pet's tasks, only tasks still to do, only finished tasks, or any combination.

**Recurring tasks**
- **Daily and weekly recurrence:** marking a task done records the day and adds the next copy to the same pet, due 1 day (daily) or 7 days (weekly) after the day it was completed. Dates roll over months and years correctly.
- **Due dates:** a task due in the future stays out of today's plan. An overdue task is still planned, and completing the same task twice in one day is refused.

**Conflict warnings**
- **Overlap detection:** `find_overlaps()` checks every pair of scheduled tasks and flags a pair when the later one starts before the earlier one ends. Back-to-back tasks (08:00-08:05, then 08:05) are fine. Each warning says whether the clash is for the same pet or different pets.
- **Past-midnight warning:** a task that ends after 24:00 is flagged.
- **Fix suggestions in the app:** clashing rows are marked ⚠️ in the schedule, and each clash comes with a suggested new time (the end of the earlier task).

**Input validation**
- Priority, frequency, preferred time, duration and start time are checked when a task is created or edited. Bad values such as `"8am"` or `"25:00"` are rejected with a clear message, and a failed edit leaves the task unchanged.

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

[`main.py`](main.py) is a terminal demo with one owner and two pets. The final class diagram is in [`diagrams/uml_final.mmd`](diagrams/uml_final.mmd) (first draft: [`diagrams/uml.mmd`](diagrams/uml.mmd)).

## 🖥️ Sample Output

See [Sample CLI output](#sample-cli-output) in the Demo Walkthrough below.

## 🧪 Testing PawPal+

Run the full test suite from the project folder (with `.venv` activated):

```bash
python -m pytest
```

The 27 tests in [`tests/test_pawpal.py`](tests/test_pawpal.py) check both normal use and edge cases:

- **Sorting:** tasks come out in time order (fixed times, then preferred part of the day, untimed tasks last); tasks at the same time put higher priority first; priority order breaks ties by time of day, then shortest first; `"HIGH"` is treated as `"high"`.
- **Building the plan:** an owner with no pets or a pet with no tasks gets an empty plan without crashing; a task that uses up exactly the remaining minutes is still scheduled; with 0 minutes every task is skipped with a reason; a large task that doesn't fit is skipped while a smaller one still fits.
- **Placing tasks:** fixed-time tasks land exactly at their time; flexible tasks move past fixed tasks they would overlap; afternoon tasks wait until 12:00; plan entries are in time order.
- **Recurring tasks:** completing a daily task creates one due tomorrow, and a weekly one creates one due in 7 days (across a month boundary); the new copy stays out of today's plan; completing the same task twice in one day is rejected; an overdue task is still planned, and its next copy is due the day after it was completed.
- **Conflict detection:** two tasks at the exact same time are flagged; overlaps are labeled as the same pet or different pets; three overlapping tasks give one warning per pair; back-to-back tasks are not conflicts; `find_overlaps()` returns each clashing pair with its times; a task ending exactly at midnight is fine, but one running past it is flagged.
- **Validation and filtering:** bad start times like `"8am"` or `"25:00"` are rejected; an invalid edit leaves the task unchanged; filtering by pet and by done/not done returns the right tasks.

Output of a successful run:

```
============================= test session starts ==============================
platform darwin -- Python 3.13.15, pytest-9.1.1, pluggy-1.7.0
rootdir: /Users/claudiacassandra/projects/ai110-module2show-pawpal-starter
configfile: pytest.ini
testpaths: tests
plugins: anyio-4.15.1
collected 27 items

tests/test_pawpal.py ...........................                         [100%]

============================== 27 passed in 0.01s ==============================
```

### Confidence Level: ★★★★☆ (4/5)

All 27 tests pass. They cover each scheduling feature, including the edge cases most likely to break it: empty input, tasks at the same time, hitting the time limit exactly, repeating a task, and the midnight cutoff. I'm not giving 5 stars for three reasons. The Streamlit UI in `app.py` has no automated tests. The scheduler fills the day greedily by priority, so it can skip a high-priority task that doesn't fit even when a different combination would use the time better; the tests confirm this behavior but don't make it the best choice. And there are no tests for very large numbers of pets or tasks.

## 📐 Smarter Scheduling

Beyond building a basic plan, the `Scheduler` in [`pawpal_system.py`](pawpal_system.py) can sort, filter, repeat, and check tasks.

| Feature | Method(s) | Summary |
|---------|-----------|---------|
| Sorting | `Scheduler.sort_by_time()`, `Scheduler.task_time()`, `Scheduler.sort_tasks()` | Orders tasks by time of day, or by priority when choosing what fits |
| Filtering | `Scheduler.filter_tasks()`, `Scheduler.collect_tasks()` | Shows one pet's tasks and/or done or not-done tasks; keeps only tasks due today |
| Conflict detection | `Scheduler.detect_conflicts()`, `Scheduler.find_overlaps()` | Warns when tasks overlap, for the same pet or different pets |
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

Start the app with `streamlit run app.py`, or run the terminal demo with `python main.py`.

### What you can do in the app

| Section | Actions |
|---------|---------|
| **Owner** | Set your name, how many minutes you have for pet care today, and when your day starts. |
| **Pets** | Add a pet with a name and species (dog, cat, other). A table lists each pet and how many tasks it has. Duplicate names are refused. |
| **Tasks** | Add a task for a pet with a title, duration, priority, preferred time (any/morning/afternoon/evening) and frequency (daily/weekly), and optionally pin it to a fixed time. **Mark a task done** from a list of today's tasks. The task table is sorted by time and can be filtered by pet and by All / To do / Done. |
| **Build Schedule** | **Generate schedule** builds today's plan: a summary message, any time clashes with suggested fixes, the schedule table with a reason for each task, tasks that didn't fit, and a plain-text version of the plan. The plan stays on screen and updates as you add or complete tasks. |

### Example workflow

1. **Set up the owner.** Keep the defaults: *Jordan*, **60** minutes available, day starts at **08:00**.
2. **Add two pets.** Add *Mochi* (dog), then *Luna* (cat). Each shows a green "Added …" message and appears in the pets table.
3. **Add tasks.**

   | Pet | Task | Minutes | Priority | Time |
   |-----|------|---------|----------|------|
   | Mochi | Walk | 30 | high | prefers morning |
   | Mochi | Breakfast | 10 | high | fixed 08:15 |
   | Luna | Breakfast | 10 | high | fixed 08:15 |
   | Luna | Litter box | 5 | medium | fixed 08:20 |
   | Luna | Brush coat | 20 | medium | prefers afternoon |
   | Mochi | Bath | 45 | low | any time |

   The task table sorts them by time, whatever order you added them in: Walk 08:00, the two Breakfasts at 08:15, Litter box 08:20, Brush coat 12:00, and Bath ("any time") last.
4. **Complete a task.** Under **Mark a task done**, choose *Walk (Mochi)* and click **Mark done**. The app shows *"Done: Walk for Mochi. Next one (daily) is due Mon Oct 19."* The table now has two Walk rows: **✅ done Oct 18** and **🔁 due Oct 19**. Set the filter to **Done** to see only the finished walk.
5. **Generate today's schedule.** Click **Generate schedule**:
   - A yellow summary: *"Scheduled 4 tasks (45 of 60 min), but some times need your attention."*
   - A **⚠️ 3 time clashes** box, one line per clash with a suggested fix, for example: *"08:20: Litter box (Luna) overlaps Breakfast (Luna) by 5 min; Luna can't do both at once. Try moving Litter box to 08:25 or later."*
   - The schedule table: Breakfast (Mochi) ⚠️ 08:15, Breakfast (Luna) ⚠️ 08:15, Litter box ⚠️ 08:20, Brush coat 12:00 ("medium priority, prefers afternoon").
   - A **Didn't fit today** box: *"Bath (Mochi): not enough time (45 min needed, 15 min left)"*.
6. **Adjust and regenerate.** Raise **Minutes available today** to 90. The plan updates right away: Bath now fits and is placed at 12:20-13:05, after Brush coat. The clash warnings stay until the fixed times stop overlapping. If you add Luna's Breakfast at 08:25 and Litter box at 08:35 instead, there are no clashes and the summary turns green.

### Scheduler behaviors shown

- **Sorting by time:** the task table and plan are ordered by time, not by the order tasks were added.
- **Filtering:** the pet and status filters use `filter_tasks()`.
- **Daily recurrence:** completing Walk creates tomorrow's Walk and keeps it out of today's plan.
- **Priority-first time budget:** with 60 minutes, the high and medium tasks fit first and the low-priority Bath is skipped with a reason.
- **Time-of-day placement:** Brush coat waits until 12:00 because it prefers the afternoon.
- **Conflict warnings:** overlaps between the same pet and different pets are both flagged, with a suggested time to move to.

### Sample CLI output

`python main.py` runs the same features without the UI: one owner with 90 minutes, two pets, tasks added out of order, and two deliberate time clashes. The date is fixed to 2026-10-18 so the output is the same every run.

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
