import { useCellForgeStore } from '@/stores/cellforgeStore';

export function SimControls() {
  const { state, isRunning, speed, play, pause, stepOnce, reset, setSpeed } = useCellForgeStore();

  return (
    <div style={{ border: '1px solid #333', padding: 8, borderRadius: 4 }}>
      <h4 style={{ margin: '0 0 8px' }}>Simulation</h4>

      <div style={{ display: 'flex', gap: 4, marginBottom: 8 }}>
        {isRunning ? (
          <button onClick={pause} style={btnStyle('#c44')}>Pause</button>
        ) : (
          <button onClick={play} style={btnStyle('#4a4')}>Play</button>
        )}
        <button onClick={stepOnce} disabled={isRunning} style={btnStyle('#668')}>Step</button>
        <button onClick={reset} style={btnStyle('#666')}>Reset</button>
      </div>

      <div style={{ marginBottom: 8 }}>
        <label style={{ fontSize: 11, color: '#aaa' }}>
          Speed: {speed}x
          <input
            type="range"
            min={0.1}
            max={10}
            step={0.1}
            value={speed}
            onChange={(e) => setSpeed(parseFloat(e.target.value))}
            style={{ width: '100%', marginTop: 2 }}
          />
        </label>
      </div>

      <div style={{ fontSize: 11, color: '#aaa', lineHeight: 1.6 }}>
        <div>Time: <span style={{ color: '#fff' }}>{state.time.toFixed(1)}s</span></div>
        <div>Growth: <span style={{ color: '#6f6' }}>{(state.growthRate * 3600).toFixed(4)}/h</span></div>
        <div>Mass: <span style={{ color: '#fff' }}>{state.cellMass.toFixed(0)} fg</span></div>
        <div>Replication: <span style={{ color: '#88f' }}>{(state.replicationProgress * 100).toFixed(1)}%</span></div>
      </div>
    </div>
  );
}

function btnStyle(bg: string): React.CSSProperties {
  return {
    padding: '4px 10px',
    border: 'none',
    borderRadius: 3,
    background: bg,
    color: '#fff',
    cursor: 'pointer',
    fontSize: 12,
    fontWeight: 600,
  };
}
