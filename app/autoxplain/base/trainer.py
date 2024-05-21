import random
import sys
from abc import ABC, abstractmethod
from collections import defaultdict
from inspect import signature
from pathlib import Path
from time import perf_counter
from typing import Sized

import numpy as np
import torch
import torch.nn.functional as F
from matplotlib import pyplot as plt
from sklearn.metrics import confusion_matrix, ConfusionMatrixDisplay
from torch.optim.lr_scheduler import StepLR
from torch.utils.data import DataLoader
from tqdm import tqdm

from app.autoxplain.base.util import delete_files_recursive, plot

supported_stages = {'train', 'val', 'test'}

_immutable_dl_attrs = {'dataset', 'batch_size', 'batch_sampler', 'sampler',
                       'drop_last', 'persistent_workers', 'shuffle'}
_dl_init_args = set(signature(DataLoader.__init__).parameters)
_dl_init_args.remove('self')


def new_run_dict_factory():
    return defaultdict(list, {'loss': []})


class StageMetrics:
    def __init__(self, trainer, stage):
        self.stage_id = stage
        self.states = trainer.metric_states[stage]
        run_id = trainer.train_run_id if stage != 'test' else trainer.eval_run_id
        self.metrics = trainer.metrics[stage][run_id]
        self.run_id = run_id


class Trainer(ABC):
    def __init__(self, model, train_dataset, val_dataset=None, test_dataset=None,
                 base_dir='model_save', data_dir_name='data', **kwargs):
        self.model = model
        self.model_id = kwargs.pop('model_id', type(self.model).__name__)
        if 'optimizer' in kwargs:
            self.model.setup_training(**kwargs)
        base_dir = Path(base_dir)
        base_dir.mkdir(parents=True, exist_ok=True)
        self.base_dir = base_dir
        self.run_dir = base_dir
        self.eval_dir = base_dir
        self.data_dir_name = data_dir_name
        self.seed = kwargs['seed'] if 'seed' in kwargs else None
        self.train_dl = self.val_dl = self.test_dl = self.metric_states = self.metrics = self.metrics_excluded = None
        self.train_run_id = self.eval_run_id = -1  # -1 denotes that this was not run ever
        self.setup_dataloader(train_dataset, **kwargs)
        if val_dataset is not None:
            self.setup_dataloader(val_dataset, 'val', **kwargs)
        if test_dataset is not None:
            self.setup_dataloader(test_dataset, 'test', **kwargs)
        self.evaluators = {}
        if 'load_path' in kwargs and kwargs['load_path'] is not None:
            self.load_state(kwargs['load_path'])
        else:
            self.reset()

    def train_epochs(self, run_id=None):
        if run_id is None:
            run_id = self.train_run_id
        return len(self.metrics['train'][run_id]['loss'])

    def eval_epochs(self, run_id=None):
        if run_id is None:
            run_id = self.eval_run_id
        return len(self.metrics['test'][run_id]['loss'])

    def reset(self):
        self.train_run_id = self.eval_run_id = -1
        self.metrics_excluded = set()
        self.metric_states = {'train': defaultdict(float),
                              'val': defaultdict(float),
                              'test': defaultdict(float)}
        self.metrics = {'train': defaultdict(new_run_dict_factory),
                        'val': defaultdict(new_run_dict_factory),
                        'test': defaultdict(new_run_dict_factory)}
        self.apply_seed(self.seed)

    def load_state(self, model_path='trainer_model', from_run=None):
        model_path = Path(model_path)
        if not model_path.parent.name:
            if from_run is None:
                model_path = self.base_dir / f'train_{from_run}' / model_path
            else:
                model_path = self.run_dir / model_path
        if not model_path.suffix:
            model_path = model_path.with_suffix('.pt')
        state_dict = self.model.load(model_path)
        self.apply_seed(state_dict['seed'])
        self.metrics = state_dict['metrics']
        self.train_run_id = state_dict['run_train']
        self.eval_run_id = state_dict['run_eval']
        self.metric_states = state_dict['metric_states']
        self.metrics_excluded = state_dict['metrics_excluded']
        self.run_dir = self.base_dir / f'train_{self.train_run_id}'
        self.eval_dir = self.base_dir / f'eval_{self.eval_run_id}'
        print(f'Model loaded from <== {model_path}')

    def save_state(self, save_path='trainer_model'):
        save_path = Path(save_path)
        if not save_path.parent.name:
            save_path = self.run_dir / save_path
        save_path = save_path.with_suffix('.pt')
        self.model.save(save_path, self.metrics, seed=self.seed, run_train=self.train_run_id,
                        run_eval=self.eval_run_id, metric_states=self.metric_states,
                        metrics_excluded=self.metrics_excluded)

    def apply_seed(self, seed=None):
        if seed is not None:
            self.seed = int(seed)
        if seed and self.seed is not None:
            random.seed(self.seed)
            torch.manual_seed(self.seed)

    def setup_dataloader(self, dataset, stage='train', **kwargs):
        assert stage in supported_stages
        kwarg_prefix = f'{stage}_'
        if isinstance(dataset, DataLoader):
            dl = dataset
        else:
            kwargs = kwargs.copy()
            for key in tuple(kwargs.keys()):
                if key.startswith(kwarg_prefix):
                    kwargs[key[len(kwarg_prefix):]] = kwargs.pop(key)
                elif key not in _dl_init_args:
                    del kwargs[key]
            batch_size = kwargs['batch_size'] if 'batch_size' in kwargs else 32
            num_workers = kwargs['num_workers'] if 'num_workers' in kwargs else 4
            pin_memory = kwargs['pin_memory'] if 'pin_memory' in kwargs else True
            dl = DataLoader(dataset, batch_size=batch_size, num_workers=num_workers, pin_memory=pin_memory, **kwargs)
        setattr(self, f'{kwarg_prefix}dl', dl)

    def update_dataloader(self, stage='train', **kwargs):
        assert stage in supported_stages
        assert all(key in _dl_init_args for key in kwargs)
        dl_attr = f'{stage}_dl'
        dl = getattr(self, dl_attr)
        assert dl is not None
        if any(key in _immutable_dl_attrs for key in kwargs):
            sampler_specified = 'sampler' in kwargs and kwargs['sampler'] is not None
            batch_sampler_specified = 'batch_sampler' in kwargs and kwargs['batch_sampler'] is not None
            for dl_arg in _dl_init_args:
                if dl_arg not in kwargs:
                    kwargs[dl_arg] = getattr(dl, dl_arg, None)
            if kwargs['shuffle'] is None:
                kwargs['shuffle'] = False
            elif kwargs['shuffle']:
                if sampler_specified:
                    raise ValueError('sampler option is mutually exclusive with shuffle')
                else:
                    del kwargs['sampler']
            if batch_sampler_specified:
                if any(arg in kwargs for arg in ('batch_size', 'shuffle', 'sampler', 'drop_last')):
                    raise ValueError('batch_sampler option is mutually exclusive '
                                     'with batch_size, shuffle, sampler, and drop_last')
            else:
                del kwargs['batch_sampler']
            setattr(self, dl_attr, DataLoader(**kwargs))
        else:
            for key, val in kwargs.items():
                setattr(dl, key, val)

    def _finish_train_run(self, overwrite):
        self.train_run_id += 1
        self.run_dir = self.base_dir / f'train_{self.train_run_id}'
        if self.run_dir.exists():
            if overwrite:
                delete_files_recursive(self.run_dir)
        else:
            self.run_dir.mkdir()

    def _finish_eval_run(self, overwrite):
        self.eval_run_id += 1
        self.eval_dir = self.base_dir / f'eval_{self.eval_run_id}'
        if self.eval_dir.exists():
            if overwrite:
                delete_files_recursive(self.eval_dir)
        else:
            self.eval_dir.mkdir()

    def finish_run(self, train=True, overwrite=True):
        if train is None:
            self._finish_train_run(overwrite)
            self._finish_eval_run(overwrite)
        elif train:
            self._finish_train_run(overwrite)
        else:
            self._finish_eval_run(overwrite)

    def add_metric_func(self, name, func, stages=None, higher_is_better=True, init_fn=None, display=True):
        if isinstance(stages, str):
            stages = (stages,)
        assert stages is None or all(stage in supported_stages for stage in stages)
        if stages is None:
            stages = supported_stages
        elif isinstance(stages, str):
            stages = {stages}
        else:
            stages = set(stages)
        self.evaluators[name] = (func, stages, higher_is_better, init_fn)
        if not display:
            self.exclude_metric_display(name)

    def remove_metric_func(self, name):
        return self.evaluators.pop(name)

    def exclude_metric_display(self, metric):
        self.metrics_excluded.add(metric)

    def reinclude_metric(self, metric):
        self.metrics_excluded.remove(metric)

    @staticmethod
    def compute_accuracy(y, pred):
        return (pred == y).sum().item()

    @staticmethod
    def compute_rmse(y, pred):
        return np.sqrt(F.mse_loss(pred, y).item()) * y.shape[0]

    @staticmethod
    def compute_l1(y, pred):  # aka mean absolute error
        return F.l1_loss(pred, y).item() * y.shape[0]

    @staticmethod
    def confusions(num_labels):
        def func(y_true, y_pred):
            return confusion_matrix(y_true, y_pred, labels=tuple(range(num_labels)))

        return func

    @staticmethod
    def _init_confusion(last_state=None):
        num_classes = last_state.shape[0]
        return np.zeros((num_classes, num_classes), dtype=int)

    def add_confusion_metric(self, num_classes, stages=None):
        for state in self.metric_states.values():
            state['confusions'] = np.zeros((num_classes, num_classes), dtype=int)
        self.add_metric_func('confusions', self.confusions(num_classes), stages, None, self._init_confusion, False)

    def start_training(self, epochs, lrs, validate=True, evaluate=True, scheduler_kwargs=None, **kwargs):
        overwrite = kwargs['overwrite'] if 'overwrite' in kwargs else True
        if self.train_run_id < 0 or 'new_run' in kwargs and kwargs['new_run']:
            self.finish_run(True, overwrite)
        if 'batch_size' in kwargs:
            self.update_dataloader(stage='train', batch_size=kwargs['batch_size'])
            self.update_dataloader(stage='val', batch_size=kwargs['batch_size'])
        else:
            if 'train_batch_size' in kwargs:
                self.update_dataloader(stage='train', batch_size=kwargs['train_batch_size'])
            if 'val_batch_size' in kwargs:
                self.update_dataloader(stage='val', batch_size=kwargs['val_batch_size'])
        save_fname = kwargs['save_fname'] if 'save_fname' in kwargs else 'trainer_model.pt'
        print_each = kwargs.pop('print_each', 1)
        if isinstance(epochs, Sized) or isinstance(lrs, Sized):
            if isinstance(epochs, Sized) and not isinstance(lrs, Sized):
                lrs = [lrs] * len(epochs)
            elif not isinstance(epochs, Sized) and isinstance(lrs, Sized):
                epochs = [epochs] * len(lrs)
            for ep, lr in zip(epochs, lrs):
                self._train(ep, lr, print_each, validate, scheduler_kwargs)
        else:
            self._train(epochs, lrs, print_each, validate, scheduler_kwargs)
        if evaluate:
            self.run_evaluation(kwargs['stats_fname'] if 'stats_fname' in kwargs else "stat_history.csv",
                                overwrite=overwrite)
        if save_fname:
            self.save_state(self.run_dir / save_fname)

    def _add_metric_batch(self, loss, y, pred, stage):
        states = stage.states
        states['total'] += y.shape[0]
        states['loss'] += loss
        for key, (fn, stages, _, _) in self.evaluators.items():
            if stage.stage_id in stages:
                states[key] += fn(y, pred)

    def _compute_epoch_metrics(self, stage):
        states = stage.states
        metrics = stage.metrics
        total = states['total']
        metrics['loss'].append(states['loss'] / total)
        new_highscores = False if stage.stage_id == 'val' else None
        for key, (_, stages, hbt, inif) in self.evaluators.items():
            if stage.stage_id in stages:
                curr = states[key] / total if inif is None else states[key]
                metrics[key].append(curr)
                if new_highscores is not None and hbt is not None:
                    highscore = f'{key}_highscore'
                    if highscore not in metrics or (hbt and curr > metrics[highscore]) or (
                            not hbt and curr < metrics[highscore]):
                        metrics[highscore] = curr
                        if new_highscores is False:
                            new_highscores = key
                states[key] = 0.0 if inif is None else inif(states[key])
        states['loss'] = 0.0
        states['total'] = 0.0
        if new_highscores:
            self.save_state(self.run_dir / f'{new_highscores}_highscore')

    def _validate(self, epoch_iter, postfix, plotting):
        self.model.eval()
        c = 0
        metstage = StageMetrics(self, 'val')
        epoch_iter.set_postfix_str(f'{postfix}validating...')
        with torch.no_grad():
            for x, y, *z in self.val_dl:
                if x.ndim > 4:
                    x = torch.squeeze(x, dim=0)
                if y.ndim > 1:
                    y = y.reshape(-1)
                loss, pred = self.model.step_eval(x, y, *z)
                self._add_metric_batch(loss, y, pred, metstage)
                c = c % 3 + 1
                epoch_iter.set_postfix_str(f"{postfix}validating{'.' * c}")
        self._compute_epoch_metrics(metstage)
        if plotting and self.train_epochs() >= 2:
            epochs = self.train_epochs()
            pass  # TODO: make option to show plot(s) at the end of validation

    def _train(self, epochs=10, lr=0.001, print_each=5, validate=True, scheduler_kwargs=None, **kwargs):
        validate = validate and self.val_dl is not None
        parameters = filter(lambda p: p.requires_grad, self.model.parameters())
        device = kwargs.pop('device', None)
        val_plot = kwargs.pop('plot', False)
        if lr:
            criterion = kwargs.pop('criterion', None)
            optimizer = kwargs.pop('opt_type', None)
            if optimizer is None:
                if self.model.optimizer is None:
                    optimizer = torch.optim.Adam
                elif type(self.model.optimizer) is type:
                    optimizer = self.model.optimizer
                else:
                    optimizer = type(self.model.optimizer)
            optimizer = optimizer(parameters, lr=lr, **kwargs)
            self.model.setup_training(optimizer, criterion, device=device)
            if scheduler_kwargs is not None:
                if 'type' in scheduler_kwargs:
                    scheduler_type = scheduler_kwargs['type']
                else:
                    scheduler_type = StepLR
                self.model.add_lr_scheduler(scheduler_type, **scheduler_kwargs)
        else:
            assert self.model.optimizer is not None
            if device is not None:
                self.model.set_device(device)
        print(f"Starting training of {epochs} epochs on {self.model.device}...")
        epoch_iter = tqdm(range(epochs), unit='epoch', file=sys.stdout)
        metstage = StageMetrics(self, 'train')
        postfix = ""
        for i in epoch_iter:
            self.model.train()
            start = perf_counter()
            for j, (x, y, *z) in enumerate(self.train_dl, start=1):
                if x.ndim > 4:
                    x = torch.squeeze(x, dim=0)
                if y.ndim > 1:
                    y = y.reshape(-1)
                loss, pred = self.model.step_train(x, y, *z)
                self._add_metric_batch(loss, y, pred, metstage)
                epoch_iter.set_postfix_str(f"{postfix}avg step time: {(perf_counter() - start) / j:.3f}")
            self._compute_epoch_metrics(metstage)
            if validate:
                self._validate(epoch_iter, postfix, val_plot)
            if i % print_each == 0:
                print_stage = 'val' if validate else 'train'
                run_id = self.train_run_id
                postfix = ' | '.join(f'{print_stage} {key} {self.metrics[print_stage][run_id][key][-1]:.3f}'
                                     for key in self.evaluators if key not in self.metrics_excluded)
                postfix = f"{postfix} | "
                epoch_iter.set_postfix_str(postfix[:-3])

    def run_evaluation(self, stats_fname='eval_stats', test_dset=None, plot_prefix=None, **kwargs):
        if self.eval_run_id < 0 or 'new_run' in kwargs and kwargs['new_run']:
            overwrite = kwargs['overwrite'] if 'overwrite' in kwargs else True
            self.finish_run(False, overwrite)
        self.model.eval()
        save_dir = self.eval_dir / f'results_for_{self.model_id}'
        stats_fname = self.eval_dir / stats_fname
        save_dir.mkdir(parents=True, exist_ok=True)

        if test_dset is not None:
            self.setup_dataloader(test_dset, stage='test', **kwargs)
        assert self.test_dl is not None or self.val_dl is not None
        test_dl = self.val_dl if self.test_dl is None else self.test_dl
        metstage = StageMetrics(self, 'test')

        self._full_evaluation(save_dir, stats_fname, metstage, test_dl, **kwargs)
        plt_metrics = kwargs['plot_metrics'] if 'plot_metrics' in kwargs else None
        self.plot_metrics(plt_metrics, save_dir.name, plot_prefix)
        if 'save_fname' in kwargs:
            save_fname = self.eval_dir / kwargs['save_fname']
            self.save_state(save_fname)

    @abstractmethod
    def _full_evaluation(self, save_dir, stats_fname, metstage, test_dl, **kwargs):
        pass

    def _get_metric_names(self, metrics):
        if metrics is None:
            return [mm for mm in self.evaluators.keys() if mm not in self.metrics_excluded]
        else:
            return list(metrics)

    def _get_plot_dir(self, save_dirname, train, parents):
        if save_dirname.is_absolute():
            stage = 'train' if train else 'eval'
            save_dir = save_dirname / stage
        else:
            stage = self.run_dir if train else self.eval_dir
            save_dir = stage / save_dirname
        if parents:
            save_dir.mkdir(parents=True, exist_ok=True)
        else:
            save_dir.mkdir(exist_ok=True)
        return save_dir

    @staticmethod
    def _evaluate_stage(stages, check_stage):
        return stages is True or check_stage in stages

    def plot_metrics(self, metrics=None, save_dirname='metric_plots', plot_prefix=None, stages=None, **kwargs):
        save_dirname = Path(save_dirname)
        if stages is None:
            stages = supported_stages
        else:
            if isinstance(stages, str):
                stages = {stages}
            else:
                stages = set(stages)
            assert all(stage in supported_stages for stage in stages)
        if stages:
            make_parents = kwargs['make_parent_dirs'] if 'make_parent_dirs' in kwargs else False
            metric_names = self._get_metric_names(metrics)
            metric_names.append('loss')
            if self.train_run_id >= 0 and ('train' in stages or 'val' in stages):
                run_id = self.train_run_id
                train_metrs = self.metrics['train'][run_id]
                num_eps = len(train_metrs['loss'])
                if num_eps >= 2:
                    # plot train progress
                    epochs = np.arange(1, num_eps + 1)
                    save_dir = self._get_plot_dir(save_dirname, True, make_parents)
                    val_metrs = self.metrics['val'][run_id]
                    for metr in metric_names:
                        if metr not in self.metrics_excluded:
                            y = labels = stage_titles = None
                            metr_stages = True if metr == 'loss' else self.evaluators[metr][1]
                            if 'train' in stages and self._evaluate_stage(metr_stages, 'train'):
                                if 'val' in stages and self._evaluate_stage(metr_stages, 'val'):
                                    y = (train_metrs[metr], val_metrs[metr])
                                    labels = ('train', 'val')
                                    stage_titles = 'training and validation'
                                else:
                                    y = train_metrs[metr]
                                    labels = 'train'
                                    stage_titles = 'training'
                            elif 'val' in stages and self._evaluate_stage(metr_stages, 'val'):
                                y = val_metrs[metr]
                                labels = 'val'
                                stage_titles = 'validation'
                            if y is not None:
                                path = save_dir / metr if plot_prefix is None else save_dir / f'{plot_prefix}_{metr}'
                                plot(epochs, y, f'{stage_titles} {metr}', 'epoch',
                                     metr, path.with_suffix('.jpg'), labels=labels)
                elif num_eps == 1:
                    pass
            if self.eval_run_id >= 0 and 'test' in stages:
                # plot eval progress
                save_dir = self._get_plot_dir(save_dirname, False, make_parents)
                test_metrs = self.metrics['test'][self.eval_run_id]
                num_evals = len(test_metrs['loss'])
                if num_evals >= 2:
                    epochs = np.arange(1, num_evals + 1)
                    for metr in metric_names:
                        metr_stages = True if metr == 'loss' else self.evaluators[metr][1]
                        if metr not in self.metrics_excluded and self._evaluate_stage(metr_stages, 'test'):
                            path = save_dir / metr if plot_prefix is None else save_dir / f'{plot_prefix}_{metr}'
                            plot(epochs, test_metrs[metr], f'test {metr}', 'epoch', metr, path.with_suffix('.jpg'))
                elif num_evals == 1:
                    pass  # TODO: use better output when having only one evaluation (don't plot)

    def plot_confusions(self, confusions, class_names=None, normalize=True, save_dir=None):
        if isinstance(confusions, str):
            assert confusions in self.evaluators['confusions'][1]
            run_id = self.eval_run_id if confusions == 'test' else self.train_run_id
            confusions = self.metrics[confusions][run_id]['confusions'][-1]
        if normalize:
            confusions = confusions / confusions.sum(axis=0)
        disp = ConfusionMatrixDisplay(confusion_matrix=confusions, display_labels=class_names)
        disp.plot()
        if save_dir:
            plt.savefig(save_dir / 'confusion_matrix.jpg')
        plt.show()

    def _write_to_csv(self, fname, stage, metrics, run_ids, overwrite):
        fname = fname.with_name(f'{stage}_{fname.stem}.csv')
        if overwrite or not fname.exists():
            with open(fname, 'w') as file:
                head = ','.join(metrics)
                file.write(f'run_id,{head}\n')
        m = self.metrics[stage]
        if run_ids is None:
            run_ids = tuple(m.keys())
        elif isinstance(run_ids, int):
            assert run_ids in m
            run_ids = (run_ids,)
        elif run_ids == 'current':
            rid = self.eval_run_id if stage == 'test' else self.train_run_id
            run_ids = (rid,)
        else:
            assert run_ids in m
        for rid in run_ids:
            run = m[rid]
            for metrs in zip(run[name] for name in metrics):
                metrs = [str(round(mt, 4)) for mt in metrs]
                metrs.insert(0, str(rid))
                with open(fname, 'a') as file:
                    stats = ','.join(metrs)
                    file.write(f'{stats}\n')

    def metrics_to_csv(self, fname, stages=None, metrics=None, run_ids=None, overwrite=False):
        # if current_run is False, then write all runs to CSV file
        fname = Path(fname)
        metrics = self._get_metric_names(metrics)
        if stages is None:
            stages = supported_stages
        elif isinstance(stages, str):
            self._write_to_csv(fname, stages, metrics, run_ids, overwrite)
            return
        for stage in stages:
            self._write_to_csv(fname, stage, metrics, run_ids, overwrite)
