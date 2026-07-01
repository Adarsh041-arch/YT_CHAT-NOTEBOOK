import { useRef, useEffect } from 'react';
import * as d3 from 'd3';

export default function D3Graph({ spec, isExpanded = false }) {
  const ref = useRef(null);

  useEffect(() => {
    if (!ref.current) return;
    const container = ref.current;
    let simulation = null;

    const draw = () => {
      // Clear previous simulation and elements
      if (simulation) {
        simulation.stop();
        simulation = null;
      }
      d3.select(container).selectAll('svg').remove();
      d3.select(container).selectAll('.d3-tooltip').remove();

      const width = container.clientWidth || 400;
      const height = isExpanded ? 500 : 350;

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
          .attr('x', width / 2).attr('y', 22)
          .attr('text-anchor', 'middle')
          .attr('fill', '#f1f5f9')
          .attr('font-size', '14px')
          .attr('font-weight', '600');
      }

      const g = svg.append('g');

      // Pan and Zoom Behavior
      const zoom = d3.zoom()
        .scaleExtent([0.3, 3])
        .on('zoom', (event) => {
          g.attr('transform', event.transform);
        });
      svg.call(zoom);

      const nodes = spec.nodes.map(n => ({ ...n }));
      const nodeMap = {};
      nodes.forEach(n => { nodeMap[n.id] = n; });

      const edges = spec.edges.map(e => ({
        source: typeof e.source === 'object' ? e.source.id : e.source,
        target: typeof e.target === 'object' ? e.target.id : e.target,
        label: e.label || '',
      }));

      // Build Adjacency List for highlighting neighbors
      const adjacencyList = {};
      nodes.forEach(n => { adjacencyList[n.id] = new Set(); });
      edges.forEach(e => {
        if (adjacencyList[e.source]) adjacencyList[e.source].add(e.target);
        if (adjacencyList[e.target]) adjacencyList[e.target].add(e.source);
      });

      const linkElements = g.append('g')
        .selectAll('line')
        .data(edges)
        .join('line')
        .attr('stroke', '#334155')
        .attr('stroke-width', 1.5)
        .attr('stroke-opacity', 0.6);

      const nodeElements = g.append('g')
        .selectAll('g')
        .data(nodes)
        .join('g')
        .call(d3.drag()
          .on('start', (event, d) => {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
          })
          .on('drag', (event, d) => {
            d.fx = event.x;
            d.fy = event.y;
          })
          .on('end', (event, d) => {
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
          })
        );

      nodeElements.append('circle')
        .attr('r', 8)
        .attr('fill', '#818cf8')
        .attr('stroke', '#6366f1')
        .attr('stroke-width', 2);

      nodeElements.append('text')
        .text(d => d.label)
        .attr('dx', 12)
        .attr('dy', 4)
        .attr('fill', '#cbd5e1')
        .attr('font-size', '11px')
        .style('pointer-events', 'none');

      // Hover Highlight Actions
      nodeElements
        .on('mouseover', function (event, d) {
          // Dim all nodes and labels
          nodeElements.selectAll('circle')
            .transition().duration(200)
            .attr('opacity', n => (n.id === d.id || adjacencyList[d.id].has(n.id)) ? 1 : 0.2);

          nodeElements.selectAll('text')
            .transition().duration(200)
            .attr('opacity', n => (n.id === d.id || adjacencyList[d.id].has(n.id)) ? 1 : 0.2);

          // Highlight selected node's circle
          d3.select(this).select('circle')
            .transition().duration(150)
            .attr('fill', '#34d399') // emerald
            .attr('r', 10);

          // Dim links and highlight connection lines
          linkElements
            .transition().duration(200)
            .attr('stroke', l => (l.source.id === d.id || l.target.id === d.id) ? '#6366f1' : '#334155')
            .attr('stroke-width', l => (l.source.id === d.id || l.target.id === d.id) ? 3 : 1.5)
            .attr('stroke-opacity', l => (l.source.id === d.id || l.target.id === d.id) ? 1 : 0.15);

          tooltip.style('visibility', 'visible')
            .html(`
              <div class="font-semibold text-slate-200 mb-0.5">${d.label}</div>
              <div class="text-indigo-400 font-medium">${adjacencyList[d.id].size} connections</div>
            `);
        })
        .on('mousemove', function (event) {
          const [mx, my] = d3.pointer(event, container);
          tooltip.style('left', `${mx + 12}px`).style('top', `${my - 12}px`);
        })
        .on('mouseleave', function (event) {
          // Reset everything
          nodeElements.selectAll('circle')
            .transition().duration(200)
            .attr('opacity', 1)
            .attr('fill', '#818cf8')
            .attr('r', 8);

          nodeElements.selectAll('text')
            .transition().duration(200)
            .attr('opacity', 1);

          linkElements
            .transition().duration(200)
            .attr('stroke', '#334155')
            .attr('stroke-width', 1.5)
            .attr('stroke-opacity', 0.6);

          tooltip.style('visibility', 'hidden');
        });

      simulation = d3.forceSimulation(nodes)
        .force('link', d3.forceLink(edges).id(d => d.id).distance(110))
        .force('charge', d3.forceManyBody().strength(-200))
        .force('center', d3.forceCenter(width / 2, height / 2 + 10))
        .force('collision', d3.forceCollide(30))
        .on('tick', () => {
          linkElements
            .attr('x1', d => d.source.x)
            .attr('y1', d => d.source.y)
            .attr('x2', d => d.target.x)
            .attr('y2', d => d.target.y);
          nodeElements.attr('transform', d => `translate(${d.x},${d.y})`);
        });
    };

    const resizeObserver = new ResizeObserver(() => {
      draw();
    });
    resizeObserver.observe(container);

    return () => {
      resizeObserver.disconnect();
      if (simulation) simulation.stop();
      d3.select(container).selectAll('svg').remove();
      d3.select(container).selectAll('.d3-tooltip').remove();
    };
  }, [spec, isExpanded]);

  return <div ref={ref} className={`w-full my-3 relative overflow-hidden ${isExpanded ? 'h-[500px]' : 'h-[350px]'}`} />;
}
