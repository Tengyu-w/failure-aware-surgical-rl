# Expanded Experiment Upgrade Plan

## Target Volume Benchmark

The reference documents have much larger evidence structures:

- HARP-VLA: 1050 paragraphs, 145 headings, 26 tables, 15 embedded figures.
- VT/VF reliability compendium: 214 tables, 294 embedded figures.

The RL project should therefore move from a single-task prototype report to a
multi-task, multi-stress, multi-ablation compendium.

## Expansion Axes

1. Task proxy axis:
   - constrained tool navigation;
   - needle reaching;
   - needle insertion;
   - tight corridor navigation;
   - tissue retraction proxy;
   - gauze manipulation proxy.

2. Algorithm axis:
   - constraint-conditioned PPO;
   - curriculum-conditioned PPO;
   - standard shield;
   - tangent backup controller;
   - no phase/budget ablation;
   - random-policy sanity check;
   - heuristic controller baseline.

3. Evaluation axis:
   - prototype;
   - strict;
   - surgical-proxy stress presets;
   - seed-level variance;
   - controller intervention rate;
   - final distance and cumulative cost;
   - action-deviation metrics as next upgrade.

4. Report axis:
   - aggregate result tables;
   - seed-level appendices;
   - rollout galleries;
   - failure-case gallery;
   - preset-by-preset stress transfer section;
   - supervisor-direction mapping.

## Supervisor Alignment

- Fangxun Zhong / surgical planning and control: emphasize surgical tool navigation, collision avoidance, task-stage control.
- Guiliang Liu / safe and constrained RL: emphasize safety budget, constraint-conditioned policy, random sanity checks.
- Yiding Ji / supervisory control: emphasize tangent backup controller as a supervisory layer.
- Qi Dou / surgical embodied autonomy: emphasize surgical-proxy tasks and transfer to SurRoL.
- Lu Liu / surgical robotics: emphasize embodied autonomy and safe surgical manipulation.
- Hongliang Ren / medical robotics: emphasize constrained medical tool operation.
- Changhao Chen / robot learning and control: emphasize learning plus controller intervention.
- Yuxiang Sun / robot learning/control: emphasize manipulation and safety-aware policy learning.
- Minjing Dong / Yang Li: connect only through reliability, robustness, and transfer; dissertation remains stronger for them.

## Immediate Upgrade

Run:

```powershell
.\scripts\run_stress_transfer_suite.ps1 -Episodes 100
```

Then regenerate the comprehensive DOCX with the stress suite included.

