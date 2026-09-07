"""Run the actual attack hierarchy over a reproducible strength/noise grid."""
from pathlib import Path
import sys
if __package__ in (None,''): sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import argparse
import json
import numpy as np
from scipy.stats import binomtest
from attack_simulation.attack_orchestrator import run_scenario
from quantum_core.bell_state_generator import sample_chsh
from quantum_core.channel_noise_model import calibration_metadata
from detection_engine.integrity_monitor import inspect
from attribution_engine.rule_engine import attribute
from evaluation.baseline_threshold_detector import design, detect
from evaluation.roc_curve_generator import roc, plot_curves


def calibrate(exposure: float, seed: int=9182) -> dict:
    """Independent honest training-free reference with exact upper confidence bound."""
    records=run_scenario('honest',0,exposure,seed,8192).records
    errors=sum(r.error for r in records)
    interval=binomtest(errors,len(records)).proportion_ci(.999)
    # Guard margin is explicit, not an invented physical noise parameter.
    p0=min(.45,max(.005,float(interval.high)+.01));p1=min(.8,p0+.15)
    return {'p0':p0,'p1':p1,'observed_qber':errors/len(records),'errors':errors,'shots':len(records),
            'confidence_upper':float(interval.high),'guard_margin':.01,'seed':seed}


def evaluate_grid(output: Path, repeats: int=5, n: int=512, chsh_shots: int=2048) -> dict:
    """Every label is confined here; all reports originate from receiver observations."""
    if repeats<1 or n<32 or n%2:raise ValueError('Require repeats>=1 and even n>=32')
    output.mkdir(parents=True,exist_ok=True)
    kinds=('individual','collective','coherent','impersonation','replay','channel_manipulation')
    strengths=(.2,.6,1.);exposures=(.1,.5,1.)
    calibration={str(x):calibrate(x) for x in exposures};rows=[]
    baseline_designs={str(x):design(calibration[str(x)]['p0'],calibration[str(x)]['p1']) for x in exposures}
    for level_id,exposure in enumerate(exposures):
        c=calibration[str(exposure)];fixed=baseline_designs[str(exposure)]
        conditions=[('honest',0.)]+[(kind,strength) for kind in kinds for strength in strengths]
        for condition_id,(kind,strength) in enumerate(conditions):
            for repeat in range(repeats):
                seed=100000+level_id*10000+condition_id*100+repeat
                scenario=run_scenario(kind,strength,exposure,seed,n)
                pairs=sample_chsh(chsh_shots,exposure,seed+1000000,strength if kind=='impersonation' else 0.)
                report=inspect(scenario.records,pairs,scenario.integrity,c['p0'],c['p1'])
                baseline=detect([r.error for r in scenario.records],fixed['n'],fixed['cutoff'])
                rows.append({'kind':kind,'strength':strength,'exposure':exposure,'seed':seed,'label':int(kind!='honest'),
                             'report':report,'attribution':attribute(report),'baseline':baseline,
                             'quantum_resources':{'teleported_tokens':n,'chsh_pairs':chsh_shots,
                                                  'note':'SPRT prefix saving excludes already simulated tokens and witness overhead'}})
            print(f'Grid: exposure={exposure}, {kind} strength={strength}, {repeats} measured runs',flush=True)
    labels=[r['label'] for r in rows]
    curves={'Full observable score':roc(labels,[r['report']['score'] for r in rows]),
            'Fixed mismatch baseline':roc(labels,[r['baseline']['score'] for r in rows])}
    plot_curves(curves,str(output/'roc.png'))
    summary={'runs':len(rows),'repeats':repeats,'n':n,'chsh_shots':chsh_shots,'strengths':strengths,'exposures':exposures,
             'calibration':calibration,'backend':calibration_metadata(),'fixed_designs':baseline_designs,'roc':curves,
             'mean_sprt_rounds':float(np.mean([r['report']['sprt']['rounds'] for r in rows])),
             'mean_baseline_rounds':float(np.mean([r['baseline']['rounds'] for r in rows])),
             'full_fpr':float(np.mean([r['report']['decision']=='REJECT' for r in rows if not r['label']])),
             'full_tpr':float(np.mean([r['report']['decision']=='REJECT' for r in rows if r['label']])),
             'baseline_fpr':float(np.mean([r['baseline']['decision']=='REJECT' for r in rows if not r['label']])),
             'baseline_tpr':float(np.mean([r['baseline']['decision']=='REJECT' for r in rows if r['label']])),
             'inconclusive':sum(r['report']['decision']=='INCONCLUSIVE' for r in rows)}
    (output/'evaluation_runs.json').write_text(json.dumps(rows,indent=2,allow_nan=False))
    (output/'evaluation_summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False))
    return summary

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=Path('artifacts'));parser.add_argument('--repeats',type=int,default=5)
    args=parser.parse_args();result=evaluate_grid(args.output,args.repeats)
    print(json.dumps({k:v for k,v in result.items() if k in ('runs','mean_sprt_rounds','mean_baseline_rounds','full_fpr','full_tpr','baseline_tpr')},indent=2))
