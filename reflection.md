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

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

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
