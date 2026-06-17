import { useEffect, useRef, useState, useCallback } from 'react';
import * as d3 from 'd3';
import './WigglePlot.css';

export default function WigglePlot({
  data,
  metadata,
  width = 1200,
  height = 700,
  traceSpacing = 2,
  amplitudeScale = 1.0,
  onViewChange,
  viewState,
}) {
  const svgRef = useRef(null);
  const containerRef = useRef(null);
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [viewOffset, setViewOffset] = useState({ x: 0, y: 0 });
  const [zoom, setZoom] = useState(1);

  useEffect(() => {
    if (viewState) {
      setViewOffset({ x: viewState.offsetX || 0, y: viewState.offsetY || 0 });
      setZoom(viewState.zoom || 1);
    }
  }, [viewState]);

  const normalizeAmplitude = useCallback((value, minAmp, maxAmp) => {
    const maxAbs = Math.max(Math.abs(minAmp), Math.abs(maxAmp));
    if (maxAbs === 0) return 0;
    return (value / maxAbs) * amplitudeScale;
  }, [amplitudeScale]);

  useEffect(() => {
    if (!data || !data.data || data.data.length === 0) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    const traces = data.data;
    const traceCount = traces.length;
    const sampleCount = traces[0].length;

    const traceWidth = traceSpacing + 1;
    const totalWidth = traceCount * traceWidth;
    const totalHeight = sampleCount;

    const scaledWidth = totalWidth * zoom;
    const scaledHeight = totalHeight * zoom;

    svg.attr('width', width)
       .attr('height', height)
       .attr('viewBox', `${-viewOffset.x} ${-viewOffset.y} ${width} ${height}`);

    const defs = svg.append('defs');

    const g = svg.append('g')
      .attr('transform', `scale(${zoom})`);

    const minAmp = data.min_amplitude;
    const maxAmp = data.max_amplitude;

    for (let i = 0; i < traceCount; i++) {
      const trace = traces[i];
      const xBase = i * traceWidth + traceSpacing / 2;

      const pathData = [];
      const areaData = [];

      for (let j = 0; j < sampleCount; j++) {
        const value = normalizeAmplitude(trace[j], minAmp, maxAmp);
        const xPos = xBase + value * traceWidth * 0.4;
        const yPos = j;

        pathData.push(`${j === 0 ? 'M' : 'L'} ${xPos} ${yPos}`);

        if (value > 0) {
          areaData.push({ value, x: xPos, y: yPos, baseX: xBase });
        }
      }

      const traceGroup = g.append('g')
        .attr('class', 'trace-group')
        .attr('transform', `translate(0, 0)`);

      const areaPath = traceGroup.append('path')
        .attr('class', 'wiggle-area')
        .attr('fill', '#000000');

      let areaD = '';
      let inPositive = false;
      let areaStartY = 0;

      for (let j = 0; j < sampleCount; j++) {
        const value = normalizeAmplitude(trace[j], minAmp, maxAmp);
        const xPos = xBase + value * traceWidth * 0.4;
        const yPos = j;

        if (value > 0 && !inPositive) {
          inPositive = true;
          areaStartY = yPos;
          areaD = `M ${xBase} ${yPos}`;
        }

        if (inPositive) {
          areaD += ` L ${xPos} ${yPos}`;
        }

        if (value <= 0 && inPositive) {
          inPositive = false;
          areaD += ` L ${xBase} ${yPos} Z`;
          traceGroup.append('path')
            .attr('class', 'wiggle-area')
            .attr('fill', '#000000')
            .attr('d', areaD);
          areaD = '';
        }
      }

      if (inPositive && areaD) {
        areaD += ` L ${xBase} ${sampleCount} Z`;
        traceGroup.append('path')
          .attr('class', 'wiggle-area')
          .attr('fill', '#000000')
          .attr('d', areaD);
      }

      traceGroup.append('path')
        .attr('class', 'wiggle-line')
        .attr('fill', 'none')
        .attr('stroke', '#000000')
        .attr('stroke-width', 0.5 / zoom)
        .attr('d', pathData.join(' '));
    }

    const xAxisScale = d3.scaleLinear()
      .domain([0, traceCount])
      .range([0, totalWidth]);

    const yAxisScale = d3.scaleLinear()
      .domain([0, data.z_end])
      .range([0, totalHeight]);

    const xAxis = d3.axisBottom(xAxisScale)
      .ticks(10)
      .tickFormat(d => {
        if (data.inline_start === data.inline_end) {
          return Math.round(data.crossline_start + d / traceCount * (data.crossline_end - data.crossline_start));
        } else {
          return Math.round(data.inline_start + d / traceCount * (data.inline_end - data.inline_start));
        }
      });

    const yAxis = d3.axisLeft(yAxisScale)
      .ticks(10)
      .tickFormat(d => d.toFixed(0));

    svg.append('g')
      .attr('class', 'x-axis')
      .attr('transform', `translate(0, ${totalHeight})`)
      .call(xAxis);

    svg.append('g')
      .attr('class', 'y-axis')
      .call(yAxis);

  }, [data, width, height, traceSpacing, normalizeAmplitude, viewOffset, zoom]);

  const handleMouseDown = useCallback((e) => {
    setIsDragging(true);
    setDragStart({ x: e.clientX - viewOffset.x, y: e.clientY - viewOffset.y });
  }, [viewOffset]);

  const handleMouseMove = useCallback((e) => {
    if (!isDragging) return;
    
    const newOffset = {
      x: e.clientX - dragStart.x,
      y: e.clientY - dragStart.y,
    };
    setViewOffset(newOffset);
    
    if (onViewChange) {
      onViewChange({
        offsetX: newOffset.x,
        offsetY: newOffset.y,
        zoom,
      });
    }
  }, [isDragging, dragStart, zoom, onViewChange]);

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
  }, []);

  const handleWheel = useCallback((e) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? 0.9 : 1.1;
    const newZoom = Math.max(0.5, Math.min(5, zoom * delta));
    setZoom(newZoom);
    
    if (onViewChange) {
      onViewChange({
        offsetX: viewOffset.x,
        offsetY: viewOffset.y,
        zoom: newZoom,
      });
    }
  }, [zoom, viewOffset, onViewChange]);

  return (
    <div 
      ref={containerRef}
      className="wiggle-plot-container"
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
      onWheel={handleWheel}
      style={{ cursor: isDragging ? 'grabbing' : 'grab' }}
    >
      <svg ref={svgRef} className="wiggle-svg" />
      
      <div className="wiggle-info">
        <div>道数: {data?.trace_count || 0}</div>
        <div>采样点: {data?.sample_count || 0}</div>
        <div>缩放: {(zoom * 100).toFixed(0)}%</div>
        <div>振幅范围: [{data?.min_amplitude?.toFixed(2)}, {data?.max_amplitude?.toFixed(2)}]</div>
      </div>
    </div>
  );
}
