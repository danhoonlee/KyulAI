# GointMLP
해당 프로젝트는 TDM N차 제안 모델인 GointMLP(GRU-Intergrated JointMLP)의 Repository 입니다.  
TDM N차 논문과 관련 링크는 해당 [링크](https://gitlab.ziovision.ai/research/serial-tabular/tdm2/tdm-gjtn)를 참고 바랍니다.

## Installation
1\.  Pull the Docker image
```shell
docker pull pytorch/pytorch:2.1.1-cuda12.1-cudnn8-runtime
docker run -it --gpus all pytorch/pytorch:2.1.1-cuda12.1-cudnn8-runtime
```

2\. Clone the TDM-GJTN repository and Install requirements
```shell
git clone https://gitlab.ziovision.ai/research/serial-tabular/tdm2/GointMLP.git
cd GointMLP/
pip install -r requirement.txt
```

## Run Code
### fit
반드시 **dir_file_config** 내 **train_dir**, **save_ckpt_dir** 설정되어 있어야 합니다.  
또한, **no_save_scaler=False**인 경우 **save_scaler_dir**도 설정되어 있어야 합니다.
```sh
python main.py --mode=fit --dir_file_config=dir_file_config.json --model_config=model_config.json 
```
#### Multi-GPU 
```sh
python main.py --mode=fit --dir_file_config=dir_file_config.json --model_config=model_config.json --devices=4
```

### test
반드시 **dir_file_config** 내 **test_dir**, **x_scaler**, **y_scaler**, **ckpt_file** 설정되어 있어야 합니다.
```sh
python main.py --mode=pred --dir_file_config=dir_file_config.json --model_config=model_config.json 
```
#### Test set
- 해당 프로트젝트는 단일 Test set과 멀티 Test set을 지원함
- dir_file_config 옵션에서 사용되는 json 파일 중 *test_dir*에 따라 단일 혹은 멀티 Test set을 사용할 수 있음
##### 단일 Test set
```json
{
    ...
    "test_dir": "./dataset/TDM/DKU_train"
    ...
}
```

#### 멀티 Test set
```json
{
    ...
    "test_dir": [
        "./dataset/TDM/DKU_train",
        "./dataset/TDM/DKU_test",
        "./dataset/TDM/KNU",
        "./dataset/TDM/MIMIC_FINE_TUNING/test_data"
    ],   
    ...
}
```

### pred
반드시 **dir_file_config** 내 **x_scaler**, **y_scaler**, **ckpt_file** 설정되어 있어야 합니다.
```sh
python main.py --mode=fit --dir_file_config=dir_file_config.json --model_config=model_config.json --csv_file=test.csv
```

## Click Option
|       Option      |                     Description                           | Default |
|-------------------|-----------------------------------------------------------|---------|
| --mode            | Pytorch lightning 동작 옵션[fit, test, pred]               |         |
| --dir_file_config | 폴더와 파일에 대한 설정이 있는 json 파일                     |   None  |
| --model_config    | GointMLP 파라미터 설정이 있는 json 파일                     |   None  |
| --no_save_scaler  | Min/Max Scaler를 저장 여부                                 |   False |
| --csv_file        | pred mode에서 사용할 csv 파일                              |   None  |
| --devices         | 학습에 사용한 디바이스 수                                   |    1    |

## Configuration
### Train Configuration
Please, Refer to [dir_file_config.json](./dir_file_config.json) for Train-specific hyperparameter configurations.
([Configuration Description](./doc/dir_file_config.md))

### Model Configuration
Please, Refer to [model_config.json](./model_config.json) for Model-specific hyperparameter configurations.
([Configuration Description](./doc/model_configuration.md))


## to-do
- [x] Dataloader 수정
- [x] trainer 학습 할 수 있게 수정
- [x] 모델 구조 수정
- [x] requirement.txt 생성
- [x] 멀티 test_dir 설명
