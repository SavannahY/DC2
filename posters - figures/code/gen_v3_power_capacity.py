#!/usr/bin/env python3
"""Generate power-capacity comparison figure."""
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

OUTPUT_PATH = Path(__file__).resolve().parents[1] / "figures" / "fig4_power_capacity_ac_vs_dc.png"

fig, ax = plt.subplots(figsize=(16, 8))
fig.patch.set_facecolor('white')

# Data - same 500 MCM conductor, I = 380A
# P_AC = sqrt(3) * V_AC * I * cos(phi), cos(phi)=0.9
# P_DC = 2 * V_DC * I (bipolar)
categories = ['480V AC\n800V DC', '4.16 kV AC\n1.5 kV DC', '12.47 kV AC\n10 kV DC', '34.5 kV AC\n35 kV DC']
ac_vals = [0.3, 2.6, 7.8, 21.6]
dc_vals = [0.6, 1.1, 7.6, 26.6]

x = np.arange(len(categories))
width = 0.35

bars_ac = ax.bar(x - width/2, ac_vals, width, label='AC (3-phase)', color='#C62828', 
                  edgecolor='#8C1515', linewidth=1.2, alpha=0.9)
bars_dc = ax.bar(x + width/2, dc_vals, width, label='DC (bipolar)', color='#2E7D32',
                  edgecolor='#1B5E20', linewidth=1.2, alpha=0.9)

# Value labels
for bar, val in zip(bars_ac, ac_vals):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3, 
            f'{val}', ha='center', va='bottom', fontsize=16, fontweight='bold', color='#C62828')
for bar, val in zip(bars_dc, dc_vals):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3,
            f'{val}', ha='center', va='bottom', fontsize=16, fontweight='bold', color='#2E7D32')

ax.set_xlabel('Voltage Class', fontsize=18, fontweight='bold', labelpad=10)
ax.set_ylabel('Power Capacity (MW)', fontsize=18, fontweight='bold', labelpad=10)
ax.set_title('Power Capacity: AC vs. DC\n(Same 500 MCM Conductor, I = 380A)', 
             fontsize=22, fontweight='bold', pad=15)
ax.set_xticks(x)
ax.set_xticklabels(categories, fontsize=15, fontweight='bold')
ax.tick_params(axis='y', labelsize=14)
ax.legend(fontsize=16, loc='upper left', framealpha=0.9)
ax.set_ylim(0, 30)
ax.grid(axis='y', alpha=0.3)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

# Formula box
formula = r'$P_{DC} = 2V_{DC} \cdot I$  vs.  $P_{AC} = \sqrt{3} \cdot V_{AC} \cdot I \cdot \cos\phi$'
ax.text(0.72, 0.15, formula, transform=ax.transAxes, fontsize=16,
        bbox=dict(boxstyle='round,pad=0.5', facecolor='#FFFDE7', edgecolor='#D2C295', linewidth=2),
        ha='center', va='center')

# Source
ax.text(0.99, -0.12, 'Sources: Nami et al. [5]; Pratt et al. [6]; Lin et al. [11]',
        transform=ax.transAxes, fontsize=11, color='#888888', ha='right', style='italic')

plt.tight_layout()
OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
plt.savefig(OUTPUT_PATH, dpi=220, bbox_inches='tight', facecolor='white', edgecolor='none')
plt.close()
print(f"Power capacity chart saved to {OUTPUT_PATH}")
