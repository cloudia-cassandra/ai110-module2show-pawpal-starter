from datetime import date, time

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

# Streamlit reruns this script on every interaction, so keep the Owner in session_state.
# It is created only on the first run; later runs reuse the same object and its pets/tasks.
if "owner" not in st.session_state:
    st.session_state.owner = Owner(name="Jordan", available_minutes=60)
owner = st.session_state.owner

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

all_tasks = owner.get_all_tasks()
if all_tasks:
    st.table(
        [
            {
                "Pet": task.pet_name,
                "Task": task.title,
                "Minutes": task.duration_minutes,
                "Priority": task.priority,
                "Preferred time": task.preferred_time or "any",
                "Fixed time": task.start_time or "",
                "Frequency": task.frequency,
            }
            for task in all_tasks
        ]
    )
else:
    st.info("No tasks yet.")

st.divider()

st.subheader("Build Schedule")
if st.button("Generate schedule"):
    plan = Scheduler(owner, date.today()).generate_plan()
    if plan.entries:
        st.success(
            f"Scheduled {len(plan.entries)} task{'s' if len(plan.entries) != 1 else ''} "
            f"({plan.total_minutes()} of {owner.available_minutes} min)."
        )
        st.table(
            [
                {
                    "Time": f"{start}-{to_hhmm(to_minutes(start) + task.duration_minutes)}",
                    "Pet": task.pet_name,
                    "Task": task.title,
                    "Priority": task.priority,
                    "Why": reason,
                }
                for start, task, reason in plan.entries
            ]
        )
    else:
        st.info("Nothing to schedule today.")
    for task, reason in plan.skipped:
        st.warning(f"Skipped {task.title} for {task.pet_name}: {reason}")
    for warning in plan.warnings:
        st.error(f"Conflict: {warning}")
