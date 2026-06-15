import json
import os


def loadDirAndFileJSON(json_file):
    with open(json_file) as f:
        json_config = json.load(f)

        if "train_dir" not in json_config:
            json_config["train_dir"] = None
            
        if "test_dir" not in json_config:
            json_config["test_dir"] = None

        if "root_save_dir" not in json_config:
            json_config["root_save_dir"] = "./save"

        if "save_ckpt_dir" not in json_config:
            json_config["save_ckpt_dir"] = "./checkpoints"

        if "save_scaler_dir" not in json_config:
            json_config["save_scaler_dir"] = "./scaler"

        if "ckpt_file" not in json_config:
            json_config["ckpt_file"] = None

        if "x_scaler" not in json_config:
            json_config["x_scaler"] = None

        if "y_scaler" not in json_config:
            json_config["y_scaler"] = None

        return json_config


def loadTrainJSON(json_file):
    default_dict = {
        "seed": 123,
        "epochs": 1000,
        "batch_size": 512,
        "max_seq_len": 20,
        "hidden_size": 15,
        "gru_num_layers": 3,
        "jmlp_num_layers": 5,
        "jmlp_layer_size": 64,
        "bias": True,
        "batch_first": True,
        "dropout": 0,
        "learning_rate": 5e-4,
        "num_nets": 15,
        "num_classes": 4,
        "patiences": 50,
        "warmups": 300,
        "val_ratio": 0.1,
    }

    if json_file == None or not os.path.exists(json_file):
        return default_dict

    with open(json_file) as f:
        json_config = json.load(f)

        for key, value in default_dict.items():
            if key not in json_config:
                json_config[key] = value

        return json_config
