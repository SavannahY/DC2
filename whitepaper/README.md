# Whitepaper LaTeX Package

This folder contains a GitHub-ready LaTeX position paper derived from the poster, the source-backed architecture model, and the OpenDSS AC-boundary validation.

## Files

- `dc_subtransmission_backbone_position_paper.tex`
- `references.bib`
- `figures/`

## Included figures

- `figures/gpu_power_trace.png`
- `figures/cumulative_efficiency.png`
- `figures/architecture_comparison.png`

## Reproduce the model outputs first

From the project root:

```bash
cd /Users/zhengjieyang/Documents/DC2
python3 dc_backbone_model.py --run-opendss \
  --save-json source_backed_model_report.json \
  --write-memo MODEL_RESULTS_MEMO.md
```

## Compile the LaTeX paper

This machine does not currently have a LaTeX engine installed, so the manuscript source was prepared but not compiled here.

On a machine with LaTeX installed:

```bash
cd /Users/zhengjieyang/Documents/DC2/whitepaper
pdflatex dc_subtransmission_backbone_position_paper.tex
bibtex dc_subtransmission_backbone_position_paper
pdflatex dc_subtransmission_backbone_position_paper.tex
pdflatex dc_subtransmission_backbone_position_paper.tex
```

If you use `latexmk`, the shorter command is:

```bash
latexmk -pdf dc_subtransmission_backbone_position_paper.tex
```

## Suggested GitHub commit contents

At minimum, include:

- `/Users/zhengjieyang/Documents/DC2/dc_backbone_model.py`
- `/Users/zhengjieyang/Documents/DC2/scientific_assumptions_v1.json`
- `/Users/zhengjieyang/Documents/DC2/source_backed_model_report.json`
- `/Users/zhengjieyang/Documents/DC2/MODEL_RESULTS_MEMO.md`
- `/Users/zhengjieyang/Documents/DC2/whitepaper/`

## If this folder is not yet a Git repository

From `/Users/zhengjieyang/Documents/DC2`:

```bash
git init
git add dc_backbone_model.py scientific_assumptions_v1.json \
  source_backed_model_report.json MODEL_RESULTS_MEMO.md whitepaper
git commit -m "Add DC backbone model, OpenDSS validation, and LaTeX whitepaper"
```

Then connect the remote and push:

```bash
git branch -M main
git remote add origin <YOUR_GITHUB_REPO_URL>
git push -u origin main
```
