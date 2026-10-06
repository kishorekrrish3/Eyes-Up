import tempfile
from pathlib import Path
import pytest
from app.db import (
    add_sighting,
    get_life_list,
    get_touch_grass_stats,
    init_db,
    is_heard_before,
    start_outing,
    stop_outing,
)


@pytest.fixture
def temp_db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name
    init_db(db_path)
    yield db_path
    Path(db_path).unlink(missing_ok=True)


def test_add_and_query_sightings(temp_db):
    assert is_heard_before("Turdus migratorius", db_path=temp_db) is False

    sighting = add_sighting(
        common_name="American Robin",
        scientific_name="Turdus migratorius",
        confidence=0.88,
        tip="Look for brick-red breast on lawns.",
        db_path=temp_db,
    )
    assert sighting["id"] is not None
    assert sighting["common_name"] == "American Robin"

    # Now it should be heard before
    assert is_heard_before("Turdus migratorius", db_path=temp_db) is True
    # Case insensitivity check
    assert is_heard_before("turdus migratorius", db_path=temp_db) is True

    # Add second sighting of same species
    add_sighting(
        common_name="American Robin",
        scientific_name="Turdus migratorius",
        confidence=0.92,
        db_path=temp_db,
    )

    life_list = get_life_list(db_path=temp_db)
    assert len(life_list) == 1
    assert life_list[0]["total_heard"] == 2
    assert life_list[0]["max_confidence"] == 0.92


def test_outing_and_touch_grass_score(temp_db):
    outing_id = start_outing(db_path=temp_db)
    assert outing_id is not None

    stopped = stop_outing(outing_id, screen_seconds=60, db_path=temp_db)
    assert stopped["id"] == outing_id
    assert stopped["screen_seconds"] == 60

    stats = get_touch_grass_stats(days=7, db_path=temp_db)
    assert stats["total_outings"] == 1
    assert stats["screen_minutes"] == 1.0
    assert stats["ratio"] >= 0
    assert "eyes_up_percentage" in stats
