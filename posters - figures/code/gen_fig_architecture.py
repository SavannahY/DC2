#!/usr/bin/env python3
"""Generate 3-scenario architecture comparison diagram for poster."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np

fig, axes = plt.subplots(1, 3, figsize=(16, 8))
fig.patch.set_facecolor('white')

# Color definitions
GRAY_BG = '#F0F0F0'
GRAY_BORDER = '#999999'
PINK_BG = '#FCE4E4'
PINK_BORDER = '#C0392B'
LTBLUE_BG = '#E0F4F8'
LTBLUE_BORDER = '#2E86C1'
TEAL_BG = '#E0F0ED'
TEAL_BORDER = '#1A7A5C'
ORANGE_BG = '#FFF3E0'
ORANGE_BORDER = '#E67E22'
GREEN_BG = '#E8F5E9'
GREEN_BORDER = '#27AE60'

HEADER_GRAY = '#4A4A4A'
HEADER_RED = '#8C1515'
HEADER_TEAL = '#006B5E'

def draw_box(ax, x, y, w, h, text, bg, border, fontsize=9, bold=False):
    rect = FancyBboxPatch((x - w/2, y - h/2), w, h,
                           boxstyle="round,pad=0.02",
                           facecolor=bg, edgecolor=border, linewidth=1.5)
    ax.add_patch(rect)
    weight = 'bold' if bold else 'normal'
    ax.text(x, y, text, ha='center', va='center', fontsize=fontsize,
            fontweight=weight, color='#333333', wrap=True)

def draw_arrow(ax, x1, y1, x2, y2):
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle='->', color='#666666', lw=1.5))

# Common parameters
box_w = 0.6
box_h = 0.08
x_center = 0.5
y_positions = [0.88, 0.76, 0.64, 0.52, 0.40, 0.28, 0.16]
gap = 0.12

for ax in axes:
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')

# ============ SCENARIO 1: Traditional AC-centric ============
ax = axes[0]
# Header bar
header = FancyBboxPatch((0.05, 0.92), 0.9, 0.06, boxstyle="round,pad=0.01",
                         facecolor=HEADER_GRAY, edgecolor='none')
ax.add_patch(header)
ax.text(0.5, 0.95, 'Traditional\nAC-centric path', ha='center', va='center',
        fontsize=12, fontweight='bold', color='white')

stages_1 = [
    ('Utility\nMV AC', GRAY_BG, GRAY_BORDER),
    ('50/60 Hz\ntransformer', GRAY_BG, GRAY_BORDER),
    ('Facility\nAC / UPS / PDU', GRAY_BG, GRAY_BORDER),
    ('Server PSU\nAC/DC', ORANGE_BG, ORANGE_BORDER),
    ('Board\nDC/DC', ORANGE_BG, ORANGE_BORDER),
    ('GPU / IT\nrails', GRAY_BG, GRAY_BORDER),
]

for i, (text, bg, border) in enumerate(stages_1):
    y = y_positions[i]
    draw_box(ax, x_center, y, box_w, box_h, text, bg, border, fontsize=9)
    if i > 0:
        draw_arrow(ax, x_center, y_positions[i-1] - box_h/2, x_center, y + box_h/2)

# Conversion count annotation
ax.text(0.5, 0.05, '5-6 conversion stages', ha='center', va='center',
        fontsize=10, fontweight='bold', color=HEADER_GRAY,
        bbox=dict(boxstyle='round,pad=0.3', facecolor='#FFF9C4', edgecolor=HEADER_GRAY, lw=1))

# ============ SCENARIO 2: AC-fed SST / 800 Vdc ============
ax = axes[1]
header = FancyBboxPatch((0.05, 0.92), 0.9, 0.06, boxstyle="round,pad=0.01",
                         facecolor=HEADER_RED, edgecolor='none')
ax.add_patch(header)
ax.text(0.5, 0.95, 'AC-fed SST /\n800 Vdc pod path', ha='center', va='center',
        fontsize=12, fontweight='bold', color='white')

stages_2 = [
    ('Utility\nAC', GRAY_BG, GRAY_BORDER),
    ('Grid-side\nAC/DC', PINK_BG, PINK_BORDER),
    ('HF isolated\npod', LTBLUE_BG, LTBLUE_BORDER),
    ('800 Vdc\nbus', GRAY_BG, GRAY_BORDER),
    ('Rack / node\nDC/DC', ORANGE_BG, ORANGE_BORDER),
    ('GPU / IT\nrails', GRAY_BG, GRAY_BORDER),
]

for i, (text, bg, border) in enumerate(stages_2):
    y = y_positions[i]
    draw_box(ax, x_center, y, box_w, box_h, text, bg, border, fontsize=9)
    if i > 0:
        draw_arrow(ax, x_center, y_positions[i-1] - box_h/2, x_center, y + box_h/2)

ax.text(0.5, 0.05, '4 conversion stages', ha='center', va='center',
        fontsize=10, fontweight='bold', color=HEADER_RED,
        bbox=dict(boxstyle='round,pad=0.3', facecolor='#FFEBEE', edgecolor=HEADER_RED, lw=1))

# ============ SCENARIO 3: Proposed MVDC hub ============
ax = axes[2]
header = FancyBboxPatch((0.05, 0.92), 0.9, 0.06, boxstyle="round,pad=0.01",
                         facecolor=HEADER_TEAL, edgecolor='none')
ax.add_patch(header)
ax.text(0.5, 0.95, 'Proposed MVDC hub +\nisolated DC pod', ha='center', va='center',
        fontsize=12, fontweight='bold', color='white')

stages_3 = [
    ('Utility\nAC', GRAY_BG, GRAY_BORDER),
    ('MV front-end\nAC/DC', PINK_BG, PINK_BORDER),
    ('MVDC\nbackbone', TEAL_BG, TEAL_BORDER),
    ('HF isolated\npod', TEAL_BG, TEAL_BORDER),
    ('800 Vdc\nbus', GREEN_BG, GREEN_BORDER),
    ('GPU / IT\nrails', GRAY_BG, GRAY_BORDER),
]

for i, (text, bg, border) in enumerate(stages_3):
    y = y_positions[i]
    draw_box(ax, x_center, y, box_w, box_h, text, bg, border, fontsize=9)
    if i > 0:
        draw_arrow(ax, x_center, y_positions[i-1] - box_h/2, x_center, y + box_h/2)

ax.text(0.5, 0.05, '3-4 conversion stages', ha='center', va='center',
        fontsize=10, fontweight='bold', color=HEADER_TEAL,
        bbox=dict(boxstyle='round,pad=0.3', facecolor='#E0F2F1', edgecolor=HEADER_TEAL, lw=1))

plt.tight_layout(pad=0.5)
plt.savefig('/home/ubuntu/poster/v2_fig_architecture.png', dpi=200, bbox_inches='tight',
            facecolor='white', edgecolor='none')
plt.close()
print("Architecture diagram saved.")
