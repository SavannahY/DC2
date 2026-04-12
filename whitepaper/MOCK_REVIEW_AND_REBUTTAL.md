# Mock Review and Rebuttal

This file records a deliberately harsh internal review of the current manuscript and a corresponding author-response summary. The purpose is not to claim acceptance readiness. The purpose is to identify what still blocks a top power-systems-journal submission and what has already been corrected in the repository.

## Reviewer Outcome

Likely decision in current form: `reject` for a Transactions-level journal.

Main reason: the paper is still strongest as an architecture position paper supported by source-anchored modeling, not as a deployment-grade power-systems study.

## Simulated Reviewer Criticisms

### 1. Scenario endpoint mismatch biased the original headline result

Reviewer criticism:
- The original Scenario 3 ended at a different electrical boundary than Scenario 2 because Scenario 2 included board-level DC/DC while Scenario 3 did not.
- That made the original efficiency advantage artificially large.

Author response:
- Accepted.
- The model has been corrected so Scenario 3 now includes board-level DC/DC regulation and terminates at the same end-use electrical boundary as Scenario 2.
- The manuscript was revised to state this explicitly.

Repository changes:
- [scientific_assumptions_v1.json](/Users/zhengjieyang/Documents/DC2/scientific_assumptions_v1.json)
- [whitepaper/dc_subtransmission_backbone_position_paper.tex](/Users/zhengjieyang/Documents/DC2/whitepaper/dc_subtransmission_backbone_position_paper.tex)

Residual issue:
- After correction, the Scenario 3 advantage over Scenario 2 is modest rather than dramatic.

### 2. OpenDSS was overstated as validation

Reviewer criticism:
- The OpenDSS study used a short synthetic AC stub for Scenario 3 and therefore did not constitute independent validation of the DC architecture.
- The manuscript overclaimed by using words such as `validation` and `independently confirms`.

Author response:
- Accepted.
- The manuscript has been revised to describe the OpenDSS layer as an `AC-boundary cross-check`.
- Claims of independent validation were removed or softened.

Repository changes:
- [whitepaper/dc_subtransmission_backbone_position_paper.tex](/Users/zhengjieyang/Documents/DC2/whitepaper/dc_subtransmission_backbone_position_paper.tex)
- [MODEL_RESULTS_MEMO.md](/Users/zhengjieyang/Documents/DC2/MODEL_RESULTS_MEMO.md)

Residual issue:
- The OpenDSS layer is still a surrogate upstream cross-check, not a site-specific interconnection study.

### 3. The dynamic model is not a true power-system dynamic simulation

Reviewer criticism:
- The dynamic layer is a load-envelope sensitivity study, not an RMS or EMT dynamic model.

Author response:
- Partially accepted.
- The manuscript now uses more cautious language and avoids implying converter-aware dynamic validation.
- The dynamic layer is still included because it is useful for ranking architectures under time-varying loading, but it is not presented as an EMT study.

Residual issue:
- A journal-grade paper would still need converter-aware RMS or EMT modeling.

### 4. The single-path comparison was too easy to dismiss as a collapsed topology

Reviewer criticism:
- A 100 MW campus cannot be represented credibly by only one serialized path if topology is central to the claim.

Author response:
- Accepted.
- A separate apples-to-apples multi-node campus comparison was added for Scenario 1(M), Scenario 2(M), and Scenario 3(M) on the same four-block topology.
- The manuscript now includes that comparison.

Repository changes:
- [dc_backbone_multinode_campus_model.py](/Users/zhengjieyang/Documents/DC2/dc_backbone_multinode_campus_model.py)
- [multinode_campus_topology.json](/Users/zhengjieyang/Documents/DC2/multinode_campus_topology.json)
- [multinode_campus_report.json](/Users/zhengjieyang/Documents/DC2/multinode_campus_report.json)
- [whitepaper/dc_subtransmission_backbone_position_paper.tex](/Users/zhengjieyang/Documents/DC2/whitepaper/dc_subtransmission_backbone_position_paper.tex)

Residual issue:
- The multi-node model is still radial, balanced, and quasi-static.

### 5. Proxy uncertainty was not previously addressed

Reviewer criticism:
- The ranking could be dominated by the assumed front-end and isolated-pod efficiency curves.

Author response:
- Accepted.
- A proxy sensitivity script was added to stress-test the key advanced-converter curves.
- The result is informative but not fully favorable: Scenario 3 dominates Scenario 2 in only `69/125` single-path cases and Scenario 3(M) dominates Scenario 2(M) in `88/125` multi-node cases.

Repository changes:
- [dc_backbone_proxy_sensitivity.py](/Users/zhengjieyang/Documents/DC2/dc_backbone_proxy_sensitivity.py)
- [proxy_sensitivity_report.json](/Users/zhengjieyang/Documents/DC2/proxy_sensitivity_report.json)

Residual issue:
- Measured converter data remain a gating need for a stronger quantitative claim.

### 6. Base-case stage ratings were slightly infeasible

Reviewer criticism:
- Some stages operated above rated output under the nominal base case.

Author response:
- Accepted.
- Stage rating margins were increased so the nominal base case is internally feasible.

Residual issue:
- This is a consistency fix, not a substitute for explicit redundancy and contingency sizing.

### 7. Annual-loss numbers were written too much like realistic operating studies

Reviewer criticism:
- The original annual-loss presentation looked like a realistic annual dispatch result even though it used a single full-load bin.

Author response:
- Accepted.
- The manuscript now describes these values as `annualized reference continuous-operation` losses.

Residual issue:
- A journal-grade techno-economic study would still need a realistic multi-bin or hourly operating profile.

## Current Technical Position After Revision

What the revised paper can support:
- Scenario 3 remains directionally favorable in the corrected single-path comparison.
- Scenario 3(M) remains best in the added four-block campus comparison.
- OpenDSS cross-checks show lower modeled AC-boundary feeder burden and lower AC-boundary harmonic sensitivity for the centralized-front-end architecture.
- The paper is materially more honest about what is and is not proven.

What the revised paper still cannot support at Transactions level:
- converter-control stability claims,
- IEEE 519 compliance claims,
- protection or grounding readiness,
- site-specific interconnection claims,
- robust quantitative superiority independent of proxy assumptions.

## What Would Still Be Needed for a Strong Journal Submission

1. Replace the key proxy curves with vendor or measured data for the centralized front end and isolated DC pod.
2. Add a realistic annual operating profile instead of a reference continuous-operation year.
3. Upgrade the dynamic layer to RMS or EMT modeling with explicit converter controls.
4. Replace the OpenDSS surrogate boundary cross-check with a common-network study using utility Thevenin equivalents.
5. Add protection, grounding, insulation-coordination, and fault-clearing treatment.

## Practical Conclusion

The revised manuscript is stronger and more defensible than the earlier version, but it is still closer to a high-quality position paper or technical white paper than to a top power-systems-journal article.
