"""Evidence-based temporal world model unit tests."""
from genesis.temporal_world import TemporalWorldModel


def run():
    memory=TemporalWorldModel(min_period=2,max_period=12)
    cycle=((0,0),(5,0),(10,0),(5,0))
    for step in range(8):
        memory.observe("episode-a",{"shape":cycle[step%4]},step)
    f=memory.forecast("episode-a","shape",8)
    assert f is not None, "two observed cycles should establish a motion forecast"
    assert f.period==4, f
    assert f.positions_after_actions[:5]==((0,0),(5,0),(10,0),(5,0),(0,0)),f
    assert f.confidence>=0.75
    confirmation=memory.observe("episode-a",{"shape":(0,0)},8)
    assert not confirmation["prediction_errors"],confirmation
    assert memory.summary("episode-a")["tracks"]["shape"]["prediction_confirmations"]==1
    f=memory.forecast("episode-a","shape",3)
    assert f is not None
    contradiction=memory.observe("episode-a",{"shape":(55,0)},9)
    assert contradiction["prediction_errors"]["shape"]["observed"]==(55,0)
    assert memory.forecast("episode-a","shape",4) is None, "surprise invalidates cycle"
    assert memory.summary("episode-a")["tracks"]["shape"]["prediction_contradictions"]==1

    memory.observe("episode-b",{"shape":(1,2)},0)
    assert memory.forecast("episode-b","shape",2) is None
    assert "shape" in memory.summary("episode-b")["tracks"]
    memory.reset_episode("episode-a")
    assert memory.summary("episode-a")["tracks"]=={}
    assert "shape" in memory.summary("episode-b")["tracks"]
    print("TEMPORAL_WORLD_MODEL=PASS")


if __name__=="__main__":
    run()
