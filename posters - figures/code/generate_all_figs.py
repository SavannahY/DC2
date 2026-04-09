import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# Common style
plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.sans-serif': ['DejaVu Sans'],
    'font.size': 14,
    'axes.labelsize': 15,
    'axes.titlesize': 16,
    'xtick.labelsize': 12,
    'ytick.labelsize': 12,
    'legend.fontsize': 11,
    'figure.dpi': 300,
})

CARDINAL = '#8C1515'
DARK_RED = '#820000'
GOLD = '#B83A4B'
DARK_GREEN = '#006B3F'

# ============================================================
# FIG 1: Voltage Advantage — Power Capacity vs Voltage Level
# ============================================================
def fig1_voltage_advantage():
    fig, ax = plt.subplots(figsize=(7, 4.5))
    
    voltages_ac = [480, 4160, 12470, 34500]
    voltages_dc = [800, 1500, 10000, 35000]
    
    # For same 500 MCM conductor, current capacity ~380A
    I_max = 380  # Amps
    
    # AC: P = sqrt(3) * V * I * cos(phi), cos(phi)=0.95
    power_ac = [np.sqrt(3) * v * I_max * 0.95 / 1e6 for v in voltages_ac]
    # DC: P = 2 * V * I (bipolar)
    power_dc = [2 * v * I_max / 1e6 for v in voltages_dc]
    
    x = np.arange(4)
    width = 0.35
    
    bars1 = ax.bar(x - width/2, power_ac, width, color='#CC4444', label='AC (3-phase)', edgecolor='black', linewidth=0.5)
    bars2 = ax.bar(x + width/2, power_dc, width, color=DARK_GREEN, label='DC (bipolar)', edgecolor='black', linewidth=0.5)
    
    # Add value labels
    for bar in bars1:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., h + 0.3, f'{h:.1f}', ha='center', va='bottom', fontsize=10, fontweight='bold', color='#CC4444')
    for bar in bars2:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., h + 0.3, f'{h:.1f}', ha='center', va='bottom', fontsize=10, fontweight='bold', color=DARK_GREEN)
    
    ax.set_xlabel('Voltage Class')
    ax.set_ylabel('Power Capacity (MW)')
    ax.set_title('Power Capacity: AC vs. DC\n(Same 500 MCM Conductor, I = 380A)', fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(['480V AC\n800V DC', '4.16 kV AC\n1.5 kV DC', '12.47 kV AC\n10 kV DC', '34.5 kV AC\n35 kV DC'])
    ax.legend(loc='upper left')
    ax.grid(axis='y', alpha=0.3)
    
    # Add formula
    ax.text(0.98, 0.02, r'$P_{DC}=2V_{DC}\cdot I$ vs. $P_{AC}=\sqrt{3}\cdot V_{AC}\cdot I\cdot\cos\phi$',
            transform=ax.transAxes, ha='right', va='bottom', fontsize=11,
            bbox=dict(boxstyle='round,pad=0.3', facecolor='lightyellow', edgecolor='gray'))
    
    plt.tight_layout()
    plt.savefig('poster_fig1_voltage.png', dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print("Fig 1: Voltage advantage generated")

# ============================================================
# FIG 2: Conversion Stages Comparison (AC vs DC path)
# ============================================================
def fig2_conversion_stages():
    fig, ax = plt.subplots(figsize=(7, 4.5))
    
    # AC path: 6-7 stages
    ac_stages = ['Grid\nInput', 'HV→MV\nXfmr', 'MV→LV\nXfmr', 'UPS\n(AC-DC-AC)', 'AC-DC\nRectifier', 'DC-DC\nPSU', 'PoL\nVRM']
    ac_eff = [100, 99.5, 99.0, 94.0, 96.0, 94.0, 97.0]
    ac_cum = [100]
    for i in range(1, len(ac_eff)):
        ac_cum.append(ac_cum[-1] * ac_eff[i] / 100)
    
    # DC path: 3-4 stages
    dc_stages = ['Grid\nInput', 'AC-DC\n(MMC)', 'MVDC→800V\n(SST)', '800V→48V\n(DC-DC)', '48V→1V\n(PoL)']
    dc_eff = [100, 99.0, 99.0, 99.5, 97.0]
    dc_cum = [100]
    for i in range(1, len(dc_eff)):
        dc_cum.append(dc_cum[-1] * dc_eff[i] / 100)
    
    # Also 380 VDC and 800 VDC partial
    vdc380_eff = [100, 99.5, 99.0, 92.0, 98.0, 96.0, 97.0]
    vdc380_cum = [100]
    for i in range(1, len(vdc380_eff)):
        vdc380_cum.append(vdc380_cum[-1] * vdc380_eff[i] / 100)
    
    vdc800_eff = [100, 99.5, 99.0, 93.0, 98.5, 97.0, 97.0]
    vdc800_cum = [100]
    for i in range(1, len(vdc800_eff)):
        vdc800_cum.append(vdc800_cum[-1] * vdc800_eff[i] / 100)
    
    stages_x = list(range(7))
    dc_x = [0, 1, 2.5, 4, 5.5]
    
    ax.plot(stages_x, ac_cum, 'o-', color='#CC4444', linewidth=2.5, markersize=8, label=f'Traditional AC ({ac_cum[-1]:.1f}%)')
    ax.plot(stages_x, vdc380_cum, 's-', color='#E8A317', linewidth=2.5, markersize=8, label=f'380 VDC ({vdc380_cum[-1]:.1f}%)')
    ax.plot(stages_x, vdc800_cum, 'D-', color='#1565C0', linewidth=2.5, markersize=8, label=f'800 VDC ({vdc800_cum[-1]:.1f}%)')
    ax.plot(dc_x, dc_cum, '^-', color=DARK_GREEN, linewidth=2.5, markersize=10, label=f'MVDC E2E ({dc_cum[-1]:.1f}%)')
    
    # Shade the efficiency gain
    ax.fill_between([5, 6], [ac_cum[-2], ac_cum[-1]], [dc_cum[-2], dc_cum[-1]], alpha=0.15, color=DARK_GREEN)
    ax.annotate(f'Δη = {dc_cum[-1]-ac_cum[-1]:.1f}%\nefficiency gain',
                xy=(5.8, (ac_cum[-1]+dc_cum[-1])/2), fontsize=11, fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='#E8F5E9', edgecolor=DARK_GREEN))
    
    ax.set_xticks(stages_x)
    ax.set_xticklabels(['Grid\nInput', 'Trans-\nmission', 'MV\nConv.', 'Facility\nDist.', 'Rack\nPSU', 'PoL/\nVRM', ''], fontsize=10)
    ax.set_ylabel('Cumulative Efficiency (%)')
    ax.set_title('Cumulative Efficiency: AC vs. DC Architectures', fontweight='bold')
    ax.set_ylim(70, 101)
    ax.legend(loc='lower left', fontsize=10)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('poster_fig2_efficiency.png', dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print("Fig 2: Cumulative efficiency generated")

# ============================================================
# FIG 3: Power Loss & Cost Savings (100 MW AI Factory)
# ============================================================
def fig3_power_loss():
    fig, ax = plt.subplots(figsize=(7, 4.5))
    
    categories = ['Transmission\nLoss', 'MV\nConversion', 'Facility\nDistribution', 'Rack PSU\n+ PoL', 'TOTAL\nSaved']
    ac_loss = [3.0, 5.0, 7.0, 10.1, 25.1]
    dc_loss = [0.5, 1.0, 2.0, 2.4, 5.9]
    
    x = np.arange(len(categories))
    width = 0.35
    
    bars1 = ax.bar(x - width/2, ac_loss, width, color='#CC4444', label='AC Loss (MW)', edgecolor='black', linewidth=0.5)
    bars2 = ax.bar(x + width/2, dc_loss, width, color=DARK_GREEN, label='DC Loss (MW)', edgecolor='black', linewidth=0.5)
    
    for bar in bars1:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., h + 0.2, f'{h:.1f}', ha='center', va='bottom', fontsize=10, fontweight='bold')
    for bar in bars2:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., h + 0.2, f'{h:.1f}', ha='center', va='bottom', fontsize=10, fontweight='bold')
    
    # Highlight savings
    savings_x = x[-1]
    ax.annotate(f'Savings:\n19.2 MW\n(~$17M/yr)', xy=(savings_x, 15), fontsize=11, fontweight='bold',
                ha='center', color=DARK_GREEN,
                bbox=dict(boxstyle='round,pad=0.3', facecolor='#E8F5E9', edgecolor=DARK_GREEN))
    
    ax.set_ylabel('Power Loss (MW)')
    ax.set_title('Power Loss: AC vs. DC for 100 MW AI Factory', fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(categories, fontsize=10)
    ax.legend(loc='upper left')
    ax.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('poster_fig3_loss.png', dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print("Fig 3: Power loss generated")

# ============================================================
# FIG 4: Conductor Loss vs Distance (I²R advantage)
# ============================================================
def fig4_conductor_loss():
    fig, ax = plt.subplots(figsize=(7, 4.5))
    
    distance = np.linspace(0, 50, 100)  # km
    R_per_km = 0.065  # ohm/km for 500 MCM
    P_total = 100e6  # 100 MW
    
    # AC 3-phase at 35 kV: I = P / (sqrt(3)*V*cos_phi)
    V_ac = 34500
    I_ac = P_total / (np.sqrt(3) * V_ac * 0.95)
    loss_ac = 3 * I_ac**2 * R_per_km * distance / 1e6  # MW, 3 phases
    
    # DC bipolar at ±35 kV: I = P / (2*V)
    V_dc = 35000
    I_dc = P_total / (2 * V_dc)
    loss_dc = 2 * I_dc**2 * R_per_km * distance / 1e6  # MW, 2 conductors
    
    ax.plot(distance, loss_ac, '-', color='#CC4444', linewidth=2.5, label=f'35 kV AC (3-phase), I={I_ac:.0f}A')
    ax.plot(distance, loss_dc, '-', color=DARK_GREEN, linewidth=2.5, label=f'±35 kV DC (bipolar), I={I_dc:.0f}A')
    ax.fill_between(distance, loss_dc, loss_ac, alpha=0.15, color=DARK_GREEN)
    
    # Mark 60% less loss
    mid_idx = 60
    mid_x = distance[mid_idx]
    ax.annotate(f'60% less loss\nwith DC', xy=(mid_x, (loss_ac[mid_idx]+loss_dc[mid_idx])/2),
                fontsize=12, fontweight='bold', ha='center',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='#E8F5E9', edgecolor=DARK_GREEN))
    
    ax.set_xlabel('Distance (km)')
    ax.set_ylabel('Conductor Loss (MW)')
    ax.set_title('Conductor Loss: 100 MW Delivery over Distance', fontweight='bold')
    ax.legend(loc='upper left', fontsize=10)
    ax.grid(True, alpha=0.3)
    
    # Formula
    ax.text(0.98, 0.02, r'$P_{loss}=n \cdot I^2 \cdot R \cdot L$; DC: n=2, AC: n=3',
            transform=ax.transAxes, ha='right', va='bottom', fontsize=11,
            bbox=dict(boxstyle='round,pad=0.3', facecolor='lightyellow', edgecolor='gray'))
    
    plt.tight_layout()
    plt.savefig('poster_fig4_conductor.png', dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print("Fig 4: Conductor loss generated")

# ============================================================
# FIG 5: Voltage Drop Comparison (DC advantage)
# ============================================================
def fig5_voltage_drop():
    fig, ax = plt.subplots(figsize=(7, 4.5))
    
    # For 100 MW delivery at various voltages
    voltages = [480, 800, 4160, 10000, 35000]
    voltage_labels = ['480V\nAC', '800V\nDC', '4.16kV\nAC', '10kV\nDC', '±35kV\nDC']
    
    # Current for each (simplified)
    P = 100e6
    currents_ac = [P/(np.sqrt(3)*480*0.95), None, P/(np.sqrt(3)*4160*0.95), None, None]
    currents_dc = [None, P/(2*800), None, P/(2*10000), P/(2*35000)]
    
    # Number of parallel conductors needed (500 MCM, 380A max)
    I_max = 380
    conductors = []
    for i, v in enumerate(voltages):
        if currents_ac[i] is not None:
            I = currents_ac[i]
        else:
            I = currents_dc[i]
        n = int(np.ceil(I / I_max))
        conductors.append(n)
    
    colors = ['#CC4444', DARK_GREEN, '#CC4444', DARK_GREEN, DARK_GREEN]
    
    bars = ax.bar(range(len(voltages)), conductors, color=colors, edgecolor='black', linewidth=0.5, width=0.6)
    
    for bar, n in zip(bars, conductors):
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., h + 1, f'{n}', ha='center', va='bottom', fontsize=14, fontweight='bold')
    
    ax.set_xticks(range(len(voltages)))
    ax.set_xticklabels(voltage_labels, fontsize=11)
    ax.set_ylabel('Number of Parallel Conductors\n(500 MCM, 380A each)')
    ax.set_title('Conductor Count for 100 MW Delivery', fontweight='bold')
    ax.grid(axis='y', alpha=0.3)
    
    # Annotation
    ax.annotate('Higher voltage → fewer conductors\n→ less copper, less space, less cost',
                xy=(3.5, max(conductors)*0.6), fontsize=11, ha='center',
                bbox=dict(boxstyle='round,pad=0.4', facecolor='lightyellow', edgecolor='gray'))
    
    plt.tight_layout()
    plt.savefig('poster_fig5_conductors.png', dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print("Fig 5: Conductor count generated")

# ============================================================
# FIG 6: Harmonic / Power Quality Comparison
# ============================================================
def fig6_power_quality():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7, 4))
    
    # Left: AC architecture — multiple harmonic sources
    categories = ['Grid\nInterface', 'UPS\nStages', 'VFDs &\nRectifiers', 'PDU\nTransformers', 'Server\nPSUs']
    thd_ac = [3, 8, 12, 6, 15]
    thd_dc = [3, 0, 0, 0, 2]
    
    x = np.arange(len(categories))
    width = 0.35
    
    ax1.bar(x - width/2, thd_ac, width, color='#CC4444', label='AC Architecture', edgecolor='black', linewidth=0.5)
    ax1.bar(x + width/2, thd_dc, width, color=DARK_GREEN, label='DC Architecture', edgecolor='black', linewidth=0.5)
    ax1.set_ylabel('THD Contribution (%)')
    ax1.set_title('Harmonic Sources\nby Architecture', fontweight='bold', fontsize=13)
    ax1.set_xticks(x)
    ax1.set_xticklabels(categories, fontsize=9)
    ax1.legend(fontsize=9, loc='upper left')
    ax1.grid(axis='y', alpha=0.3)
    
    # Right: Number of power quality management points
    arch = ['Traditional\nAC', '380 VDC', '800 VDC', 'MVDC\nE2E']
    pq_points = [6, 4, 3, 1]
    colors = ['#CC4444', '#E8A317', '#1565C0', DARK_GREEN]
    
    bars = ax2.barh(arch, pq_points, color=colors, edgecolor='black', linewidth=0.5, height=0.6)
    for bar, v in zip(bars, pq_points):
        ax2.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height()/2, f'{v}',
                va='center', fontsize=12, fontweight='bold')
    
    ax2.set_xlabel('PQ Management Points')
    ax2.set_title('Power Quality\nComplexity', fontweight='bold', fontsize=13)
    ax2.set_xlim(0, 8)
    ax2.grid(axis='x', alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('poster_fig6_pq.png', dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print("Fig 6: Power quality generated")

# ============================================================
# FIG 7: Architecture Block Diagram (simplified for poster)
# ============================================================
def fig7_architecture():
    fig, axes = plt.subplots(2, 1, figsize=(9, 5), gridspec_kw={'height_ratios': [1, 1], 'hspace': 0.4})
    
    # Top: Conventional AC Path
    ax = axes[0]
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 10)
    ax.axis('off')
    ax.set_title('Conventional AC Path (6-7 stages, η_total = 75-85%)', fontsize=13, fontweight='bold', color='#CC4444', loc='left')
    
    ac_blocks = [
        ('HV AC\nSubstation', '#8B0000'),
        ('Step-Down\nTransformer', '#A52A2A'),
        ('MV AC\nDistribution', '#CD5C5C'),
        ('AC-DC\nRectifier', '#DC143C'),
        ('UPS\n(AC-DC-AC)', '#E74C3C'),
        ('PDU', '#F08080'),
        ('480V AC\n→ Server PSU', '#FFB6C1'),
    ]
    
    box_w = 12
    gap = 1.5
    start_x = 1
    for i, (label, color) in enumerate(ac_blocks):
        x = start_x + i * (box_w + gap)
        rect = mpatches.FancyBboxPatch((x, 1.5), box_w, 7, boxstyle="round,pad=0.3",
                                        facecolor=color, edgecolor='black', linewidth=1)
        ax.add_patch(rect)
        ax.text(x + box_w/2, 5, label, ha='center', va='center', fontsize=8, color='white', fontweight='bold')
        if i < len(ac_blocks) - 1:
            ax.annotate('', xy=(x + box_w + gap, 5), xytext=(x + box_w, 5),
                       arrowprops=dict(arrowstyle='->', color='black', lw=1.5))
    
    # Efficiency annotations
    eff_labels = ['η≈99.5%', 'η≈99%', 'η≈94%', 'η≈92%', 'η≈96%', 'η≈94%', 'η≈97%']
    for i, eff in enumerate(eff_labels):
        x = start_x + i * (box_w + gap)
        ax.text(x + box_w/2, 0.5, eff, ha='center', va='center', fontsize=7, color='#666')
    
    # Bottom: Proposed DC Path
    ax = axes[1]
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 10)
    ax.axis('off')
    ax.set_title('Proposed DC Subtransmission Path (3-4 stages, η_total = 94-97%)', fontsize=13, fontweight='bold', color=DARK_GREEN, loc='left')
    
    dc_blocks = [
        ('HVDC\nTransmission\n±320-800 kV', '#004D40'),
        ('MMC\nConverter\nη≈99%', '#00695C'),
        ('MVDC\nBackbone\n10-50 kV DC', '#00796B'),
        ('SST\n(SiC)\nη≈99%', '#00897B'),
        ('800 VDC\nFacility Bus\nη≈99.5%', '#009688'),
        ('48V→1V\nPoL (GaN)\nη≈97%', '#26A69A'),
    ]
    
    box_w2 = 14
    gap2 = 2
    start_x2 = 2
    for i, (label, color) in enumerate(dc_blocks):
        x = start_x2 + i * (box_w2 + gap2)
        rect = mpatches.FancyBboxPatch((x, 1.5), box_w2, 7, boxstyle="round,pad=0.3",
                                        facecolor=color, edgecolor='black', linewidth=1)
        ax.add_patch(rect)
        ax.text(x + box_w2/2, 5, label, ha='center', va='center', fontsize=8.5, color='white', fontweight='bold')
        if i < len(dc_blocks) - 1:
            ax.annotate('', xy=(x + box_w2 + gap2, 5), xytext=(x + box_w2, 5),
                       arrowprops=dict(arrowstyle='->', color='black', lw=1.5))
    
    plt.savefig('poster_fig7_arch.png', dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print("Fig 7: Architecture generated")

# Generate all
fig1_voltage_advantage()
fig2_conversion_stages()
fig3_power_loss()
fig4_conductor_loss()
fig5_voltage_drop()
fig6_power_quality()
fig7_architecture()
print("\nAll 7 figures generated successfully!")
