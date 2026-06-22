from __future__ import annotations

from constraint_surgical_rl import ConstrainedToolNavigationEnv


def main() -> None:
    env = ConstrainedToolNavigationEnv(render_mode="rgb_array")
    obs, info = env.reset(seed=7)
    print("reset_obs_shape", obs.shape)
    print("reset_info", info)

    total_reward = 0.0
    for _ in range(10):
        action = env.action_space.sample()
        obs, reward, terminated, truncated, info = env.step(action)
        total_reward += reward
        if terminated or truncated:
            break

    frame = env.render()
    print("last_obs_shape", obs.shape)
    print("total_reward_10_steps", round(total_reward, 4))
    print("last_info", info)
    print("render_shape", None if frame is None else frame.shape)


if __name__ == "__main__":
    main()

