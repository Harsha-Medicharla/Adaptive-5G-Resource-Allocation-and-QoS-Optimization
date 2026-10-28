#!/usr/bin/env python3
"""Run a DQN controller against the native ns-3/ns3-ai slicing environment."""

from __future__ import annotations

import argparse
import os
import random
from collections import deque
from pathlib import Path

import gymnasium as gym
import numpy as np
import torch
from torch import nn

# ns3-ai's current Python helper still uses NumPy aliases removed in NumPy 2.
if not hasattr(np, "float"):
    np.float = float
if not hasattr(np, "int"):
    np.int = int
if not hasattr(np, "uint"):
    np.uint = int

import ns3ai_gym_env  # noqa: F401 - registers the Gym environment


class QNetwork(nn.Module):
    def __init__(self, observation_size: int, action_size: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(observation_size, 128),
            nn.ReLU(),
            nn.Linear(128, 128),
            nn.ReLU(),
            nn.Linear(128, action_size),
        )

    def forward(self, state: torch.Tensor) -> torch.Tensor:
        return self.net(state)


def choose_action(model: QNetwork, observation: np.ndarray, epsilon: float, action_size: int) -> int:
    if np.random.random() < epsilon:
        return int(np.random.randint(action_size))
    with torch.no_grad():
        state = torch.as_tensor(observation, dtype=torch.float32).unsqueeze(0)
        return int(model(state).argmax(dim=1).item())


def update_dqn(
    online: QNetwork,
    target: QNetwork,
    optimizer: torch.optim.Optimizer,
    replay: deque,
    batch_size: int,
    gamma: float,
) -> float | None:
    if len(replay) < batch_size:
        return None
    batch = random.sample(replay, batch_size)
    states, actions, rewards, next_states, dones = zip(*batch)
    states_t = torch.as_tensor(np.asarray(states), dtype=torch.float32)
    actions_t = torch.as_tensor(actions, dtype=torch.int64).unsqueeze(1)
    rewards_t = torch.as_tensor(rewards, dtype=torch.float32)
    next_states_t = torch.as_tensor(np.asarray(next_states), dtype=torch.float32)
    dones_t = torch.as_tensor(dones, dtype=torch.float32)

    q_values = online(states_t).gather(1, actions_t).squeeze(1)
    with torch.no_grad():
        best_actions = online(next_states_t).argmax(dim=1, keepdim=True)
        next_q = target(next_states_t).gather(1, best_actions).squeeze(1)
        expected = rewards_t + gamma * next_q * (1.0 - dones_t)
    loss = nn.functional.smooth_l1_loss(q_values, expected)
    optimizer.zero_grad()
    loss.backward()
    nn.utils.clip_grad_norm_(online.parameters(), 5.0)
    optimizer.step()
    return float(loss.item())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ns3", default=os.path.expanduser("~/ns3/ns-3.45"))
    parser.add_argument("--run", type=int, default=1)
    parser.add_argument("--model", default="")
    parser.add_argument("--epsilon", type=float, default=0.10)
    parser.add_argument("--train", action="store_true")
    parser.add_argument("--episodes", type=int, default=20)
    parser.add_argument("--max-steps", type=int, default=60)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--gamma", type=float, default=0.95)
    parser.add_argument("--learning-rate", type=float, default=5e-4)
    parser.add_argument("--out", default="")
    args = parser.parse_args()

    ns3_path = str(Path(args.ns3).expanduser().resolve())
    project_root = Path(__file__).resolve().parent.parent
    output = str(
        (project_root / args.out).resolve()
        if args.out
        else project_root / "results" / "native_dqn_run.csv"
    )
    model_path = str(
        (project_root / args.model).resolve()
        if args.model
        else project_root / "results" / "native_dqn.pt"
    )

    # ns3-ai's launcher uses #!/usr/bin/env python3; this keeps the configured
    # Python 3.12 environment first when the script is invoked from a shell.
    venv_bin = str(Path(sys_executable()).parent)
    os.environ["PATH"] = venv_bin + os.pathsep + os.environ.get("PATH", "")

    env = gym.make(
        "ns3ai_gym_env/Ns3-v0",
        targetName="slicing-sim",
        ns3Path=ns3_path,
        ns3Settings={"rl": 1, "run": args.run, "out": output},
    )

    model = QNetwork(int(np.prod(env.observation_space.shape)), env.action_space.n)
    if args.model and not args.train and os.path.exists(model_path):
        model.load_state_dict(torch.load(model_path, map_location="cpu", weights_only=True))
    target = QNetwork(int(np.prod(env.observation_space.shape)), env.action_space.n)
    target.load_state_dict(model.state_dict())
    optimizer = torch.optim.Adam(model.parameters(), lr=args.learning_rate)
    replay = deque(maxlen=50000)
    if not args.train:
        model.eval()

    total_reward = 0.0
    steps = 0
    losses = []
    best_episode_reward = float("-inf")
    try:
        for episode in range(1, args.episodes + 1):
            observation, _ = env.reset()
            episode_reward = 0.0
            for step_idx in range(args.max_steps):
                epsilon = args.epsilon if not args.train else max(0.02, 0.65 - 0.60 * (episode / max(1, args.episodes)))
                action = choose_action(
                    model,
                    observation,
                    epsilon,
                    env.action_space.n,
                )
                next_observation, reward, terminated, truncated, info = env.step(action)
                replay.append(
                    (
                        np.asarray(observation, dtype=np.float32),
                        action,
                        float(reward),
                        np.asarray(next_observation, dtype=np.float32),
                        bool(terminated or truncated),
                    )
                )
                if args.train:
                    loss = update_dqn(
                        model, target, optimizer, replay, args.batch_size, args.gamma
                    )
                    if loss is not None:
                        losses.append(loss)
                    if step_idx % 10 == 0:
                        target.load_state_dict(model.state_dict())
                observation = next_observation
                episode_reward += float(reward)
                steps += 1
                total_reward += float(reward)
                print(
                    f"episode={episode} step={step_idx + 1} action={action} reward={float(reward):.4f} "
                    f"info={info.get('info', '')}",
                    flush=True,
                )
                if terminated or truncated:
                    break
            best_episode_reward = max(best_episode_reward, episode_reward)
            if args.train and episode % 5 == 0:
                torch.save(model.state_dict(), model_path)
                print(f"saved DQN model checkpoint: {model_path} ({episode} episodes)")
            print(
                f"episode {episode} complete: total_reward={episode_reward:.4f} best_so_far={best_episode_reward:.4f}",
                flush=True,
            )
    finally:
        env.close()

    if args.train:
        torch.save(model.state_dict(), model_path)
        print(f"saved final DQN model: {model_path}")
    mean_loss = sum(losses) / len(losses) if losses else 0.0
    print(
        f"native training complete: episodes={args.episodes} steps={steps} total_reward={total_reward:.4f} "
        f"best_episode_reward={best_episode_reward:.4f} mean_loss={mean_loss:.6f}"
    )


def sys_executable() -> str:
    return os.environ.get("VIRTUAL_ENV", "") + "/bin/python" if os.environ.get("VIRTUAL_ENV") else os.sys.executable


if __name__ == "__main__":
    main()
