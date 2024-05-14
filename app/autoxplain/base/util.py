import logging
import random

import numpy as np
import torch
from matplotlib import pyplot as plt

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


def _recurse_rm_files(path, rm_root=False):
    if path.is_dir():
        for pth in path.iterdir():
            _recurse_rm_files(pth, True)
        if rm_root:
            path.rmdir()
    else:
        path.unlink()


def delete_files_recursive(path, rm_root=False):
    if path.exists():
        _recurse_rm_files(path, rm_root)
    else:
        raise FileNotFoundError(str(path))


def plot(x, y, title, xlabel, ylabel, path=None, plot_type=plt.plot, labels=None, **kwargs):
    with plt.style.context(kwargs['style'] if 'style' in kwargs else 'ggplot'):
        if 'width' in kwargs or 'height' in kwargs:
            width = kwargs['width'] if 'width' in kwargs else 6.4
            height = kwargs['height'] if 'height' in kwargs else 4.8
            plt.figure(figsize=(width, height))
        if isinstance(y, tuple):
            # multiple plots in one figure
            if labels is not None:
                for yi, labl in zip(y, labels):
                    plot_type(x, yi, label=labl)
                plt.legend(loc="best")
            else:
                for yi in y:
                    plot_type(x, yi)
        else:
            plot_type(x, y)
        plt.title(title)
        plt.xlabel(xlabel)
        plt.ylabel(ylabel)
        if plot_type == plt.bar or 'grid_lines' in kwargs:
            grid_lines = kwargs['grid_lines'] if 'grid_lines' in kwargs else 'y'
            plt.grid(axis=grid_lines)
        if path is not None:
            plt.savefig(path)
        plt.show()
