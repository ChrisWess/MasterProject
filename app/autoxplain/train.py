import warnings

import numpy as np
import torch
from sklearn.metrics import precision_recall_fscore_support, classification_report
from torch.optim.lr_scheduler import ExponentialLR
from torch.utils.data import Dataset, DataLoader

from app.autoxplain.base.trainer import Trainer
from app.autoxplain.model import BaseClassifier, CCNN, ccnn_net, dset, train_bs


class ClassifierTrainer(Trainer):
    def __init__(self, model, train_dataset, val_dataset=None, test_dataset=None, base_dir='model_save',
                 data_dir_name='data', class_names=None, **kwargs):
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
        # self.plot_confusions('test', self.class_names)
        if len(np.unique(pred_all)) == 1:
            pass  # TODO: raise warning and break execution (classification did not result in anything useful)
        precision, recall, f_score, _ = precision_recall_fscore_support(y_all, pred_all, average=metric_avg_type)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            print(classification_report(y_all, pred_all, labels=tuple(range(len(self.class_names))),
                                        target_names=self.class_names, digits=4))
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
                 data_dir_name='data', class_names=None, **kwargs):
        super().__init__(model, train_dataset, val_dataset, test_dataset, base_dir,
                         data_dir_name, class_names, root_dir='app/autoxplain', **kwargs)
        assert isinstance(model, CCNN)
        self.scheduler_kwargs = {'type': ExponentialLR, 'step_every': 10000, 'gamma': 0.96}

    def start_training(self, epochs, lrs, validate=True, evaluate=True, **kwargs):
        return super().start_training(epochs, lrs, validate, evaluate, self.scheduler_kwargs.copy(), **kwargs)

    def set_fc_layer_train_strategy(self):
        self.train_run = self.model.step_train_fc_layers

    def set_regular_train_strategy(self):
        self.train_run = self.model.step_train

    def set_vgg_base_frozen(self, freeze=False, freeze_concept_filters=False):
        if freeze:
            if type(freeze) is int:
                self.model.freeze_conv_base(freeze_concept_filters, freeze)
            else:
                self.model.freeze_conv_base(freeze_concept_filters)
        else:
            self.model.unfreeze_conv_base()


def run_ccnn_training(lr=0.001, load_path=None):
    sampler = torch.utils.data.sampler.BatchSampler(
        torch.utils.data.sampler.RandomSampler(dset),
        batch_size=train_bs,
        drop_last=True)
    tdl = DataLoader(dset, sampler=sampler, num_workers=3)

    val_dset = dset.validation_dataset()
    val_sampler = torch.utils.data.sampler.BatchSampler(
        torch.utils.data.sampler.RandomSampler(val_dset),
        batch_size=64,
        drop_last=True)
    vdl = DataLoader(val_dset, sampler=val_sampler, num_workers=2)

    trainr = CCNNTrainer(ccnn_net, tdl, vdl, load_path=load_path)
    # Train newly added layers first
    trainr.set_vgg_base_frozen(True)
    trainr.start_training(15, lr)
    # Fine-tune all the variables in the network
    lr *= 0.1
    trainr.set_vgg_base_frozen(False)
    # trainr.set_vgg_base_frozen(8)
    trainr.start_training(30, lr)
    # Finally fine-tune the fully connected layer in isolation
    trainr.set_fc_layer_train_strategy()
    trainr.set_vgg_base_frozen(False, True)
    trainr.start_training(10, lr, save_fname='trainer_model.pt')
