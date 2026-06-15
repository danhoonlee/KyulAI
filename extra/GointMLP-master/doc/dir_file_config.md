| 분류            | 설명                                                 | 예시                                                                 |
|-----------------|-----------------------------------------------------|----------------------------------------------------------------------|
| train_dir       | 학습을 위해 사용되는 데이터가 저장된 폴더              | /data/train                                                          |
| test_dir        | 모델 테스트 데이터가 저장된 폴더                      | 단일  /data/test<br> 리스트 [ /data/test1, /data/test2,/data/test3 ]  |
| save_ckpt_dir   | 학습 중 생성되는 모델 ckpt 파일 저장 폴더             | /checkpoints                                                         |
| save_scaler_dir | 학습 데이터 정규화에 사용되는 Scaler 파일 저장 폴더    | /Result_Scaler                                                       |
| x_scaler        | 입력 데이터(X) 정규화에 사용되는 스케일러 파일         | /Result_Scaler/x_scaler.pkl                                          |
| y_scaler        | 출력 데이터(Y) 정규화에 사용되는 스케일러 파일         | /Result_Scaler/y_scaler.pkl                                          |
| ckpt_file       | 실제 예측에 사용될 체크포인트 파일                    | /checkpoints/best_weight.ckpt                                        |