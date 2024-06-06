import numpy as np
import torch
from torch.utils.data import DataLoader
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


def show_dset(num_sample=5):
    vds = dset.validation_dataset(False)
    sampler = torch.utils.data.sampler.BatchSampler(torch.utils.data.sampler.RandomSampler(vds),
                                                    batch_size=1, drop_last=False)
    tdl = DataLoader(vds, sampler=sampler)
    to_pil = v2.ToPILImage()
    for i, x in enumerate(tdl, start=1):
        to_pil(x[0].squeeze()).show()
        if i == num_sample:
            return


def binary_activation_mask():
    # TODO: create a binary mask where activation values greater
    #  than 0.995 of the maximum activation are set to 1, and the rest
    #  are set to 0. Then we use bilinear interpolation to generate the
    #  image-resolution mask, and overlay the mask on an image
    #  to identify the receptive field
    pass
