from pytorch_lightning.callbacks import EarlyStopping
from pytorch_lightning.callbacks.early_stopping import EarlyStopping


class EarlyStoppingWithWarmup(EarlyStopping):
    """
    EarlyStopping, except don't watch the first `warmup` epochs.
    """

    def __init__(self, warmup=10, **kwargs):
        super().__init__(**kwargs)
        self.warmup = warmup

    def on_train_epoch_end(self, trainer, pl_module):
        pass

    def on_validation_end(self, trainer, pl_module):
        if trainer.current_epoch < self.warmup:
            return
        else:
            super()._run_early_stopping_check(trainer)
