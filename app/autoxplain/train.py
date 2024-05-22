import os
from io import BytesIO
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from bson import ObjectId
from gridfs import GridFS
from pymongo import MongoClient
from sklearn.metrics import precision_recall_fscore_support, classification_report
from torch.optim.lr_scheduler import ExponentialLR
from torch.utils.data import Dataset, DataLoader
from torchvision.models import VGG19_Weights
from torchvision.transforms import v2, InterpolationMode

import config
from app.autoxplain.base.trainer import Trainer
from app.autoxplain.model import BaseClassifier, CCNN


class CUBDataset(Dataset):
    db_client = MongoClient(
        (config.Production if 'PRODUCTION' in os.environ else config).Debug.MONGODB_DATABASE_URI).xplaindb
    fs = GridFS(db_client)
    _query = {}
    _batch_fetch = {}
    _projection = {}

    def __init__(self, classes, img_indicators, concept_embeddings, apply_transforms=True, validation=False):
        self.classes = classes
        # defining the indices of the image dataset
        if validation:
            self.img_ids = tuple(key for i, key in enumerate(img_indicators.keys(), start=1) if i % 10 == 0)
        else:
            self.img_ids = tuple(key for i, key in enumerate(img_indicators.keys(), start=1) if i % 10 != 0)
        self.img_indicators = img_indicators  # mapping from Image IDs to tuple of one-hot vector and class idx
        self.concept_embeddings = torch.tensor(concept_embeddings, dtype=torch.float32)
        self.convert_and_crop = v2.Compose([
            v2.PILToTensor(),
            v2.ToDtype(torch.uint8),
            v2.RandomCrop(size=(448, 448), pad_if_needed=True)
        ])
        self.transforms = v2.RandomChoice([
            v2.RandomHorizontalFlip(p=1),
            v2.RandomRotation(degrees=45, interpolation=InterpolationMode.BILINEAR),
            v2.GaussianBlur(kernel_size=(5, 9), sigma=(0.1, 2)),
            v2.ColorJitter(contrast=2.5),
            v2.ColorJitter(saturation=2.5),
            v2.ColorJitter(brightness=2.5),
        ]) if apply_transforms else None
        self._vgg_transforms = VGG19_Weights.DEFAULT.transforms()
        # Skip every 10th image from the dataset and use these in validation
        self.validation = validation

    @staticmethod
    def from_file(cls_fname, img_indic_fname, concept_vecs_fname, base_dir=None, validation=False):
        cls_fname = Path(cls_fname)
        img_indic_fname = Path(img_indic_fname)
        cls_fname = Path(cls_fname)
        if base_dir:
            base_dir = Path(base_dir)
            cls_fname = base_dir / cls_fname
            img_indic_fname = base_dir / img_indic_fname
            concept_vecs_fname = base_dir / concept_vecs_fname
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
        return CUBDataset(class_list, img_indicators_dict, concept_vecs, not validation, validation)

    def validation_dataset(self):
        if not self.validation:
            return CUBDataset(self.classes, self.img_indicators, self.concept_embeddings, False, True)
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

    def __getitem__(self, idxs):
        self._query.clear()
        self._batch_fetch['$in'] = [ObjectId(self.img_ids[idx]) for idx in idxs]
        self._query['objects._id'] = self._batch_fetch
        self._projection['image'] = 1
        self._projection['objects._id'] = 1
        # TODO: crop the images to include only the part of the object BBox
        img_docs = self.db_client.images.find(self._query, self._projection)
        imgs = []
        cls_idxs = []
        img_concept_indicators = None if self.validation else []
        for doc in img_docs:
            imgs.append(self.convert_and_crop(Image.open(BytesIO(self.fs.get(doc['image']).read()))))
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
        # finally apply VGG19 transforms
        img_arr = self._vgg_transforms(img_arr)
        if self.validation:
            return img_arr, torch.stack(cls_idxs)
        else:
            return img_arr, torch.stack(cls_idxs), torch.stack(img_concept_indicators), self.concept_embeddings


class ClassifierTrainer(Trainer):
    def __init__(self, model, train_dataset, val_dataset=None, test_dataset=None, base_dir='model_save',
                 data_dir_name='base/data', class_names=None, **kwargs):
        super().__init__(model, train_dataset, val_dataset, test_dataset, base_dir, data_dir_name, **kwargs)
        assert isinstance(model, BaseClassifier)
        self.class_names = [f'class{i}' for i in range(self.model.num_classes)] if class_names is None else class_names
        assert len(self.class_names) == self.model.num_classes
        self.add_metric_func('accuracy', self.compute_accuracy)
        self.add_confusion_metric(self.model.num_classes)

    def _full_evaluation(self, save_dir, stats_fname, metstage, test_dl, **kwargs):
        metric_avg_type = 'binary' if self.model.num_classes == 2 else 'macro'  # 'weighted'
        y_all = []
        pred_all = []
        with torch.no_grad():
            for x, y, *z in test_dl:
                if x.ndim > 4:
                    x = torch.squeeze(x, dim=0)
                if y.ndim > 1:
                    y = y.reshape(-1)
                loss, pred = self.model.step_eval(x, y, *z)
                self._add_metric_batch(loss, y, pred, metstage)
                y_all.append(y)
                pred_all.append(pred)
        self._compute_epoch_metrics(metstage)
        y_all = torch.cat(y_all)
        pred_all = torch.cat(pred_all)
        accuracy = metstage.metrics['accuracy'][-1]
        self.plot_confusions('test', self.class_names)
        if len(np.unique(pred_all)) == 1:
            pass  # TODO: raise warning and break execution (classification did not result in anything useful)
        precision, recall, f_score, _ = precision_recall_fscore_support(y_all, pred_all, average=metric_avg_type)
        print(classification_report(y_all, pred_all, target_names=self.class_names, digits=4))
        if stats_fname:
            stats_fname = stats_fname.with_suffix('.csv')
            if not stats_fname.exists():
                with open(stats_fname, 'w') as file:
                    file.write(f'eval_run_id,accuracy,precision,recall,f_score\n')
            with open(stats_fname, 'a') as file:
                stats = ','.join((str(self.eval_run_id), str(round(accuracy, 4)), str(round(precision, 4)),
                                  str(round(recall, 4)), str(round(f_score, 4))))
                file.write(f'{stats}\n')


class CCNNTrainer(ClassifierTrainer):
    def __init__(self, model, train_dataset, val_dataset=None, test_dataset=None, base_dir='model_save',
                 data_dir_name='base/data', class_names=None, **kwargs):
        super().__init__(model, train_dataset, val_dataset, test_dataset, base_dir,
                         data_dir_name, class_names, **kwargs)
        assert isinstance(model, CCNN)
        self.scheduler_kwargs = {'type': ExponentialLR, 'step_every': 10000, 'gamma': 0.96}

    def start_training(self, epochs, lrs, validate=True, evaluate=True, **kwargs):
        return super().start_training(epochs, lrs, validate, evaluate, self.scheduler_kwargs, **kwargs)

    def set_fc_layer_train_strategy(self):
        self.train_run = self.model.step_train_fc_layers

    def set_regular_train_strategy(self):
        self.train_run = self.model.step_train

    def set_vgg_base_frozen(self, freeze=False, freeze_concept_filters=False):
        if freeze:
            self.model.freeze_conv_base(freeze_concept_filters)
        else:
            self.model.unfreeze_conv_base()


def run_ccnn_training(lr=0.001, load_path=None):
    dset_args = ('class_ids.txt', 'image_indicator_vectors.npy',
                 'concept_word_phrase_vectors.npy', 'app/autoxplain/base/data')
    dset = CUBDataset.from_file(*dset_args)
    sampler = torch.utils.data.sampler.BatchSampler(
        torch.utils.data.sampler.RandomSampler(dset),
        batch_size=32,
        drop_last=True)
    tdl = DataLoader(dset, sampler=sampler, num_workers=3)

    val_dset = dset.validation_dataset()
    val_sampler = torch.utils.data.sampler.BatchSampler(
        torch.utils.data.sampler.RandomSampler(val_dset),
        batch_size=64,
        drop_last=True)
    vdl = DataLoader(val_dset, sampler=val_sampler, num_workers=2)

    net = CCNN(dset.num_concepts, dset.num_classes)
    trainr = CCNNTrainer(net, tdl, vdl, load_path=load_path)
    # Train newly added layers first
    trainr.set_vgg_base_frozen(True)
    trainr.start_training(20, lr)
    # Fine-tune all the variables in the network
    lr *= 0.1
    trainr.set_vgg_base_frozen(False)
    trainr.start_training(50, lr)
    # Finally fine-tune the fully connected layer in isolation
    trainr.set_fc_layer_train_strategy()
    trainr.set_vgg_base_frozen(False, True)
    trainr.start_training(20, lr, save_fname='trainer_model.pt')
