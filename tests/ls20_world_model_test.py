"""Regression checks for time-indexed observable operator planning."""
from genesis.ls20_search import LS20SearchPlanner, SearchWorld
from genesis.visual_navigation import VisualObject


def run():
    before = ((1,0,0),(0,1,0),(0,0,1))
    after = ((0,1,0),(1,1,0),(0,0,1))
    world = SearchWorld(
        walkable=frozenset({(0,0),(5,0),(10,0),(15,0)}),
        door=(VisualObject(10,0,"door",after,12),),
        rotation=frozenset(), color=frozenset(),
        shape=frozenset({(15,0)}), energy=(),
        player=(0,0), key_shape=before, key_color=12,
        meter_units=10, unit_cost=1, launches={}
    )
    route, metrics = LS20SearchPlanner.search(
        world,shape_edges={before:after},
        moving={"shape":[(15,0),(5,0),(15,0),(5,0)]}
    )
    assert route == ["ACTION4","ACTION4"], (route, metrics)
    assert metrics["temporal_model"] is True
    # Operator that never intercepts the player cannot be assumed triggered.
    missing, metrics = LS20SearchPlanner.search(
        world,shape_edges={before:after},
        moving={"shape":[(15,0),(15,0),(15,0)]}
    )
    assert missing is None, missing
    # A periodic modifier can be reasoned about beyond a fixed 40-action
    # horizon: a long, resource-sufficient path remains discoverable.
    observed=[(5,0),(10,0),(15,0)]*3
    phase=LS20SearchPlanner._detect_period(observed)
    assert phase==[(15,0),(5,0),(10,0)], phase
    assert LS20SearchPlanner._detect_period([(5,0),(10,0),(15,0)]) is None
    print("LS20_TIME_INDEXED_SEARCH=PASS")


if __name__=="__main__":
    run()
