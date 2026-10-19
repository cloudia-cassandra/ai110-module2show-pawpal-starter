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

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
