import { SimControls } from './SimControls';
import { PerturbationPanel } from './PerturbationPanel';

export function Toolbar() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8, padding: 8 }}>
      <h3>Controls</h3>
      <SimControls />
      <PerturbationPanel />
    </div>
  );
}
