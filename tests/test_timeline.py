from lifecanvas.sample import build_genki_family_plan
from lifecanvas.timeline import build_life_events, build_life_periods


def test_baseline_timeline_contains_children_car_and_housing_start():
    plan = build_genki_family_plan()
    events = build_life_events(plan)
    titles = {event.title for event in events}

    assert "第一子誕生" in titles
    assert "第二子誕生" in titles
    assert "車を購入" in titles
    assert any(event.category == "housing" and event.offset == 0 for event in events)
    assert not any(
        event.category == "housing" and event.offset == 26
        for event in events
    )


def test_explicit_move_shortens_housing_finance_period():
    plan = build_genki_family_plan()
    plan.housing.move_mode = "sell"
    plan.housing.move_offset = 26

    events = build_life_events(plan)
    periods = build_life_periods(plan)
    housing_period = next(
        period for period in periods if period.category == "housing"
    )

    assert any(
        event.category == "housing" and event.offset == 26
        for event in events
    )
    assert housing_period.start_offset == 0
    assert housing_period.end_offset == 26


def test_baseline_housing_finance_period_runs_to_term_end():
    plan = build_genki_family_plan()
    periods = build_life_periods(plan)
    housing_period = next(
        period for period in periods if period.category == "housing"
    )

    assert housing_period.start_offset == 0
    assert housing_period.end_offset == plan.housing.mortgage.term_years


def test_car_replacement_events_follow_cycle():
    plan = build_genki_family_plan()
    events = [event for event in build_life_events(plan) if event.title == "車を買い替え"]

    assert events[0].offset == plan.car.purchase_offset + plan.car.replacement_cycle_years
    assert all(
        later.offset - earlier.offset == plan.car.replacement_cycle_years
        for earlier, later in zip(events, events[1:])
    )
