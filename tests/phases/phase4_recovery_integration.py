from __future__ import annotations
import json, sqlite3, tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from genesis import Genesis
from genesis.engine_boundary import EngineReceipt
from genesis.types import Candidate


def run():
    with tempfile.TemporaryDirectory() as td:
        root=Path(td); db=root/'state.db'; ws=root/'ws'
        g=Genesis(state_path=db,workspace=ws,enable_ollama=False)

        calls={'n':0}
        def ext(): calls['n']+=1; return 'should-not-run'
        g.register_tool('phase4_external','external',ext,mutating=True,external_side_effect=True,policy_declared=True)
        c=Candidate('ext','',100,'phase4',action={'type':'tool','name':'phase4_external','args':{}})
        msg,ok,_=g.cognition.act(c,authorization='explicit')
        assert ok and calls['n']==0,msg
        tx=g.store.recent_actions(1)[0]; request_id=tx['engine_request_id']; action_id=tx['action_id']
        assert tx['state']=='PREPARED'
        g.close()

        g=Genesis(state_path=db,workspace=ws,enable_ollama=False)
        pending=g.pending_engine_actions()
        assert any(x['action_id']==action_id and x['engine_request_id']==request_id for x in pending),pending
        result=g.reconcile_engine_receipt(EngineReceipt(request_id,'COMMITTED','receipt-phase4',{'ok':True}))
        assert result['accepted'] and result['state']=='COMMITTED',result
        tx2=g.store.action_transaction(action_id); assert tx2['state']=='COMMITTED'
        same=g.reconcile_engine_receipt(EngineReceipt(request_id,'COMMITTED','receipt-phase4',{'ok':True}))
        assert same['accepted'] and same['idempotent']
        different=g.reconcile_engine_receipt(EngineReceipt(request_id,'COMMITTED','receipt-phase4-other',{'ok':True}))
        assert not different['accepted']

        def calc(i): return g.respond(f'Calculate {i} + 1')
        with ThreadPoolExecutor(max_workers=8) as ex:
            out=list(ex.map(calc,range(50)))
        assert all(str(i+1) in out[i] for i in range(50)),out[:5]
        recent=g.store.recent_actions(60)
        assert sum(1 for x in recent if x['state']=='COMMITTED')>=51
        assert g.self_check()['ok'],g.self_check()

        export=g.export_state(root/'export.json'); backup=g.backup_state(root/'backup.db')
        payload=json.loads(export.read_text())
        assert payload['schema_version']>=6 and 'stats' in payload
        b=sqlite3.connect(backup); assert b.execute('PRAGMA quick_check').fetchone()[0]=='ok'; b.close()
        assert g.store.db.execute('PRAGMA quick_check').fetchone()[0]=='ok'
        g.close()

        legacy=root/'legacy.db'
        con=sqlite3.connect(legacy)
        con.executescript('''
        CREATE TABLE meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
        CREATE TABLE facts(id INTEGER PRIMARY KEY AUTOINCREMENT,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,namespace TEXT NOT NULL DEFAULT 'world',key TEXT NOT NULL,key_norm TEXT NOT NULL,value TEXT NOT NULL,value_norm TEXT NOT NULL,confidence REAL NOT NULL DEFAULT 1.0,source TEXT NOT NULL DEFAULT 'interaction',status TEXT NOT NULL DEFAULT 'active',use_count INTEGER NOT NULL DEFAULT 0,UNIQUE(namespace,key_norm));
        CREATE TABLE triples(id INTEGER PRIMARY KEY AUTOINCREMENT,created_at TEXT NOT NULL,subject TEXT NOT NULL,subject_norm TEXT NOT NULL,relation TEXT NOT NULL,relation_norm TEXT NOT NULL,object TEXT NOT NULL,object_norm TEXT NOT NULL,confidence REAL NOT NULL DEFAULT 1.0,source TEXT NOT NULL DEFAULT 'interaction',status TEXT NOT NULL DEFAULT 'active');
        '''); con.commit(); con.close()
        from genesis.storage import Store
        s=Store(legacy)
        assert 'truth_state' in {r[1] for r in s.db.execute('PRAGMA table_info(facts)').fetchall()}
        assert 'truth_state' in {r[1] for r in s.db.execute('PRAGMA table_info(triples)').fetchall()}
        assert s.db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='action_transactions'").fetchone()
        s.close()
    print('PHASE4_RECOVERY_INTEGRATION=PASS concurrent_turns=50')

if __name__=='__main__': run()
