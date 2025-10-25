import numpy as np

from deck_battler.rl import DeckBattlerEnv, PPOConfig
from deck_battler.training import RLTrainingSession


def test_environment_reset_and_mask():
    env = DeckBattlerEnv()
    obs, info = env.reset()
    assert obs.shape == env.observation_space.shape
    mask = info["action_mask"]
    assert mask.shape[0] == env.action_space.n
    # end turn must always be legal
    assert mask[env.end_turn_index] == 1


def test_environment_invalid_action_penalty():
    env = DeckBattlerEnv()
    obs, info = env.reset()
    mask = info["action_mask"]
    invalid_indices = np.where(mask == 0)[0]
    if invalid_indices.size:
        action = int(invalid_indices[0])
        _, reward, _, _, info = env.step(action)
        assert info.get("invalid_action") is True
        assert reward < 0
    # take a valid action afterwards
    valid_action = int(np.where(info["action_mask"] == 1)[0][0])
    obs, reward, terminated, truncated, info = env.step(valid_action)
    assert obs.shape == env.observation_space.shape
    assert isinstance(reward, float)
    assert isinstance(terminated, bool)
    assert isinstance(truncated, bool)


def test_training_session_smoke():
    config = PPOConfig(rollout_steps=64, minibatch_size=32, update_epochs=1, total_updates=1)
    session = RLTrainingSession(config=config)
    report = session.train(progress_bar=False)
    assert report.total_updates == 1
    assert isinstance(report.mean_return, float)
    assert isinstance(report.history, list)
