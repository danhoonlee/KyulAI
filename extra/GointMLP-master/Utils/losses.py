import torch
import torch.nn as nn
from Utils.utils import levels_from_labelbatch, proba_to_label
import torch.nn.functional as F
from torchmetrics.functional.regression import r2_score
from torchmetrics import Accuracy

def R2(output: torch.Tensor, reg_labels, loss_mask):
    _regression_logits = output[:, :, 0].unsqueeze(-1)

    _regression_logits = torch.masked_select(_regression_logits, loss_mask)
    _reg_labels = torch.masked_select(reg_labels, loss_mask)
    
    return r2_score(_regression_logits, _reg_labels)

def mae_loss(output: torch.Tensor, reg_labels, loss_mask):
    _regression_logits = output[:, :, 0].unsqueeze(-1)

    _regression_logits = torch.masked_select(_regression_logits, loss_mask)
    _reg_labels = torch.masked_select(reg_labels, loss_mask)

    # MAE Loss ----------------------------------------------
    real_size = loss_mask.sum()
    mae_reg = torch.abs(_regression_logits - _reg_labels)
    mae_reg = mae_reg.sum() / real_size
    
    return mae_reg

def rmse_loss(output: torch.Tensor, reg_labels, loss_mask):
    return torch.sqrt(mse_loss(output, reg_labels, loss_mask))


def mse_loss(output: torch.Tensor, reg_labels, loss_mask):
    _regression_logits = output[:, :, 0].unsqueeze(-1)

    _regression_logits = torch.masked_select(_regression_logits, loss_mask)
    _reg_labels = torch.masked_select(reg_labels, loss_mask)

    # Reg Loss ----------------------------------------------
    real_size = loss_mask.sum()
    loss_reg = (_regression_logits - _reg_labels) ** 2    
    loss_reg = loss_reg.sum() / real_size
    
    return loss_reg


def CORAL_loss(output: torch.Tensor, class_labels, loss_mask, num_classes, device):
    # Convert class labels for CORAL ------------------------
    levels = [
        levels_from_labelbatch(label, num_classes=num_classes) for label in class_labels
    ]
    levels = torch.stack(levels, dim=0).to(device)

    # Masking
    classification_logits = output[:, :, 1:]    

    # Loss --------------------------------------------------
    # CORAL Loss --------------------------------------------
    _levels=levels.type_as(classification_logits)
    term1 = (F.logsigmoid(classification_logits)*_levels
                      + (F.logsigmoid(classification_logits) - classification_logits)*(1-_levels))
    val = (-torch.sum(term1 * loss_mask, dim=1))
    
    # 실 값만 Loss에 반영
    real_size = loss_mask.sum()
    loss = torch.sum(val) / real_size    

    return loss

def CORAL_Accurancy(output: torch.Tensor, class_labels, loss_mask, threshold, device):            
    # Masking
    _classification_logits = torch.sigmoid(output[:, :, 1:])
    class_pred_labels = proba_to_label(_classification_logits, threshold)
    
    _class_labels = class_labels
    
    _loss_mask = torch.squeeze(loss_mask, dim=-1)
        
    class_pred_labels = torch.masked_select(class_pred_labels, _loss_mask)
    _class_labels = torch.masked_select(_class_labels, loss_mask)
    
    acc = Accuracy(task="multiclass", num_classes=4).to(device=device)
    
    return acc(class_pred_labels, _class_labels)
    