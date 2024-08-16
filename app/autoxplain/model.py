from abc import ABC, abstractmethod
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision
from torch.nn.utils.clip_grad import clip_grad_norm
from torchvision.models import VGG19_Weights, ResNet101_Weights

from app.autoxplain.base.dataset import CUBDataset


class BaseModel(nn.Module, ABC):
    def __init__(self, device, clip_value=None, optimizer=torch.optim.Adam, criterion=None):
        super().__init__()
        self.optimizer = optimizer
        self.update_epoch = 0
        self.scheduler = None
        self.schedule_step_every = None
        self.criterion = criterion
        self.device = None
        self.clip_value = clip_value
        self.model_on_device = False
        self.set_device(device)

    @abstractmethod
    def forward(self, *args):
        pass

    @abstractmethod
    def infer(self, *args):
        pass

    @abstractmethod
    def step_train(self, *args):
        pass

    @abstractmethod
    def step_eval(self, *args):
        pass

    def update_step(self, y_pred, target, loss=None):
        self.update_epoch += 1
        self.optimizer.zero_grad()
        if loss is None:
            loss = self.criterion(y_pred, target)
        loss.backward()
        if self.clip_value is not None:
            clip_grad_norm(self.parameters(), self.clip_value)
        self.optimizer.step()
        if self.scheduler is not None and self.update_epoch % self.schedule_step_every == 0:
            self.scheduler.step()
        loss = loss.item() * target.shape[0]
        y_pred = self._pred_fn(y_pred)
        return loss, y_pred.detach().cpu()

    def set_device(self, device):
        # not sending model to device yet
        if device is None:
            device = "cuda:0" if torch.cuda.is_available() else "cpu"
        device = torch.device(device)
        if device != self.device:
            self.device = device
            self.model_on_device = False

    def to(self, *args, **kwargs):
        super().to(*args, **kwargs)
        if args or 'device' in kwargs:
            self.model_on_device = True

    def train(self, mode=True):
        if not self.model_on_device:
            self.to(self.device)
        super().train(mode)

    def setup_training(self, optimizer, criterion=nn.CrossEntropyLoss(), device=None):
        self.optimizer = optimizer
        if criterion is not None:
            self.criterion = criterion
        if device is not None:
            self.set_device(device)

    def add_lr_scheduler(self, scheduler_type, step_every=1, **scheduler_kwargs):
        self.scheduler = scheduler_type(optimizer=self.optimizer, **scheduler_kwargs)
        self.schedule_step_every = step_every

    def save(self, save_path, metrics, **kwargs):
        if save_path is None:
            return
        state_dict = {'model_state_dict': self.state_dict(), 'metrics': metrics}
        state_dict.update(kwargs)
        torch.save(state_dict, save_path)

    def load(self, load_path):
        if load_path is None:
            return
        state_dict = torch.load(load_path, map_location=self.device)
        self.load_state_dict(state_dict['model_state_dict'])
        return state_dict


class BaseClassifier(BaseModel, ABC):
    def __init__(self, num_classes, device, clip_value=None, optimizer=torch.optim.Adam, criterion=None):
        super().__init__(device, clip_value, optimizer, criterion)
        self.num_classes = num_classes
        self._pred_fn = self.determine_bin if self.num_classes == 2 else self.determine_multi

    @staticmethod
    def determine_bin(y_hat, thresh=0):
        return torch.where(y_hat > thresh, 1, 0)

    @staticmethod
    def determine_multi(y_hat):
        return torch.argmax(y_hat, dim=1)

    def infer(self, x, thresh=0):
        with torch.no_grad():
            x = torch.atleast_2d(x.to(self.device, torch.float32))
            y_hat = self(x)
            if self.num_classes == 2:
                return self.determine_bin(y_hat, thresh)
            else:
                return self.determine_multi(y_hat)


class CCNN(BaseClassifier):
    def __init__(self, num_concepts, num_classes, conv_base=torchvision.models.vgg19(VGG19_Weights.DEFAULT).features,
                 train_batch_size=32, conv_base_out_fms=512, device=None, clip_value=None, optimizer=torch.optim.Adam,
                 word_vec_size=50, embeds_size=40, dropout_rate=0.5, lambda_arg=0.4, additional_pool=False):
        super(CCNN, self).__init__(num_classes, device, clip_value, optimizer, nn.CrossEntropyLoss(reduction='none'))
        # TODO: cls_indicator should be a buffer (to allow saving and loading)
        cls_indicator_vectors = torch.tensor(
            np.load('app/autoxplain/base/data/class_indicator_vectors.npy').astype(np.float32), device=self.device)
        self.register_buffer('cls_indicator_vectors', cls_indicator_vectors)
        # TODO: option to use own saved weights from previous training
        #  (otherwise full VGG19 weights with fully connected layers need to be saved to disk)
        self.num_concepts = num_concepts
        self.embeds_size = embeds_size
        self.lambda_arg = lambda_arg
        self.conv_base = conv_base
        if additional_pool:
            self.maxpool = nn.MaxPool2d(kernel_size=2, stride=2)
            self.v_e_in_size = 9 * train_batch_size  # (kernel dims times batch size)
        else:
            self.maxpool = None
            self.v_e_in_size = 49 * train_batch_size
        self.concept_kernels = nn.Conv2d(conv_base_out_fms, num_concepts, kernel_size=1)
        self.dropout = nn.Dropout(p=dropout_rate)
        self.v_e_converter = nn.Linear(self.v_e_in_size, embeds_size)  # visual embedding layer
        self.w_e_converter = nn.Linear(word_vec_size, embeds_size)  # word embedding layer
        self.classifier = nn.Linear(num_concepts, num_classes)
        self.sigmoid_cross_entropy = nn.BCEWithLogitsLoss(reduction='none')
        with torch.no_grad():
            # initialize classifier layer from class indicators, which
            # allows only all possible concepts for a class as outputs.
            self.classifier.weight.copy_(self.cls_indicator_vectors.T * 0.1)
        self.to(self.device)

    def freeze_conv_base(self, freeze_concept_filters=False, freeze_until_vgg_layer=None):
        for i, param in enumerate(self.conv_base.parameters(), start=1):
            if freeze_until_vgg_layer is not None and freeze_until_vgg_layer < i / 2:
                break
            param.requires_grad = False
        if freeze_concept_filters:
            for param in self.concept_kernels.parameters():
                param.requires_grad = False

    def unfreeze_conv_base(self):
        for param in self.conv_base.parameters():
            param.requires_grad = True
        for param in self.concept_kernels.parameters():
            param.requires_grad = True

    @staticmethod
    def global_avg_pool(x: torch.Tensor) -> torch.Tensor:
        # Global average pooling over axes Width and Height
        return torch.mean(x, dim=(2, 3))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.conv_base(x)  # Regular VGG19 classification conv_base returns 7x7 feature maps.
        if self.maxpool is not None:
            x = self.maxpool(x)
        x = self.concept_kernels(x)
        x = self.dropout(x)
        return x  # Resulting feature maps are only 3x3 in width and height when using additional max-pooling.

    def classify(self, x: torch.Tensor) -> torch.Tensor:
        return self.classifier(x)

    def semantic_loss(self, visual_feats: torch.Tensor, text_feats: torch.Tensor, indicator_vectors: torch.Tensor,
                      alpha: float = 1.) -> tuple[torch.Tensor, torch.Tensor]:
        cosine_similarity = torch.matmul(visual_feats, text_feats.T).unsqueeze(0)
        eye = torch.eye(self.num_concepts, device=self.device)
        positive = (cosine_similarity * eye).sum(dim=2)
        metric_p = torch.tile(positive.unsqueeze(dim=2), (1, 1, self.num_concepts))
        delta = cosine_similarity - metric_p
        loss = F.relu((alpha + delta) + (-2 * eye)).sum(dim=2)
        return loss * indicator_vectors, positive

    def counter_loss(self, positive: torch.Tensor, indicator_vectors: torch.Tensor, beta: float = .5) -> torch.Tensor:
        indices = torch.arange(start=0, end=positive.shape[1], dtype=torch.int64, device=self.device)
        shuffled_indices = indices[torch.randperm(len(indices))]
        shuffled_indices = shuffled_indices.unsqueeze(0)

        shuffled_positive = torch.gather(positive, 1, shuffled_indices)
        shuffled_indicator_vectors = torch.gather(indicator_vectors, 1, shuffled_indices)

        img_only_feats = F.relu(indicator_vectors - shuffled_indicator_vectors)
        return F.relu(shuffled_positive * img_only_feats - positive * img_only_feats + beta) * img_only_feats

    def uniqueness_loss(self, global_ap: torch.Tensor, indicator_vectors: torch.Tensor):
        sigmoid_inputs = global_ap - torch.tile(torch.mean(global_ap, dim=1).unsqueeze(1), (1, self.num_concepts))
        return self.sigmoid_cross_entropy(sigmoid_inputs + 1e-5, indicator_vectors)

    def combine_loss(self, global_ap: torch.Tensor, visual_feats: torch.Tensor, text_feats: torch.Tensor,
                     img_indic: torch.Tensor) -> torch.Tensor:
        semantic_loss, positive = self.semantic_loss(visual_feats, text_feats, img_indic)
        count_loss = self.counter_loss(positive, img_indic)
        uniqueness_loss = self.uniqueness_loss(global_ap, img_indic)
        interpretation_loss = uniqueness_loss + semantic_loss + count_loss
        return interpretation_loss.mean(dim=1)

    def step_train(self, x, y, img_indic, embed):
        x = x.to(self.device, torch.float32)
        y = y.to(self.device, torch.int64)

        # Classify
        x = self(x)
        global_ap = self.global_avg_pool(x)
        y_pred = self.classify(global_ap)  # classification result

        # Compute Training Loss
        x = x.reshape((-1, self.v_e_in_size, self.num_concepts)).permute(0, 2, 1).reshape((-1, self.v_e_in_size))
        embedded_visual_feats = F.normalize(self.v_e_converter(x), dim=1)
        embedded_text_feats = F.normalize(self.w_e_converter(embed.to(self.device, torch.float32)).squeeze(0), dim=1)
        img_indic = img_indic.squeeze(0).to(self.device)
        interpr_loss = self.combine_loss(global_ap, embedded_visual_feats, embedded_text_feats, img_indic)
        # incorporate the classification loss
        class_loss = self.criterion(y_pred, y)
        loss = self.lambda_arg * interpr_loss + class_loss
        return self.update_step(y_pred, y, loss.mean())

    def step_train_fc_layers(self, x, y, *_):
        # Train the fully-connected layer in isolation
        x = x.to(self.device, torch.float32)
        y = y.to(self.device, torch.int64)

        y_pred = self.classify(self.global_avg_pool(self(x)))
        class_loss = self.criterion(y_pred, y)

        fc_total_loss = class_loss.mean()
        fc_total_loss = fc_total_loss + torch.abs((1 - self.cls_indicator_vectors) * self.classifier.weight.T).mean()
        return self.update_step(y_pred, y, fc_total_loss)

    def step_eval(self, x, y):
        x = x.to(self.device, torch.float32)
        y = y.to(self.device, torch.int64)
        y_hat = self.classify(self.global_avg_pool(self(x)))
        loss = self.criterion(y_hat, y).mean().cpu()
        pred = self._pred_fn(y_hat)
        return loss, pred.cpu()

    def infer(self, x):
        with torch.no_grad():
            x = torch.atleast_3d(x.to(self.device, torch.float32))
            if x.ndim == 3:
                x = x.unsqueeze(0)
            x = self.classify(self.global_avg_pool(self(x)))
            pred_idxs = self.determine_multi(x).cpu()
            confidences = F.softmax(x, dim=0).gather(1, pred_idxs.unsqueeze(-1)).squeeze()
            return pred_idxs, torch.atleast_1d(confidences).cpu()

    def get_concept_feature_maps(self, x):
        with torch.no_grad():
            x = torch.atleast_3d(x.to(self.device, torch.float32))
            if x.ndim == 3:
                x = x.unsqueeze(0)
            return self(x).cpu()

    def find_top_concept_idxs(self, x):
        with torch.no_grad():
            x = torch.atleast_3d(x.to(self.device, torch.float32))
            if x.ndim == 3:
                x = x.unsqueeze(0)
            x = F.softmax(self.global_avg_pool(self(x)), dim=1)
            conf, idxs = x.topk(3, dim=1)
            return idxs.cpu(), conf.cpu()

    def infer_complete(self, x):
        with torch.no_grad():
            x = torch.atleast_3d(x.to(self.device, torch.float32))
            if x.ndim == 3:
                x = x.unsqueeze(0)
            fms = self(x)  # concept feature maps
            pooled = self.global_avg_pool(fms)
            x = self.classify(pooled)
            class_idxs = self.determine_multi(x)
            class_conf = F.softmax(x, dim=0).gather(1, class_idxs.unsqueeze(-1)).squeeze()
            con_conf, con_idxs = F.softmax(pooled, dim=1).topk(3, dim=1)
            return fms.cpu(), class_idxs.cpu(), torch.atleast_1d(class_conf).cpu(), con_idxs.cpu(), con_conf.cpu()


# Initialize the network model and training datasets and parameters on startup
train_bs = 32
net_weights = ResNet101_Weights.IMAGENET1K_V2

oxp_root_dir = Path('app/autoxplain')
oxp_model_base_dir = oxp_root_dir / 'base'
oxp_model_data_dir = oxp_model_base_dir / 'data'
dset_args = ('class_ids.txt', 'image_indicator_vectors.npy', 'concept_word_phrase_vectors.npy',
             oxp_model_data_dir, net_weights.transforms())
dset = CUBDataset.from_file(*dset_args)
# Load model if it exists
model_save_dir = oxp_root_dir / 'model_save'
model_path = model_save_dir / 'train_0/accuracy_highscore.pt'
if dset is None:
    ccnn_net = None
else:
    if model_path.exists():
        resnet = torchvision.models.resnet101()
        resnet_feat_extractor = nn.Sequential(resnet.conv1, resnet.bn1, resnet.relu, resnet.maxpool, resnet.layer1,
                                              resnet.layer2, resnet.layer3, resnet.layer4)
        ccnn_net = CCNN(dset.num_concepts, dset.num_classes, resnet_feat_extractor, train_bs, conv_base_out_fms=2048)
        ccnn_net.load(model_path)
    else:
        resnet = torchvision.models.resnet101(net_weights)
        resnet_feat_extractor = nn.Sequential(resnet.conv1, resnet.bn1, resnet.relu, resnet.maxpool, resnet.layer1,
                                              resnet.layer2, resnet.layer3, resnet.layer4)
        ccnn_net = CCNN(dset.num_concepts, dset.num_classes, resnet_feat_extractor, train_bs, conv_base_out_fms=2048)
    ccnn_net.train(False)
