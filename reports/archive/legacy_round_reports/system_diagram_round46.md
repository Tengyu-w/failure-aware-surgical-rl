# System Diagram: Failure-Aware Surgical Reliability Supervisor

```mermaid
flowchart TD
    A["Rendered RGB + Proprioception"] --> B["Visual Feature Encoder<br/>current: RGB pooling + adapter<br/>future: CNN / keypoint / RAM-VLM embedding"]
    B --> C["Base Surgical Policy<br/>current: NeedleReach visual DAgger policy"]
    B --> D["Risk Head<br/>policy-oracle action gap proxy"]
    B --> E["Recovery Memory / Recovery Head<br/>current: old visual memory<br/>future: phase-aware learned recovery"]
    C --> F["Candidate Action"]
    D --> G{"Risk Routing"}
    E --> G
    H["Temporal Evidence<br/>recovery count, stagnation, risk trend"] --> G
    I["OOD / Memory Distance"] --> G
    G -->|low risk| J["Auto Execute"]
    G -->|recoverable risk<br/>within budget| K["Auto Recovery"]
    G -->|high risk or OOD| L["Human Review"]
    G -->|unsafe / repeated failure| M["Abort Candidate"]
    J --> N["Episode Outcome Logs"]
    K --> N
    L --> N
    M --> N
    N --> O["Offline Analysis<br/>coverage-risk, selected success, auto failures"]
    O --> D
    O --> E
    O --> H
```

## Current Implemented Modules

| Module | Current status |
|---|---|
| Visual observation | Implemented as 208D `render_proprio_vision` |
| Visual adapter | Strict split offline denoising, candidate preprocessor |
| Base policy | NeedleReach visual DAgger policy |
| Risk head | Implemented, action-gap proxy |
| Recovery memory | Old augmented memory remains primary |
| OOD gate | Implemented via memory distance |
| Recovery budget | Budget 10 selected as current conservative guard |
| Temporal stagnation | Implemented as candidate secondary guard |
| Cross-task learned visual transfer | Blocked; task-specific data needed |

## Interpretation

The project should be presented as an external reliability supervisor rather than a replacement controller. Its central value is deciding whether autonomy should continue, recover, defer, or stop.

