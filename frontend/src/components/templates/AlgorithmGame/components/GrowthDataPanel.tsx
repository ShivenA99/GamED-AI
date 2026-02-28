'use client';

interface GrowthDataPanelProps {
  inputSizes: number[];
  operationCounts: number[];
  theme?: 'dark' | 'light';
}

export default function GrowthDataPanel({
  inputSizes,
  operationCounts,
  theme = 'dark',
}: GrowthDataPanelProps) {
  const isDark = theme === 'dark';

  // SVG chart dimensions
  const width = 360;
  const height = 200;
  const padding = { top: 20, right: 20, bottom: 30, left: 50 };
  const plotW = width - padding.left - padding.right;
  const plotH = height - padding.top - padding.bottom;

  const maxX = Math.max(...inputSizes);
  const maxY = Math.max(...operationCounts);

  const scaleX = (v: number) => padding.left + (v / maxX) * plotW;
  const scaleY = (v: number) => padding.top + plotH - (v / maxY) * plotH;

  const pathD = inputSizes
    .map((x, i) => {
      const cx = scaleX(x);
      const cy = scaleY(operationCounts[i]);
      return `${i === 0 ? 'M' : 'L'}${cx},${cy}`;
    })
    .join(' ');

  // Y-axis ticks (5 ticks)
  const yTicks = Array.from({ length: 5 }, (_, i) =>
    Math.round((maxY / 4) * i),
  );

  return (
    <div className={`rounded-lg border ${isDark ? 'border-gray-700 bg-gray-900' : 'border-gray-200 bg-white'}`}>
      <div className={`px-3 py-2 border-b text-xs font-medium ${isDark ? 'border-gray-700 bg-gray-800 text-gray-400' : 'border-gray-200 bg-gray-50 text-gray-500'}`}>
        Growth Data — How does operation count grow with input size?
      </div>

      {/* SVG chart */}
      <div className="p-3 flex justify-center">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="w-full max-w-[360px]"
          role="img"
          aria-label="Growth data chart"
        >
          {/* Grid lines */}
          {yTicks.map((t) => (
            <line
              key={t}
              x1={padding.left}
              y1={scaleY(t)}
              x2={width - padding.right}
              y2={scaleY(t)}
              stroke={isDark ? '#374151' : '#e5e7eb'}
              strokeDasharray="4 2"
            />
          ))}

          {/* Y-axis labels */}
          {yTicks.map((t) => (
            <text
              key={`yl-${t}`}
              x={padding.left - 6}
              y={scaleY(t) + 4}
              textAnchor="end"
              className={`text-[10px] ${isDark ? 'fill-gray-500' : 'fill-gray-400'}`}
            >
              {t >= 1000 ? `${(t / 1000).toFixed(0)}k` : t}
            </text>
          ))}

          {/* X-axis labels */}
          {inputSizes.map((x) => (
            <text
              key={`xl-${x}`}
              x={scaleX(x)}
              y={height - 6}
              textAnchor="middle"
              className={`text-[10px] ${isDark ? 'fill-gray-500' : 'fill-gray-400'}`}
            >
              {x}
            </text>
          ))}

          {/* Axis labels */}
          <text
            x={width / 2}
            y={height}
            textAnchor="middle"
            className={`text-[10px] ${isDark ? 'fill-gray-400' : 'fill-gray-500'}`}
          >
            Input Size (n)
          </text>

          {/* Data line */}
          <path
            d={pathD}
            fill="none"
            stroke={isDark ? '#60a5fa' : '#3b82f6'}
            strokeWidth={2}
            strokeLinecap="round"
            strokeLinejoin="round"
          />

          {/* Data points */}
          {inputSizes.map((x, i) => (
            <circle
              key={i}
              cx={scaleX(x)}
              cy={scaleY(operationCounts[i])}
              r={4}
              fill={isDark ? '#60a5fa' : '#3b82f6'}
            />
          ))}
        </svg>
      </div>

      {/* Data table */}
      <div className={`px-3 pb-3`}>
        <table className="w-full text-xs">
          <thead>
            <tr className={isDark ? 'text-gray-400' : 'text-gray-500'}>
              <th className="text-left py-1 px-2">n (input)</th>
              {inputSizes.map((x) => (
                <th key={x} className="text-right py-1 px-2">
                  {x}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            <tr className={isDark ? 'text-gray-200' : 'text-gray-800'}>
              <td className="py-1 px-2 font-medium">ops</td>
              {operationCounts.map((c, i) => (
                <td key={i} className="text-right py-1 px-2">
                  {c.toLocaleString()}
                </td>
              ))}
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
