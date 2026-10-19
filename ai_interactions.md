# AI Interactions Log

> **Stretch features only.** Only fill in the sections that apply to stretch features you attempted. If you did not attempt a stretch feature, leave its section blank or delete it. This file is not required for the core project.

---

## Agent Workflow (SF7)

> Document your experience using an AI agent (e.g., Cursor Agent, Claude, Copilot) to make multi-step changes autonomously.

**Agent used:** Claude Code (Claude Opus 5.5) in VS Code, in agent mode: it read files, edited them, and ran commands itself.

**What task did you give the agent?**

Challenge 1: *"Add a third algorithmic capability (like 'next available slot', weighted prioritization, etc.) that goes beyond the basic requirements."* I attached `pawpal_system.py` and asked it to document the work here as well.

The agent chose **next available slot** because it fixed a real weakness. Before this change, the app's fix for a clash was "move the later task to when the earlier one ends". That could suggest a time that was also taken, or the same new time for two tasks. For example, both of Luna's clashing tasks were told to move to 08:25, where they would clash with each other.

**What did the agent do?**

| File | Change |
|------|--------|
| `pawpal_system.py` | Added three `Scheduler` methods. `_first_gap()` walks the busy times in start order and returns the first gap long enough. `find_next_slot(plan, duration, earliest, ignore)` returns the first free `"HH:MM"`, or `None` before midnight. `suggest_moves(plan)` resolves clashes one at a time, moving the lower-priority task (later one on a tie) into the next free slot, so its suggestions never clash with each other. |
| `tests/test_pawpal.py` | Added 8 tests: empty plan, gaps too small vs. an exact fit, overlapping busy times, `earliest`, `ignore`, no room before midnight, invalid duration, and `suggest_moves` (clears every clash, moves the lower-priority task even if it starts first, reports `None` when the day is full). Suite went from 27 to 35 tests. |
| `app.py` | Replaced the old per-clash "Try moving X to …" hints with a **💡 Suggested fix** box and an **Apply suggested times** button (uses `Pet.edit_task()`), and added a **Find a free time slot** helper. |
| `main.py` | Prints the suggested fix and a free-slot search after the schedule. |
| `README.md` | New "Next available slot" feature and Smarter Scheduling section, updated demo walkthrough (new steps 6–7), test count and pytest output, and fresh `main.py` output. |
| `diagrams/uml_final.mmd` | Added the three new methods and updated the notes. |
| `reflection.md` | Updated the test count and the conflict example that quoted the old hint. |

Steps it took, in order:

1. Read `main.py` and checked `git status` so it knew the starting state.
2. Wrote the three methods, then the 8 tests, and ran `pytest` (35 passed).
3. Updated `app.py`, then drove the app headlessly with Streamlit's `AppTest`: two pets, three clashing fixed-time tasks, a free-slot search, then clicking **Apply suggested times**. The summary went from "3 time clashes" to "no time clashes".
4. Updated `main.py` and ran it.
5. Ran the README's example workflow through `AppTest` again and wrote the walkthrough from the real output (for example "Move Breakfast (Luna) from 08:15 to 08:25").
6. Updated the README, UML, and reflection, then searched for stale text ("Try moving", "27 tests").

**What did you have to verify or fix manually?**

The agent checked its own work and caught these:

- **Its first design for suggestions was wrong.** Suggesting a new time for each clash on its own would have sent both of Luna's tasks to 08:25 and created a new clash. It changed `suggest_moves()` to resolve clashes one at a time, with earlier moves taken into account, and added a test that applies the moves and checks the new plan has no warnings.
- **Priority, not start time, decides who moves.** With a low-priority brush at 08:00 and high-priority meds at 08:10, moving "the later one" would have moved the meds. The rule is now "lower priority moves; later one only on a tie", and a test covers it.
- **Flexible tasks are busy time too.** In the app run, Mochi's flexible Walk had been placed at 08:25-08:55, so the suggestion for Luna's Breakfast became 08:55, not 08:25. That's correct (the slot finder avoids every task in the plan), but it meant the README numbers had to come from a real run, not from the `main.py` scenario.
- **Stale documentation.** The README and reflection still quoted the old "Try moving Litter box to 08:25 or later" hint and said 27 tests. Both were updated.

My own review: *(fill in anything you checked or changed by hand, e.g. reading the diff, running `streamlit run app.py` in the browser, or adjusting wording)*

---

## Prompt Comparison (SF11)

> Compare two different prompts (or two different models) on the same task.

**Task:** rescheduling recurring tasks. `Task.next_occurrence()` set the next due date to *completion day + 1 day/week*. A weekly task done late therefore drifted to a new weekday: a Saturday bath done on Monday became a Monday bath. A task several weeks overdue was pushed only one week past the day it was done.

**How it was run:** the same prompt went to two models as separate Claude Code subagents. Neither could read the project or run code, so each answered from the prompt alone. I then ran both solutions in a script against both models' edge-case tables (26 cases), against each other on 100,000 random inputs, and against the five requirements as property checks. Both models are Claude models; to compare across vendors, paste the prompt below into Gemini or ChatGPT and add a third column.

<details>
<summary>The prompt (identical for both models)</summary>

```text
I'm building a pet-care scheduler in Python. Recurring tasks are dataclasses like this (simplified):

[the Task dataclass with title, duration_minutes, priority, frequency, due_date, completed,
 last_completed, is_due_today(), and the current next_occurrence():
     due_date = day + RECURRENCE_GAP[self.frequency]   # day = the day it was completed]

Problem: the next due date is "completion day + gap". So a weekly bath due every Saturday that gets
done on Monday becomes due the following Monday — the schedule drifts later every time a task is done
late. If the owner misses several weeks, the task stays overdue and completing it once only pushes it
one gap past the completion day.

Design and implement a better next_occurrence for weekly (and daily) tasks with these requirements:
1. Weekly tasks keep their original weekday ("anchored" schedule): done late or early, the next due
   date is the next anchored date strictly after the completion day.
2. If several occurrences were missed, completing the task once should not create a backlog of
   overdue copies; the next due date is simply the next anchored date after today.
3. Tasks created without a due_date (due now) need a sensible anchor.
4. Daily tasks should behave sensibly under the same rules.
5. Completing early (before the due date) must not skip a week by accident or make the task due
   twice in the same week.

Give: (a) the code, (b) a short explanation of the algorithm, (c) a list of edge-case tests
(inputs -> expected next due date), and (d) any trade-offs or open questions. Keep it under ~80
lines of code.
```

</details>

| | Option A | Option B |
|-|----------|----------|
| **Model / tool used** | Claude Sonnet 5.5 (Claude Code subagent) | Claude Haiku 5.5 (Claude Code subagent) |
| **Prompt** | The prompt above, unchanged | The prompt above, unchanged |
| **Response summary** | One formula for every frequency: `anchor = due_date or day`, `ref = max(day, anchor)`, `next = anchor + k × gap` with `k = (ref − anchor) // gap + 1`. 11 weekly and 4 daily test cases, plus property checks (next is after the day, on the anchor's cadence, at most one gap past `ref`). Six trade-offs. | A helper `next_anchored_date(anchor, base, frequency)`: daily returns `base + 1 day`; weekly finds the next matching weekday with `(anchor.weekday() − base.weekday() − 1) % 7 + 1`, where `base = max(day, anchor)`. 13 test cases and seven trade-offs. |
| **What was useful** | • **Correct:** passed all 26 cases from both tables, and never broke a requirement on 100,000 random inputs.<br>• **General:** one formula for daily and weekly, and adding e.g. "every 2 weeks" to `RECURRENCE_GAP` would just work.<br>• **Exact arithmetic:** pointed out that `timedelta // timedelta` is an exact integer.<br>• **Better tests:** suggested property checks rather than only examples.<br>• **Edge cases:** covered the year boundary and the "exactly one week late" case.<br>• **Useful trade-offs:** for example, a separate anchor field if "move this one occurrence" should differ from "change the schedule". | • **Correct:** passed all 26 cases, and gave exactly the same dates as Option A on all 100,000 random inputs.<br>• **Clear explanation** of why `max(day, anchor)` is needed, with the counterexample: a naive "next Saturday after today" returns the *same* Saturday when the task is done early on Thursday.<br>• **Useful trade-offs:** a `missed_count` for reporting skipped weeks, and blocking due-date edits that change the weekday. |
| **Problems noticed** | • Missed weeks are silently dropped (acknowledged as a trade-off).<br>• A task with no due date is anchored to the weekday of its first completion, not a weekday the owner chose (also acknowledged).<br>• Suggested changing `mark_complete` to return a pair, which would ripple through the app for little gain. | • **Sets `last_completed` on the new, not-yet-done copy.** This app keeps history on the completed copy, so a fresh task would wrongly look like it was already done. It also clashes with the "✅ done" status display.<br>• **Weekly logic is weekday arithmetic,** so it can't express "every 2 weeks" (weekday math loses week parity). Each new frequency needs its own branch.<br>• **Daily ignores the anchor entirely.** It works, but the two frequencies follow different rules.<br>• The `% 7 + 1` expression is correct but hard to check by eye. |
| **Decision** | **Adopted.** It's now `Task.next_occurrence()` in `pawpal_system.py`, with `last_completed=None` kept on the new copy. | Not adopted. Its explanation of the early-completion case went into the code comment ("Early completion counts as completing the anchored occurrence"). |

**Which approach did you use in your final implementation and why?**

Option A (Claude Sonnet 5.5). Both answers were correct; on 100,000 random inputs they never disagreed. So the decision came down to design, not correctness:

- **One rule for every frequency.** Option A's `anchor + k × gap` works for any fixed gap, so the code doesn't branch on frequency and a new frequency is one line in `RECURRENCE_GAP`.
- **Fits the existing design.** It keeps the new copy's `last_completed` empty, so completed history stays on the completed copy. Option B quietly changed that.
- **Clear invariants.** "Strictly after the reference day, on the anchor's cadence, at most one gap away" is easy to test, and it became the property I checked both solutions against.

Verification after adopting it:
- **New tests:** 11 parametrized cases in `tests/test_pawpal.py`, for weekly (on time, late, a week late, three weeks missed, early, year boundary, no due date) and daily (overdue, early, year boundary), plus one Scheduler-level test that a late Saturday task comes back on Saturday.
- **Existing tests:** all earlier recurrence tests still pass, because for an on-time task the result is the same as before.

What I learned: I couldn't tell the two answers apart by running them. They gave the same dates on every input. The differences only showed up in how each fit the rest of the system: the extra `last_completed` side effect, and whether the logic generalizes to new frequencies. Running both against the same tests is what made it safe to choose on design.
