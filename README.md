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
- **Priority-first time budgeting:** `generate_plan()` goes through due tasks from high to low priority (within a priority: earliest time of day first, tasks with no time last, then shortest first) and adds each one that still fits in the owner's available minutes. Tasks that don't fit are listed as skipped with the minutes needed and the minutes left. This is a greedy approach: it never removes a task it already chose, so a large high-priority task can be skipped while a smaller low-priority one still fits.
- **Fixed-time tasks:** a task with a `start_time` (for example, meds at 08:00) is placed at exactly that time.
- **Time-of-day placement:** flexible tasks are placed back to back from the owner's day start. A task that prefers afternoon or evening waits until 12:00 or 17:00, and any task that would overlap a fixed-time task moves to right after it.
- **Explained plans:** every scheduled task has a reason ("high priority, prefers morning"), and `DailyPlan.explain()` prints the whole plan, skipped tasks and warnings as text.

**Sorting and filtering**
- **Sorting by time:** `sort_by_time()` orders tasks by fixed time, or by the start of their preferred part of the day. Times are compared in minutes, so `"8:00"` comes before `"10:00"`. Tasks at the same time put higher priority first, and tasks with no time go last.
- **Sorting by priority, then time** *(Challenge 3)*: `sort_by_priority()` orders tasks high → medium → low, and by clock time within each priority (a fixed 07:00 task before a flexible 08:00 morning task, untimed tasks last). The planner uses this order to decide what fits, and the app can show the task list in either order. See [Priority-based scheduling](#priority-based-scheduling-schedulersort_by_priority).
- **Filtering:** `filter_tasks(pet_name, completed)` shows one pet's tasks, only tasks still to do, only finished tasks, or any combination.

**Recurring tasks**
- **Daily and weekly recurrence:** marking a task done records the day and adds the next copy to the same pet, due 1 day (daily) or 7 days (weekly) after the day it was completed. Dates roll over months and years correctly.
- **Due dates:** a task due in the future stays out of today's plan. An overdue task is still planned, and completing the same task twice in one day is refused.

**Conflict warnings**
- **Overlap detection:** `find_overlaps()` checks every pair of scheduled tasks and flags a pair when the later one starts before the earlier one ends. Back-to-back tasks (08:00-08:05, then 08:05) are fine. Each warning says whether the clash is for the same pet or different pets.
- **Past-midnight warning:** a task that ends after 24:00 is flagged.
- **Clashing rows marked in the app:** each clashing task is marked ⚠️ in the schedule table.

**Next available slot** *(advanced)*
- **Free-slot finder:** `find_next_slot(plan, minutes, earliest)` returns the first time at or after `earliest` where a task of that length fits without overlapping anything in the plan. It walks the busy times in start order and moves a cursor past each one until a gap is big enough, so small gaps are skipped and overlapping busy times are handled. It returns `None` if nothing fits before midnight.
- **Clash-free fix suggestions:** `suggest_moves(plan)` resolves clashes one at a time. For the earliest clash, it moves the lower-priority task (on a tie, the later one) to the next free slot at or after its current time, then checks again with that move in place. The suggested times therefore never clash with each other or with the rest of the plan, and high-priority tasks such as medication stay where they are. In the app, **Apply suggested times** updates the tasks in one click.

**Saving your data** *(Challenge 2)*
- **Automatic save and load:** pets, tasks (including completed history and due dates) and owner settings are saved to `data.json` after every change and loaded when the app starts. See [💾 Data Persistence](#-data-persistence).

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

The 49 tests in [`tests/test_pawpal.py`](tests/test_pawpal.py) check both normal use and edge cases:

- **Sorting:** tasks come out in time order (fixed times, then preferred part of the day, untimed tasks last); tasks at the same time put higher priority first; priority-then-time order puts a fixed 07:00 task before a flexible 08:00 one and untimed tasks last within each priority, then shortest first; a tight budget keeps the earlier of two high-priority tasks; priority, not time, decides what is skipped; `"HIGH"` is treated as `"high"`.
- **Building the plan:** an owner with no pets or a pet with no tasks gets an empty plan without crashing; a task that uses up exactly the remaining minutes is still scheduled; with 0 minutes every task is skipped with a reason; a large task that doesn't fit is skipped while a smaller one still fits.
- **Placing tasks:** fixed-time tasks land exactly at their time; flexible tasks move past fixed tasks they would overlap; afternoon tasks wait until 12:00; plan entries are in time order.
- **Recurring tasks:** completing a daily task creates one due tomorrow, and a weekly one creates one due in 7 days (across a month boundary); the new copy stays out of today's plan; completing the same task twice in one day is rejected; an overdue task is still planned, and its next copy is due the day after it was completed.
- **Conflict detection:** two tasks at the exact same time are flagged; overlaps are labeled as the same pet or different pets; three overlapping tasks give one warning per pair; back-to-back tasks are not conflicts; `find_overlaps()` returns each clashing pair with its times; a task ending exactly at midnight is fine, but one running past it is flagged.
- **Next available slot:** an empty plan's first slot is the day start; gaps that are too small are skipped and a gap that fits exactly is used; overlapping busy times are treated as one block; a task can ignore itself when looking for a new time; nothing fits past midnight; suggested moves clear every clash without creating new ones, and move the lower-priority task even if it starts first.
- **Saving and loading:** a save/load round trip gives back an identical owner (dates, completed history, duplicate titles, `pet_name`), and the reloaded data builds the same plan; the file is plain JSON with ISO dates and no temp file is left behind; an owner with no pets round-trips; a missing file raises `FileNotFoundError`; broken JSON, an unknown version, a missing owner, an invalid task value, an unknown field or a bad date each raise a clear `ValueError`.
- **Validation and filtering:** bad start times like `"8am"` or `"25:00"` are rejected; an invalid edit leaves the task unchanged; filtering by pet and by done/not done returns the right tasks.

Output of a successful run:

```
============================= test session starts ==============================
platform darwin -- Python 3.13.15, pytest-9.1.1, pluggy-1.7.0
rootdir: /Users/claudiacassandra/projects/ai110-module2show-pawpal-starter
configfile: pytest.ini
testpaths: tests
plugins: anyio-4.15.1
collected 49 items

tests/test_pawpal.py .................................................   [100%]

============================== 49 passed in 0.02s ==============================
```

### Confidence Level: ★★★★☆ (4/5)

All 49 tests pass. They cover each scheduling feature, including the edge cases most likely to break it: empty input, tasks at the same time, hitting the time limit exactly, repeating a task, and the midnight cutoff. I'm not giving 5 stars for three reasons. The Streamlit UI in `app.py` has no automated tests. The scheduler fills the day greedily by priority, so it can skip a high-priority task that doesn't fit even when a different combination would use the time better; the tests confirm this behavior but don't make it the best choice. And there are no tests for very large numbers of pets or tasks.

## 📐 Smarter Scheduling

Beyond building a basic plan, the `Scheduler` in [`pawpal_system.py`](pawpal_system.py) can sort, filter, repeat, and check tasks, and find free time to fix clashes.

| Feature | Method(s) | Summary |
|---------|-----------|---------|
| Sorting | `Scheduler.sort_by_time()`, `Scheduler.sort_by_priority()`, `Scheduler.task_time()`, `Scheduler.task_minutes()` | Orders tasks by time of day, or by priority when choosing what fits |
| Filtering | `Scheduler.filter_tasks()`, `Scheduler.collect_tasks()` | Shows one pet's tasks and/or done or not-done tasks; keeps only tasks due today |
| Conflict detection | `Scheduler.detect_conflicts()`, `Scheduler.find_overlaps()` | Warns when tasks overlap, for the same pet or different pets |
| Recurring tasks | `Task.mark_complete()`, `Task.next_occurrence()`, `Scheduler.mark_task_complete()` | Completing a daily or weekly task creates the next one automatically |
| Next available slot | `Scheduler.find_next_slot()`, `Scheduler.suggest_moves()` | Finds the first free gap of a given length, and suggests new times that clear every clash |

### Sorting: `Scheduler.sort_by_time()`

Returns tasks ordered from earliest to latest. `Scheduler.task_time()` decides each task's time: its fixed `start_time` if it has one, otherwise the start of its preferred part of the day (morning = the owner's `day_start`, afternoon = 12:00, evening = 17:00). Times are converted from `"HH:MM"` to minutes before sorting, so `"8:00"` correctly comes before `"10:00"`. Tasks with no time go last, and tasks at the same time are ordered by priority, high first.

A second method, `Scheduler.sort_by_priority()`, orders by priority first and time second. `generate_plan()` uses it to decide which tasks fit in the owner's available minutes. See below.

### Priority-based scheduling: `Scheduler.sort_by_priority()`

Every `Task` has a `priority` of `"low"`, `"medium"` or `"high"`. It is case-insensitive (`"HIGH"` works), anything else is rejected, and `Task.priority_rank()` turns it into 1, 2 or 3 for sorting. `sort_by_priority()` sorts by three keys:

1. **Priority**, high first (`-task.priority_rank()`).
2. **Time of day**, earliest first: `Scheduler.task_minutes()` turns the task's fixed time, or the start of its preferred part of the day, into minutes after midnight. Tasks with no time get 24:00 so they come last within their priority.
3. **Duration**, shortest first, so more small tasks fit when priority and time are tied.

`sort_by_time()` uses the same time key but puts it first, with priority only breaking ties. The two orders differ when priority and time disagree. In the demo, Brush teeth is the earliest task (07:00) but low priority, and Evening meds is the latest timed task (20:00) but high priority:

```
Sorted by time:
  07:00     Brush teeth     Mochi  low     to do
  07:30     Morning walk    Mochi  high    to do
  08:00     Heartworm meds  Mochi  high    to do
  08:15     Breakfast       Mochi  high    to do
  08:15     Breakfast       Luna   high    to do
  08:20     Litter box      Luna   medium  to do
  12:00     Brush coat      Luna   medium  to do
  17:00     Puzzle toy      Mochi  medium  to do
  20:00     Evening meds    Luna   high    to do
  any time  Bath            Mochi  low     to do
```

```
Sorted by priority, then time:
  07:30     Morning walk    Mochi  high    to do
  08:00     Heartworm meds  Mochi  high    to do
  08:15     Breakfast       Mochi  high    to do
  08:15     Breakfast       Luna   high    to do
  20:00     Evening meds    Luna   high    to do
  08:20     Litter box      Luna   medium  to do
  12:00     Brush coat      Luna   medium  to do
  17:00     Puzzle toy      Mochi  medium  to do
  07:00     Brush teeth     Mochi  low     to do
  any time  Bath            Mochi  low     to do
```

**How this changes the plan.** `generate_plan()` picks tasks in `sort_by_priority()` order until the owner's minutes run out. With the same tasks and only 25 minutes, all the high-priority tasks are considered first, earliest first. The 30-minute walk doesn't fit, but the 10-minute breakfasts and the 20:00 Evening meds do. The early, low-priority Brush teeth is skipped even though it comes first in the day. Litter box (medium) is skipped too, because the high tasks used every minute:

```
============================================================
Tight day: same tasks, only 25 minutes
============================================================
Choosing order: Morning walk (Mochi, high), Breakfast (Mochi, high), Breakfast (Luna, high), Evening meds (Luna, high), Litter box (Luna, medium), Brush coat (Luna, medium), Puzzle toy (Mochi, medium), Brush teeth (Mochi, low), Bath (Mochi, low)
Plan for 2026-10-18 (25 min scheduled)
  08:15-08:25  Breakfast for Mochi (10 min, high): high priority, fixed time
  08:15-08:25  Breakfast for Luna (10 min, high): high priority, fixed time
  20:00-20:05  Evening meds for Luna (5 min, high): high priority, fixed time
Skipped:
  Morning walk for Mochi: not enough time (30 min needed, 25 min left)
  Litter box for Luna: not enough time (5 min needed, 0 min left)
  Brush coat for Luna: not enough time (20 min needed, 0 min left)
  Puzzle toy for Mochi: not enough time (15 min needed, 0 min left)
  Brush teeth for Mochi: not enough time (5 min needed, 0 min left)
  Bath for Mochi: not enough time (45 min needed, 0 min left)
Warnings:
  Breakfast for Mochi (08:15-08:25) overlaps Breakfast for Luna (08:15-08:25); different pets
```

Before this change, ties within a priority were broken by *part of the day* (morning, afternoon, evening, none) rather than by clock time, so a fixed 07:00 high-priority task was considered after a flexible morning one. With a 30-minute budget, a 30-minute morning walk then pushed out 07:00 medication. Now the earlier task wins (tested in `test_tight_budget_keeps_the_earliest_task_within_the_same_priority`).

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

### Next available slot: `Scheduler.find_next_slot()` and `Scheduler.suggest_moves()`

`find_next_slot(plan, duration_minutes, earliest=None, ignore=None)` finds the first free gap:

1. Collect the plan's busy times as `(start, end)` in minutes, leaving out `ignore` (so a task can look for a new time for itself).
2. Start a cursor at `earliest` (default: the owner's day start) and walk the busy times in start order. If the next busy time starts at least `duration` minutes after the cursor, the gap fits. Otherwise move the cursor to the end of that busy time. Taking the later end each time means overlapping busy times act as one block.
3. Return the cursor as `"HH:MM"`, or `None` if the task would run past midnight.

```python
scheduler.find_next_slot(plan, 20)                   # first 20-minute gap from the day start
scheduler.find_next_slot(plan, 20, earliest="09:00") # first one at 09:00 or later
```

`suggest_moves(plan)` turns this into a fix for every clash. It repeatedly takes the earliest clashing pair and moves the lower-priority task (on a tie, the later one) to the next free slot at or after its current time, then checks again with that move in place. Each move lands in a free gap, so a moved task never needs to move twice and the loop ends after at most one move per task. It returns `(task, current start, new start)` for each task to move. For the demo's clashes, it keeps Mochi's Breakfast at 08:15, moves Luna's Breakfast to 08:25 and the Litter box to 08:35. Suggesting 08:25 for both Luna tasks would have caused a new clash, and this approach avoids that.

### Recurring tasks: `Scheduler.mark_task_complete(pet_name, title)`

Marks a task done and adds its next occurrence to the same pet:

1. `Task.mark_complete(day)` sets `completed` and `last_completed`, then calls `Task.next_occurrence(day)`.
2. `next_occurrence` returns a copy of the task with the same details, not completed, and `due_date = day + timedelta(days=1)` for daily tasks or `day + timedelta(weeks=1)` for weekly tasks. `timedelta` handles month and year boundaries (10/30 + 1 week = 11/06).
3. `Task.is_due_today(day)` returns `True` only when the task isn't completed and its `due_date` has arrived, so tomorrow's copy stays out of today's plan.

Completed tasks stay in the pet's list as history. `Pet.find_task()` picks the open copy first, and `mark_task_complete` refuses to complete a task that isn't due yet, so completing twice in one day can't skip ahead.

## 💾 Data Persistence

PawPal+ remembers your pets and tasks between runs by saving them to `data.json` next to `app.py`.

### How it works

1. **Starting the app:** `app.py` calls `Owner.load_from_json("data.json")`. If the file exists, your owner settings, pets and tasks come back exactly as you left them, and a "Loaded your pets and tasks" message appears. If there is no file yet, you start with an empty owner.
2. **Every change is saved:** at the end of each Streamlit run, the app compares `owner.to_dict()` with what it last saved. If anything changed (owner settings, a new pet or task, a task marked done, applied suggested times), it calls `owner.save_to_json("data.json")`. Nothing is written when nothing changed.
3. **Safe writes:** `save_to_json` writes to `data.json.tmp` first and then swaps it into place with `os.replace`, so a crash mid-save can't leave a half-written file.
4. **Bad files are kept, not overwritten:** if `data.json` can't be read (broken JSON, an unknown version, or invalid values like `"priority": "urgent"`), the app moves it to `data.corrupt.json`, shows an error, and starts fresh.
5. **Start over:** the **Start over** button in the sidebar deletes `data.json` and clears all pets and tasks.

You can also use it from Python:

```python
owner.save_to_json("data.json")
owner = Owner.load_from_json("data.json")
```

### Turning objects into JSON

`json` can't save dataclasses or `date` objects directly, so each class converts itself to and from plain dictionaries:

| Method | What it does |
|--------|--------------|
| `Task.to_dict()` | `dataclasses.asdict()`, then dates become `"YYYY-MM-DD"` strings. `pet_name` is left out because it is rebuilt on load. |
| `Task.from_dict(data)` | Turns date strings back into `date`s and calls `Task(**data)`, so **the same validation runs on saved data as on new tasks**. Bad values or unknown fields raise an error instead of loading silently. |
| `Owner.to_dict()` / `Owner.from_dict(data)` | Nest the pets and their tasks. Loading adds tasks through `Pet.add_task()`, so every task gets its `pet_name` back. |
| `Owner.save_to_json(path)` / `Owner.load_from_json(path)` | Wrap the data as `{"version": 1, "owner": ...}` and read or write the file. Loading raises `FileNotFoundError` for a missing file and `ValueError` with a clear message for anything invalid. |

**Why custom dictionaries instead of marshmallow?** A library like [marshmallow](https://marshmallow.readthedocs.io/) declares a schema for each class (`fields.Date()`, `fields.Nested(PetSchema)`) and handles conversion and validation for you. That pays off with many classes or complex types. PawPal+ has only two field types that need converting (`date` and the derived `pet_name`), and `Task` already validates itself in `__post_init__`. A marshmallow schema would repeat those rules in a second place, where they could drift apart, and add a dependency. The custom `to_dict`/`from_dict` methods are about 50 lines, need no new package, and reuse the existing validation.

### Example `data.json`

One dog with a daily walk that was done on Oct 18, so its next copy is due Oct 19:

```json
{
  "version": 1,
  "owner": {
    "name": "Jordan",
    "available_minutes": 60,
    "day_start": "08:00",
    "pets": [
      {
        "name": "Mochi",
        "species": "dog",
        "tasks": [
          {
            "title": "Walk",
            "duration_minutes": 30,
            "priority": "high",
            "preferred_time": "morning",
            "start_time": null,
            "frequency": "daily",
            "due_date": null,
            "completed": true,
            "last_completed": "2026-10-18"
          },
          {
            "title": "Walk",
            "duration_minutes": 30,
            "priority": "high",
            "preferred_time": "morning",
            "start_time": null,
            "frequency": "daily",
            "due_date": "2026-10-19",
            "completed": false,
            "last_completed": null
          }
        ]
      }
    ]
  }
}
```

### Files modified

| File | Change |
|------|--------|
| [`pawpal_system.py`](pawpal_system.py) | Added `Task.to_dict()` / `Task.from_dict()`, `Owner.to_dict()` / `Owner.from_dict()`, `Owner.save_to_json()` and `Owner.load_from_json()`, plus the `DATA_VERSION` and `DATE_FIELDS` constants. |
| [`app.py`](app.py) | Loads `data.json` on the first run of a session, saves after any change, handles unreadable files, and adds the sidebar **Start over** button. |
| [`tests/test_pawpal.py`](tests/test_pawpal.py) | 11 persistence tests, using pytest's `tmp_path` so they never touch your real `data.json`. |
| [`.gitignore`](.gitignore) | Ignores `data.json`, `data.json.tmp` and `data.corrupt.json`, since they hold your personal data. |
| [`diagrams/uml_final.mmd`](diagrams/uml_final.mmd) | Added the new methods. |

## 📸 Demo Walkthrough

Start the app with `streamlit run app.py`, or run the terminal demo with `python main.py`.

### What you can do in the app

| Section | Actions |
|---------|---------|
| **Owner** | Set your name, how many minutes you have for pet care today, and when your day starts. |
| **Pets** | Add a pet with a name and species (dog, cat, other). A table lists each pet and how many tasks it has. Duplicate names are refused. |
| **Tasks** | Add a task for a pet with a title, duration, priority, preferred time (any/morning/afternoon/evening) and frequency (daily/weekly), and optionally pin it to a fixed time. **Mark a task done** from a list of today's tasks. The task table can be sorted by **Time** or **Priority, then time**, and filtered by pet and by All / To do / Done. Priorities show as 🔴 high, 🟡 medium and 🟢 low. |
| **Build Schedule** | **Generate schedule** builds today's plan: a summary message, any time clashes with a **Suggested fix** and an **Apply suggested times** button, the schedule table with a reason for each task, tasks that didn't fit, a **Find a free time slot** helper (minutes needed + no earlier than → next free slot), and a plain-text version of the plan. The plan stays on screen and updates as you add or complete tasks. |

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
   - A **⚠️ 3 time clashes** box, one line per clash, for example: *"08:20: Litter box (Luna) overlaps Breakfast (Luna) by 5 min; Luna can't do both at once."*
   - A **💡 Suggested fix** box: *"Move Breakfast (Luna) from 08:15 to 08:25"* and *"Move Litter box (Luna) from 08:20 to 08:35"*. Mochi's Breakfast stays put, and the two new times don't clash with each other.
   - The schedule table: Breakfast (Mochi) ⚠️ 08:15, Breakfast (Luna) ⚠️ 08:15, Litter box ⚠️ 08:20, Brush coat 12:00 ("medium priority, prefers afternoon").
   - A **Didn't fit today** box: *"Bath (Mochi): not enough time (45 min needed, 15 min left)"*.
6. **Adjust the plan.** Raise **Minutes available today** to 90. The plan updates right away: Bath now fits and is placed at 12:20-13:05, after Brush coat. Then click **Apply suggested times**. Luna's Breakfast moves to 08:25-08:35 and the Litter box to 08:35-08:40, the ⚠️ marks disappear, and the summary turns green: *"Scheduled 5 tasks (90 of 90 min) with no time clashes."*
7. **Find free time.** Open **Find a free time slot**. With the default 15 minutes from 08:00, it answers *"Next free 15-minute slot: 08:00-08:15"*, the gap before Mochi's Breakfast.
8. **Close and reopen.** Stop the app and run `streamlit run app.py` again. A *"Loaded your pets and tasks from data.json."* message appears, and Mochi, Luna, all their tasks (with Walk still ✅ done and 🔁 due tomorrow) and the 90 minutes are back. Click **Start over** in the sidebar to clear everything.

### Scheduler behaviors shown

- **Sorting by time:** the task table and plan are ordered by time, not by the order tasks were added.
- **Filtering:** the pet and status filters use `filter_tasks()`.
- **Daily recurrence:** completing Walk creates tomorrow's Walk and keeps it out of today's plan.
- **Priority-based scheduling:** switch **Sort by** to *Priority, then time* to see the order the planner uses. With 60 minutes, the high and medium tasks fit first and the low-priority Bath is skipped with a reason.
- **Time-of-day placement:** Brush coat waits until 12:00 because it prefers the afternoon.
- **Conflict warnings:** overlaps between the same pet and different pets are both flagged.
- **Data persistence:** everything is saved to `data.json` and comes back when the app is reopened.
- **Next available slot:** `suggest_moves()` offers clash-free new times that keep the higher-priority task in place, and `find_next_slot()` answers "when am I next free for N minutes?".

### Sample CLI output

`python main.py` runs the same features without the UI: one owner with 90 minutes, two pets, tasks added out of order, two deliberate time clashes, and two tasks where priority and time disagree. It shows the task list sorted by time and by priority, today's plan, the suggested fix, a free-slot search, and the same tasks planned on a tight 25-minute day. The date is fixed to 2026-10-18 so the output is the same every run.

```
Unsorted (each pet's tasks in the order added):
  17:00     Puzzle toy      Mochi  medium  to do
  any time  Bath            Mochi  low     to do
  08:00     Heartworm meds  Mochi  high    to do
  07:30     Morning walk    Mochi  high    to do
  07:00     Brush teeth     Mochi  low     to do
  08:15     Breakfast       Mochi  high    to do
  08:15     Breakfast       Luna   high    to do
  12:00     Brush coat      Luna   medium  to do
  20:00     Evening meds    Luna   high    to do
  08:20     Litter box      Luna   medium  to do

Sorted by time:
  07:00     Brush teeth     Mochi  low     to do
  07:30     Morning walk    Mochi  high    to do
  08:00     Heartworm meds  Mochi  high    to do
  08:15     Breakfast       Mochi  high    to do
  08:15     Breakfast       Luna   high    to do
  08:20     Litter box      Luna   medium  to do
  12:00     Brush coat      Luna   medium  to do
  17:00     Puzzle toy      Mochi  medium  to do
  20:00     Evening meds    Luna   high    to do
  any time  Bath            Mochi  low     to do

Sorted by priority, then time:
  07:30     Morning walk    Mochi  high    to do
  08:00     Heartworm meds  Mochi  high    to do
  08:15     Breakfast       Mochi  high    to do
  08:15     Breakfast       Luna   high    to do
  20:00     Evening meds    Luna   high    to do
  08:20     Litter box      Luna   medium  to do
  12:00     Brush coat      Luna   medium  to do
  17:00     Puzzle toy      Mochi  medium  to do
  07:00     Brush teeth     Mochi  low     to do
  any time  Bath            Mochi  low     to do

Only Luna's tasks:
  08:15     Breakfast       Luna   high    to do
  12:00     Brush coat      Luna   medium  to do
  20:00     Evening meds    Luna   high    to do
  08:20     Litter box      Luna   medium  to do

Marked Heartworm meds done; next one (daily) is due 2026-10-19.

Completed tasks:
  08:00     Heartworm meds  Mochi  high    done 2026-10-18

Mochi's tasks still to do, sorted by time:
  07:00     Brush teeth     Mochi  low     to do
  07:30     Morning walk    Mochi  high    to do
  08:00     Heartworm meds  Mochi  high    due 2026-10-19
  08:15     Breakfast       Mochi  high    to do
  17:00     Puzzle toy      Mochi  medium  to do
  any time  Bath            Mochi  low     to do

============================================================
Today's Schedule for Jordan's pets
============================================================
Plan for 2026-10-18 (85 min scheduled)
  07:00-07:05  Brush teeth for Mochi (5 min, low): low priority, fixed time
  07:30-08:00  Morning walk for Mochi (30 min, high): high priority, prefers morning
  08:15-08:25  Breakfast for Mochi (10 min, high): high priority, fixed time
  08:15-08:25  Breakfast for Luna (10 min, high): high priority, fixed time
  08:20-08:25  Litter box for Luna (5 min, medium): medium priority, fixed time
  12:00-12:20  Brush coat for Luna (20 min, medium): medium priority, prefers afternoon
  20:00-20:05  Evening meds for Luna (5 min, high): high priority, fixed time
Skipped:
  Puzzle toy for Mochi: not enough time (15 min needed, 10 min left)
  Bath for Mochi: not enough time (45 min needed, 5 min left)
Warnings:
  Breakfast for Mochi (08:15-08:25) overlaps Breakfast for Luna (08:15-08:25); different pets
  Breakfast for Mochi (08:15-08:25) overlaps Litter box for Luna (08:20-08:25); different pets
  Breakfast for Luna (08:15-08:25) overlaps Litter box for Luna (08:20-08:25); both for Luna

Suggested fix for the clashes:
  Move Breakfast for Luna from 08:15 to 08:25
  Move Litter box for Luna from 08:20 to 08:35
Next free 20-minute slot after 09:00: 09:00

============================================================
Tight day: same tasks, only 25 minutes
============================================================
Choosing order: Morning walk (Mochi, high), Breakfast (Mochi, high), Breakfast (Luna, high), Evening meds (Luna, high), Litter box (Luna, medium), Brush coat (Luna, medium), Puzzle toy (Mochi, medium), Brush teeth (Mochi, low), Bath (Mochi, low)
Plan for 2026-10-18 (25 min scheduled)
  08:15-08:25  Breakfast for Mochi (10 min, high): high priority, fixed time
  08:15-08:25  Breakfast for Luna (10 min, high): high priority, fixed time
  20:00-20:05  Evening meds for Luna (5 min, high): high priority, fixed time
Skipped:
  Morning walk for Mochi: not enough time (30 min needed, 25 min left)
  Litter box for Luna: not enough time (5 min needed, 0 min left)
  Brush coat for Luna: not enough time (20 min needed, 0 min left)
  Puzzle toy for Mochi: not enough time (15 min needed, 0 min left)
  Brush teeth for Mochi: not enough time (5 min needed, 0 min left)
  Bath for Mochi: not enough time (45 min needed, 0 min left)
Warnings:
  Breakfast for Mochi (08:15-08:25) overlaps Breakfast for Luna (08:15-08:25); different pets
```
