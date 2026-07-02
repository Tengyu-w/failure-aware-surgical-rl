# SurRoL Recovery Demo

This directory contains a real SurRoL/PyBullet NeedlePick recovery rollout
exported from simulator frames. It is separate from the CircleRL proxy media
and is not a storyboard or introduction video.

| Asset | File |
| --- | --- |
| MP4 video | [surrol_needlepick_action_freeze_monitor_recovery.mp4](surrol_needlepick_action_freeze_monitor_recovery.mp4) |
| GIF preview | [surrol_needlepick_action_freeze_monitor_recovery.gif](surrol_needlepick_action_freeze_monitor_recovery.gif) |
| Trace CSV | [surrol_needlepick_action_freeze_monitor_recovery_trace.csv](surrol_needlepick_action_freeze_monitor_recovery_trace.csv) |
| Fault start frame | [step_000_fault_start.png](frames/step_000_fault_start.png) |
| Monitor trigger frame | [step_016_monitor_trigger.png](frames/step_016_monitor_trigger.png) |
| Recovery completion frame | [step_final_recovered.png](frames/step_final_recovered.png) |

Result: success=1.0, final_distance=0.0169, trigger_step=16, total_steps=59.

Fault protocol: the first segment freezes the executed action, causing no meaningful progress. The monitor then routes execution to a bounded recovery override using the SurRoL scripted task action.

What to look for in the video:

1. `fault_action_freeze`: the controller action is frozen and progress stalls.
2. `monitor_trigger`: the monitor detects lack of useful progress at step 16.
3. `monitor_recovery_oracle_override`: the recovery route switches to the SurRoL scripted task action.
4. `recovery_complete`: the rollout reaches success=1.0 with final_distance=0.0169.

Scope note: this is SurRoL/PyBullet simulator footage with a scripted monitor recovery override; it is not real-robot or clinical validation.
