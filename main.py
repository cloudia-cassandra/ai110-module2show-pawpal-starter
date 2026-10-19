"""Demo script: build a sample owner with two pets and print today's schedule."""

from datetime import date

from pawpal_system import Owner, Pet, Scheduler, Task


def main() -> None:
    owner = Owner(name="Jordan", available_minutes=90, day_start="07:30")

    mochi = Pet(name="Mochi", species="dog")
    luna = Pet(name="Luna", species="cat")
    owner.add_pet(mochi)
    owner.add_pet(luna)

    mochi.add_task(Task("Heartworm meds", 5, "high", start_time="08:00"))
    mochi.add_task(Task("Morning walk", 30, "high", preferred_time="morning"))
    mochi.add_task(Task("Puzzle toy", 15, "medium", preferred_time="evening"))
    mochi.add_task(Task("Bath", 45, "low", frequency="weekly"))
    luna.add_task(Task("Breakfast", 10, "high", start_time="08:15"))
    luna.add_task(Task("Brush coat", 20, "medium", preferred_time="afternoon"))

    plan = Scheduler(owner, date.today()).generate_plan()

    print("=" * 60)
    print(f"Today's Schedule for {owner.name}'s pets")
    print("=" * 60)
    print(plan.explain())


if __name__ == "__main__":
    main()
