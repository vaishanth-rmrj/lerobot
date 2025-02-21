#!/usr/bin/env python

# Copyright 2024 The HuggingFace Inc. team. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import torch
from torch import nn

from scipy.signal import butter, filtfilt
import numpy as np

def populate_queues(queues, batch):
    for key in batch:
        # Ignore keys not in the queues already (leaving the responsibility to the caller to make sure the
        # queues have the keys they want).
        if key not in queues:
            continue
        if len(queues[key]) != queues[key].maxlen:
            # initialize by copying the first observation several times until the queue is full
            while len(queues[key]) != queues[key].maxlen:
                queues[key].append(batch[key])
        else:
            # add latest observation to the queue
            queues[key].append(batch[key])
    return queues


def get_device_from_parameters(module: nn.Module) -> torch.device:
    """Get a module's device by checking one of its parameters.

    Note: assumes that all parameters have the same device
    """
    return next(iter(module.parameters())).device


def get_dtype_from_parameters(module: nn.Module) -> torch.dtype:
    """Get a module's parameter dtype by checking one of its parameters.

    Note: assumes that all parameters have the same dtype.
    """
    return next(iter(module.parameters())).dtype

def butterworth_lowpass_filter(data:np.ndarray, cutoff_freq:float = 0.5, sampling_freq:float = 15.0, order=2) -> np.ndarray:
    """
    Applies a low-pass Butterworth filter to the input data.
    
    Parameters:
        data (np.array): Input data array.
        cutoff (float): Cutoff frequency of the filter (Hz). Smoother for lower values.
        fs (float): Sampling frequency of the data (Hz).
        order (int): Order of the filter. Higher order may introduce phase distortions.
        
    Returns:
        filtered_data (np.array): Filtered data array with same shape as data.
    """
    nyquist = 0.5 * sampling_freq
    normal_cutoff = cutoff_freq / nyquist
    b, a = butter(order, normal_cutoff, btype='low', analog=False)

    # apply the filter along axis 0
    filtered_data = filtfilt(b, a, data, axis=0)
    return filtered_data

def smoothen_actions(actions: torch.Tensor) -> torch.Tensor:
    """
    Smoothens the provided action sequence tensor
    Args:
        actions (torch.Tensor): actions from policy
    """
    if not isinstance(actions, torch.Tensor):
        raise ValueError(f"Invalid input type for actions {type(actions)}. Expected torch.Tensor!")
    
    if len(actions.shape) == 3 and not actions.shape[0] == 1:
        raise NotImplementedError(f"Batch processing not implemented!!")

    actions_np = actions.squeeze(0).cpu().numpy()
    # apply the low-pass filter
    actions_np = butterworth_lowpass_filter(actions_np)
    return torch.from_numpy(actions_np.copy()).unsqueeze(0).to(actions.device)