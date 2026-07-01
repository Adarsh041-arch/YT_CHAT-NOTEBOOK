import { useRef, useEffect, useState } from 'react';

function cleanMermaidSyntax(text) {
  if (!text) return '';
  
  // Strip markdown backticks if present
  let s = text.trim();
  s = s.replace(/^```mermaid\s*/i, '');
  s = s.replace(/```$/, '');
  s = s.trim();

  // Process line by line to sanitize labels containing special characters
  let lines = s.split('\n');
  lines = lines.map(line => {
    let trimmed = line.trim();
    if (!trimmed) return '';

    // Match patterns like: nodeId[Label Text] or nodeId(Label Text) or nodeId{Label Text}
    // If the label contains parentheses, brackets, colons, or dashes, and is not quoted, wrap it in double quotes.
    const bracketRegex = /^(\s*[A-Za-z0-9_-]+)\s*(\[|\(|\{\s*\(?)(\s*[^"\[\]\(\)\{\}]+?\s*)(\)?\s*\]|\)|\})/;
    const match = trimmed.match(bracketRegex);
    if (match) {
      const nodeId = match[1];
      const openChar = match[2];
      const label = match[3].trim();
      const closeChar = match[4];

      if (label && !label.startsWith('"') && !label.endsWith('"')) {
        // If label contains space or special character, wrap in double quotes
        if (/[\s()\-:/\\]/.test(label)) {
          return `${nodeId}${openChar}"${label}"${closeChar}`;
        }
      }
    }
    return line;
  });

  s = lines.filter(l => l !== null).join('\n');
  s = s.replace(/\bgraph\b/g, 'flowchart');
  
  if (!/^flowchart|^sequenceDiagram|^classDiagram|^stateDiagram|^erDiagram|^gantt|^pie/.test(s)) {
    s = 'flowchart TD\n' + s;
  }
  
  return s;
}

export default function MermaidDiagram({ spec, isExpanded = false }) {
  const ref = useRef(null);
  const idRef = useRef(`mermaid-${Math.random().toString(36).slice(2, 8)}`);
  const [error, setError] = useState(null);

  useEffect(() => {
    setError(null);
    if (!ref.current || !spec?.mermaidSyntax) return;
    let cancelled = false;

    (async () => {
      try {
        const mermaidModule = await import('mermaid');
        const mermaid = mermaidModule.default;
        
        mermaid.initialize({
          startOnLoad: false,
          theme: 'dark',
          securityLevel: 'loose',
          fontFamily: 'Inter, system-ui, sans-serif',
          flowchart: { useMaxWidth: true, htmlLabels: true },
        });

        if (cancelled) return;

        const cleaned = cleanMermaidSyntax(spec.mermaidSyntax);

        // Validate syntax before rendering
        try {
          await mermaid.parse(cleaned);
        } catch (parseErr) {
          if (cancelled) return;
          console.warn('Mermaid parse failed, trying default fallback...', parseErr);
          setError('Diagram syntax parsing error. Review the schema in the JSON tab.');
          return;
        }

        const { svg } = await mermaid.render(idRef.current, cleaned);
        if (!cancelled) {
          ref.current.innerHTML = svg;
          setError(null);
        }
      } catch (renderErr) {
        if (!cancelled) {
          console.error('Mermaid render error:', renderErr);
          setError('Failed to render flow diagram.');
        }
      }
    })();

    return () => { cancelled = true; };
  }, [spec]);

  if (error) {
    return (
      <div className="w-full my-3 p-4 bg-red-950/20 border border-red-900/50 rounded-xl text-center">
        <p className="text-xs text-red-400 font-semibold mb-1">Diagram Render Error</p>
        <p className="text-[10px] text-slate-400 max-h-24 overflow-y-auto font-mono">{error}</p>
      </div>
    );
  }

  return (
    <div className={`w-full my-3 flex justify-center overflow-auto items-center ${isExpanded ? 'h-[500px]' : 'min-h-[200px]'}`}>
      <div ref={ref} className="w-full max-w-full scale-[0.98] transition-transform" />
    </div>
  );
}
