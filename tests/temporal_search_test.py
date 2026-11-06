"""Unit tests for time-expanded visual planning using observations, not game internals."""
from genesis.ls20_search import SearchWorld
from genesis.temporal_search import search_temporal
from genesis.visual_navigation import VisualObject

SHAPE_A=((1,0,0),(0,1,0),(0,0,1))
SHAPE_B=((1,1,0),(0,1,0),(1,0,1))
COLORS=(12,9,14,8)


def world(goal_shape=SHAPE_A,goal_color=9):
    return SearchWorld(
        walkable=frozenset({(0,0),(5,0),(10,0),(15,0)}),
        door=(VisualObject(10,0,"door",goal_shape,goal_color),),
        rotation=frozenset(), color=frozenset({(15,0)}),
        shape=frozenset({(15,0)}), energy=(), player=(0,0),
        key_shape=SHAPE_A, key_color=12, meter_units=7, unit_cost=1,
        launches={},
    )


def run():
    color_forecast={"color":tuple([(5,0),(15,0)]*5)}
    plan,info=search_temporal(world(),{},color_forecast,
                              color_cycle=COLORS,horizon=10)
    assert plan is not None,(plan,info)
    assert list(plan.actions)==["ACTION4","ACTION4"],(plan,info)
    assert plan.goal_mask==1

    shape_forecast={"shape":tuple([(5,0),(15,0)]*5)}
    plan,info=search_temporal(world(SHAPE_B,12),{SHAPE_A:SHAPE_B},
                              shape_forecast,color_cycle=COLORS,horizon=10)
    assert plan is not None and len(plan.actions)==2,(plan,info)

    no_path,reason=search_temporal(world(SHAPE_B,12),{},shape_forecast,
                                   color_cycle=COLORS,horizon=10)
    assert no_path is None and reason["unknown_shape_edges_blocked"]>0
    none,reason=search_temporal(world(),{}, {},
                                color_cycle=COLORS,horizon=10)
    assert none is None and reason["reason"]=="no_evidence_backed_motion"
    print("TEMPORAL_GOAL_SEARCH=PASS")


if __name__=="__main__":
    run()
