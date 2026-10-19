# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

- Briefly describe your initial UML design.
- What classes did you include, and what responsibilities did you assign to each?

Before drawing the UML, I identified three core actions a user should be able to perform in PawPal+:

1. **Enter owner and pet information.** The user starts by telling the app who they are, how much time they have for pet care today, and basic details about their pet, such as its name and species. This comes first because the owner's available time limits what the schedule can include, and every task belongs to a specific pet.

2. **Add and edit care tasks.** The user can create tasks such as a morning walk, feeding, giving medication, or grooming. Each task has at least a duration (how long it takes) and a priority (how important it is). The user can also update or remove tasks as their pet's needs change.

3. **Generate and view today's plan.** The user asks the app to build a daily schedule. The app orders tasks by priority, fits as many as possible into the available time, and leaves out lower-priority tasks when time runs short. It then shows the plan clearly and explains its reasoning, for example why one task was scheduled before another or why a task was skipped.

From these actions, my UML design ended up with five classes. Three of them mostly hold data, one holds the scheduling logic, and one holds the result:

- **Owner** represents the person using the app. It stores their name, how many minutes they have for pet care today, the time their day starts, and the list of pets they own. Its main job is to hold the constraints the scheduler must respect.
- **Pet** represents one animal. It stores the pet's name, species, and its list of care tasks, and it is responsible for adding, editing, and removing those tasks.
- **Task** represents one care activity, like a walk or a feeding. It stores the title, duration, priority, preferred time of day, how often it repeats, and whether it has been completed. It can turn its priority into a number for sorting, decide whether it is due on a given day, and mark itself complete.
- **Scheduler** is the "brain" of the system. It gathers all of today's tasks from the owner's pets, sorts them by priority, fits as many as possible into the available time, and checks for conflicts.
- **DailyPlan** is what the scheduler produces. It holds the scheduled tasks with their start times, the tasks that were skipped, and a reason for each decision, and it can total up the time used and explain the plan in plain language.

The relationships are simple: an Owner has one or more Pets, each Pet has its own Tasks, and the Scheduler reads from the Owner to create a DailyPlan. I used Python dataclasses for Owner, Pet, Task, and DailyPlan because they mainly hold data, and a regular class for Scheduler because it mainly holds logic.

**b. Design changes**

- Did your design change during implementation?
- If yes, describe at least one change and why you made it.

Yes, my design changed in two rounds of review with AI.

First, when reviewing the UML diagram, I removed things that nothing in the system actually used. I dropped simple getter and setter methods like `get_pets()` and `update_availability()`, because in Python you can just read the attribute directly. I also removed a vague `preferences` dictionary on Owner, plus `age`, `special_needs`, and `category` fields that the scheduler never looked at, and a `display()` method on DailyPlan, since showing the plan is the Streamlit app's job. This kept the design focused on what the scheduler needs.

Second, when reviewing the class skeleton in `pawpal_system.py`, I found two missing pieces:

- **Tasks didn't know which pet they belonged to.** Pet holds a list of Tasks, but the link only goes one way. When the Scheduler gathers tasks from every pet into a single list, that information is lost, so a plan for two dogs would just say "Walk" without saying which dog. I added a `pet_name` field to Task, which `Pet.add_task()` fills in automatically.
- **Weekly tasks had no way to know if they were due.** `is_due_today()` only had a `frequency` of "daily" or "weekly" to go on, which isn't enough to tell whether a weekly task was already done this week. I added a `last_completed` date to Task and changed `mark_complete()` to take the day it was completed, so a weekly task can check whether seven days have passed since it was last done.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
- How did you decide which constraints mattered most?

My scheduler considers six constraints:

- **Available time:** the owner's minutes for pet care today. This is a hard limit, so the plan never goes over it.
- **Priority:** low, medium, or high. It decides which tasks get the time first.
- **Fixed start time:** tasks like medication at 08:00 are placed at exactly that time.
- **Preferred time of day:** morning, afternoon (from 12:00), or evening (from 17:00). Flexible tasks wait for their part of the day.
- **Day start:** flexible tasks aren't placed before the owner's day begins.
- **Due date and completion:** only tasks that are due today and not yet done are planned. Recurring tasks become due again one day or one week after they are completed.

I ranked them by what goes wrong for the pet if the constraint is ignored. Time comes first because a plan the owner can't finish is useless. Priority comes next, because a missed medication matters much more than a missed puzzle toy. Fixed times come after that, because some tasks only make sense at a certain time. Preferred time of day is the softest constraint: it shapes the order, but it never pushes a task out of the plan.

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
- Why is that tradeoff reasonable for this scenario?

My scheduler chooses tasks greedily by priority instead of searching for the combination that fills the most time. It sorts tasks from highest to lowest priority and adds each one if it still fits in the owner's remaining minutes. If a task doesn't fit, it is skipped and the scheduler moves on to the next one, so a smaller task further down the list can still fill the gap. This doesn't always use every available minute. For example, with 60 minutes free, a 50-minute high-priority walk, and two 30-minute medium-priority tasks, the scheduler picks the walk and skips both medium tasks. That uses 50 minutes, while the two medium tasks together would have used all 60.

I think this is reasonable for a pet owner, because priority usually means "this matters more", like medication or a dog that needs exercise. Most owners would rather get the important task done than squeeze in more minutes of less important ones. The greedy approach is also easy to explain: every skipped task gets a reason like "not enough time (30 min needed, 10 min left)". A search for the "best" combination would be slower to run and much harder to explain in the plan.

A related tradeoff is that conflicts are reported, not fixed. Flexible tasks are placed around fixed-time tasks, so they never clash. If two fixed-time tasks overlap, though, the scheduler keeps both and adds a warning instead of moving one. It does check real overlaps, not just identical start times, so breakfast at 08:15–08:25 and a litter box at 08:20 are flagged. It leaves the decision to the owner, who knows whether the two tasks can really happen together, for example if another person can feed one pet.

When simplifying the code, I also made a readability tradeoff in `detect_conflicts()`. An earlier version used a "sweep" that tracked which tasks were still running, which does less work on long lists. I replaced it with a simpler check of every pair of tasks using `itertools.combinations`, because a day has only a handful of tasks, so the speed difference doesn't matter, and the pairwise version is much easier to read and check.

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

I used Claude Code at every stage of the design and build. First I had it read the scenario and suggest the three core actions a user should be able to perform. Then I had it brainstorm the classes with their attributes and methods, turn that into a Mermaid UML diagram, and generate class stubs in `pawpal_system.py`. After that, it wrote the full implementation, a demo script (`main.py`), and the first tests.

The most helpful prompts asked the AI to review its own work instead of just producing more. Examples were "Review the diagram. Ensure relationships make sense and that you haven't included unnecessary complexity" and "Do you notice any missing relationships or potential logic bottlenecks?" These prompts found real problems that a "write the code" prompt would have skipped right past. Asking a specific question also helped, like "How should the Scheduler retrieve all tasks from the Owner's pets?" It led directly to `Owner.get_all_tasks()`, so the scheduler works across all pets instead of just one.

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

I didn't accept the AI's first class design as-is. The first brainstorm included getter and setter methods, a vague `preferences` dictionary, and fields like `age`, `special_needs`, and `category`. Nothing in the scheduler would ever use them. When I asked for a review aimed at unnecessary complexity, those were removed. The review of the skeleton also found two gaps that the first design missed. Tasks didn't record which pet they belonged to, and weekly tasks had no way to tell whether they were due. Both were fixed before any logic was written.

I verified the implementation by running it rather than just reading it. The first version of the scheduler put a task marked "prefers evening" at 08:50 in the morning. That was easy to spot in the printed schedule but hard to see in the code, so the scheduler was changed to wait until 17:00 for evening tasks and 12:00 for afternoon tasks. I ran `main.py` again to confirm the fix. I also checked that an invalid priority like "urgent" raises an error. Finally, I ran the tests with plain `pytest`, the command the README uses. That showed the tests couldn't import the module, which was fixed by adding a `pytest.ini`.

**c. AI strategy**

- Which AI coding assistant features were most effective for building your scheduler?
- Give one example of an AI suggestion you rejected or modified to keep your system design clean.
- How did using separate chat sessions for different phases help you stay organized?

The most effective features were the ones that let Claude Code work from my real files and check its own results. Attaching `pawpal_system.py` to a prompt meant its answers were based on the code I actually had, not a guess. That is how the UML review found that the diagram said an owner needs at least one pet, while my code and tests allow zero. Running commands was just as useful. It ran `pytest` after every change and ran `main.py` to compare the README's sample output with the real output. It also drove the Streamlit app headlessly through a full workflow: adding pets and tasks, marking a task done, and generating a schedule. That run caught a bug where the past-midnight warning showed "1425" instead of "23:45". Asking for a plan before any code also worked well. For testing, I first asked for a list of behaviors and edge cases, then for the tests themselves, so the tests followed a plan instead of whatever was easiest to write.

One change I made to keep the design clean was in how the app shows conflicts. To mark the clashing rows in the schedule and suggest a new time, the app needed to know which tasks overlap. The quickest option was to have `app.py` search the warning text that `detect_conflicts()` returns, which would make the UI depend on the exact wording of a message. Instead, I moved the overlap check into a new `Scheduler.find_overlaps()` method that returns the clashing task pairs with their times. `detect_conflicts()` uses it to build the same warning text as before, and the app uses it directly. The logic stays in the scheduler, the UI only displays results, and the existing tests didn't need to change. I also added a test for the new method and added it to the final UML.

Using a separate chat session for each phase kept each conversation focused on one job: design, the core logic, the smarter scheduling features, and then testing, UI and documentation. Each session started from the committed code and the files I attached, instead of a long history of earlier ideas, some of which I had already rejected. Committing at the end of each phase ("phase 1 done", "phase 3 done") gave every new session a clean starting point, and I could always roll back to a version I knew worked. It also made it obvious when documentation fell behind the code. For example, the README still said 26 tests after the 27th was added, and the UML diagram was missing the new methods.

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

The test suite has 27 tests in `tests/test_pawpal.py`, covering both normal use and edge cases:

- **Sorting:** tasks come out in time order with untimed tasks last; tasks at the same time put higher priority first; `"HIGH"` is treated as `"high"`.
- **Building the plan:** an owner with no pets or a pet with no tasks gets an empty plan without crashing; a task that uses exactly the remaining minutes is still scheduled; with 0 minutes everything is skipped with a reason.
- **Placing tasks:** fixed-time tasks land at their exact time, flexible tasks move past fixed tasks they would overlap, and afternoon tasks wait until 12:00.
- **Recurring tasks:** completing a daily or weekly task creates the next one 1 or 7 days later, even across a month boundary; completing the same task twice in one day is refused; an overdue task is still planned.
- **Conflict detection:** two tasks at exactly the same time are flagged; three overlapping tasks give one warning per pair; back-to-back tasks are not conflicts; a task ending exactly at midnight is fine, but one minute later is flagged.
- **Validation:** bad times like `"8am"` are rejected, and an invalid edit leaves the task unchanged.

These tests matter because the scheduler's mistakes are quiet. A wrong plan still looks like a plan, so I wouldn't notice that a weekly task came back after one day, or that a 08:20 task overlapping a 08:15 one wasn't flagged, unless a test checked it. The boundary tests (exactly filling the budget, back-to-back tasks, ending exactly at midnight) are where `<` and `<=` mix-ups hide. One test also pins down a design choice instead of a bug: with 30 minutes free, a 60-minute high-priority task is skipped while a 10-minute low one fits. If I ever change the greedy approach, that test will remind me it was intentional.

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

I'd rate my confidence at 4 out of 5. All 27 tests pass, and they cover every scheduling feature, including the cases most likely to break it. I also ran the Streamlit app headlessly through a full workflow and the terminal demo, and both matched what the tests promise. I held back the fifth star because the Streamlit UI has no automated tests of its own, and because the greedy approach is a choice I tested rather than proved to be the best one.

If I had more time, I would test:

- **Duplicate task titles for one pet**, such as two "Walk" tasks. `find_task()` looks tasks up by title, so marking one done might pick the wrong one.
- **A high-priority fixed-time task that doesn't fit the budget.** Medication at 08:00 can currently be skipped if bigger high-priority tasks use up the time first.
- **A late day start**, such as 22:00, where flexible tasks get pushed past midnight.
- **Editing a recurring task**, to check that the next occurrence keeps the change.
- **The UI itself**, by turning my headless Streamlit run (`AppTest`) into real tests for marking a task done, the filters, and the conflict messages.

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

I'm most satisfied with how conflicts are handled from start to finish. The scheduler doesn't just say "conflict". It checks real overlaps, not only identical start times, says whether the clash is for the same pet or different pets, and keeps both tasks so the owner decides. In the app, the clashing rows are marked ⚠️ and each clash comes with a specific fix, like "Try moving Litter box to 08:25 or later." The `find_overlaps()` method also keeps that logic in one place, so the warnings, the UI and the tests all agree. I'm also happy that every scheduled or skipped task gets a reason, so the plan never feels like a black box.

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

- **Give tasks IDs instead of finding them by title.** Looking tasks up by title works for a demo, but it gets confusing with duplicate titles or recurring tasks that leave completed copies behind.
- **Always include fixed-time, high-priority tasks.** Medication at a set time should probably never be skipped for a long walk. I'd schedule fixed-time tasks first and only fit the flexible ones around them.
- **Edit and remove tasks in the app.** `Pet.edit_task()` and `remove_task()` exist in the backend, but the UI can only add tasks, so the only way to fix a clash is to add the task again at a new time.
- **Save data between sessions.** Everything lives in Streamlit's session state, so refreshing the page loses all pets and tasks. Saving to a JSON file would fix this.
- **Display times past midnight properly**, so a task ending at 00:25 doesn't show as "24:25".

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?

The most important thing I learned is that working with a powerful AI tool makes me the lead architect, not the typist. The AI can write a class, a test suite or a README section in seconds, so writing code stops being the hard part. The hard parts are deciding what the system should do, where each piece of logic belongs, and whether the result is actually true. Those stayed my job.

In practice, being the lead architect meant four things:

- **Setting the design before the code.** I started from three user actions and a UML diagram, and kept asking whether each class and method was really needed. The AI's first draft was bigger than it needed to be. Asking it to review for unnecessary complexity made the design smaller and clearer.
- **Keeping responsibilities in the right place.** Scheduling logic belongs in `Scheduler` and display belongs in `app.py`. When a shortcut would have mixed them, like the UI reading warning text, I moved the logic into the backend instead.
- **Verifying, not trusting.** The AI's output was usually right, but not always: an evening task placed in the morning, a midnight warning showing "1425", a README step describing an edit button the app doesn't have. Each one was caught by running the code, the tests or the app, not by reading the AI's explanation.
- **Keeping the documents honest.** The UML, README and test counts drift as the code changes. Checking them against the real code at the end of each phase kept the project consistent.

AI made me much faster, but the quality of the system still came from the questions I asked and the checks I insisted on.
