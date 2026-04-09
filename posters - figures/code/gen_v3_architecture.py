#!/usr/bin/env python3
"""Generate a 3-scenario architecture diagram aligned to the current model."""
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch


OUTPUT_PATH = Path(__file__).resolve().parents[1] / "figures" / "fig3_three_scenario_architecture.png"

fig, axes = plt.subplots(1, 3, figsize=(24, 13.5))
fig.patch.set_facecolor('white')

# Colors
GRAY_BG = '#E8E8E8'
GRAY_BOX = '#6B6B6B'
BLUE_BG = '#E3F2FD'
BLUE_BOX = '#1565C0'
GREEN_BG = '#E8F5E9'
GREEN_BOX = '#2E7D32'
CARDINAL = '#8C1515'
WHITE = '#FFFFFF'
ARROW_COLOR = '#555555'

def draw_scenario(ax, title, boxes, bg_color, box_color, stage_text, stage_color):
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 14.4)
    ax.set_aspect('equal')
    ax.axis('off')
    
    # Background
    bg = FancyBboxPatch((0.2, 0.2), 9.6, 13.8, boxstyle="round,pad=0.2",
                         facecolor=bg_color, edgecolor='#CCCCCC', linewidth=1.6)
    ax.add_patch(bg)
    
    # Title
    ax.text(5, 13.45, title, fontsize=22, fontweight='bold', ha='center', va='center',
            color=box_color, fontfamily='Arial')
    
    # Draw boxes
    n = len(boxes)
    spacing = 11.2 / (n + 1)
    y_positions = [12.35 - spacing * (i + 1) for i in range(n)]
    
    for i, (label, sublabel) in enumerate(boxes):
        y = y_positions[i]
        # Box
        rect = FancyBboxPatch((1.2, y - 0.65), 7.6, 1.3, boxstyle="round,pad=0.16",
                               facecolor=box_color, edgecolor='none', alpha=0.9)
        ax.add_patch(rect)
        ax.text(5, y + 0.14, label, fontsize=17.5, fontweight='bold', ha='center', va='center',
                color=WHITE, fontfamily='Arial')
        if sublabel:
            ax.text(5, y - 0.34, sublabel, fontsize=12.5, fontweight='bold', ha='center', va='center',
                    color='#DDDDDD', fontfamily='Arial')
        
        # Arrow to next box
        if i < n - 1:
            y_next = y_positions[i + 1]
            ax.annotate('', xy=(5, y_next + 0.72), xytext=(5, y - 0.72),
                       arrowprops=dict(arrowstyle='->', color=ARROW_COLOR, lw=2.5))
    
    # Stage count box at bottom
    stage_rect = FancyBboxPatch((1.9, 0.55), 6.2, 1.0, boxstyle="round,pad=0.12",
                                 facecolor=stage_color, edgecolor='none')
    ax.add_patch(stage_rect)
    ax.text(5, 1.05, stage_text, fontsize=16.5, fontweight='bold', ha='center', va='center',
            color=WHITE, fontfamily='Arial')

# Scenario 1: Traditional AC
trad_boxes = [
    ('Utility MV AC', '(Grid input)'),
    ('MV/LV Transformer', '(Step-down)'),
    ('UPS', '(AC → DC → AC)'),
    ('PDU', '(AC Distribution)'),
    ('Rack PSU', '(AC → DC)'),
    ('VRM', '(DC → DC)'),
    ('GPU / ASIC', '(48V → 0.7V)'),
]
draw_scenario(axes[0], 'Scenario 1:\nTraditional AC-centric', trad_boxes,
              GRAY_BG, GRAY_BOX, '5 major conversion stages', '#C62828')

# Scenario 2: 69 kV AC -> 800 VDC
sst_boxes = [
    ('Utility MV AC', '(Grid input)'),
    ('69 kV AC → 800 Vdc', '(Perimeter converter)'),
    ('800 Vdc Bus', '(Facility bus)'),
    ('Rack / Node DC-DC', '(Local conversion)'),
    ('Board DC/DC', '(Final regulation)'),
    ('GPU / ASIC', '(48V → 0.7V)'),
]
draw_scenario(axes[1], 'Scenario 2:\n69 kV AC → 800 Vdc', sst_boxes,
              BLUE_BG, BLUE_BOX, '3 major conversion stages', '#E65100')

# Scenario 3: Proposed MVDC backbone
mvdc_boxes = [
    ('Utility MV AC', '(Grid input)'),
    ('MV AC/DC Front-End', '(Centralized AC/DC + PFC)'),
    ('MVDC Backbone', '(DC Subtransmission)'),
    ('HF Isolated DC Pod', '(Galvanic Isolation)'),
    ('800 Vdc Bus → VRM', '(Direct DC path)'),
    ('GPU / ASIC', '(48V → 0.7V)'),
]
draw_scenario(axes[2], 'Scenario 3:\nProposed MVDC Backbone', mvdc_boxes,
              GREEN_BG, GREEN_BOX, '3 major conversion stages', '#2E7D32')

plt.tight_layout(pad=0.8)
OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
plt.savefig(OUTPUT_PATH, dpi=260, bbox_inches='tight', facecolor='white', edgecolor='none')
plt.close()
print(f"Architecture diagram saved to {OUTPUT_PATH}")
