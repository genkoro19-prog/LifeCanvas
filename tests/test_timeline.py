from lifecanvas.sample import build_genki_family_plan
from lifecanvas.timeline import build_life_events, build_life_periods


def test_timeline_contains_children_car_and_loan_events():
    plan = build_genki_family_plan()
    events = build_life_events(plan)
    titles = {event.title for event in events}

    assert "第一子誕生" in titles
    assert "第二子誕生" in titles
    assert "車を購入" in titles
    assert "住宅ローン開始" in titles
    assert "住み替え・ローン一括返済" in titles


def test_timeline_contains_mortgage_period():
    plan = build_genki_family_plan()
    periods = build_life_periods(plan)
    mortgage = next(period for period in periods if period.title == "住宅ローン返済期間")

    assert mortgage.start_offset == 0
    assert mortgage.end_offset == plan.housing.move_offset


def test_car_replacement_events_follow_cycle():
    plan = build_genki_family_plan()
    events = [event for event in build_life_events(plan) if event.title == "車を買い替え"]

    assert events[0].offset == plan.car.purchase_offset + plan.car.replacement_cycle_years
    assert all(
        later.offset - earlier.offset == plan.car.replacement_cycle_years
        for earlier, later in zip(events, events[1:])
    )
