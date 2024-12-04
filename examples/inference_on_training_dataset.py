"""This script demonstrates how to slice a dataset and calculate the loss on a subset of the data.

This technique can be useful for debugging and testing purposes, as well as identifying whether a policy
is learning effectively.

Furthermore, relying on validation loss to evaluate performance is generally not considered a good practice,
especially in the context of imitation learning. The most reliable approach is to evaluate the policy directly
on the target environment, whether that be in simulation or the real world.
"""

import math
from pathlib import Path

import torch
from huggingface_hub import snapshot_download

from lerobot.common.datasets.lerobot_dataset import LeRobotDataset
from lerobot.common.policies.diffusion.modeling_diffusion import DiffusionPolicy

device = torch.device("cuda")

# Download the diffusion policy for pusht environment
# pretrained_policy_path = Path(snapshot_download("lerobot/diffusion_pusht"))
# OR uncomment the following to evaluate a policy from the local outputs/train folder.
pretrained_policy_path = Path("/root/lerobot/outputs/train/2024-11-25/02-37-53_aloha_diffusion_run2/checkpoints/last/pretrained_model")

policy = DiffusionPolicy.from_pretrained(pretrained_policy_path)
policy.eval()
policy.to(device)

# Set up the dataset.
delta_timestamps = {
    # Load the previous image and state at -0.1 seconds before current frame,
    # then load current image and state corresponding to 0.0 second.
    "observation.images.top": [-0.02, 0.0],
    "observation.state": [-0.02, 0.0],
    # Load the previous action (-0.1), the next action to be executed (0.0),
    # and 14 future actions with a 0.1 seconds spacing. All these actions will be
    # used to calculate the loss.
    "action": [-0.02, 0.0, 0.02, 0.04, 0.06, 0.08, 0.1, 0.12, 0.14, 0.16, 0.18, 0.2, 0.22, 0.24, 0.26, 0.28, 0.3, 0.32, 0.34, 0.36, 0.38, 0.4, 0.42, 0.44, 0.46, 0.48, 0.5, 0.52, 0.54, 0.56, 0.58, 0.6, 0.62, 0.64, 0.66, 0.68, 0.7, 0.72, 0.74, 0.76, 0.78, 0.8, 0.82, 0.84, 0.86, 0.88, 0.9, 0.92, 0.94, 0.96, 0.98, 1.0, 1.02, 1.04, 1.06, 1.08, 1.1, 1.12, 1.14, 1.16, 1.18, 1.2, 1.22, 1.24, 1.26, 1.28, 1.3, 1.32, 1.34, 1.36, 1.38, 1.4, 1.42, 1.44, 1.46, 1.48, 1.5, 1.52, 1.54, 1.56, 1.58, 1.6, 1.62, 1.64, 1.66, 1.68, 1.7, 1.72, 1.74, 1.76, 1.78, 1.8, 1.82, 1.84, 1.86, 1.88, 1.9, 1.92, 1.94, 1.96, 1.98, 2.0, 2.02, 2.04, 2.06, 2.08, 2.1, 2.12, 2.14, 2.16, 2.18, 2.2, 2.22, 2.24, 2.26, 2.28, 2.3, 2.32, 2.34, 2.36, 2.38, 2.4, 2.42, 2.44, 2.46, 2.48, 2.5, 2.52],
}

# Load the last 10% of episodes of the dataset as a validation set.
# - Load full dataset
full_dataset = LeRobotDataset("lerobot/aloha_sim_insertion_human", split="train")

# - Calculate train and val subsets
num_train_episodes = math.floor(full_dataset.num_episodes * 90 / 100)
num_val_episodes = full_dataset.num_episodes - num_train_episodes

print(f"Number of episodes in full dataset: {full_dataset.num_episodes}")
print(f"Number of episodes in training dataset (90% subset): {num_train_episodes}")
print(f"Number of episodes in validation dataset (10% subset): {num_val_episodes}")

# - Get first frame index of the validation set
first_val_frame_index = full_dataset.episode_data_index["from"][num_train_episodes].item()

# - Load frames subset belonging to validation set using the `split` argument.
#   It utilizes the `datasets` library's syntax for slicing datasets.
#   For more information on the Slice API, please see:
#   https://huggingface.co/docs/datasets/v2.19.0/loading#slice-splits
train_dataset = LeRobotDataset(
    "lerobot/aloha_sim_insertion_human", split=f"train[:{first_val_frame_index}]", delta_timestamps=delta_timestamps
)
# val_dataset = LeRobotDataset(
#     "lerobot/pusht", split=f"train[{first_val_frame_index}:]", delta_timestamps=delta_timestamps
# )
print(f"Number of frames in training dataset (90% subset): {len(train_dataset)}")
# print(f"Number of frames in validation dataset (10% subset): {len(val_dataset)}")

train_dataloader = torch.utils.data.DataLoader(
    train_dataset,
    num_workers=4,
    batch_size=8,
    shuffle=False,
    pin_memory=device != torch.device("cpu"),
    drop_last=True,
)

# Create dataloader for evaluation.
# val_dataloader = torch.utils.data.DataLoader(
#     val_dataset,
#     num_workers=4,
#     batch_size=64,
#     shuffle=False,
#     pin_memory=device != torch.device("cpu"),
#     drop_last=False,
# )

# Run validation loop.
loss_cumsum = 0
n_examples_evaluated = 0
for batch in train_dataloader:
    batch = {k: v.to(device, non_blocking=True) for k, v in batch.items()}
    output_dict = policy.forward(batch)

    loss_cumsum += output_dict["loss"].item()
    n_examples_evaluated += batch["index"].shape[0]

# Calculate the average loss over the validation set.
average_loss = loss_cumsum / n_examples_evaluated

print(f"Average loss on validation set: {average_loss:.4f}")
