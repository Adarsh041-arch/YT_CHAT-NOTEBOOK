import { useRef, useEffect, useState } from 'react';
import p5 from 'p5';
import { Play, Pause, RotateCcw, ChevronLeft, ChevronRight } from 'lucide-react';

function createParticlesSketch(p, params, height) {
  const count = params?.count || 50;
  const speed = params?.speed || 2;
  let particles = [];

  p.setup = () => {
    const el = p._curElement?.elt?.parentElement;
    const w = el?.clientWidth || 400;
    p.createCanvas(w, height);
    for (let i = 0; i < count; i++) {
      particles.push({
        x: p.random(p.width),
        y: p.random(p.height),
        vx: p.random(-speed, speed),
        vy: p.random(-speed, speed),
      });
    }
  };

  p.draw = () => {
    p.background(15, 15, 30);
    
    // Draw connections between close particles
    p.stroke(129, 140, 248, 45);
    p.strokeWeight(1);
    for (let i = 0; i < particles.length; i++) {
      for (let j = i + 1; j < particles.length; j++) {
        const d = p.dist(particles[i].x, particles[i].y, particles[j].x, particles[j].y);
        if (d < 60) {
          p.line(particles[i].x, particles[i].y, particles[j].x, particles[j].y);
        }
      }
    }
    
    p.noStroke();
    for (const pt of particles) {
      pt.x += pt.vx;
      pt.y += pt.vy;
      if (pt.x < 0 || pt.x > p.width) pt.vx *= -1;
      if (pt.y < 0 || pt.y > p.height) pt.vy *= -1;
      p.fill(129, 140, 248, 180);
      p.circle(pt.x, pt.y, 6);
    }
  };
}

function createPhysicsSketch(p, params, height) {
  const count = params?.count || 30;
  let balls = [];

  p.setup = () => {
    const el = p._curElement?.elt?.parentElement;
    const w = el?.clientWidth || 400;
    p.createCanvas(w, height);
    for (let i = 0; i < count; i++) {
      balls.push({
        x: p.random(p.width),
        y: p.random(p.height / 2),
        vx: p.random(-3, 3),
        vy: p.random(0, 2),
        r: p.random(5, 15),
      });
    }
  };

  p.draw = () => {
    p.background(15, 15, 30);
    p.noStroke();
    for (const b of balls) {
      b.vy += 0.2;
      b.x += b.vx;
      b.y += b.vy;
      if (b.x < b.r || b.x > p.width - b.r) b.vx *= -0.8;
      if (b.y > p.height - b.r) { b.y = p.height - b.r; b.vy *= -0.8; }
      p.fill(129, 140, 248, 200);
      p.circle(b.x, b.y, b.r * 2);
    }
  };
}

function createAlgorithmSketch(p, params, steps, height) {
  p.isPlaying = true;
  p.currentStep = 0;
  p.stepDelay = params?.stepDelay || 2000;
  let lastSwitch = 0;

  p.setup = () => {
    const el = p._curElement?.elt?.parentElement;
    const w = el?.clientWidth || 400;
    p.createCanvas(w, height);
    p.textAlign(p.CENTER, p.CENTER);
  };

  p.draw = () => {
    p.background(15, 15, 30);
    if (!steps || steps.length === 0) {
      p.fill(100);
      p.textSize(14);
      p.text('No steps available', p.width / 2, p.height / 2);
      return;
    }
    
    // Automatically switch steps if playing
    if (p.isPlaying) {
      if (p.millis() - lastSwitch > p.stepDelay) {
        const nextStep = (p.currentStep + 1) % steps.length;
        p.currentStep = nextStep;
        lastSwitch = p.millis();
        if (p.onStepChange) {
          setTimeout(() => p.onStepChange(nextStep), 0);
        }
      }
    } else {
      lastSwitch = p.millis(); // Keep timer fresh
    }

    const step = steps[p.currentStep];
    if (!step) return;
    
    // Draw wrapped description box at the top
    p.fill(255);
    p.noStroke();
    p.textSize(12);
    p.textAlign(p.CENTER, p.TOP);
    p.text(step.description, 20, 15, p.width - 40, 60);

    const state = step.state || {};
    const keys = Object.keys(state);
    if (keys.length === 0) return;

    // Calculate maximum absolute value across all keys to normalize heights
    const maxVal = Math.max(...keys.map(k => Math.abs(parseFloat(state[k]) || 0)), 1);

    const chartAreaH = p.height - 130;
    const chartYBottom = p.height - 50;
    const barW = Math.min(45, (p.width - 50) / Math.max(keys.length, 1));
    const startX = (p.width - (keys.length * (barW + 8) - 8)) / 2;

    keys.forEach((key, i) => {
      const val = parseFloat(state[key]) || 0;
      const barH = p.map(Math.abs(val), 0, maxVal, 5, chartAreaH);
      
      // Color-coding: positive values (emerald), negative values (rose)
      if (val >= 0) {
        p.fill(52, 211, 153); // emerald-400
      } else {
        p.fill(248, 113, 113); // red-400
      }
      p.noStroke();
      p.rect(startX + i * (barW + 8), chartYBottom - barH, barW, barH, 4);

      // Value label on top of the bar
      p.fill(226, 232, 240);
      p.textSize(9);
      p.textAlign(p.CENTER, p.BOTTOM);
      p.text(val.toFixed(2), startX + i * (barW + 8) + barW / 2, chartYBottom - barH - 4);

      // Key label rotated at 25 degrees under the bar to prevent overlap
      p.push();
      p.translate(startX + i * (barW + 8) + barW / 2, chartYBottom + 8);
      p.rotate(p.radians(25));
      p.textAlign(p.LEFT, p.CENTER);
      p.fill(148, 163, 184);
      p.textSize(10);
      p.text(key.substring(0, 10), 0, 0);
      p.pop();
    });
  };
}

export default function P5Simulation({ spec, isExpanded = false }) {
  const ref = useRef(null);
  const p5Ref = useRef(null);
  const [isPlaying, setIsPlaying] = useState(true);
  const [currentStep, setCurrentStep] = useState(0);
  const numSteps = spec.steps?.length || 0;

  useEffect(() => {
    if (!ref.current || !spec) return;

    // Reset local steps on spec changes
    setCurrentStep(0);
    setIsPlaying(true);

    const height = isExpanded ? 450 : 280;

    const sketch = (p) => {
      p.isPlaying = true;
      p.currentStep = 0;
      p.onStepChange = (stepIdx) => {
        setCurrentStep(stepIdx);
      };

      switch (spec.simType) {
        case 'particles': createParticlesSketch(p, spec.params, height); break;
        case 'physics': createPhysicsSketch(p, spec.params, height); break;
        case 'algorithm-steps': createAlgorithmSketch(p, spec.params, spec.steps, height); break;
        default: createParticlesSketch(p, spec.params, height);
      }
    };

    p5Ref.current = new p5(sketch, ref.current);

    const resizeObserver = new ResizeObserver(() => {
      const width = ref.current?.clientWidth || 400;
      if (p5Ref.current && p5Ref.current.resizeCanvas) {
        p5Ref.current.resizeCanvas(width, height);
      }
    });
    resizeObserver.observe(ref.current);

    return () => {
      resizeObserver.disconnect();
      if (p5Ref.current) {
        p5Ref.current.remove();
        p5Ref.current = null;
      }
    };
  }, [spec, isExpanded]);

  // Synchronize playing and currentStep states into the running p5 instance
  useEffect(() => {
    if (p5Ref.current) {
      p5Ref.current.isPlaying = isPlaying;
    }
  }, [isPlaying]);

  useEffect(() => {
    if (p5Ref.current && p5Ref.current.currentStep !== currentStep) {
      p5Ref.current.currentStep = currentStep;
    }
  }, [currentStep]);

  const handlePlayPause = () => {
    setIsPlaying(!isPlaying);
  };

  const handleRestart = () => {
    setCurrentStep(0);
    setIsPlaying(true);
  };

  const handlePrev = () => {
    setIsPlaying(false);
    setCurrentStep((prev) => (prev - 1 + numSteps) % numSteps);
  };

  const handleNext = () => {
    setIsPlaying(false);
    setCurrentStep((prev) => (prev + 1) % numSteps);
  };

  return (
    <div className="w-full my-3 flex flex-col items-center">
      <div ref={ref} className="w-full flex justify-center" />
      
      {spec.simType === 'algorithm-steps' && numSteps > 0 && (
        <div className="mt-4 w-full max-w-sm flex flex-col items-center gap-2.5 p-3 bg-dark-950/40 rounded-2xl border border-dark-800">
          <div className="flex items-center justify-between w-full px-1 text-[11px] text-slate-400">
            <span>Simulation Progress</span>
            <span className="font-semibold text-indigo-400">Step {currentStep + 1} of {numSteps}</span>
          </div>
          
          <div className="w-full bg-dark-800 h-1.5 rounded-full overflow-hidden">
            <div 
              className="bg-indigo-500 h-full transition-all duration-300"
              style={{ width: `${((currentStep + 1) / numSteps) * 100}%` }}
            />
          </div>
          
          <div className="flex items-center gap-4 mt-1">
            <button 
              onClick={handleRestart}
              title="Restart"
              className="p-1.5 hover:text-white text-slate-400 hover:bg-dark-800 rounded-lg transition-all"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
            
            <button 
              onClick={handlePrev}
              title="Previous Step"
              className="p-1.5 hover:text-white text-slate-400 hover:bg-dark-800 rounded-lg transition-all"
            >
              <ChevronLeft className="w-4.5 h-4.5" />
            </button>
            
            <button 
              onClick={handlePlayPause}
              title={isPlaying ? "Pause" : "Play"}
              className="p-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-full transition-all shadow-lg shadow-indigo-600/20 active:scale-95"
            >
              {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4 fill-white" />}
            </button>
            
            <button 
              onClick={handleNext}
              title="Next Step"
              className="p-1.5 hover:text-white text-slate-400 hover:bg-dark-800 rounded-lg transition-all"
            >
              <ChevronRight className="w-4.5 h-4.5" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
