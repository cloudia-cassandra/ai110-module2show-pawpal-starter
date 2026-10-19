from datetime import date, time
from pathlib import Path

import streamlit as st

from pawpal_system import Owner, Pet, Scheduler, Task, to_hhmm, to_minutes

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")

st.markdown(
    """
Add your pets and their care tasks, tell PawPal+ how much time you have today,
and it will build a daily plan and explain why it chose it.
"""
)

with st.expander("Scenario", expanded=True):
    st.markdown(
        """
**PawPal+** is a pet care planning assistant. It helps a pet owner plan care tasks
for their pet(s) based on constraints like time, priority, and preferences.

You will design and implement the scheduling logic and connect it to this Streamlit UI.
"""
    )

with st.expander("What you need to build", expanded=True):
    st.markdown(
        """
At minimum, your system should:
- Represent pet care tasks (what needs to happen, how long it takes, priority)
- Represent the pet and the owner (basic info and preferences)
- Build a plan/schedule for a day that chooses and orders tasks based on constraints
- Explain the plan (why each task was chosen and when it happens)
"""
    )

st.divider()

# Pets and tasks are saved here after every change and loaded when a new session starts.
DATA_FILE = Path(__file__).with_name("data.json")

# Streamlit reruns this script on every interaction, so keep the Owner in session_state.
# It is loaded (or created) only on the first run; later runs reuse the same object and its pets/tasks.
if "owner" not in st.session_state:
    try:
        st.session_state.owner = Owner.load_from_json(DATA_FILE)
        st.toast(f"Loaded your pets and tasks from {DATA_FILE.name}.", icon="💾")
    except FileNotFoundError:
        st.session_state.owner = Owner(name="Jordan", available_minutes=60)
    except ValueError as error:
        # Keep the unreadable file instead of overwriting it with the next save.
        backup = DATA_FILE.with_name("data.corrupt.json")
        DATA_FILE.replace(backup)
        st.session_state.owner = Owner(name="Jordan", available_minutes=60)
        st.session_state.load_error = f"{error}. The file was moved to {backup.name} and PawPal+ started fresh."
    st.session_state.saved_data = st.session_state.owner.to_dict()
owner = st.session_state.owner

if "load_error" in st.session_state:
    st.error(st.session_state.pop("load_error"))

with st.sidebar:
    st.subheader("💾 Saved data")
    st.caption(f"Pets and tasks are saved to `{DATA_FILE.name}` after every change and loaded when the app starts.")
    if st.button("Start over", help=f"Delete {DATA_FILE.name} and clear all pets and tasks"):
        DATA_FILE.unlink(missing_ok=True)
        del st.session_state["owner"]
        st.session_state.show_plan = False
        st.rerun()

st.subheader("Owner")
col1, col2, col3 = st.columns(3)
with col1:
    owner.name = st.text_input("Owner name", value=owner.name)
with col2:
    owner.available_minutes = int(
        st.number_input("Minutes available today", min_value=0, max_value=1440, value=owner.available_minutes)
    )
with col3:
    day_start = st.time_input("Day starts at", value=time.fromisoformat(owner.day_start))
    owner.day_start = day_start.strftime("%H:%M")

today = date.today()
scheduler = Scheduler(owner, today)

st.subheader("Pets")
with st.form("add_pet", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        pet_name = st.text_input("Pet name")
    with col2:
        species = st.selectbox("Species", ["dog", "cat", "other"])
    if st.form_submit_button("Add pet"):
        name = pet_name.strip()
        if not name:
            st.error("Please enter a pet name.")
        elif any(pet.name == name for pet in owner.pets):
            st.error(f"{owner.name} already has a pet named {name}.")
        else:
            owner.add_pet(Pet(name=name, species=species))
            st.success(f"Added {name}.")

if owner.pets:
    st.table([{"Pet": pet.name, "Species": pet.species, "Tasks": len(pet.tasks)} for pet in owner.pets])
else:
    st.info("No pets yet. Add one above.")

st.subheader("Tasks")
if not owner.pets:
    st.caption("Add a pet before adding tasks.")
else:
    with st.form("add_task", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            task_pet = st.selectbox("Pet", [pet.name for pet in owner.pets])
            task_title = st.text_input("Task title", value="Morning walk")
        with col2:
            duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
            priority = st.selectbox("Priority", ["low", "medium", "high"], index=2)
        with col3:
            preferred = st.selectbox("Preferred time", ["any", "morning", "afternoon", "evening"])
            frequency = st.selectbox("Frequency", ["daily", "weekly"])
        has_fixed_time = st.checkbox("Must happen at a fixed time")
        fixed_time = st.time_input("Fixed time", value=time(8, 0))
        if st.form_submit_button("Add task"):
            try:
                task = Task(
                    title=task_title.strip(),
                    duration_minutes=int(duration),
                    priority=priority,
                    preferred_time=None if preferred == "any" else preferred,
                    start_time=fixed_time.strftime("%H:%M") if has_fixed_time else None,
                    frequency=frequency,
                )
            except ValueError as error:
                st.error(str(error))
            else:
                owner.find_pet(task_pet).add_task(task)
                st.success(f"Added {task.title} for {task_pet}.")

    # Mark a task done before drawing the task list, so the list already shows the change.
    due_today = scheduler.sort_by_time(scheduler.collect_tasks())
    if due_today:
        with st.form("complete_task"):
            col1, col2 = st.columns([3, 1], vertical_alignment="bottom")
            with col1:
                done_task = st.selectbox(
                    "Mark a task done",
                    due_today,
                    format_func=lambda task: f"{task.title} ({task.pet_name})",
                )
            with col2:
                mark_done = st.form_submit_button("Mark done")
            if mark_done:
                next_task = scheduler.mark_task_complete(done_task.pet_name, done_task.title)
                st.success(
                    f"Done: {done_task.title} for {done_task.pet_name}. "
                    f"Next one ({next_task.frequency}) is due {next_task.due_date:%a %b %d}."
                )


def task_status(task: Task) -> str:
    """Describe whether a task is still to do today, done, or waiting for a later day."""
    if task.completed:
        return f"✅ done {task.last_completed:%b %d}"
    if not task.is_due_today(today):
        return f"🔁 due {task.due_date:%b %d}"
    return "to do"


# Colored badges so priority stands out in every table.
PRIORITY_BADGE = {"high": "🔴 high", "medium": "🟡 medium", "low": "🟢 low"}

all_tasks = owner.get_all_tasks()
if all_tasks:
    col1, col2, col3 = st.columns(3)
    with col1:
        pet_filter = st.selectbox("Show pet", ["All pets"] + [pet.name for pet in owner.pets])
    with col2:
        status_filter = st.radio("Show tasks", ["All", "To do", "Done"], horizontal=True)
    with col3:
        sort_order = st.radio("Sort by", ["Time", "Priority, then time"], horizontal=True)
    filtered = scheduler.filter_tasks(
        pet_name=None if pet_filter == "All pets" else pet_filter,
        completed={"All": None, "To do": False, "Done": True}[status_filter],
    )
    sort = scheduler.sort_by_time if sort_order == "Time" else scheduler.sort_by_priority
    shown = sort(filtered)
    if shown:
        st.table(
            [
                {
                    "Time": scheduler.task_time(task) or "any time",
                    "Pet": task.pet_name,
                    "Task": task.title,
                    "Minutes": task.duration_minutes,
                    "Priority": PRIORITY_BADGE[task.priority],
                    "Repeats": task.frequency,
                    "Status": task_status(task),
                }
                for task in shown
            ]
        )
        if sort_order == "Time":
            st.caption("Sorted by time of day. Tasks without a set or preferred time are listed last.")
        else:
            st.caption(
                "Sorted by priority (high first), then by time of day. "
                "This is the order the planner uses to decide what fits in your time."
            )
    else:
        st.info("No tasks match these filters.")
else:
    st.info("No tasks yet.")

st.divider()

st.subheader("Build Schedule")
st.caption(f"Plan for {today:%A, %B %d}")
if st.button("Generate schedule"):
    st.session_state.show_plan = True

# Keep the plan on screen after other buttons are clicked, rebuilt from the latest tasks each time.
if st.session_state.get("show_plan"):
    plan = scheduler.generate_plan()
    overlaps = scheduler.find_overlaps(plan)
    clashing = {id(task) for pair in overlaps for _, _, task in pair}
    late = [(start, task) for start, end, task in scheduler.plan_slots(plan) if end > 24 * 60]

    if not plan.entries:
        st.info("Nothing to schedule today.")
    elif overlaps or late:
        st.warning(
            f"Scheduled {len(plan.entries)} tasks ({plan.total_minutes()} of {owner.available_minutes} min), "
            "but some times need your attention. See below."
        )
    else:
        st.success(
            f"Scheduled {len(plan.entries)} task{'s' if len(plan.entries) != 1 else ''} "
            f"({plan.total_minutes()} of {owner.available_minutes} min) with no time clashes."
        )

    # Show clashes above the table, with a fix that clears all of them, so they are seen before the day starts.
    if overlaps:
        lines = []
        for (a_start, a_end, a), (b_start, b_end, b) in overlaps:
            overlap = min(a_end, b_end) - b_start
            if a.pet_name == b.pet_name:
                who = f"{a.pet_name} can't do both at once"
            else:
                who = f"you can't care for {a.pet_name} and {b.pet_name} at the same moment unless someone helps"
            lines.append(
                f"- **{to_hhmm(b_start)}**: {b.title} ({b.pet_name}) overlaps {a.title} ({a.pet_name}) "
                f"by {overlap} min; {who}."
            )
        count = len(overlaps)
        st.warning(f"**{count} time clash{'es' if count != 1 else ''}**\n\n" + "\n".join(lines), icon="⚠️")

        # suggest_moves() resolves the clashes one at a time, so its new times don't clash with each other.
        moves = scheduler.suggest_moves(plan)
        lines = [
            f"- Move **{task.title}** ({task.pet_name}) from {old} to **{new}**"
            if new
            else f"- No free {task.duration_minutes}-minute gap is left today for **{task.title}** ({task.pet_name})"
            for task, old, new in moves
        ]
        st.info("**Suggested fix:** these times are free and don't clash with each other.\n\n" + "\n".join(lines), icon="💡")
        fixable = [(task, new) for task, _, new in moves if new]
        if fixable and st.button("Apply suggested times"):
            for task, new in fixable:
                owner.find_pet(task.pet_name).edit_task(task.title, {"start_time": new})
            st.rerun()
    for start, task in late:
        st.warning(
            f"{task.title} ({task.pet_name}) starts at {to_hhmm(start)} and runs past midnight. Try an earlier time.",
            icon="🌙",
        )

    if plan.entries:
        st.table(
            [
                {
                    "Time": ("⚠️ " if id(task) in clashing else "")
                    + f"{start}-{to_hhmm(to_minutes(start) + task.duration_minutes)}",
                    "Pet": task.pet_name,
                    "Task": task.title,
                    "Minutes": task.duration_minutes,
                    "Priority": PRIORITY_BADGE[task.priority],
                    "Why": reason,
                }
                for start, task, reason in plan.entries
            ]
        )

    with st.expander("Find a free time slot"):
        col1, col2 = st.columns(2)
        with col1:
            needed = int(st.number_input("Minutes needed", min_value=1, max_value=240, value=15))
        with col2:
            earliest = st.time_input("No earlier than", value=time.fromisoformat(owner.day_start))
        slot = scheduler.find_next_slot(plan, needed, earliest.strftime("%H:%M"))
        if slot:
            st.success(f"Next free {needed}-minute slot: **{slot}-{to_hhmm(to_minutes(slot) + needed)}**")
        else:
            st.warning(f"No free {needed}-minute gap is left today after {earliest:%H:%M}.")

    if plan.skipped:
        lines = [f"- {task.title} ({task.pet_name}): {reason}" for task, reason in plan.skipped]
        st.info(
            "**Didn't fit today**\n\n" + "\n".join(lines)
            + "\n\nAdd more minutes above or lower another task's priority to fit these in."
        )

    with st.expander("Plain-text plan"):
        st.code(plan.explain(), language=None)

# Save after any change on this run (owner settings, new pets or tasks, tasks marked done, applied moves).
current_data = owner.to_dict()
if current_data != st.session_state.saved_data:
    owner.save_to_json(DATA_FILE)
    st.session_state.saved_data = current_data
