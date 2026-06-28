# CircleRL Recovery Demo

This media asset shows the custom constrained tool-navigation proxy used before the SurRoL migration.
A biased target estimate first drives the tool along the wrong route. At the recovery trigger, the target is re-estimated and the monitor uses the true target while the risk-gated tangent controller remains available near the forbidden zone.

| Asset | Path |
| --- | --- |
| MP4 video | [circlerl_bias_recovery.mp4](circlerl_bias_recovery.mp4) |
| GIF preview | [circlerl_bias_recovery.gif](circlerl_bias_recovery.gif) |
| Trace CSV | [circlerl_bias_recovery_trace.csv](circlerl_bias_recovery_trace.csv) |
| Fault start frame | [step_000_fault_start.png](frames/step_000_fault_start.png) |
| Recovery trigger frame | [step_034_recovery_trigger.png](frames/step_034_recovery_trigger.png) |
| Final recovered frame | [step_final_recovered.png](frames/step_final_recovered.png) |

Scope note: this is a CircleRL/proxy controller visualization, not a SurRoL/PyBullet surgical rollout and not real-robot footage.
