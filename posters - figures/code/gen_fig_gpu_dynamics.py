#!/usr/bin/env python3
"""Generate an illustrative GPU dynamics figure for the motivation section."""
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

OUTPUT_PATH = Path(__file__).resolve().parents[1] / "figures" / "fig1_gpu_power_trace_and_breakdown.png"

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5), gridspec_kw={'width_ratios': [2, 1]})
fig.patch.set_facecolor('white')

# ============ LEFT: GPU Power Draw Time Series ============
np.random.seed(42)
t = np.linspace(0, 200, 2000)

# Simulate GPU training power trace: high during compute, low during communication
power = np.ones_like(t) * 0.82
# Add periodic drops (communication phases)
for center in np.arange(10, 200, 15):
    mask = (t > center - 1.5) & (t < center + 1.5)
    power[mask] = 0.1 + 0.05 * np.random.randn(mask.sum())
# Add some noise
power += 0.03 * np.random.randn(len(t))
power = np.clip(power, 0.05, 1.0)
# Add occasional deeper drops
for center in [45, 90, 135, 175]:
    mask = (t > center - 3) & (t < center + 3)
    power[mask] = 0.15 + 0.05 * np.random.randn(mask.sum())

power = np.clip(power, 0.0, 1.0)

ax1.plot(t, power, color='#1565C0', linewidth=0.6, alpha=0.9)
ax1.set_xlabel('Time (s)', fontsize=11)
ax1.set_ylabel('Normalized GPU Power', fontsize=11)
ax1.set_title('Illustrative GPU Power Trace During Training', fontsize=13, fontweight='bold', color='#333')
ax1.set_xlim(0, 200)
ax1.set_ylim(0, 1.05)
ax1.set_yticks([0, 0.2, 0.4, 0.6, 0.8, 1.0])
ax1.grid(True, alpha=0.3)

# Annotations
ax1.annotate('Compute\nphase', xy=(60, 0.85), fontsize=9, color='#1565C0',
             fontweight='bold', ha='center')
ax1.annotate('Comm.\nphase', xy=(25, 0.25), fontsize=9, color='#C62828',
             fontweight='bold', ha='center',
             arrowprops=dict(arrowstyle='->', color='#C62828', lw=1.2),
             xytext=(30, 0.45))

# Source
ax1.text(0.02, 0.02, 'Illustrative trace informed by public AI-training workload discussions',
         transform=ax1.transAxes, fontsize=7, color='gray', style='italic')

# ============ RIGHT: Server Power Breakdown Pie ============
labels = ['GPU\n(~65%)', 'CPU\n(~27%)', 'Other\n(~8%)']
sizes = [65, 27, 8]
colors = ['#006B5E', '#1565C0', '#999999']
explode = (0.05, 0, 0)

wedges, texts, autotexts = ax2.pie(sizes, labels=labels, colors=colors, explode=explode,
                                     autopct='%1.0f%%', startangle=90,
                                     textprops={'fontsize': 10},
                                     pctdistance=0.6)
for autotext in autotexts:
    autotext.set_fontsize(10)
    autotext.set_fontweight('bold')
    autotext.set_color('white')

ax2.set_title('GB200 Server Power\nBreakdown', fontsize=13, fontweight='bold', color='#333')

plt.tight_layout(pad=1.5)
OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
plt.savefig(OUTPUT_PATH, dpi=220, bbox_inches='tight', facecolor='white', edgecolor='none')
plt.close()
print(f"GPU dynamics figure saved to {OUTPUT_PATH}")
