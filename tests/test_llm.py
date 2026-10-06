from app.llm_service import (
    generate_daily_nudge,
    generate_journal_entry,
    generate_species_tip,
)


def test_species_tip_generation():
    tip = generate_species_tip("American Robin", "Turdus migratorius")
    assert tip is not None
    assert len(tip) > 10
    # Must be grounded and concise (under 2 sentences)
    assert tip.count(".") <= 3


def test_daily_nudge_generation():
    fake_life_list = [
        {"common_name": "American Robin", "total_heard": 3},
        {"common_name": "Blue Jay", "total_heard": 1},
    ]
    nudge = generate_daily_nudge(fake_life_list, month_name="October")
    assert nudge is not None
    assert len(nudge) > 10
    assert nudge.count(".") <= 3


def test_journal_entry_generation():
    entry = generate_journal_entry(["American Robin", "Song Sparrow"], outing_minutes=25.0)
    assert entry is not None
    assert len(entry) > 10
    assert "Robin" in entry or "outing" in entry.lower() or "minutes" in entry.lower()
