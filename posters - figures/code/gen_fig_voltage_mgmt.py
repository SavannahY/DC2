#!/usr/bin/env python3
"""Generate voltage management & DC-native integration diagram."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
import numpy as np

fig, ax = plt.subplots(1, 1, figsize=(14, 6))
fig.patch.set_facecolor('white')

TEAL = '#006B5E'
TEAL_LIGHT = '#E0F2F1'
BLUE = '#1565C0'
BLUE_LIGHT = '#E3F2FD'
ORANGE = '#E65100'
ORANGE_LIGHT = '#FFF3E0'
GREEN = '#2E7D32'
GREEN_LIGHT = '#E8F5E9'
PURPLE = '#6A1B9A'
PURPLE_LIGHT = '#F3E5F5'
GRAY = '#666666'

ax.set_xlim(0, 10)
ax.set_ylim(0, 6)
ax.axis('off')
ax.set_title('DC-Native Integration: Cleaner Path for Storage, Solar & AI Power Blocks',
             fontsize=14, fontweight='bold', color=TEAL, pad=15)

def draw_box(x, y, w, h, text, bg, border, fontsize=10, bold=False, text_color='#333'):
    rect = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.05",
                           facecolor=bg, edgecolor=border, linewidth=2)
    ax.add_patch(rect)
    weight = 'bold' if bold else 'normal'
    ax.text(x + w/2, y + h/2, text, ha='center', va='center',
            fontsize=fontsize, fontweight=weight, color=text_color)

# Central MVDC backbone (horizontal bar)
draw_box(1.5, 2.6, 7, 0.8, 'MVDC Backbone Bus (10-50 kV DC)', TEAL_LIGHT, TEAL, 13, True, TEAL)

# Top: Grid connection (single AC/DC)
draw_box(0.2, 4.5, 2.5, 0.8, 'Utility AC Grid', '#F0F0F0', GRAY, 11, True)
draw_box(3.2, 4.5, 2.5, 0.8, 'MV AC/DC\n(single conversion)', '#FFCDD2', '#C62828', 10, True)
ax.annotate('', xy=(3.2, 4.9), xytext=(2.7, 4.9),
            arrowprops=dict(arrowstyle='->', color=GRAY, lw=2))
ax.annotate('', xy=(5, 3.4), xytext=(5, 4.5),
            arrowprops=dict(arrowstyle='->', color=TEAL, lw=2))

# Bottom connections from MVDC bus
# 1. Battery / BESS
draw_box(0.3, 0.5, 2.0, 1.2, 'Battery\nStorage\n(BESS)', BLUE_LIGHT, BLUE, 10, True, BLUE)
ax.annotate('', xy=(1.3, 1.7), xytext=(2.5, 2.6),
            arrowprops=dict(arrowstyle='<->', color=BLUE, lw=2))
ax.text(1.5, 2.2, 'DC-DC\ndirect', fontsize=8, ha='center', va='center', color=BLUE,
        bbox=dict(boxstyle='round,pad=0.15', facecolor='white', edgecolor=BLUE, lw=0.8))

# 2. Solar PV
draw_box(2.8, 0.5, 2.0, 1.2, 'Solar PV\nArray', ORANGE_LIGHT, ORANGE, 10, True, ORANGE)
ax.annotate('', xy=(3.8, 1.7), xytext=(3.8, 2.6),
            arrowprops=dict(arrowstyle='<->', color=ORANGE, lw=2))
ax.text(4.2, 2.2, 'DC-DC\nMPPT', fontsize=8, ha='center', va='center', color=ORANGE,
        bbox=dict(boxstyle='round,pad=0.15', facecolor='white', edgecolor=ORANGE, lw=0.8))

# 3. GPU Racks (via isolated pod)
draw_box(5.3, 0.5, 2.0, 1.2, 'HF Isolated\nPod → 800V\n→ GPU Racks', GREEN_LIGHT, GREEN, 10, True, GREEN)
ax.annotate('', xy=(6.3, 1.7), xytext=(6.3, 2.6),
            arrowprops=dict(arrowstyle='->', color=GREEN, lw=2))
ax.text(6.7, 2.2, 'DC-DC\nisolated', fontsize=8, ha='center', va='center', color=GREEN,
        bbox=dict(boxstyle='round,pad=0.15', facecolor='white', edgecolor=GREEN, lw=0.8))

# 4. Future modular AI power blocks
draw_box(7.8, 0.5, 2.0, 1.2, 'Future\nModular AI\nPower Blocks', PURPLE_LIGHT, PURPLE, 10, True, PURPLE)
ax.annotate('', xy=(8.8, 1.7), xytext=(8.5, 2.6),
            arrowprops=dict(arrowstyle='<->', color=PURPLE, lw=2))
ax.text(9.0, 2.2, 'Plug &\nplay DC', fontsize=8, ha='center', va='center', color=PURPLE,
        bbox=dict(boxstyle='round,pad=0.15', facecolor='white', edgecolor=PURPLE, lw=0.8))

# Top-right: key advantage callout
draw_box(6.5, 4.3, 3.3, 1.2, 'No AC-DC-AC\nre-conversion needed!\nAll resources connect\nnatively to DC bus',
         '#C8E6C9', TEAL, 10, True, TEAL)

plt.tight_layout(pad=0.5)
plt.savefig('/home/ubuntu/poster/v2_fig_voltage_mgmt.png', dpi=200, bbox_inches='tight',
            facecolor='white', edgecolor='none')
plt.close()
print("Voltage management diagram saved.")
