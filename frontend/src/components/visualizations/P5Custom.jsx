import { useRef, useEffect, useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { validateSketchCode } from '../../utils/astValidator';
import { AlertTriangle, ShieldCheck, Loader2 } from 'lucide-react';

export default function P5Custom({ spec, isExpanded = false }) {
  const iframeRef = useRef(null);
  const { token } = useAuth();
  const [error, setError] = useState(null);
  const [loaded, setLoaded] = useState(false);
  
  const [currentSpec, setCurrentSpec] = useState(spec);
  const [retryCount, setRetryCount] = useState(0);
  const [isRegenerating, setIsRegenerating] = useState(false);
  const [regStatus, setRegStatus] = useState('');

  // Sync state if a new spec is requested from parent
  useEffect(() => {
    setCurrentSpec(spec);
    setError(null);
    setLoaded(false);
    setRetryCount(0);
    setIsRegenerating(false);
    setRegStatus('');
  }, [spec]);

  // Static AST Validation
  useEffect(() => {
    if (!currentSpec) return;
    setError(null);
    setLoaded(false);

    const validation = validateSketchCode(currentSpec.code);
    if (!validation.valid) {
      handleFailure(`Validation failed: ${validation.error}`);
    }
  }, [currentSpec]);

  const logErrorToBackend = async (errMessage) => {
    try {
      await fetch(`${import.meta.env.VITE_API_URL}/visualize/log-validation`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          video_id: currentSpec.video_id || spec.video_id || '',
          query: currentSpec.query || spec.query || currentSpec.title || '',
          category: currentSpec.type || 'custom',
          spec: currentSpec,
          validation_error: errMessage
        })
      });
    } catch (e) {
      console.error('Failed to log validation error:', e);
    }
  };

  const handleFailure = async (errMessage) => {
    logErrorToBackend(errMessage);

    if (retryCount < 2) {
      setIsRegenerating(true);
      const nextRetry = retryCount + 1;
      setRegStatus(`Error: "${errMessage.slice(0, 50)}...". Regenerating corrected sketch (Attempt ${nextRetry}/2)...`);
      
      try {
        const queryText = currentSpec.query || spec.query || currentSpec.title || 'custom visualization';
        const { api } = await import('../../services/api');
        
        const newSpec = await api.regenerateVisualization(
          currentSpec.video_id || spec.video_id || '',
          queryText,
          currentSpec.type || 'custom',
          currentSpec.code,
          errMessage,
          token
        );
        
        if (newSpec && newSpec.code) {
          setRetryCount(nextRetry);
          setIsRegenerating(false);
          setRegStatus('');
          setCurrentSpec(newSpec);
        } else {
          throw new Error('Regeneration returned empty code');
        }
      } catch (err) {
        console.error('Self-correction failed:', err);
        setIsRegenerating(false);
        setRegStatus('');
        setError(`Self-correction failed. ${errMessage}`);
      }
    } else {
      setError(errMessage);
    }
  };

  useEffect(() => {
    if (error || isRegenerating) return;

    // Listen to messages from the sandboxed iframe
    const handleMessage = (event) => {
      if (iframeRef.current && event.source === iframeRef.current.contentWindow) {
        if (event.data.type === 'error') {
          handleFailure(event.data.message);
        } else if (event.data.type === 'loaded') {
          setLoaded(true);
        }
      }
    };

    window.addEventListener('message', handleMessage);
    return () => window.removeEventListener('message', handleMessage);
  }, [error, isRegenerating, currentSpec, token, retryCount]);

  if (isRegenerating) {
    return (
      <div className="flex flex-col items-center justify-center p-6 bg-indigo-500/10 border border-indigo-500/25 rounded-2xl text-center min-h-[220px]">
        <Loader2 className="w-8 h-8 text-indigo-400 animate-spin mb-3" />
        <h4 className="text-xs font-semibold text-indigo-300 uppercase tracking-wider mb-1">Self-Healing Canvas</h4>
        <p className="text-xs text-indigo-200/80 max-w-xs">{regStatus}</p>
        <p className="text-[10px] text-slate-500 mt-2">Correcting script syntax & constraints automatically...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center p-6 bg-red-500/10 border border-red-500/25 rounded-2xl text-center">
        <AlertTriangle className="w-8 h-8 text-red-400 mb-3" />
        <h4 className="text-xs font-semibold text-red-300 uppercase tracking-wider mb-1">Visualization Blocked</h4>
        <p className="text-xs text-red-200/80 max-w-xs">{error}</p>
        <p className="text-[10px] text-slate-500 mt-2">The generated code did not meet safety constraints.</p>
      </div>
    );
  }

  // Construct iframe srcdoc
  const srcDoc = `
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <style>
        html, body {
          margin: 0;
          padding: 0;
          width: 100%;
          height: 100%;
          overflow: hidden;
          background-color: #0f0f1e;
        }
        #canvas-container {
          width: 100%;
          height: 100%;
          display: flex;
          justify-content: center;
          align-items: center;
        }
      </style>
      <script src="https://cdnjs.cloudflare.com/ajax/libs/p5.js/1.9.0/p5.min.js"></script>
    </head>
    <body>
      <div id="canvas-container"></div>
      <script>
        (function() {
          const code = ${JSON.stringify(currentSpec.code)};
          const container = document.getElementById('canvas-container');
          
          window.addEventListener('error', (event) => {
            window.parent.postMessage({ type: 'error', message: event.message }, '*');
          });

          try {
            const buildSketch = new Function('p', 'container', code);
            
            const sketch = (p) => {
              let origSetup = null;
              let origDraw = null;
              let setupTimer = null;
              let drawErrorCount = 0;
              let frameBudgetViolations = 0;

              // Run buildSketch to assign p.setup and p.draw
              try {
                buildSketch(p, container);
              } catch (err) {
                window.parent.postMessage({ type: 'error', message: 'Initialization error: ' + err.message }, '*');
                return;
              }

              origSetup = p.setup;
              origDraw = p.draw;

              p.setup = () => {
                setupTimer = setTimeout(() => {
                  window.parent.postMessage({ type: 'error', message: 'p.setup timed out (>3000ms)' }, '*');
                }, 3000);
                
                try {
                  const originalCreateCanvas = p.createCanvas;
                  p.createCanvas = (w, h) => {
                    const targetHeight = container.clientHeight || h || 280;
                    return originalCreateCanvas.call(p, w, targetHeight);
                  };

                  if (origSetup) {
                    origSetup();
                  } else {
                    p.createCanvas(container.clientWidth || 400, container.clientHeight || 280);
                  }
                } catch (err) {
                  window.parent.postMessage({ type: 'error', message: 'Error inside setup: ' + err.message }, '*');
                  throw err;
                } finally {
                  clearTimeout(setupTimer);
                }
              };

              p.draw = () => {
                const startTime = performance.now();
                try {
                  if (origDraw) {
                    origDraw();
                  }
                } catch (err) {
                  drawErrorCount++;
                  if (drawErrorCount >= 5) {
                    p.noLoop();
                    window.parent.postMessage({ type: 'error', message: 'p.draw crashed repeatedly: ' + err.message }, '*');
                  }
                  throw err;
                }
                
                const frameDuration = performance.now() - startTime;
                if (frameDuration > 100) {
                  frameBudgetViolations++;
                  if (frameBudgetViolations > 5) {
                    p.noLoop();
                    window.parent.postMessage({ type: 'error', message: 'Frame budget exceeded (>100ms per frame)' }, '*');
                  }
                } else {
                  frameBudgetViolations = Math.max(0, frameBudgetViolations - 1);
                }
              };

              p.windowResized = () => {
                p.resizeCanvas(container.clientWidth, container.clientHeight || 280);
              };
            };

            new p5(sketch, container);
            window.parent.postMessage({ type: 'loaded' }, '*');
          } catch (err) {
            window.parent.postMessage({ type: 'error', message: 'Parse/Execution error: ' + err.message }, '*');
          }
        })();
      </script>
    </body>
    </html>
  `;

  return (
    <div className="w-full flex flex-col items-center gap-2 relative">
      <div className="w-full flex items-center justify-between px-1 text-[11px] text-slate-500 mb-1">
        <span className="flex items-center gap-1 text-slate-400">
          <ShieldCheck className="w-3.5 h-3.5 text-indigo-400" />
          Sandboxed p5.js Sketch
        </span>
        {!loaded && (
          <span className="flex items-center gap-1 text-slate-500">
            <Loader2 className="w-3 h-3 animate-spin" /> Loading
          </span>
        )}
      </div>

      <div className={`w-full bg-dark-950 rounded-2xl overflow-hidden border border-dark-800 relative ${isExpanded ? 'h-[500px]' : 'aspect-[4/3] max-h-[300px]'}`}>
        <iframe
          ref={iframeRef}
          title={currentSpec.title || 'Dynamic Visualization'}
          sandbox="allow-scripts"
          srcDoc={srcDoc}
          className="w-full h-full border-none"
        />
      </div>
    </div>
  );
}
