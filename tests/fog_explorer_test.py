"""Fog-of-war exploration tests from synthetic 64x64 observations."""
import json
from genesis.fog_explorer import FogExplorer


def frame(shift_x=0):
    cells=[[5]*64 for _ in range(64)]
    # Distinct repeatable walls and corridors: no hidden map knowledge.
    for cy in range(0,7):
        for cx in range(0,8):
            x,y=4+cx*5+shift_x,cy*5
            value=4 if (cx==0 or cy==0 or (cx==5 and cy in (2,3))
                        or (cy==6 and cx in (2,3))) else 3
            for yy in range(y,y+5):
                for xx in range(x,x+5):
                    if 0<=xx<64 and 0<=yy<64:
                        cells[yy][xx]=value
    return json.dumps(cells)


def run():
    a=FogExplorer()
    f=frame()
    one=a.decide(f,0,(19,15),["ACTION1","ACTION2","ACTION3","ACTION4"],42)
    assert one["action"] is not None,one
    assert one["policy"]=="fog-explore-v1",one
    assert a.summary()["mapped_cells"]>10,a.summary()
    first=one["action"]["action_type"]
    repeated=a.decide(f,0,(19,15),["ACTION1","ACTION2","ACTION3","ACTION4"],42)
    assert ((19,15),first) in a.blocked, a.summary()
    assert repeated["action"] is not None or repeated["reason"]=="no_reachable_unexplored_frontier"

    # Separately validate the camera registrar on a known repeatable scene.
    b=FogExplorer()
    pos=b.update(frame(),1,(19,15))
    assert pos==(19,15),pos
    shifted=b.update(frame(-5),1,(19,15))
    assert shifted[0]>=19, (shifted,b.summary())
    assert b.summary()["mapped_cells"]>10
    b.reset(2)
    assert b.summary()["mapped_cells"]==0

    print("FOG_EXPLORATION=PASS")


if __name__=="__main__":
    run()
