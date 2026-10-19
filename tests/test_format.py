"""Tests for the PawPal+ presentation helpers (emojis, colors, and tables)."""

import io
import re
from datetime import date

import pandas as pd
from wcwidth import wcswidth

from pawpal_format import (
    ANSI_RESET,
    cell_style,
    plan_report,
    priority_label,
    species_icon,
    status_label,
    task_icon,
    task_table,
    use_color,
)
from pawpal_system import Owner, Pet, Scheduler, Task

ANSI = re.compile(r"\033\[[0-9;]*m")
DAY = date(2026, 10, 18)


def make_scheduler(*tasks, minutes=120):
    owner = Owner("Jordan", minutes)
    mochi, luna = Pet("Mochi", "dog"), Pet("Luna", "cat")
    owner.add_pet(mochi)
    owner.add_pet(luna)
    for pet_name, task in tasks:
        owner.find_pet(pet_name).add_task(task)
    return Scheduler(owner, DAY)


def test_task_icon_matches_keywords_case_insensitively_with_a_default():
    assert task_icon(Task("Heartworm MEDS", 5, "high")) == "💊"
    assert task_icon(Task("Morning walk", 30, "high")) == "🦮"
    assert task_icon(Task("Breakfast", 10, "high")) == "🍖"
    assert task_icon(Task("Bath", 45, "low")) == "🛁"
    assert task_icon(Task("Brush coat", 20, "medium")) == "🧼"
    assert task_icon(Task("Litter box", 5, "medium")) == "🧹"
    assert task_icon(Task("Puzzle toy", 15, "medium")) == "🧸"
    assert task_icon(Task("Cuddles", 5, "low")) == "🐾"


def test_species_icons():
    assert (species_icon("dog"), species_icon("cat"), species_icon("other")) == ("🐶", "🐱", "🐾")


def test_priority_label_is_plain_without_color_and_colored_with_it():
    assert priority_label("high") == "🔴 high"
    colored = priority_label("high", color=True)
    assert colored.startswith("\033[31m") and colored.endswith(ANSI_RESET)
    assert ANSI.sub("", colored) == "🔴 high"


def test_status_label_for_to_do_done_and_future_tasks():
    scheduler = make_scheduler(("Mochi", Task("Feeding", 10, "high")))
    original = scheduler.owner.find_pet("Mochi").tasks[0]
    assert status_label(original, scheduler) == "⏳ to do"

    next_task = scheduler.mark_task_complete("Mochi", "Feeding")

    assert status_label(original, scheduler) == "✅ done Oct 18"
    assert status_label(next_task, scheduler) == "🔁 due Oct 19"


def test_color_is_off_for_non_terminals_and_when_no_color_is_set(monkeypatch):
    assert use_color(io.StringIO()) is False

    class FakeTerminal(io.StringIO):
        def isatty(self):
            return True

    monkeypatch.delenv("NO_COLOR", raising=False)
    assert use_color(FakeTerminal()) is True
    monkeypatch.setenv("NO_COLOR", "1")
    assert use_color(FakeTerminal()) is False


def test_task_table_columns_line_up_with_emojis_and_colors():
    scheduler = make_scheduler(
        ("Mochi", Task("Heartworm meds", 5, "high", start_time="08:00")),
        ("Luna", Task("Litter box", 5, "medium", start_time="08:20")),
        ("Mochi", Task("Bath", 45, "low")),
    )

    for color in (False, True):
        table = task_table(scheduler, scheduler.sort_by_time(scheduler.owner.get_all_tasks()), color)
        widths = {wcswidth(ANSI.sub("", line)) for line in table.splitlines()}
        assert len(widths) == 1, table  # every row, border included, has the same on-screen width
        assert ("\033[" in table) is color
    assert "💊 Heartworm meds" in table and "🐱 Luna" in table and "any time" in table


def test_plan_report_marks_clashes_lists_skipped_tasks_and_warnings():
    scheduler = make_scheduler(
        ("Mochi", Task("Breakfast", 10, "high", start_time="08:15")),
        ("Luna", Task("Breakfast", 10, "high", start_time="08:15")),
        ("Mochi", Task("Bath", 45, "low")),
        minutes=30,
    )

    report = plan_report(scheduler, scheduler.generate_plan())

    assert "📅 Plan for Sunday, October 18: 20 of 30 min scheduled" in report
    assert report.count("⚠ 08:15-08:25") == 2
    assert "Didn't fit (1):" in report and "🛁 Bath" in report
    assert "⚠ 1 warning:" in report and "No time clashes" not in report


def test_plan_report_says_when_there_are_no_clashes():
    scheduler = make_scheduler(("Mochi", Task("Walk", 30, "high")))

    report = plan_report(scheduler, scheduler.generate_plan())

    assert "✅ No time clashes." in report and "⚠" not in report and "Didn't fit" not in report


def test_cell_style_tints_priorities_and_statuses_only():
    assert "255, 75, 75" in cell_style("🔴 high")
    assert "33, 195, 84" in cell_style("🟢 low") and "33, 195, 84" in cell_style("✅ done Oct 18")
    assert "28, 131, 225" in cell_style("🔁 due Oct 19")
    assert cell_style("⏳ to do") == "" and cell_style("") == "" and cell_style(30) == ""


def test_cell_style_works_as_a_pandas_styler_map():
    frame = pd.DataFrame([{"Task": "Walk", "Priority": "🔴 high", "Status": "⏳ to do"}])

    html = frame.style.map(cell_style, subset=["Priority", "Status"]).to_html()

    assert "background-color: rgba(255, 75, 75, 0.18)" in html
