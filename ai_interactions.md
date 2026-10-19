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

| | Option A | Option B |
|-|----------|----------|
| **Model / tool used** | | |
| **Prompt** | | |
| **Response summary** | | |
| **What was useful** | | |
| **Problems noticed** | | |
| **Decision** | | |

**Which approach did you use in your final implementation and why?**

<!-- Your conclusion -->
