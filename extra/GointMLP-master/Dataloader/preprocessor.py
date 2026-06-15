import numpy as np
import os
import joblib
from sklearn.preprocessing import MinMaxScaler
import copy


class Preprocessor:
    def __init__(
        self,
        x_scaler_file=None,
        y_scaler_file=None,
        no_save_scaler=False,
        save_dir="./scaler",
    ):
        self.loaded = False
        self.no_save_scaler = no_save_scaler
        self.save_dir = save_dir
        
        if x_scaler_file is not None and y_scaler_file is not None:
            self.x_scaler = joblib.load(x_scaler_file)
            self.y_scaler = joblib.load(y_scaler_file)
            self.loaded = True
            self.no_save_scaler = True
            print(f"loaded scaler")
        else:
            self.x_scaler = MinMaxScaler(feature_range=(-1, 1))
            self.y_scaler = MinMaxScaler(feature_range=(-1, 1))        

    # load_file은 2개의 리스트 가정함
    def fit(self, data):
        if not self.loaded:
            total_x = np.concatenate(data["x"], axis=0)
            total_y = np.concatenate(data["reg_y"], axis=0)

            self.x_scaler.fit(total_x)
            self.y_scaler.fit(total_y)

        if not self.no_save_scaler:
            path_x_scaler = os.path.join(self.save_dir, "x_scaler.pkl")
            path_y_scaler = os.path.join(self.save_dir, "y_scaler.pkl")

            if not os.path.exists(self.save_dir):
                os.makedirs(self.save_dir, 0o775, exist_ok=True)

            joblib.dump(
                self.x_scaler,
                path_x_scaler,
            )
            joblib.dump(
                self.y_scaler,
                path_y_scaler,
            )
            print(f"scaler saved")

    def transform(self, data):
        _data = copy.deepcopy(data)
        for i, (x, y) in enumerate(zip(_data["x"], _data["reg_y"])):
            _data["x"][i] = self.x_scaler.transform(x)
            _data["reg_y"][i] = self.y_scaler.transform(y)

        return _data
    
    def transform_x(self, data):
        _data = copy.deepcopy(data)
        _data = self.x_scaler.transform(_data)        
        return _data

    def inv_transform(self, data):
        return self.y_scaler.inverse_transform(data)
