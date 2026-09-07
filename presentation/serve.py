"""Persistent local API with a preloaded receiver session and live event stream."""
import argparse
from pathlib import Path
import uvicorn
from qds_protocol.key_distribution import distribute
from qds_protocol.signing_engine import sign
from qds_protocol.verification_engine import VerificationEngine
from quantum_core.bell_state_generator import sample_chsh
from presentation.security_event_log import SecurityEventLog
from presentation.verification_api import create_app


def main() -> None:
    """Start a localhost-only API; write an actual request payload for curl."""
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8000);parser.add_argument('--output',type=Path,default=Path('artifacts/live'))
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    d=distribute(512,901);p,r=sign(d,'Live API verification',.1,902);v=VerificationEngine();v.register(d,r)
    (args.output/'payload.json').write_text(p.model_dump_json(indent=2))
    app=create_app(v,{d.session_id:sample_chsh(8192,.1,903)},SecurityEventLog(args.output/'events.jsonl'),.03,.18)
    uvicorn.run(app,host='127.0.0.1',port=args.port)

if __name__=='__main__':main()
