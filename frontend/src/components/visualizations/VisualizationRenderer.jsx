import VizErrorBoundary from './VizErrorBoundary';
import D3Chart from './D3Chart';
import D3Graph from './D3Graph';
import P5Simulation from './P5Simulation';
import MermaidDiagram from './MermaidDiagram';
import P5Custom from './P5Custom';

export default function VisualizationRenderer({ spec, isExpanded = false }) {
  if (!spec || spec.type === 'none') return null;

  return (
    <VizErrorBoundary>
      <div className={isExpanded ? "w-full h-full flex flex-col justify-center items-stretch min-h-0 min-w-0" : "mt-3 pt-3 border-t border-dark-700/50 w-full"}>
        {spec.type === 'chart' && <D3Chart spec={spec} isExpanded={isExpanded} />}
        {spec.type === 'graph' && <D3Graph spec={spec} isExpanded={isExpanded} />}
        {spec.type === 'simulation' && <P5Simulation spec={spec} isExpanded={isExpanded} />}
        {spec.type === 'diagram' && <MermaidDiagram spec={spec} isExpanded={isExpanded} />}
        {spec.type === 'custom' && <P5Custom spec={spec} isExpanded={isExpanded} />}
      </div>
    </VizErrorBoundary>
  );
}
