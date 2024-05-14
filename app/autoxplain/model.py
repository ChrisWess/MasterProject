from abc import ABC, abstractmethod

import numpy as np
import torch
import torch.nn as nn
import torchvision
from torch.nn.utils.clip_grad import clip_grad_norm
from torchvision.models import VGG19_Weights


class BaseModel(nn.Module, ABC):
    def __init__(self, device, clip_value=None, optimizer=torch.optim.Adam, criterion=None):
        super().__init__()
        self.optimizer = optimizer
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
        self.optimizer.zero_grad()
        if loss is None:
            loss = self.criterion(y_pred, target)
        loss.backward()
        if self.clip_value is not None:
            clip_grad_norm(self.parameters(), self.clip_value)
        self.optimizer.step()
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

    @staticmethod
    def determine_bin(y_hat, thresh=0):
        return torch.where(y_hat > thresh, 1, 0)

    @staticmethod
    def determine_multi(y_hat):
        return torch.argmax(y_hat, dim=1)

    def infer(self, x, thresh=0, lengths=None):
        with torch.no_grad():
            x = torch.atleast_2d(torch.LongTensor(x)).to(self.device)
            lengths = torch.LongTensor(lengths)
            y_hat = self(x, lengths)
            if self.num_classes == 2:
                return self.determine_bin(y_hat, thresh)
            else:
                return self.determine_multi(y_hat)


class CCNN(BaseClassifier):
    def __init__(self, num_concepts, num_classes, device=None, clip_value=None, optimizer=torch.optim.Adam,
                 word_vec_size=50, embeds_size=40, dropout_rate=0.5):
        super(CCNN, self).__init__(num_classes, device, clip_value, optimizer, nn.CrossEntropyLoss())
        self.cls_indicator_vectors = torch.tensor(
            np.load('app/autoxplain/base/data/class_indicator_vectors.npy').astype(np.float32) * 0.1)
        self._vgg_weights = VGG19_Weights.DEFAULT
        self._vgg_preproc = self._vgg_weights.transforms()
        self.head = torchvision.models.vgg19(self._vgg_weights).features
        self.maxpool = nn.MaxPool2d(kernel_size=2, stride=2)
        self.concept_kernels = nn.Conv2d(512, num_concepts, kernel_size=1)
        self.dropout = nn.Dropout(p=dropout_rate)
        self.v_e_converter = nn.Linear(351, embeds_size)  # visual embedding layer
        self.w_e_converter = nn.Linear(word_vec_size, embeds_size)  # word embedding layer
        self.classifier = nn.Linear(num_concepts, num_classes)
        with torch.no_grad():
            # initialize classifier layer from class indicators, which
            # allows only all possible concepts for a class as outputs.
            self.classifier.weight.copy_(self.cls_indicator_vectors.T)

    @staticmethod
    def global_avg_pool(x: torch.Tensor) -> torch.Tensor:
        # Global average pooling over axes Width and Height
        return torch.mean(x, dim=(2, 3))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self._vgg_preproc(x)
        x = self.head(x)
        x = self.maxpool(x)
        print(x.shape)
        x = self.concept_kernels(x)
        print(x.shape)
        x = self.dropout(x)
        exit()
        return x

    def classify(self, x: torch.Tensor) -> torch.Tensor:
        return self.classifier(x)

    def combine_loss(self, y_hat: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
        pass  # TODO: combine the different CCNN losses and use this as criterion

    def step_train(self, x, y):
        x = x.to(self.device, torch.float32)
        y = y.to(self.device, self._label_dtype)
        y_pred = self.classify(self.global_avg_pool(self(x)))
        return self.update_step(y_pred, y)

    def step_eval(self, x, y):
        x = x.to(self.device, torch.float32)
        y = y.to(self.device, self._label_dtype)
        y_hat = self(x)
        loss = self.criterion(y_hat, y)
        loss = loss.item() * y.shape[0]
        pred = self._pred_fn(y_hat)
        return loss, pred.cpu()
