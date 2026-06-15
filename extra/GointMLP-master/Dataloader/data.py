import pandas as pd
import os
import numpy as np
import multiprocessing as mp
import random
class proposed_column:
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
    
    test_cols = [
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
        "total_dose"     
    ]

def load_data_for_np(csv_file):
    data = pd.read_csv(csv_file, usecols=proposed_column.test_cols).values
    feature = np.array(data)
    return feature
    

def _load_data_Proposed(paths):
    """
    For Proposed model (Regression + CORAL)
    load data from paths
    :param paths: raw files' paths
    :return: feature information and target
    """

    ids = []
    cycles = []
    features = []
    reg_targets = []
    class_targets = []

    for path in paths:
        # read CSV
        id_number = path.split("/")[-1].split(".")[0]
        id_ = id_number.split("_")[0]
        cycle_ = id_number.split("_")[1]

        data = pd.read_csv(path, usecols=proposed_column.cols).values
        feature = data[:, :-2]
        reg_target = data[:, -2, None]
        class_target = data[:, -1, None]

        # y가 0인 경우 nan으로 치환
        e = 1e-5
        idx, _ = np.where(reg_target < e)
        reg_target[idx] = np.nan

        ids.append(id_)
        cycles.append(cycle_)
        features.append(feature)
        reg_targets.append(reg_target)
        class_targets.append(class_target)

    return ids, cycles, features, reg_targets, class_targets


def _load_data_parallel_Proposed(paths):
    num_processes = os.cpu_count()
    split_paths = np.array_split(paths, num_processes)
    arguments = zip(split_paths)

    with mp.Pool(num_processes) as pool:
        data = pool.starmap(_load_data_Proposed, arguments)

    pool.close()
    pool.join()

    concat_ids = []
    concat_cycles = []
    concat_features = []
    concat_reg_targets = []
    concat_class_targets = []

    for i in range(num_processes):
        ids, cycles, features, reg_targets, class_targets = data[i]
        concat_ids.extend(ids)
        concat_cycles.extend(cycles)
        concat_features.extend(features)
        concat_reg_targets.extend(reg_targets)
        concat_class_targets.extend(class_targets)

    return (
        concat_ids,
        concat_cycles,
        concat_features,
        concat_reg_targets,
        concat_class_targets,
    )


def _stay_ids_to_paths(dir_path, stay_ids):
    return list(map(lambda stay_id: os.path.join(dir_path, stay_id + ".csv"), stay_ids))


def load_csv_files(dir_path):
    file_names = os.listdir(dir_path)
    stay_ids = map(lambda file_name: (file_name.split(".")[0]), file_names)

    path_list = []

    paths = _stay_ids_to_paths(dir_path, stay_ids)
    path_list.extend(paths)

    for index, path in enumerate(path_list):
        if "/.csv" in path:
            path_list.pop(index)

    (ids, cycles, features, reg_targets, class_targets) = _load_data_parallel_Proposed(
        path_list
    )

    dict_data = {
        "id": ids,
        "cycle": cycles,
        "x": features,
        "reg_y": reg_targets,
        "class_y": class_targets,
    }

    return dict_data


def shuffle_together_and_split(input_dict, split_ratio=0.1):
    # 입력 딕셔너리에서 모든 리스트의 길이가 동일한지 확인하고, 그 길이를 가져옵니다.
    lengths = [len(v) for v in input_dict.values()]
    if len(set(lengths)) > 1:
        raise ValueError("All lists must have the same length.")
    list_length = lengths[0]

    # 모든 리스트의 동일한 인덱스를 함께 섞습니다.
    indices = list(range(list_length))
    #random.shuffle(indices)

    # 새로운 딕셔너리를 생성하여 섞인 인덱스에 따라 값을 재배치합니다.
    shuffled_dict = {
        key: [value[i] for i in indices] for key, value in input_dict.items()
    }

    # 분할 지점을 계산합니다.
    split_point = int(list_length * split_ratio)

    # 섞인 딕셔너리를 분할합니다.
    dict_a = {key: value[:split_point] for key, value in shuffled_dict.items()}
    dict_b = {key: value[split_point:] for key, value in shuffled_dict.items()}

    return dict_a, dict_b
