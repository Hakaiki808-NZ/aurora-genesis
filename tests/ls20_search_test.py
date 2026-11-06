"""Unit checks for observation-based temporal interception in LS20 adapter."""
from genesis.ls20_search import LS20SearchPlanner, SearchWorld
from genesis.visual_navigation import VisualObject


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
    # A one-door route must still be found when a second door has an
    # unmatched shape and is currently impossible to open.
    shape = ((1,0,0),(0,1,0),(0,0,1))
    other_shape = ((1,1,0),(0,0,1),(1,0,1))
    two_doors = SearchWorld(
        walkable=frozenset({(0,0),(5,0),(10,0),(15,0)}),
        door=(
            VisualObject(5,0,"door",shape,12),
            VisualObject(15,0,"door",other_shape,12),
        ),
        rotation=frozenset(), color=frozenset(), shape=frozenset(),
        energy=(), player=(0,0), key_shape=shape,
        key_color=12, meter_units=42, unit_cost=1, launches={}
    )
    impossible,reason=LS20SearchPlanner.search(two_doors)
    assert impossible is None, (impossible,reason)
    partial,info=LS20SearchPlanner.search(two_doors,target_mask=1)
    assert partial == ["ACTION4"], (partial,info)
    assert info["target_mask"] == 1
    assert LS20SearchPlanner.search(two_doors,target_mask=4)[0] is None
    print("LS20_PARTIAL_OBJECTIVES=PASS")
    print("LS20_TEMPORAL_NAVIGATION=PASS")


if __name__ == "__main__":
    run()
