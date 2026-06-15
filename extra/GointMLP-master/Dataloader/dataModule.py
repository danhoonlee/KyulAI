from Dataloader.preprocessor import Preprocessor
from Dataloader.data import load_csv_files, shuffle_together_and_split
import torch
from torch.utils.data import Dataset
from torch.utils.data import DataLoader
import numpy as np

from pytorch_lightning import LightningDataModule


class SequenceDataset(Dataset):
    def __init__(self, data, max_seq_len=-1):
        self._x = data["x"]
        self._reg_y = data["reg_y"]
        self._class_y = data["class_y"]
        self._max_seq_len = max_seq_len        
    
    def __getitem__(self, idx):
        x = self._x[idx]
        reg_y = self._reg_y[idx]
        class_y = self._class_y[idx]
        seq_len = len(x)

        if self._max_seq_len == -1:
            max_seq_len = seq_len
        else:
            max_seq_len = self._max_seq_len

        if seq_len >= max_seq_len:
            start_idx = np.random.choice(range(0, seq_len - max_seq_len + 1))
            stop_idx = start_idx + max_seq_len

            x = x[start_idx:stop_idx]
            reg_y = reg_y[start_idx:stop_idx]
            class_y = class_y[start_idx:stop_idx]

            # Two masks one for regression and one for CORAL(classification)
            loss_mask = np.ones((max_seq_len, 1))
            reg_y_mask = np.where(np.isnan(reg_y))[0]

            loss_mask[reg_y_mask] = 0

        else:
            pad1 = np.zeros((max_seq_len - seq_len, x.shape[1]))
            pad2 = np.zeros((max_seq_len - seq_len, 1))

            x = np.concatenate([x, pad1], axis=0)
            reg_y = np.concatenate([reg_y, pad2], axis=0)
            class_y = np.concatenate([class_y, pad2], axis=0)

            # Two masks one for regression and one for CORAL(classification)
            loss_mask = np.concatenate(
                [np.ones((seq_len, 1)), np.zeros((max_seq_len - seq_len, 1))], axis=0
            )
            reg_y_mask = np.where(np.isnan(reg_y))[0]

            loss_mask[reg_y_mask] = 0

        # FOR RNN, GRU, and LSTM
        x = torch.tensor(x, dtype=torch.float32)
        reg_y = torch.tensor(reg_y, dtype=torch.float32)
        class_y = torch.tensor(class_y, dtype=torch.float32)
        loss_mask = torch.tensor(loss_mask, dtype=torch.bool)

        return x, reg_y, class_y, loss_mask

    def __len__(self):
        return len(self._x)

from torch.nn.utils.rnn import pad_sequence

def custom_collate_fn(batch):
    # Unzip the batch
    x, reg_y, class_y, loss_mask = zip(*batch)
    
    # Pad sequences dynamically
    x_padded = pad_sequence(x, batch_first=True, padding_value=0)
    reg_y_padded = pad_sequence(reg_y, batch_first=True, padding_value=torch.nan)
    class_y_padded = pad_sequence(class_y, batch_first=True, padding_value=0)
    loss_mask_padded = pad_sequence(loss_mask, batch_first=True, padding_value=False)

    return x_padded, reg_y_padded, class_y_padded, loss_mask_padded

class GointMLPDataModule(LightningDataModule):
    def __init__(
        self, dir_file_json, batch_size, max_seq_len, pre_proc, 
        train=None, val=None,
        no_save_scaler=False, num_worker=1
    ):
        super().__init__()
        self.dir_file_json = dir_file_json        
        self.no_save_scaler = no_save_scaler
        self.batch_size = batch_size
        self.max_seq_len = max_seq_len
        self.pre_proc = pre_proc
        self.num_worker = num_worker
        self.train = train
        self.val = val

    def setup(self, stage):                                  
        if stage == "fit":              
            self.train = self.pre_proc.transform(self.train)
            self.val = self.pre_proc.transform(self.val)

            self.train = SequenceDataset(self.train, -1)
            self.val = SequenceDataset(self.val, -1)
            
        if stage == "test":
            if self.dir_file_json["test_dir"] == None:
                self.test = None
            else:
                test_paths = self.dir_file_json["test_dir"]
                            
                # 한 개의 Test만 들어왔다고 가정
                if isinstance(test_paths, str):
                    test_paths = [test_paths]
                
                test_Dataset = []                        
                
                for test in test_paths:
                    test_dataset = load_csv_files(test)
                    dict_test = self.pre_proc.transform(test_dataset)
                    temp_test_dataset = SequenceDataset(dict_test, -1)
                    test_Dataset.append(temp_test_dataset)
                    
                self.test = test_Dataset

    def train_dataloader(self):
        if self.train == None:
            return None
        else:            
            return DataLoader(dataset=self.train, batch_size=self.batch_size, shuffle=True, num_workers=self.num_worker, collate_fn=custom_collate_fn)

    def val_dataloader(self):
        if self.train == None:
            return None
        else:            
            return DataLoader(dataset=self.val, batch_size=self.batch_size, shuffle=False, num_workers=self.num_worker, collate_fn=custom_collate_fn)

    def test_dataloader(self):
        if self.test == None:
            return None
        elif len(self.test) == 1:
            return DataLoader(
                dataset=self.test[0], batch_size=self.batch_size, shuffle=False, num_workers=self.num_worker, collate_fn=custom_collate_fn
            )
        else:
            dataloader_list = []
            for t in self.test:
                dataloader_list.append(                    
                    DataLoader(dataset=t,  batch_size=self.batch_size, shuffle=False, num_workers=self.num_worker, collate_fn=custom_collate_fn)
                )
        return dataloader_list
