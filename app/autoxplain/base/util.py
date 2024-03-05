import logging
import random

import numpy as np
import torch

logger = logging.getLogger(__name__)


def flatten(lst, inplace=True):
    if inplace:
        for sublist in lst:
            for item in sublist:
                lst.append(item)
            del lst[0]
        return lst
    else:
        return [item for sublist in lst for item in sublist]


def set_seed(seed, set_gpu=True):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if set_gpu and torch.cuda.is_available():
        # Necessary for reproducibility; lower performance
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
        torch.cuda.manual_seed_all(seed)
    logger.info('Random seed is set to %d' % seed)


def cuda_allocated_memory(device):
    giga_byte = 1073741824  # 1024**3
    if torch.cuda.is_available():
        return torch.cuda.memory_allocated(device=device) / giga_byte
    else:
        return 0.0
