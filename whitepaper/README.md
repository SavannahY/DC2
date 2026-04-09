# White Paper Package

This folder contains the public-facing white paper package for the MVDC backbone study for AI factories.

## Included Files

- `dc_subtransmission_backbone_position_paper.tex`
  - LaTeX manuscript source
- `references.bib`
  - bibliography file
- `dc_subtransmission_backbone_position_paper.pdf`
  - rendered PDF for sharing
- `dc_subtransmission_backbone_position_paper.docx`
  - Word version for collaborative editing
- `figures/`
  - figure files used in the manuscript
- `render_whitepaper_outputs.py`
  - local renderer used in this workspace to regenerate the PDF and DOCX outputs from the manuscript content

## Figures Included

- `figures/gpu_power_trace.png`
- `figures/cumulative_efficiency.png`
- `figures/architecture_comparison.png`

## Regenerating the Outputs

From the project root:

```bash
python3 whitepaper/render_whitepaper_outputs.py
```

## LaTeX Compilation

The repository includes the LaTeX source and bibliography. On a machine with a LaTeX toolchain installed, the manuscript can be compiled with:

```bash
cd whitepaper
pdflatex dc_subtransmission_backbone_position_paper.tex
bibtex dc_subtransmission_backbone_position_paper
pdflatex dc_subtransmission_backbone_position_paper.tex
pdflatex dc_subtransmission_backbone_position_paper.tex
```

Or with `latexmk`:

```bash
cd whitepaper
latexmk -pdf dc_subtransmission_backbone_position_paper.tex
```
