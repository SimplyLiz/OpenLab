import { MetaboliteChart } from './MetaboliteChart';
import { GeneExpressionHeatmap } from './GeneExpressionHeatmap';
import { FluxSankey } from './FluxSankey';

export function Dashboard() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8, padding: 8 }}>
      <h3>Dashboard</h3>
      <MetaboliteChart />
      <GeneExpressionHeatmap />
      <FluxSankey />
    </div>
  );
}
