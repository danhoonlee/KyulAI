import pickle
import os
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from mlxtend.evaluate import bootstrap
import pandas as pd
import torch
import numpy as np


def label_to_levels(label, num_classes, dtype=torch.float32):
    """Converts integer class label to extended binary label vector

    Parameters
    ----------
    label : int
        Class label to be converted into a extended
        binary vector. Should be smaller than num_classes-1.

    num_classes : int
        The number of class clabels in the dataset. Assumes
        class labels start at 0. Determines the size of the
        output vector.

    dtype : torch data type (default=torch.float32)
        Data type of the torch output vector for the
        extended binary labels.

    Returns
    ----------
    levels : torch.tensor, shape=(num_classes-1,)
        Extended binary label vector. Type is determined
        by the `dtype` parameter.

    Examples
    ----------
    >>> label_to_levels(0, num_classes=5)
    tensor([0., 0., 0., 0.])
    >>> label_to_levels(1, num_classes=5)
    tensor([1., 0., 0., 0.])
    >>> label_to_levels(3, num_classes=5)
    tensor([1., 1., 1., 0.])
    >>> label_to_levels(4, num_classes=5)
    tensor([1., 1., 1., 1.])
    """
    if not label <= num_classes - 1:
        raise ValueError(
            "Class label must be smaller or "
            "equal to %d (num_classes-1). Got %d." % (num_classes - 1, label)
        )
    if isinstance(label, torch.Tensor):
        int_label = label.item()
    else:
        int_label = label

    levels = [1] * int(int_label) + [0] * (num_classes - 1 - int(int_label))
    levels = torch.tensor(levels, dtype=dtype)
    return levels


def levels_from_labelbatch(labels, num_classes, dtype=torch.float32):
    """
    Converts a list of integer class label to extended binary label vectors

    Parameters
    ----------
    labels : list or 1D orch.tensor, shape=(num_labels,)
        A list or 1D torch.tensor with integer class labels
        to be converted into extended binary label vectors.

    num_classes : int
        The number of class clabels in the dataset. Assumes
        class labels start at 0. Determines the size of the
        output vector.

    dtype : torch data type (default=torch.float32)
        Data type of the torch output vector for the
        extended binary labels.

    Returns
    ----------
    levels : torch.tensor, shape=(num_labels, num_classes-1)

    Examples
    ----------
    >>> levels_from_labelbatch(labels=[2, 1, 4], num_classes=5)
    tensor([[1., 1., 0., 0.],
            [1., 0., 0., 0.],
            [1., 1., 1., 1.]])
    """
    levels = []
    for label in labels:
        levels_from_label = label_to_levels(
            label=label, num_classes=num_classes, dtype=dtype
        )
        levels.append(levels_from_label)

    levels = torch.stack(levels)
    return levels


def proba_to_label(probas, thresh: float):
    """
    Converts predicted probabilities from extended binary format
    to integer class labels

    Parameters
    ----------
    probas : torch.tensor, shape(n_examples, n_labels)
        Torch tensor consisting of probabilities returned by CORAL model.

    Examples
    ----------
    >>> # 3 training examples, 6 classes
    >>> probas = torch.tensor([[0.934, 0.861, 0.323, 0.492, 0.295],
    ...                        [0.496, 0.485, 0.267, 0.124, 0.058],
    ...                        [0.985, 0.967, 0.920, 0.819, 0.506]])
    >>> proba_to_label(probas)
    tensor([2, 0, 5])
    """
    predict_levels = probas > thresh
    predicted_labels = torch.sum(predict_levels, dim=2)
    return predicted_labels


def get_save_dir(save_dir, drop_id_path, drop_vars, tau, seed):
    if drop_id_path is None:
        drop_id_name = "None"
    else:
        drop_id_name = str(drop_id_path).split("/")[-1].split(".")[0]
    if drop_vars is None:
        drop_vars_name = "None"
    else:
        drop_vars_name = "drop:" + ",".join(drop_vars)
    tau_name = f"tau{tau}"
    seed_name = f"seed{seed}"

    save_dir = os.path.join(
        save_dir, "_".join([drop_id_name, drop_vars_name, tau_name, seed_name])
    )
    os.makedirs(save_dir, mode=0o775, exist_ok=True)

    return save_dir


def save_pickle(path, obj):
    with open(path, "wb") as file:
        pickle.dump(obj, file)


def load_pickle(path):
    with open(path, "rb") as file:
        obj = pickle.load(file)
    return obj


# Metrics
def mse_fit(X):
    test_y = X[:, 0]
    predict = X[:, 1]
    squared_err = np.square(test_y - predict)
    mse = squared_err.mean()
    return mse


def rmse_fit(X):
    test_y = X[:, 0]
    predict = X[:, 1]
    squared_err = np.square(test_y - predict)
    rmse = np.sqrt(squared_err.mean())
    return rmse


def mae_fit(X):
    test_y = X[:, 0]
    predict = X[:, 1]
    err = np.abs(test_y - predict)
    mae = err.mean()
    return mae


def r2_fit(X):
    test_y = X[:, 0]
    predict = X[:, 1]
    r2 = r2_score(test_y, predict)
    return r2


def adjusted_r2_fit(X):
    test_y = X[:, 0]
    predict = X[:, 1]
    r2 = r2_score(test_y, predict)
    adj_r2 = 1 - (1 - r2) * ((len(test_y) - 1) / (len(test_y) - 15 - 1))
    return adj_r2


def GetMetric_mean(pred, gt, demical="all"):
    prediction = np.reshape(pred, (-1, 1))
    ground_truth = np.reshape(gt, (-1, 1))
    pred_and_gt = np.concatenate((ground_truth, prediction), axis=1)

    rmse = rmse_fit(pred_and_gt)
    mae = mae_fit(pred_and_gt)
    r2 = r2_fit(pred_and_gt)

    metric = {
        f"rmse_mean": rmse,
        f"mae_mean": mae,
        f"r2_mean": r2,
    }

    df = pd.DataFrame([metric.values()], columns=metric.keys())

    return df


def GetMetric_bootstrap(pred, gt, decimal="all"):
    total_predicts = np.reshape(pred, (-1, 1))
    test_y = np.reshape(gt, (-1, 1))
    predict = total_predicts
    bootstrap_X = np.concatenate((test_y, predict), axis=1)

    rmse_original, rmse_std_err, rmse_ci_bounds = bootstrap(
        bootstrap_X, num_rounds=100, func=rmse_fit, ci=0.95, seed=123
    )
    mae_original, mae_std_err, mae_ci_bounds = bootstrap(
        bootstrap_X, num_rounds=100, func=mae_fit, ci=0.95, seed=123
    )
    r2_original, r2_std_err, r2_ci_bounds = bootstrap(
        bootstrap_X, num_rounds=100, func=r2_fit, ci=0.95, seed=123
    )

    metric = {
        f"rmse_mean": rmse_original,
        f"rmse_std": rmse_std_err,
        f"rmse_ci_95_low": rmse_ci_bounds[0],
        f"rmse_ci_95_high": rmse_ci_bounds[1],
        f"mae_mean": mae_original,
        f"mae_std": mae_std_err,
        f"mae_ci_95_low": mae_ci_bounds[0],
        f"mae_ci_95_high": mae_ci_bounds[1],
        f"r2_mean": r2_original,
        f"r2_std": r2_std_err,
        f"r2_ci_95_low": r2_ci_bounds[0],
        f"r2_ci_95_high": r2_ci_bounds[1],
    }

    df = pd.DataFrame([metric.values()], columns=metric.keys())

    return df


def TDM_type_only(data):
    # Ignore nan values in y
    # Cases where only doses are given are removed
    # Cases where doses are given along with TDM measuring is kept
    id_data = data["id"].copy()
    cycle_data = data["cycle"].copy()
    x_data = data["x"].copy()
    y_data = data["reg_y"].copy()

    count = 0
    for i in range(len(x_data)):
        count += x_data[i].shape[0]

    x_ = np.empty([count, len(x_data[0][0])])
    y_ = np.empty([count, 1])
    id_ = np.empty([count, 1])
    cycle_ = np.empty([count, 1])

    counter = 0
    for i in range(len(x_data)):
        for j in range(x_data[i].shape[0]):
            x_[counter + j] = x_data[i][j]
            y_[counter + j] = y_data[i][j]
            id_[counter + j] = id_data[i]
            cycle_[counter + j] = cycle_data[i]

        counter += x_data[i].shape[0]

    new_x = x_[np.argwhere(~np.isnan(y_))[:, 0]]
    new_y = np.reshape(y_[~np.isnan(y_)], (-1, 1))
    new_id = np.reshape(id_[~np.isnan(y_)], (-1, 1))
    new_cycle = np.reshape(cycle_[~np.isnan(y_)], (-1, 1))

    new_data = {
        "id": new_id,
        "cycle": new_cycle,
        "x": new_x,
        "reg_y": new_y,
    }

    return new_data


def PPK_TDM_type_only(data):
    # Ignore nan values in y
    id_data = data["id"].copy()
    cycle_data = data["cycle"].copy()
    x_data = data["x"].copy()
    y_data = data["reg_y"].copy()
    dose_number_data = data["dose_number"].copy()

    count = 0
    for i in range(len(x_data)):
        count += x_data[i].shape[0]

    x_ = np.empty([count, len(x_data[0][0])])
    y_ = np.empty([count, 1])
    id_ = np.empty([count, 1])
    cycle_ = np.empty([count, 1])
    dose_number_ = np.empty([count, 1])

    counter = 0
    for i in range(len(x_data)):
        for j in range(x_data[i].shape[0]):
            x_[counter + j] = x_data[i][j]
            y_[counter + j] = y_data[i][j]
            id_[counter + j] = id_data[i]
            cycle_[counter + j] = cycle_data[i]
            dose_number_[counter + j] = dose_number_data[i][j]

        counter += x_data[i].shape[0]

    new_x = x_[np.argwhere(~np.isnan(y_))[:, 0]]
    new_y = np.reshape(y_[~np.isnan(y_)], (-1, 1))
    new_id = np.reshape(id_[~np.isnan(y_)], (-1, 1))
    new_cycle = np.reshape(cycle_[~np.isnan(y_)], (-1, 1))
    new_dose_number = np.reshape(dose_number_[~np.isnan(y_)], (-1, 1))

    new_data = {
        "id": new_id,
        "cycle": new_cycle,
        "x": new_x,
        "reg_y": new_y,
        "dose_number": new_dose_number,
    }

    return new_data


#  Parameter counter
def get_n_params(model):
    pp = 0
    for p in list(model.parameters()):
        nn = 1
        for s in list(p.size()):
            nn = nn * s
        pp += nn
    return pp


# Get trough values
# x -> ['id', 'interval', 'tdm_interval', 'vd_avg', 'kt', 'dose', 'f', 'id_number']
# mimic_x -> ['subject_id', 'dose', 'interval', 'tdm_interval', 'vd_avg', 'kt', 'stay_id']
def get_trough(data: pd.DataFrame, dataset_index: str = "int", ind: bool = True):
    id_number = data["id"].copy()
    cycle = data["cycle"].copy()
    x = data["x"].copy()
    y = data["reg_y"].copy()
    dose_number = data["dose_number"].copy()

    trough = 0
    dose = 0
    vd_avg = 0
    kt = 0

    if (dataset_index == "int") or (dataset_index == "ext"):
        dose = x[:, 5]
        vd_avg = x[:, 3]
        kt = x[:, 4]

    elif dataset_index == "mimic":
        dose = x[:, 5]
        vd_avg = x[:, 3]
        kt = x[:, 4]

    trough = ((dose / vd_avg) * np.exp(-kt)) / (1 - np.exp(-kt))

    # Delete nan, inf, 0 values
    ignore_list = select_regular_values(x, trough)

    # Concat variables with calculated trough value
    temp = np.c_[x, trough]
    index_list = []

    # nan, inf, 0 제거
    for i in range(len(ignore_list)):
        patient_id = ignore_list[i, 0]
        n = ignore_list[i, 1]
        for j in range(len(temp)):
            if (temp[j, 0] == patient_id) and (temp[j, -2] == n):
                index_list.append(j)

    temp = np.delete(temp, index_list, axis=0)
    temp_2 = np.delete(y, index_list, axis=0)
    temp_3 = np.delete(id_number, index_list, axis=0)
    temp_4 = np.delete(cycle, index_list, axis=0)
    temp_5 = np.delete(dose_number, index_list, axis=0)

    temp_final = np.c_[temp, temp_2, temp_3, temp_4, temp_5]

    # ind = True -> interval 범위 조정 (5 ~ 96 사이 값만 유지)
    if ind == True:
        if (dataset_index == "int") or (dataset_index == "ext"):
            temp_final = temp_final[temp_final[:, 1] > 5]
            temp_final = temp_final[temp_final[:, 1] < 96]
            temp_final = temp_final[temp_final[:, 2] > 5]
            temp_final = temp_final[temp_final[:, 2] < 96]
        elif dataset_index == "mimic":
            temp_final = temp_final[temp_final[:, 2] > 5]
            temp_final = temp_final[temp_final[:, 2] < 96]
            temp_final = temp_final[temp_final[:, 3] > 5]
            temp_final = temp_final[temp_final[:, 3] < 96]

    return temp_final


def select_regular_values(x: np.ndarray, trough_df: pd.DataFrame):
    trough = trough_df.copy()

    # Problems in trough value
    nan = np.where(np.isnan(trough))
    inf = np.where(np.isinf(trough))
    zero = np.where(trough == 0)

    nan_list = [nan[0][i] for i in range(len(nan[0]))]
    inf_list = [inf[0][i] for i in range(len(inf[0]))]
    zero_list = [zero[0][i] for i in range(len(zero[0]))]
    check_list = nan_list + inf_list + zero_list
    check_list.sort()

    ignore_list = np.empty((len(check_list), 2))
    ignore_list[:, 0] = x[check_list, 0]
    ignore_list[:, 1] = x[check_list, -1]

    ignore_list = np.unique(ignore_list, axis=0)

    return ignore_list


def get_column_names(dataset_index):
    cols = []
    # set features and target columns
    if dataset_index == "a":
        cols = [
            "gender",
            "age",
            "Ht",
            "Wt",
            "interval",
            "tdm_interval",
            "loading",
            "dialysis",
            "cr",
            "vd_avg",
            "vd_adt",
            "CrCl_min",
            "CrCl_hour",
            "kt",
            "calculated_MDRD",
            "calculated_CKDEPI",
            "calculated_CL",
            "dose",
            "total_dose",
            "tdm_value",
        ]
    elif dataset_index == "ac":
        cols = [
            "gender",
            "age",
            "Ht",
            "Wt",
            "interval",
            "tdm_interval",
            "loading",
            "dialysis",
            "cr",
            "vd_avg",
            "kt",
            "calculated_CKDEPI",
            "dose",
            "total_dose",
            "tdm_value",
        ]

    elif dataset_index == "am":
        cols = [
            "gender",
            "age",
            "Ht",
            "Wt",
            "interval",
            "tdm_interval",
            "loading",
            "dialysis",
            "cr",
            "vd_avg",
            "kt",
            "calculated_MDRD",
            "dose",
            "total_dose",
            "tdm_value",
        ]
    elif dataset_index == "amshap":
        cols = [
            "Sex (female red vs male blue)",
            "Age",
            "Height",
            "Body weight",
            "Interval among each dose of of vancomycin",
            "Time between vancomycin injection and TDM",
            "Vancomycin loading",
            "Dialysis",
            "Serum creatinine",
            "Average volume of distribution",
            "The elimination rate constant at infusion time (kt)",
            "eGFR MDRD",
            "Vancomycin dose",
            "Cumulative dose",
            "TDM value",
        ]

    elif dataset_index == "amtn":
        cols = [
            "gender",
            "age",
            "Ht",
            "Wt",
            "interval",
            "tdm_interval",
            "loading",
            "dialysis",
            "cr",
            "vd_avg",
            "kt",
            "calculated_MDRD",
            "dose",
            "total_dose",
            "tdm_value",
            "range",
        ]
    elif dataset_index == "amtnshap":
        cols = [
            "Sex (female red vs male blue)",
            "Age",
            "Height",
            "Body weight",
            "Interval among each dose of of vancomycin",
            "Time between vancomycin injection and TDM",
            "Vancomycin loading",
            "Dialysis",
            "Serum creatinine",
            "Average volume of distribution",
            "The elimination rate constant at infusion time (kt)",
            "eGFR MDRD",
            "Vancomycin dose",
            "Cumulative dose",
            "TDM value",
            "TDM value in ranges with 3 classes",
        ]
    elif dataset_index == "amc":
        cols = [
            "gender",
            "age",
            "Ht",
            "Wt",
            "interval",
            "tdm_interval",
            "loading",
            "dialysis",
            "cr",
            "vd_avg",
            "kt",
            "calculated_MDRD",
            "calculated_CKDEPI",
            "dose",
            "total_dose",
            "tdm_value",
        ]

    elif dataset_index == "last":
        cols = ["last_idx", "previous_tdm", "tdm_value"]
    elif dataset_index == "mimic_last":
        cols = ["type", "n_tdm", "tdm_value"]

    # For PPK model use
    elif dataset_index == "int" or dataset_index == "ext":
        cols = [
            "id",
            "interval",
            "tdm_interval",
            "vd_avg",
            "kt",
            "dose",
            "dose_number",
            "tdm_value",
        ]

    # For PPK model use
    elif dataset_index == "mimic":
        cols = [
            "subject_id",
            "interval",
            "tdm_interval",
            "vd_avg",
            "kt",
            "dose",
            "dose_number",
            "tdm_value",
        ]

    # For interval checking
    elif dataset_index == "int_interval" or dataset_index == "ext_interval":
        cols = [
            "last_idx",
            "id",
            "interval",
            "tdm_interval",
            "vd_avg",
            "kt",
            "dose",
            "tdm_value",
        ]
    elif dataset_index == "mimic_interval":
        cols = [
            "subject_id",
            "type",
            "interval",
            "tdm_interval",
            "vd_avg",
            "kt",
            "dose",
            "tdm_value",
        ]

    return cols


def create_y_save_df(name_list, length: int = 0):
    # Create columns
    column_names = []
    for name in name_list:
        pred = name + "_pred_y"
        true = name + "_true_y"

        column_names.append(pred)
        column_names.append(true)

    # Create dataframe with column names and length
    df = pd.DataFrame(columns=column_names)

    return df


def create_metric_df(decimal="all"):
    # Create metric table dataframe
    metric_columns = [
        "rmse_mean",
        "rmse_std",
        "rmse_ci_95_low",
        "rmse_ci_95_high",
        "mae_mean",
        "mae_std",
        "mae_ci_95_low",
        "mae_ci_95_high",
        "r2_mean",
        "r2_std",
        "r2_ci_95_low",
        "r2_ci_95_high",
    ]

    df = pd.DataFrame(columns=metric_columns)

    return df


def create_metric_mean_df(decimal="all"):
    # Create metric table dataframe
    metric_columns = [
        "rmse_mean",
        "mae_mean",
        "r2_mean",
        "adj_r2_mean",
    ]

    df = pd.DataFrame(columns=metric_columns)

    return df


def feature_preproc(feature):
    feature_ = feature.copy()

    gender = feature_[-1, 0]
    age = feature_[-1, 1]
    bw = feature_[-1, 3]
    cr = feature_[-1, 8]
    tdm_interval = feature_[-1, 5]

    CrCl_min = 0.0
    if gender == 1:
        CrCl_min = 1 * ((140 - age) * bw) / (72 * cr)
    else:
        CrCl_min = 0.85 * ((140 - age) * bw) / (72 * cr)

    CrCl_hour = (CrCl_min * 0.00083) + 0.0044
    kt = CrCl_hour * tdm_interval

    feature_[-1, 10] = kt

    return feature_
