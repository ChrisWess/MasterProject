import numpy as np
import torch
from torchvision.transforms import v2

from app.autoxplain.model import ccnn_net, dset, data_dir

center_crop = v2.Compose([
    v2.PILToTensor(),
    v2.ToDtype(torch.uint8),
    v2.CenterCrop(size=(448, 448))
])


def _pil_imgs_to_tensor(imgs):
    if torch.is_tensor(imgs):
        return imgs
    if dset.preprocess_transforms is None:
        imgs = [center_crop(img) for img in imgs]
    else:
        imgs = [dset.preprocess_transforms(center_crop(img)) for img in imgs]
    return torch.stack(imgs)


def classify_object_images(imgs, confidence_thresh=0.):
    preds, confs = ccnn_net.infer(_pil_imgs_to_tensor(imgs))
    return [y.item() if conf.item() > confidence_thresh else None for y, conf in zip(preds, confs)]


def identify_object_concepts(imgs):
    cidxs_batches = ccnn_net.find_top_concept_idxs(_pil_imgs_to_tensor(imgs))
    results = []
    for row in cidxs_batches:
        concept_strs = []
        with open(data_dir + '/unique_concepts.txt', 'r') as f:
            lines = f.readlines()
            for idx in row:
                concept_strs.append(lines[idx][:-1])
        results.append((np.array(row), concept_strs))
    return results
