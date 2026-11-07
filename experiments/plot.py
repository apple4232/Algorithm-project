"""Write a simple SVG chart of completed-task median distances by size."""
import html
import json
import sys


def main():
    if len(sys.argv) != 3:
        raise SystemExit('usage: python -m experiments.plot SUMMARY.json OUTPUT.svg')
    with open(sys.argv[1], encoding='utf-8') as f:
        summary = json.load(f)
    names = sorted(summary)
    sizes = sorted({int(n) for result in summary.values() for n in result['by_n']})
    if not sizes:
        raise ValueError('no data')
    values = [data['median_distance_m'] for result in summary.values()
              for data in result['by_n'].values() if data['median_distance_m'] is not None]
    if not values:
        raise ValueError('no completed distances')
    maximum = max(values) or 1
    width, height, left, top = 900, 490, 75, 45
    plot_w, plot_h = 530, 350
    colors = ['#1f77b4', '#d62728', '#2ca02c', '#9467bd', '#ff7f0e', '#17becf', '#8c564b', '#e377c2', '#555555']
    x = lambda i: left + plot_w * i / max(len(sizes) - 1, 1)
    y = lambda value: top + plot_h * (1 - value / maximum)
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
           '<rect width="100%" height="100%" fill="white"/>',
           '<text x="75" y="23" font-family="sans-serif" font-size="16">Completed tasks: median route distance by item count</text>',
           f'<path d="M{left} {top} V{top+plot_h} H{left+plot_w}" fill="none" stroke="black"/>',
           '<text x="10" y="30" font-family="sans-serif" font-size="12">m</text>',
           f'<text x="{left+plot_w/2}" y="455" font-family="sans-serif" font-size="12">distinct item locations</text>']
    for i, n in enumerate(sizes):
        out.append(f'<text x="{x(i)}" y="{top+plot_h+20}" text-anchor="middle" font-family="sans-serif" font-size="12">{n}</text>')
    for step in range(5):
        value = maximum * step / 4
        out.append(f'<text x="{left-8}" y="{y(value)+4}" text-anchor="end" font-family="sans-serif" font-size="11">{value:.0f}</text>')
    for j, name in enumerate(names):
        color = colors[j % len(colors)]
        points = [(x(i), y(summary[name]['by_n'][str(n)]['median_distance_m'])) for i, n in enumerate(sizes)
                  if str(n) in summary[name]['by_n'] and summary[name]['by_n'][str(n)]['median_distance_m'] is not None]
        for px, py in points:
            out.append(f'<circle cx="{px:.2f}" cy="{py:.2f}" r="3" fill="{color}"/>')
        out.append(f'<polyline points="{" ".join(f"{px:.2f},{py:.2f}" for px, py in points)}" fill="none" stroke="{color}" stroke-width="1.5"/>')
        out.append(f'<text x="640" y="{65+j*22}" fill="{color}" font-family="sans-serif" font-size="12">{html.escape(name)}</text>')
    out.append('<text x="75" y="480" font-family="sans-serif" font-size="10">Failures excluded from distance medians; see summary for attempts and completion counts.</text></svg>')
    with open(sys.argv[2], 'x', encoding='utf-8') as f:
        f.write('\n'.join(out))


if __name__ == '__main__':
    main()
