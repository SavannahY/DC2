#!/usr/bin/env python3
"""Generate a 3-scenario architecture diagram aligned to the current model."""
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch


OUTPUT_PATH = Path(__file__).resolve().parents[1] / "figures" / "fig3_three_scenario_architecture.png"

fig, axes = plt.subplots(1, 3, figsize=(26, 15))
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
    ax.set_ylim(0, 15.2)
    ax.set_aspect('equal')
    ax.axis('off')
    
    # Background
    bg = FancyBboxPatch((0.2, 0.2), 9.6, 14.5, boxstyle="round,pad=0.2",
                         facecolor=bg_color, edgecolor='#CCCCCC', linewidth=1.6)
    ax.add_patch(bg)
    
    # Title
    ax.text(5, 13.95, title, fontsize=27, fontweight='bold', ha='center', va='center',
            color=box_color, fontfamily='Arial')
    
    # Draw boxes
    n = len(boxes)
    spacing = 10.8 / (n + 1)
    y_positions = [12.65 - spacing * (i + 1) for i in range(n)]
    
    for i, (label, sublabel) in enumerate(boxes):
        y = y_positions[i]
        # Box
        rect = FancyBboxPatch((0.95, y - 0.88), 8.1, 1.76, boxstyle="round,pad=0.16",
                               facecolor=box_color, edgecolor='none', alpha=0.9)
        ax.add_patch(rect)
        ax.text(5, y + 0.26, label, fontsize=21.5, fontweight='bold', ha='center', va='center',
                color=WHITE, fontfamily='Arial')
        if sublabel:
            ax.text(5, y - 0.38, sublabel, fontsize=18.0, fontweight='bold', ha='center', va='center',
                    color='#F6F6F6', fontfamily='Arial')
        
        # Arrow to next box
        if i < n - 1:
            y_next = y_positions[i + 1]
            ax.annotate('', xy=(5, y_next + 0.98), xytext=(5, y - 0.98),
                       arrowprops=dict(arrowstyle='->', color=ARROW_COLOR, lw=3.0))
    
    # Stage count box at bottom
    stage_rect = FancyBboxPatch((1.55, 0.62), 6.9, 1.2, boxstyle="round,pad=0.12",
                                 facecolor=stage_color, edgecolor='none')
    ax.add_patch(stage_rect)
    ax.text(5, 1.22, stage_text, fontsize=19.5, fontweight='bold', ha='center', va='center',
            color=WHITE, fontfamily='Arial')

# Scenario 1: Traditional AC
trad_boxes = [
    ('Utility MV AC', '(Grid input)'),
    ('MV/LV Transformer', '(Step-down)'),
    ('UPS', '(AC → DC → AC)'),
    ('PDU', '(AC distribution)'),
    ('Rack PSU + VRM', '(AC → DC → DC)'),
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
    ('GPU / ASIC', '(48V → 0.7V)'),
]
draw_scenario(axes[2], 'Scenario 3:\nProposed MVDC Backbone', mvdc_boxes,
              GREEN_BG, GREEN_BOX, '3 major conversion stages', '#2E7D32')

plt.tight_layout(pad=0.9)
OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
plt.savefig(OUTPUT_PATH, dpi=300, bbox_inches='tight', facecolor='white', edgecolor='none')
plt.close()
print(f"Architecture diagram saved to {OUTPUT_PATH}")
