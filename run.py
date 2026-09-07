"""Single-command build verification, real simulation, evaluation and evidence."""
import argparse
import json
from pathlib import Path
import subprocess
import sys


def main() -> None:
    """Execute checks in mandated order, failing loudly on computational errors."""
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,default=Path('artifacts'))
    parser.add_argument('--repeats',type=int,default=5)
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    tests=subprocess.run([sys.executable,'-m','pytest','-q','-s'],text=True,capture_output=True)
    (args.output/'tests.txt').write_text(tests.stdout+tests.stderr);print(tests.stdout,flush=True)
    result={'exit_code':tests.returncode,'output':'tests.txt'}
    if tests.returncode:raise SystemExit(tests.returncode)
    from evaluation.verification_checklist import anti_faking,functional,write_signoff
    from evaluation.run_full_evaluation import evaluate_grid
    from presentation.demo import demo
    print('Running anti-faking gate FIRST',flush=True);anti=anti_faking(args.output)
    measured=functional(args.output);http=demo(args.output);evaluation=evaluate_grid(args.output,args.repeats)
    checks=write_signoff(args.output,anti,measured,evaluation,http,result)
    print(json.dumps({'artifacts':str(args.output.resolve()),'passed':sum(v['pass'] for v in checks.values()),
                      'total':len(checks),'unsupported':[k for k,v in checks.items() if not v['pass']]},indent=2))

if __name__=='__main__':main()
