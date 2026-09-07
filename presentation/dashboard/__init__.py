"""Live local Matplotlib dashboard; no external services or synthetic telemetry."""
from pathlib import Path
from presentation.security_event_log import SecurityEventLog


def draw(log_path: str | Path, output: str | Path | None=None, live: bool=False) -> None:
    """Plot the latest sequential likelihood trace and CHSH session trend."""
    import matplotlib
    if not live: matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.animation import FuncAnimation
    fig,axes=plt.subplots(1,2,figsize=(12,4.5),layout='constrained')
    fig.suptitle('Teleportation QDS • measured security telemetry',fontweight='bold')
    log=SecurityEventLog(log_path)

    def refresh(frame: int=0) -> None:
        """Redraw only actual on-disk telemetry on each timer tick."""
        events=log.read()
        for ax in axes: ax.clear();ax.grid(alpha=.2)
        if not events:
            axes[0].set_title('Waiting for verification events');return
        stats=[event['report']['statistics'] for event in events];latest=stats[-1];sprt=latest['sprt']
        axes[0].plot(range(1,len(sprt['trace'])+1),sprt['trace'],color='#176b87')
        axes[0].axhline(sprt['upper'],color='#be3144',linestyle='--',label='Reject boundary')
        axes[0].axhline(sprt['lower'],color='#26845b',linestyle='--',label='Accept boundary')
        axes[0].set(xlabel='Measured token round',ylabel='Log likelihood ratio',title=f"Latest SPRT: {latest['sprt_decision']}");axes[0].legend()
        axes[1].plot(range(len(stats)),[s['chsh']['s'] for s in stats],marker='o',color='#7554a3')
        axes[1].axhline(2,color='gray',linestyle='--',label='Classical bound')
        axes[1].axhline(2**1.5,color='#26845b',linestyle=':',label='Quantum maximum')
        axes[1].set(xlabel='Verification event',ylabel='CHSH S',title=f"QBER {latest['qber']:.4f} • {latest['decision']}");axes[1].legend()
    refresh()
    if output: fig.savefig(output,dpi=160)
    if live:
        animation=FuncAnimation(fig,refresh,interval=1000,cache_frame_data=False)
        plt.show()
    else: plt.close(fig)
