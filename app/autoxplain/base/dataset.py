import os
from io import BytesIO
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from bson import ObjectId
from gridfs import GridFS
from pymongo import MongoClient
from torch.utils.data import Dataset
from torchvision.transforms import v2, InterpolationMode

import config


def get_object_crop(img_doc):
    """
    Get the image crop of the `DetectedObject` with the given ID
    :return: The bytes of the cropped image
    """
    objs = img_doc['objects']
    # TODO: select correct image from list of all object IDs from current batch
    obj = objs[0]
    tlx, tly, brx, bry = obj['tlx'], obj['tly'], obj['brx'], obj['bry']
    # If object image crop is outside of 0.5-1.5 width/height ratio, then try to expand the crop to
    # fall into that range. Otherwise, resizing will cause the image to become too stretched.
    width = brx - tlx
    height = bry - tly
    wh_ratio = width / height
    if wh_ratio > 1.2:
        trgt_height = width / 1.2
        height_delta = (trgt_height - height) / 2
        bbox = (tlx, max(tly - height_delta, 0), brx, min(bry + height_delta, img_doc['height']))
    elif wh_ratio < .8:
        trgt_width = height * 0.8
        width_delta = (trgt_width - width) / 2
        bbox = (max(tlx - width_delta, 0), tly, min(brx + width_delta, img_doc['width']), bry)
    else:
        bbox = (tlx, tly, brx, bry)
    return Image.open(BytesIO(CUBDataset.fs.get(img_doc['image']).read())).crop(bbox)


class CUBDataset(Dataset):
    db_client = MongoClient(
        (config.Production if 'PRODUCTION' in os.environ else config).Debug.MONGODB_DATABASE_URI).xplaindb
    fs = GridFS(db_client)
    _query = {}
    _batch_fetch = {}
    _projection = {}

    def __init__(self, classes, img_indicators, concept_embeddings, preprocess_transforms=None,
                 apply_augment_transforms=True, validation=False):
        self.classes = classes
        # defining the indices of the image dataset
        validate_every = 10
        val_shift = 3
        if validation:
            self.img_ids = tuple(
                key for i, key in enumerate(img_indicators.keys(), start=val_shift) if i % validate_every == 0)
        else:
            self.img_ids = tuple(
                key for i, key in enumerate(img_indicators.keys(), start=val_shift) if i % validate_every != 0)
        self.img_indicators = img_indicators  # mapping from Image IDs to tuple of one-hot vector and class idx
        if torch.is_tensor(concept_embeddings):
            self.concept_embeddings = concept_embeddings
        else:
            self.concept_embeddings = torch.tensor(concept_embeddings, dtype=torch.float32)
        self.to_torch_trafo = v2.Compose([
            v2.PILToTensor(),
            v2.ToDtype(torch.uint8),
        ])
        self.convert_and_resize = v2.Compose([
            self.to_torch_trafo,
            v2.Resize(size=(448, 448))
        ])
        self.transforms = v2.RandomChoice([
            v2.RandomHorizontalFlip(p=1),
            v2.RandomRotation(degrees=45, interpolation=InterpolationMode.BILINEAR),
            v2.GaussianBlur(kernel_size=(5, 9), sigma=(0.1, 2)),
            v2.ColorJitter(contrast=2.5),
            v2.ColorJitter(saturation=2.5),
            v2.ColorJitter(brightness=2.5),
        ]) if apply_augment_transforms else None
        self.preprocess_transforms = preprocess_transforms
        # Skip every 10th image from the dataset and use these in validation
        self.validation = validation

    @staticmethod
    def from_file(cls_fname, img_indic_fname, concept_vecs_fname, base_dir=None,
                  preprocess_transforms=None, validation=False):
        if base_dir:
            base_dir = Path(base_dir)
            cls_fname = base_dir / cls_fname
            img_indic_fname = base_dir / img_indic_fname
            concept_vecs_fname = base_dir / concept_vecs_fname
        else:
            cls_fname = Path(cls_fname)
            img_indic_fname = Path(img_indic_fname)
            concept_vecs_fname = Path(concept_vecs_fname)
        class_list = []
        query = CUBDataset._query
        projection = CUBDataset._projection
        with cls_fname.open() as f:
            projection['name'] = 1
            for line in f.readlines():
                if len(line) > 1:
                    query['_id'] = ObjectId(line[:-1])
                    class_list.append(CUBDataset.db_client.labels.find_one(query, projection)['name'])
        projection.clear()
        img_indicators_dict = np.load(img_indic_fname, allow_pickle=True).item()
        concept_vecs = np.load(concept_vecs_fname)
        return CUBDataset(class_list, img_indicators_dict, concept_vecs,
                          preprocess_transforms, not validation, validation)

    def validation_dataset(self, preprocess_trafo=True):
        if not self.validation:
            return CUBDataset(self.classes, self.img_indicators, self.concept_embeddings,
                              self.preprocess_transforms if preprocess_trafo else None, False, True)
        else:
            raise NotImplementedError

    def __len__(self):
        return len(self.img_ids)

    @property
    def num_classes(self):
        return len(self.classes)

    @property
    def num_concepts(self):
        return len(self.concept_embeddings)

    def get_class_by_idx(self, cls_idx):
        self._query['_id'] = ObjectId(self.classes[cls_idx])
        return self.db_client.labels.find_one(self._query)

    def _set_obj_projection(self):
        self._projection['image'] = 1
        self._projection['width'] = 1
        self._projection['height'] = 1
        self._projection['objects._id'] = 1
        self._projection['objects.tlx'] = 1
        self._projection['objects.tly'] = 1
        self._projection['objects.brx'] = 1
        self._projection['objects.bry'] = 1

    def _load_img_by_obj_id(self, obj_id):
        self._query.clear()
        self._query['objects._id'] = obj_id
        self._set_obj_projection()
        idoc = self.db_client.images.find_one(self._query, self._projection)
        self._query.clear()
        self._projection.clear()
        return idoc

    def load_torch_image(self, obj_id):
        idoc = self._load_img_by_obj_id(obj_id)
        return self.to_torch_trafo(get_object_crop(idoc))

    def load_torch_image_resized(self, obj_id):
        idoc = self._load_img_by_obj_id(obj_id)
        return self.convert_and_resize(get_object_crop(idoc))

    def __getitem__(self, idxs):
        self._query.clear()
        obj_ids = [ObjectId(self.img_ids[idx]) for idx in idxs]
        self._batch_fetch['$in'] = obj_ids
        self._query['objects._id'] = self._batch_fetch
        self._set_obj_projection()
        img_docs = self.db_client.images.find(self._query, self._projection)
        imgs = []
        cls_idxs = []
        img_concept_indicators = None if self.validation else []
        for doc in img_docs:
            # Crop the images to include only the part of the object BBox and resize to (448, 448)
            resized_img = self.convert_and_resize(get_object_crop(doc))
            imgs.append(resized_img)
            obj_id = str(doc['objects'][0]['_id'])
            img_infos = self.img_indicators[obj_id]
            cls_idxs.append(torch.tensor(img_infos[1], dtype=torch.int64))
            if not self.validation:
                img_concept_indicators.append(torch.tensor(img_infos[0], dtype=torch.float32))
        self._query.clear()
        self._batch_fetch.clear()
        self._projection.clear()
        img_arr = torch.stack(imgs)
        if self.transforms:
            img_arr = self.transforms(img_arr)
        if self.preprocess_transforms is not None:
            # finally apply necessary image preprocessing transforms
            img_arr = self.preprocess_transforms(img_arr)
        if self.validation:
            return img_arr, torch.stack(cls_idxs)
        else:
            return img_arr, torch.stack(cls_idxs), torch.stack(img_concept_indicators), self.concept_embeddings
