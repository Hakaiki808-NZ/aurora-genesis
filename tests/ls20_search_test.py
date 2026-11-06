"""Unit checks for observation-based temporal interception in LS20 adapter."""
from genesis.ls20_search import LS20SearchPlanner, SearchWorld


def run():
    observed = [(0, 0), (5, 0), (10, 0), (5, 0), (0, 0), (5, 0)]
    forecast = LS20SearchPlanner._forecast_mover(observed, 4)
    assert forecast[:4] == [(5, 0), (10, 0), (5, 0), (0, 0)], forecast
    dummy = SearchWorld(
        walkable=frozenset({(0, 0), (5, 0), (10, 0), (15, 0)}),
        door=(), rotation=frozenset(), color=frozenset(), shape=frozenset(),
        energy=(), player=(0, 0), key_shape=((0,0,0),)*3,
        key_color=12, meter_units=42, unit_cost=1, launches={}
    )
    path = LS20SearchPlanner._moving_intercept(
        dummy, [(5, 0), (10, 0)], {"ACTION1", "ACTION2", "ACTION3", "ACTION4"}, {}
    )
    assert path == ["ACTION4"], path
    assert LS20SearchPlanner._moving_intercept(
        dummy, [(50, 50)]*4, {"ACTION1", "ACTION2", "ACTION3", "ACTION4"}, {},
        horizon=4
    ) is None
    print("LS20_TEMPORAL_NAVIGATION=PASS")


if __name__ == "__main__":
    run()
