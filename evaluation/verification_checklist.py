"""Executable evidence for the supplied acceptance checklist, including scope failures."""
from quantum_core.randomness import simulator_seed
from pathlib import Path
import json
import math
import re
import numpy as np
from scipy.stats import binomtest
from qiskit import QuantumCircuit, transpile
from attack_simulation.attack_orchestrator import run_scenario
from quantum_core.bell_state_generator import sample_chsh,bell_statevector,bell_density
from quantum_core.channel_noise_model import logical_simulator
from qds_protocol.teleportation_engine import fidelity
from detection_engine.chsh_correlator import correlate
from detection_engine.integrity_monitor import inspect
from attribution_engine.rule_engine import attribute
from evaluation.run_full_evaluation import calibrate
from evaluation.baseline_threshold_detector import design
from math_model.min_entropy_bounds import forgery_bound


def save(path: Path, data: dict) -> None:
    """Write exact finite JSON numbers, refusing NaN or infinite values."""
    path.write_text(json.dumps(data,indent=2,allow_nan=False))


def anti_faking(output: Path) -> dict:
    """Run A1–A5 before the final functional/evaluation sweep."""
    output.mkdir(parents=True,exist_ok=True);c=calibrate(.1);honest=[];svalues=[]
    pairs=sample_chsh(4096,.1,800)
    for seed in range(50):
        scenario=run_scenario('honest',0,.1,2000+seed,512)
        r=inspect(scenario.records,pairs,scenario.integrity,c['p0'],c['p1'])
        honest.append({'seed':2000+seed,'qber':r['qber'],'decision':r['decision'],'rounds':r['sprt']['rounds']})
    for seed in range(20):svalues.append(correlate(sample_chsh(4096,.1,3000+seed))['s'])
    root=Path(__file__).resolve().parents[1]
    patterns=[r'return True\s+#',r'0\.987',r'#\s*TODO',r'pass\s+#\s*implement later',r'random\.choice\(\["ACCEPT","REJECT"\]\)']
    suspicious=[];label_hits=[]
    for folder in ('detection_engine','attribution_engine'):
        for path in (root/folder).glob('*.py'):
            source=path.read_text()
            suspicious.extend(f'{path.name}: {pattern}' for pattern in patterns if re.search(pattern,source))
            label_hits.extend(f'{path.name}: {name}' for name in ('ground_truth','true_label','attack_type_injected') if name in source)
            if 'attack_simulation' in source:label_hits.append(f'{path.name}: imports simulation')
    qbers=[r['qber'] for r in honest];accepts=sum(r['decision']=='ACCEPT' for r in honest)
    main_fpr=sum(r['decision']=='REJECT' for r in honest)/50
    stress_fpr=sum(q>c['observed_qber'] for q in qbers)/50
    result={'A1':{'pass':accepts>=48 and float(np.std(qbers))>0,'accepts':accepts,'runs':50,'qber_min':min(qbers),'qber_max':max(qbers),'qber_std':float(np.std(qbers))},
            'A2':{'pass':2.65<float(np.mean(svalues))<2.85 and float(np.std(svalues))>0,'mean_s':float(np.mean(svalues)),'std_s':float(np.std(svalues)),'values':svalues},
            'A3':{'pass':not suspicious,'hits':suspicious},'A4':{'pass':not label_hits,'hits':label_hits},
            'A5':{'pass':main_fpr<=.06 and stress_fpr>0,'main_fpr':main_fpr,'stress_fixed_qber_threshold':c['observed_qber'],'stress_fpr':stress_fpr,
                  'note':'Zero observed false positives is valid; an intentionally sensitive fixed threshold demonstrates stochastic false alarms.'},
            'honest_runs':honest,'calibration':c}
    save(output/'anti_faking.json',result)
    for key in ('A1','A2','A3','A4','A5'):print(key,result[key],flush=True)
    if not all(result[k]['pass'] for k in ('A1','A2','A3','A4','A5')):raise AssertionError('Anti-faking gate failed; inspect anti_faking.json')
    return result


def entropy_experiment(q: float, exposure: float, seed: int, trials: int=4096, n: int=8, tolerance: int=1) -> dict:
    """Execute Helstrom probe discrimination; validate only §1's independent model."""
    rng=np.random.default_rng(seed);bits=rng.integers(0,2,trials*n);observed=np.empty_like(bits)
    theta=math.acos(1-2*q);sim=logical_simulator(exposure)
    for bit in (0,1):
        qc=QuantumCircuit(1,1)
        if bit:qc.ry(2*theta,0)
        qc.ry(-(theta-math.pi/2),0);qc.measure(0,0)
        compiled=transpile(qc,basis_gates=['id','rz','sx','x','cx','measure'],optimization_level=0,seed_transpiler=seed)
        indices=np.flatnonzero(bits==bit)
        memory=sim.run(compiled,shots=len(indices),memory=True,seed_simulator=simulator_seed(seed,bit)).result().get_memory()
        observed[indices]=np.array([int(x) for x in memory])
    successes=int(np.sum(np.sum((bits!=observed).reshape(trials,n),axis=1)<=tolerance))
    bound=forgery_bound(n,q,1e-6,tolerance);ci=binomtest(successes,trials).proportion_ci(.99)
    return {'q_model':q,'exposure':exposure,'seed':seed,'n':n,'tolerance':tolerance,'trials':trials,'successes':successes,
            'empirical_success':successes/trials,'upper_99_ci':float(ci.high),'bound':bound,'below_bound':successes/trials<=bound,
            'scope':'Independent pure-probe discrimination only; no general QDS claim'}


def functional(output: Path) -> dict:
    """Compute B1–B7 and the explicitly restricted forgery-bound experiment."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    ns=list(range(1,97));bounds=[forgery_bound(n,.04) for n in ns]
    fig,ax=plt.subplots(figsize=(6,4),layout='constrained');ax.semilogy(ns,bounds)
    ax.set(xlabel='Independent secret bits n',ylabel='Forgery probability upper bound',title='Restricted pure-probe model: Q=0.04, ε=10⁻⁶');ax.grid(alpha=.2)
    fig.savefig(output/'min_entropy.png',dpi=170);plt.close(fig)
    state=bell_statevector().data;coherence=[float(abs(bell_density(x).data[0,3])) for x in (0,.5,1)]
    fidelities=[fidelity(exposure=x) for x in (0,.5,1)]
    intercepted=run_scenario('individual',1,0,31,8192);qber=sum(r.error for r in intercepted.records)/8192
    c=calibrate(.1);fixed=design(c['p0'],c['p1']);pairs=sample_chsh(4096,.1,800)
    strong=[];weak=[];decisions=[]
    for seed in range(20):
        for strength,target in ((1.,strong),(.3,weak)):
            s=run_scenario('individual',strength,.1,4000+seed,512)
            report=inspect(s.records,pairs,s.integrity,c['p0'],c['p1']);target.append(report['sprt']['rounds'])
            if strength==1:decisions.append(report['sprt_decision'])
    witness=[{'severity':level,'s':correlate(sample_chsh(8192,.1,5000,level))['s']} for level in (0,.25,.5,.75,1)]
    classes=('forgery','impersonation','replay','channel_manipulation');confusion={name:{} for name in classes}
    for kind in classes:
        for seed in range(20):
            s=run_scenario(kind,1,.1,6000+seed,512)
            prediction=attribute(inspect(s.records,pairs,s.integrity,c['p0'],c['p1']))['attack_class']
            confusion[kind][prediction]=confusion[kind].get(prediction,0)+1
    entropy=[]
    for i,q in enumerate((.01,.04,.1)):
        for j,exposure in enumerate((.1,.5,1.)):entropy.append(entropy_experiment(q,exposure,7000+10*i+j))
    result={'B1':{'pass':all(a>=b for a,b in zip(bounds,bounds[1:])),'n':[8,16,32,64],
                  'bounds':[forgery_bound(n,.04) for n in (8,16,32,64)],'plot':'min_entropy.png'},
            'B2':{'pass':bool(np.allclose(state,[2**-.5,0,0,2**-.5])) and coherence[0]>coherence[1]>coherence[2],
                  'statevector_real':state.real.tolist(),'max_imaginary':float(abs(state.imag).max()),'coherences':coherence},
            'B3':{'pass':fidelities[0]>=.99 and fidelities[0]>fidelities[1]>fidelities[2],'exposure':[0,.5,1],'fidelities':fidelities},
            'B4':{'pass':.23<qber<.27,'qber':qber,'n':8192},
            'B5':{'pass':float(np.mean(strong))<fixed['n'] and float(np.mean(weak))>float(np.mean(strong)),
                  'strong_mean_rounds':float(np.mean(strong)),'weak_mean_rounds':float(np.mean(weak)),
                  'strong_rejects':decisions.count('REJECT'),'runs':20,'fixed':fixed,'strong_rounds':strong,'weak_rounds':weak,
                  'note':'Comparison covers iid token mismatch hypotheses, excluding CHSH overhead and correlated attacks.'},
            'B6':{'pass':all(a['s']>b['s'] for a,b in zip(witness,witness[1:])),'observations':witness,
                  'note':'Honest optimal settings give S=√2 after full Z dephasing, below the classical bound 2.'},
            'B7':{'pass':all(confusion[k].get(k,0)>10 for k in classes),'confusion_matrix':confusion,'runs_per_class':20},
            'C3':{'pass':False,'restricted_experiment_pass':all(r['below_bound'] for r in entropy),
                  'reason':'The requested universal guarantee across coherent/classical attacks is not established. Nontrivial bound assumes independent pure probes; finite proportions are not guaranteed never to exceed probability bounds.',
                  'experiments':entropy}}
    save(output/'functional_checks.json',result)
    for k,v in result.items():print(k,{a:b for a,b in v.items() if a not in ('experiments','strong_rounds','weak_rounds')},flush=True)
    return result


def write_signoff(output: Path, anti: dict, functional_result: dict, evaluation: dict, demo: dict, test_result: dict) -> dict:
    """Write an honest final checklist with any unsatisfied requirement explicit."""
    checks={k:v for k,v in anti.items() if k.startswith('A')};checks.update(functional_result)
    checks['B8']={'pass':demo['http_status']==200 and demo['log_events']>=1,**demo}
    checks['C1']={'pass':evaluation['roc']['Full observable score']['auc']>.6,'auc':evaluation['roc']['Full observable score']['auc'],'plot':'roc.png','runs':evaluation['runs']}
    checks['C2']={'pass':evaluation['mean_sprt_rounds']!=evaluation['mean_baseline_rounds'],'sprt_mean_rounds':evaluation['mean_sprt_rounds'],
                  'baseline_mean_rounds':evaluation['mean_baseline_rounds'],'baseline_auc':evaluation['roc']['Fixed mismatch baseline']['auc'],
                  'full_tpr':evaluation['full_tpr'],'baseline_tpr':evaluation['baseline_tpr'],'full_fpr':evaluation['full_fpr'],'baseline_fpr':evaluation['baseline_fpr'],
                  'note':'Different operating sensitivities are reported, not described as matched; SPRT uses a separately matched simple-hypothesis design in B5.'}
    checks['C4']={'pass':test_result['exit_code']==0,'command':'.venv/bin/python run.py','tests':test_result,'pipeline_completed':True}
    limitations=Path(__file__).resolve().parents[1]/'LIMITATIONS.md'
    checks['C5']={'pass':limitations.exists() and limitations.stat().st_size>500,'path':'LIMITATIONS.md'}
    checks['D1']={'pass':all(v['pass'] for v in checks.values()),'reason':'Evidence is attached; full sign-off requires every A/B/C requirement to pass.'}
    checks['D2']={'pass':False,'reason':'A reviewer can reproduce the experiments, but the universal C3 claim remains unsupported.'}
    save(output/'verification_checklist.json',checks)
    lines=['# Measured verification report','',f"Evaluation: {evaluation['runs']} runs. No ML, synthetic decisions, or label access in detection.",'',
           '**Full specification sign-off: NOT ACHIEVED. C3 is unsupported beyond the restricted model; D1/D2 therefore fail.**','',
           '| Check | Result | Measured evidence |','|---|---|---|']
    for key,value in checks.items():
        details={k:v for k,v in value.items() if k not in ('pass','experiments','values','strong_rounds','weak_rounds')}
        lines.append(f"| {key} | {'PASS' if value['pass'] else 'FAIL / UNSUPPORTED'} | {json.dumps(details,ensure_ascii=False).replace('|','/')} |")
    lines+=['','## Attribution confusion matrix','','| Injected | Forgery | Impersonation | Replay | Channel manipulation | None / other |','|---|---:|---:|---:|---:|---:|']
    classes=('forgery','impersonation','replay','channel_manipulation')
    for name,row in checks['B7']['confusion_matrix'].items():
        counts=[row.get(k,0) for k in classes];lines.append('| '+name+' | '+' | '.join(map(str,counts+[sum(row.values())-sum(counts)]))+' |')
    lines+=['','## Restricted entropy experiment','','| Q | Exposure | Successes / trials | Empirical success | 99% upper CI | Bound |','|---|---|---|---|---|---|']
    for r in checks['C3']['experiments']:
        lines.append(f"| {r['q_model']} | {r['exposure']} | {r['successes']} / {r['trials']} | {r['empirical_success']:.6f} | {r['upper_99_ci']:.6f} | {r['bound']:.6f} |")
    lines+=['','![Measured ROC](roc.png)','','![Restricted entropy bound](min_entropy.png)','','![Telemetry](dashboard.png)','']
    (output/'VERIFICATION_REPORT.md').write_text('\n'.join(lines));return checks
