import datetime as datetime
import click
from Utils.loadJson import loadDirAndFileJSON, loadTrainJSON
from Dataloader.dataModule import GointMLPDataModule
from Model.GointMLP import GointMLP
from pytorch_lightning import Trainer
from Utils.callback import EarlyStoppingWithWarmup
from pytorch_lightning.callbacks import ModelCheckpoint
import pytorch_lightning as pl
from Dataloader.preprocessor import Preprocessor
from Dataloader.data import load_data_for_np
import torch
from Utils.utils import proba_to_label
import os
from Dataloader.data import load_csv_files, shuffle_together_and_split

@click.command()
@click.option(
    "--mode",
    required=True,
    type=click.Choice(["fit", "test", "pred"]),
    help='Operation Mode (fit, test, pred)'
)
@click.option("--dir_file_config", type=str, required=True, default=None, help='Config json file for directories and files.')
@click.option("--model_config", type=str, default=None, help='Config json file for GointMLP parameters.')
@click.option("--no_save_scaler", type=bool, default=False, help='Whether to save the Min/Max Scaler pickle file.')
@click.option("--csv_file", type=str, default=None, help='CSV file for predction mode.')
@click.option("--devices", type=int, default=1, help='Number of devices.')
@click.option("--seed", type=int, default=123, help='Seed for random number generation.')


def main(
    mode,
    dir_file_config,
    model_config,
    no_save_scaler,
    csv_file,
    devices,
    seed,
):
    dir_file_json = loadDirAndFileJSON(dir_file_config)
    model_json = loadTrainJSON(model_config)

    pl.seed_everything(seed)
    
    gointMLP = GointMLP(
        input_size=model_json["input_size"],
        hidden_size=model_json["hidden_size"],
        gru_num_layers=model_json["gru_num_layers"],
        jmlp_num_layers=model_json["jmlp_num_layers"],
        jmlp_layer_size=model_json["jmlp_layer_size"],
        bias=model_json["bias"],
        batch_first=model_json["batch_first"],
        dropout=model_json["dropout"],
        num_nets=model_json["num_nets"],
        num_classes=model_json["num_classes"],
        lr=model_json["learning_rate"],
    )
    
    pre_proc = Preprocessor(
        x_scaler_file=dir_file_json["x_scaler"],
        y_scaler_file=dir_file_json["y_scaler"],
        no_save_scaler=no_save_scaler,
        save_dir=dir_file_json["save_scaler_dir"],
    )
    
    if mode == "fit":     
        if dir_file_json["train_dir"] is None:
            raise TypeError("the train_dir is None. Please check it")
        
        # For Multi-GPU        
        train_dataset = load_csv_files(dir_file_json["train_dir"])
        dict_val, dict_train = shuffle_together_and_split(train_dataset, model_json["val_ratio"])
        pre_proc.fit(data=dict_train)
        
        dataModule = GointMLPDataModule(
            dir_file_json=dir_file_json,
            batch_size=model_json["batch_size"],
            max_seq_len=model_json["max_seq_len"],            
            pre_proc=pre_proc,
            train=dict_train,
            val=dict_val,
            no_save_scaler=no_save_scaler,
            num_worker = os.cpu_count() if devices == 1 else 1
        )
        
        # Callbacks
        early_stopping_callback = EarlyStoppingWithWarmup(
            warmup=model_json["warmups"],
            monitor="valid_loss",
            mode="min",
            patience=model_json["patiences"],
        )
        checkpoint_callbacks = ModelCheckpoint(
            dirpath=dir_file_json["save_ckpt_dir"], monitor="valid_loss", mode="min"
        )

        trainer = Trainer(
            max_epochs=model_json["epochs"],
            accelerator="auto",
            devices=devices,
            logger=False,
            callbacks=[early_stopping_callback, checkpoint_callbacks],
            enable_progress_bar=True,
        )
        
        if dir_file_json["ckpt_file"] is not None:
            _file_name = dir_file_json["ckpt_file"]
            print(f"Found the settings of {_file_name}. This weight is loaded.")
            gointMLP = gointMLP.load_from_checkpoint(dir_file_json["ckpt_file"])
            

        trainer.fit(model=gointMLP, datamodule=dataModule)
        trainer.test(model=gointMLP, ckpt_path='best', datamodule=dataModule)

    elif mode == "test":        
        dataModule = GointMLPDataModule(
            dir_file_json=dir_file_json,
            batch_size=model_json["batch_size"],
            max_seq_len=model_json["max_seq_len"],
            pre_proc = pre_proc,
            no_save_scaler=no_save_scaler,
            num_worker = os.cpu_count() if devices == 1 else 1
        )
        
        if dir_file_json["ckpt_file"] is None:
            raise TypeError("the ckpt_file is None. Please check it")
        
        gointMLP = gointMLP.load_from_checkpoint(dir_file_json["ckpt_file"]).eval()
        
        if dir_file_json["x_scaler"] is None or dir_file_json["y_scaler"] is None:
            raise TypeError("the x_scaler or y_scaler file is None. Please check them")
        
        trainer = Trainer(            
            accelerator="auto",
            devices=1,
            logger=False,            
            enable_progress_bar=True,
        )      
        
        trainer.test(gointMLP, datamodule=dataModule)
    
    elif mode == "pred":
        if csv_file == None:
            raise TypeError("the csv_file is None. Please check it")                
        
        if dir_file_json["ckpt_file"] is None:
            raise TypeError("the ckpt_file is None. Please check it")              
        
        if dir_file_json["x_scaler"] is None or dir_file_json["y_scaler"] is None:
            raise TypeError("the x_scaler or y_scaler file is None. Please check them")
        
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        threshold = torch.Tensor([0.5, 0.5, 0.5])
        gointMLP = gointMLP.load_from_checkpoint(dir_file_json["ckpt_file"]).to(device).eval()
        
        pre_proc = Preprocessor(
            x_scaler_file=dir_file_json["x_scaler"],
            y_scaler_file=dir_file_json["y_scaler"],
            pre_proc = pre_proc,
            no_save_scaler=no_save_scaler,
            save_dir=dir_file_json["save_scaler_dir"]
        )
        
        data = load_data_for_np(csv_file)
        
        data = pre_proc.transform_x(data=data)

        data = torch.from_numpy(data).float().to(device)
        data = torch.unsqueeze(data, dim=0)        
                
        output = gointMLP(data).detach().cpu()
        output_reg, output_cls = output[:,:, 0], output[:,:, 1:]
        
        output_cls = torch.sigmoid(output_cls)                        
        class_pred_labels = proba_to_label(output_cls, threshold)
        
        output_reg = pre_proc.inv_transform(output_reg.detach().cpu().numpy())
        print(f"TDM Value : {output_reg[0, -1]:.2f}, Class : {class_pred_labels[0, -1]}")        


if __name__ == "__main__":
    main()