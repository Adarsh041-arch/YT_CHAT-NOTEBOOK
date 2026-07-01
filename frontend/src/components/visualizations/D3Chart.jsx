import { useRef, useEffect } from 'react';
import * as d3 from 'd3';

const MARGIN = { top: 35, right: 20, bottom: 55, left: 60 };

function drawBar(svg, data, width, height, xLabel, yLabel, tooltip, container) {
  const innerW = width - MARGIN.left - MARGIN.right;
  const innerH = height - MARGIN.top - MARGIN.bottom;
  const g = svg.append('g').attr('transform', `translate(${MARGIN.left},${MARGIN.top})`);

  const x = d3.scaleBand()
    .domain(data.map(d => d.label))
    .range([0, innerW])
    .padding(0.35);

  const y = d3.scaleLinear()
    .domain([0, d3.max(data, d => d.value) || 1])
    .nice()
    .range([innerH, 0]);

  // Y Grid lines
  g.append('g')
    .attr('class', 'grid-lines')
    .style('stroke', '#334155')
    .style('stroke-opacity', 0.25)
    .style('stroke-dasharray', '3 3')
    .call(d3.axisLeft(y).tickSize(-innerW).tickFormat(''));

  g.append('g')
    .call(d3.axisLeft(y))
    .selectAll('text')
    .style('fill', '#94a3b8');

  g.append('g')
    .attr('transform', `translate(0,${innerH})`)
    .call(d3.axisBottom(x))
    .selectAll('text')
    .attr('transform', 'rotate(-25)')
    .style('text-anchor', 'end')
    .style('fill', '#94a3b8')
    .attr('font-size', '10px');

  g.selectAll('rect')
    .data(data)
    .join('rect')
    .attr('x', d => x(d.label))
    .attr('width', x.bandwidth())
    .attr('rx', 4)
    .attr('fill', '#818cf8')
    .attr('y', innerH)
    .attr('height', 0)
    .on('mouseover', function (event, d) {
      d3.select(this).transition().duration(100).attr('fill', '#6366f1');
      tooltip.style('visibility', 'visible')
        .html(`<div class="font-semibold text-slate-200 mb-0.5">${d.label}</div><div class="text-indigo-400 font-bold">${d.value}</div>`);
    })
    .on('mousemove', function (event) {
      const [mx, my] = d3.pointer(event, container);
      tooltip.style('left', `${mx + 12}px`).style('top', `${my - 12}px`);
    })
    .on('mouseleave', function (event) {
      d3.select(this).transition().duration(100).attr('fill', '#818cf8');
      tooltip.style('visibility', 'hidden');
    })
    .transition()
    .duration(800)
    .ease(d3.easeCubicOut)
    .attr('y', d => y(d.value))
    .attr('height', d => innerH - y(d.value));

  if (xLabel) svg.append('text').text(xLabel)
    .attr('x', width / 2).attr('y', height - 5)
    .attr('text-anchor', 'middle').attr('fill', '#64748b').attr('font-size', '11px');
  if (yLabel) svg.append('text').text(yLabel)
    .attr('x', 12).attr('y', MARGIN.top + innerH / 2)
    .attr('text-anchor', 'middle').attr('fill', '#64748b').attr('font-size', '11px')
    .attr('transform', `rotate(-90,12,${MARGIN.top + innerH / 2})`);
}

function drawLine(svg, data, width, height, xLabel, yLabel, tooltip, container) {
  const innerW = width - MARGIN.left - MARGIN.right;
  const innerH = height - MARGIN.top - MARGIN.bottom;
  const g = svg.append('g').attr('transform', `translate(${MARGIN.left},${MARGIN.top})`);

  const x = d3.scalePoint()
    .domain(data.map(d => d.label))
    .range([0, innerW]);

  const y = d3.scaleLinear()
    .domain([0, d3.max(data, d => d.value) || 1])
    .nice()
    .range([innerH, 0]);

  // Grid lines
  g.append('g')
    .attr('class', 'grid-lines')
    .style('stroke', '#334155')
    .style('stroke-opacity', 0.25)
    .style('stroke-dasharray', '3 3')
    .call(d3.axisLeft(y).tickSize(-innerW).tickFormat(''));

  g.append('g')
    .call(d3.axisLeft(y))
    .selectAll('text')
    .style('fill', '#94a3b8');

  g.append('g')
    .attr('transform', `translate(0,${innerH})`)
    .call(d3.axisBottom(x))
    .selectAll('text')
    .style('fill', '#94a3b8')
    .attr('font-size', '10px');

  const line = d3.line()
    .x(d => x(d.label))
    .y(d => y(d.value))
    .curve(d3.curveMonotoneX);

  const path = g.append('path')
    .datum(data)
    .attr('d', line)
    .attr('fill', 'none')
    .attr('stroke', '#818cf8')
    .attr('stroke-width', 2.5);

  const totalLength = path.node().getTotalLength();

  path
    .attr('stroke-dasharray', `${totalLength} ${totalLength}`)
    .attr('stroke-dashoffset', totalLength)
    .transition()
    .duration(1000)
    .ease(d3.easeCubicOut)
    .attr('stroke-dashoffset', 0);

  g.selectAll('circle')
    .data(data)
    .join('circle')
    .attr('cx', d => x(d.label))
    .attr('cy', d => y(d.value))
    .attr('r', 0)
    .attr('fill', '#818cf8')
    .attr('stroke', '#1e1b4b')
    .attr('stroke-width', 2)
    .on('mouseover', function (event, d) {
      d3.select(this).transition().duration(100).attr('r', 7).attr('fill', '#6366f1');
      tooltip.style('visibility', 'visible')
        .html(`<div class="font-semibold text-slate-200 mb-0.5">${d.label}</div><div class="text-indigo-400 font-bold">${d.value}</div>`);
    })
    .on('mousemove', function (event) {
      const [mx, my] = d3.pointer(event, container);
      tooltip.style('left', `${mx + 12}px`).style('top', `${my - 12}px`);
    })
    .on('mouseleave', function (event) {
      d3.select(this).transition().duration(100).attr('r', 5).attr('fill', '#818cf8');
      tooltip.style('visibility', 'hidden');
    })
    .transition()
    .delay(700)
    .duration(300)
    .attr('r', 5);

  if (xLabel) svg.append('text').text(xLabel)
    .attr('x', width / 2).attr('y', height - 5)
    .attr('text-anchor', 'middle').attr('fill', '#64748b').attr('font-size', '11px');
  if (yLabel) svg.append('text').text(yLabel)
    .attr('x', 12).attr('y', MARGIN.top + innerH / 2)
    .attr('text-anchor', 'middle').attr('fill', '#64748b').attr('font-size', '11px')
    .attr('transform', `rotate(-90,12,${MARGIN.top + innerH / 2})`);
}

function drawScatter(svg, data, width, height, xLabel, yLabel, tooltip, container) {
  const innerW = width - MARGIN.left - MARGIN.right;
  const innerH = height - MARGIN.top - MARGIN.bottom;
  const g = svg.append('g').attr('transform', `translate(${MARGIN.left},${MARGIN.top})`);

  const x = d3.scalePoint()
    .domain(data.map(d => d.label))
    .range([0, innerW]);

  const y = d3.scaleLinear()
    .domain([0, d3.max(data, d => d.value) || 1])
    .nice()
    .range([innerH, 0]);

  // Grid lines
  g.append('g')
    .attr('class', 'grid-lines')
    .style('stroke', '#334155')
    .style('stroke-opacity', 0.25)
    .style('stroke-dasharray', '3 3')
    .call(d3.axisLeft(y).tickSize(-innerW).tickFormat(''));

  g.append('g')
    .call(d3.axisLeft(y))
    .selectAll('text')
    .style('fill', '#94a3b8');

  g.append('g')
    .attr('transform', `translate(0,${innerH})`)
    .call(d3.axisBottom(x))
    .selectAll('text')
    .attr('transform', 'rotate(-25)')
    .style('text-anchor', 'end')
    .style('fill', '#94a3b8')
    .attr('font-size', '10px');

  g.selectAll('circle')
    .data(data)
    .join('circle')
    .attr('cx', d => x(d.label))
    .attr('cy', d => y(d.value))
    .attr('r', 0)
    .attr('fill', '#818cf8')
    .attr('opacity', 0.85)
    .attr('stroke', '#6366f1')
    .attr('stroke-width', 1.5)
    .on('mouseover', function (event, d) {
      d3.select(this).transition().duration(100).attr('r', 8).attr('fill', '#6366f1');
      tooltip.style('visibility', 'visible')
        .html(`<div class="font-semibold text-slate-200 mb-0.5">${d.label}</div><div class="text-indigo-400 font-bold">${d.value}</div>`);
    })
    .on('mousemove', function (event) {
      const [mx, my] = d3.pointer(event, container);
      tooltip.style('left', `${mx + 12}px`).style('top', `${my - 12}px`);
    })
    .on('mouseleave', function (event) {
      d3.select(this).transition().duration(100).attr('r', 6).attr('fill', '#818cf8');
      tooltip.style('visibility', 'hidden');
    })
    .transition()
    .duration(600)
    .attr('r', 6);

  if (xLabel) svg.append('text').text(xLabel)
    .attr('x', width / 2).attr('y', height - 5)
    .attr('text-anchor', 'middle').attr('fill', '#64748b').attr('font-size', '11px');
  if (yLabel) svg.append('text').text(yLabel)
    .attr('x', 12).attr('y', MARGIN.top + innerH / 2)
    .attr('text-anchor', 'middle').attr('fill', '#64748b').attr('font-size', '11px')
    .attr('transform', `rotate(-90,12,${MARGIN.top + innerH / 2})`);
}

function drawPie(svg, data, width, height, tooltip, container) {
  const radius = Math.min(width, height) / 2 - 35;
  const g = svg.append('g')
    .attr('transform', `translate(${width / 2},${height / 2})`);

  const color = d3.scaleOrdinal()
    .domain(data.map(d => d.label))
    .range(['#818cf8', '#34d399', '#f87171', '#fbbf24', '#a78bfa', '#22d3ee', '#f472b6']);

  const pie = d3.pie().value(d => d.value).sort(null);
  const arc = d3.arc().innerRadius(0).outerRadius(radius);

  g.selectAll('path')
    .data(pie(data))
    .join('path')
    .attr('fill', d => color(d.data.label))
    .attr('stroke', '#0f172a')
    .attr('stroke-width', 2.5)
    .on('mouseover', function (event, d) {
      d3.select(this).transition().duration(150).attr('transform', 'scale(1.04)');
      tooltip.style('visibility', 'visible')
        .html(`<div class="font-semibold text-slate-200 mb-0.5">${d.data.label}</div><div class="text-indigo-400 font-bold">${d.data.value}</div>`);
    })
    .on('mousemove', function (event) {
      const [mx, my] = d3.pointer(event, container);
      tooltip.style('left', `${mx + 12}px`).style('top', `${my - 12}px`);
    })
    .on('mouseleave', function (event) {
      d3.select(this).transition().duration(150).attr('transform', 'scale(1)');
      tooltip.style('visibility', 'hidden');
    })
    .transition()
    .duration(800)
    .attrTween('d', function (d) {
      const i = d3.interpolate({ startAngle: 0, endAngle: 0 }, d);
      return function (t) {
        return arc(i(t));
      };
    });

  // Fade labels in after slices are rendered
  g.selectAll('text')
    .data(pie(data))
    .join('text')
    .attr('transform', d => `translate(${arc.centroid(d)})`)
    .attr('text-anchor', 'middle')
    .attr('fill', '#0f172a')
    .attr('font-size', '10px')
    .attr('font-weight', '700')
    .attr('opacity', 0)
    .text(d => d.data.label)
    .transition()
    .delay(800)
    .duration(300)
    .attr('opacity', 1);
}

export default function D3Chart({ spec, isExpanded = false }) {
  const ref = useRef(null);

  useEffect(() => {
    if (!ref.current) return;
    const container = ref.current;

    const draw = () => {
      // Clear previous rendering
      d3.select(container).selectAll('svg').remove();
      d3.select(container).selectAll('.d3-tooltip').remove();

      const width = container.clientWidth || 400;
      const height = isExpanded ? 450 : 280;

      // Create absolute tooltip scoped to container
      const tooltip = d3.select(container)
        .append('div')
        .attr('class', 'd3-tooltip')
        .style('position', 'absolute')
        .style('visibility', 'hidden')
        .style('background', '#0b0f19')
        .style('color', '#f8fafc')
        .style('padding', '8px 12px')
        .style('border', '1px solid #334155')
        .style('border-radius', '8px')
        .style('font-size', '11px')
        .style('pointer-events', 'none')
        .style('z-index', '100')
        .style('box-shadow', '0 10px 15px -3px rgba(0, 0, 0, 0.3)');

      const svg = d3.select(container)
        .append('svg')
        .attr('width', width)
        .attr('height', height);

      if (spec.title) {
        svg.append('text').text(spec.title)
          .attr('x', width / 2).attr('y', 20)
          .attr('text-anchor', 'middle')
          .attr('fill', '#f1f5f9')
          .attr('font-size', '14px')
          .attr('font-weight', '600');
      }

      switch (spec.chartType) {
        case 'bar': drawBar(svg, spec.data, width, height, spec.xLabel, spec.yLabel, tooltip, container); break;
        case 'line': drawLine(svg, spec.data, width, height, spec.xLabel, spec.yLabel, tooltip, container); break;
        case 'scatter': drawScatter(svg, spec.data, width, height, spec.xLabel, spec.yLabel, tooltip, container); break;
        case 'pie': drawPie(svg, spec.data, width, height, tooltip, container); break;
      }
    };

    const resizeObserver = new ResizeObserver(() => {
      draw();
    });
    resizeObserver.observe(container);

    return () => {
      resizeObserver.disconnect();
      d3.select(container).selectAll('svg').remove();
      d3.select(container).selectAll('.d3-tooltip').remove();
    };
  }, [spec, isExpanded]);

  return <div ref={ref} className={`w-full my-3 relative ${isExpanded ? 'h-[450px]' : 'h-[280px]'}`} />;
}
