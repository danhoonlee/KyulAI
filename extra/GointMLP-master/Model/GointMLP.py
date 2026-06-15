from torch import Tensor
from torch.nn import GRU
from Model.JointmLP import JointmLP
from Utils.losses import mse_loss, CORAL_loss
from Utils.losses import mae_loss, rmse_loss, R2, CORAL_Accurancy
import torch
import pytorch_lightning as pl


class GointMLP(pl.LightningModule):
    def __init__(
        self,
        input_size: int = 14,
        hidden_size: int = 15,
        gru_num_layers: int = 3,
        jmlp_num_layers: int = 5,
        jmlp_layer_size: int = 64,
        bias: bool = True,
        batch_first: bool = True,
        dropout: int = 0,
        num_nets: int = 15,
        num_classes: int = 4,
        lr: float = 5e-4,
    ):
        super(GointMLP, self).__init__()
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.gru_num_layers = gru_num_layers
        self.num_nets = num_nets
        self.num_classes = num_classes
        self.jmlp_num_layers = jmlp_num_layers
        self.jmlp_layer_size = jmlp_layer_size
        self.lr = lr

        self.jointmlp = JointmLP(
            input_size=self.hidden_size,
            hidden_size=self.num_classes,
            num_nets=self.num_nets,
            num_classes=self.num_classes,
            num_layers=self.jmlp_num_layers,
            layer_size=self.jmlp_layer_size,
        )
        self.gru = GRU(
            input_size=self.input_size,
            hidden_size=self.hidden_size,
            num_layers=self.gru_num_layers,
            bias=bias,
            batch_first=batch_first,
            dropout=dropout,
        )

    def forward(self, input: Tensor):
        outputs, hidden = self.gru(input)
        prediction = self.jointmlp(outputs)

        return prediction

    def training_step(self, batch, batch_idx):
        features, reg_labels, class_labels, loss_mask = batch
        output = self(features)

        l_mse = mse_loss(output, reg_labels, loss_mask)
        l_coral = CORAL_loss(
            output, class_labels, loss_mask, self.num_classes, self.device
        )

        loss = l_mse + l_coral

        self.log("train_loss", loss, prog_bar=True, on_step=False, on_epoch=True)
        self.log("train_loss - l_mse", l_mse, prog_bar=True, on_step=False, on_epoch=True)
        self.log("train_loss - l_coral", l_coral, prog_bar=True, on_step=False, on_epoch=True)
        return loss

    def validation_step(self, batch, batch_idx):
        features, reg_labels, class_labels, loss_mask = batch
        output = self(features)

        l_mse = mse_loss(output, reg_labels, loss_mask)
        l_coral = CORAL_loss(
            output, class_labels, loss_mask, self.num_classes, self.device
        )

        loss = l_mse + l_coral

        self.log("valid_loss", loss, prog_bar=True, on_step=False, on_epoch=True)
        return loss

    # RMSE, R2, MAE 계산
    def test_step(self, batch, batch_idx):
        features, reg_labels, class_labels, loss_mask = batch
        output = self(features)

        output[:, :, 0] = self.trainer.datamodule.pre_proc.inv_transform(output[:, :, 0])
        reg_labels = self.trainer.datamodule.pre_proc.inv_transform(reg_labels)
        
        l_reg = mae_loss(output, reg_labels, loss_mask)
        l_coral = CORAL_loss(
            output, class_labels, loss_mask, self.num_classes, self.device
        )

        loss = l_reg + l_coral

        self.log("Total loss", loss, prog_bar=True, on_step=False, on_epoch=True)
        self.log("Regression Loss", l_reg, prog_bar=True, on_step=False, on_epoch=True)
        self.log("Coral Loss", l_coral, prog_bar=True, on_step=False, on_epoch=True)                
        
    def test_step(self, batch, batch_idx, dataloader_idx=0):
        features, reg_labels, class_labels, loss_mask = batch
        
        output = self(features)
        
        output = self(features).cpu().numpy()
        reg_labels = reg_labels.cpu().numpy()
        
        output[:, :, 0] = self.trainer.datamodule.pre_proc.inv_transform(output[:, :, 0])
        reg_labels[:, :, 0] = self.trainer.datamodule.pre_proc.inv_transform(reg_labels[:, :, 0])
        
        output = torch.Tensor(output).to(self.device)
        reg_labels = torch.Tensor(reg_labels).to(self.device)
        
        _mae_loss = mae_loss(output, reg_labels, loss_mask)
        _rmse_loss = rmse_loss(output, reg_labels, loss_mask)
        _r2 = R2(output, reg_labels, loss_mask)
        
        # Threshold는 나중에 어떻게 할지 고민이 필요
        threshold = torch.Tensor([0.5, 0.5, 0.5]).to(self.device)
        acc = CORAL_Accurancy(output, class_labels, loss_mask, threshold, self.device)
                
        self.log("MAE", _mae_loss, prog_bar=True, on_step=False, on_epoch=True)
        self.log("RMSE", _rmse_loss, prog_bar=True, on_step=False, on_epoch=True)
        self.log("R2", _r2, prog_bar=True, on_step=False, on_epoch=True)
        self.log("Coral Acc", acc, prog_bar=True, on_step=False, on_epoch=True)     
    
    def configure_optimizers(self):
        optimizer = torch.optim.Adam(self.parameters(), lr=self.lr)
        return optimizer
