# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

- Briefly describe your initial UML design.
- What classes did you include, and what responsibilities did you assign to each?

Before drawing the UML, I identified three core actions a user should be able to perform in PawPal+:

1. **Enter owner and pet information.** The user starts by telling the app who they are, how much time they have for pet care today, and basic details about their pet, such as its name, species, and any special needs. This comes first because the owner's available time limits what the schedule can include, and every task belongs to a specific pet.

2. **Add and edit care tasks.** The user can create tasks such as a morning walk, feeding, giving medication, or grooming. Each task has at least a duration (how long it takes) and a priority (how important it is). The user can also update or remove tasks as their pet's needs change.

3. **Generate and view today's plan.** The user asks the app to build a daily schedule. The app orders tasks by priority, fits as many as possible into the available time, and leaves out lower-priority tasks when time runs short. It then shows the plan clearly and explains its reasoning, for example why one task was scheduled before another or why a task was skipped.

**b. Design changes**

- Did your design change during implementation?
- If yes, describe at least one change and why you made it.

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
