"""ROC from actual labeled evaluation scores; no ML dependencies."""
import numpy as np


def roc(labels: list[int], scores: list[float]) -> dict:
    """Enumerate empirical thresholds, preserving ties and both ROC endpoints."""
    y=np.asarray(labels);s=np.asarray(scores,dtype=float)
    if y.shape!=s.shape or y.ndim!=1 or not np.isfinite(s).all() or set(y)!={0,1}: raise ValueError('ROC requires finite scores and both binary classes')
    thresholds=np.r_[np.inf,np.sort(np.unique(s))[::-1],-np.inf]
    tpr=[];fpr=[]
    for threshold in thresholds:
        predicted=s>=threshold
        tpr.append(float(np.sum(predicted&(y==1))/np.sum(y==1)))
        fpr.append(float(np.sum(predicted&(y==0))/np.sum(y==0)))
    return {'fpr':fpr,'tpr':tpr,'thresholds':[None if not np.isfinite(t) else float(t) for t in thresholds],
            'auc':float(np.trapz(tpr,fpr)),'positives':int(sum(y)),'negatives':int(sum(y==0))}


def plot_curves(curves: dict, path: str) -> None:
    """Render evaluated ROC curves with sample sizes and numeric AUC."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,ax=plt.subplots(figsize=(6.5,5.2),layout='constrained')
    for name,curve in curves.items():ax.plot(curve['fpr'],curve['tpr'],label=f"{name}: AUC {curve['auc']:.3f}")
    ax.plot([0,1],[0,1],'--',color='gray',alpha=.5)
    ax.set(xlabel='False positive rate',ylabel='True positive rate',title='Measured attack detection ROC',xlim=(0,1),ylim=(0,1.02));ax.legend();ax.grid(alpha=.2)
    fig.savefig(path,dpi=170);plt.close(fig)
