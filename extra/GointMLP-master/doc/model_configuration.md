|Name|Description|
|---|---|
|epochs|학습 Max Epoch|
|batch_size|모델 Batch Size|
|max_seq_len|모델의 입력 및 출력에 대한 최대 시퀀스 길이|
|input_size|모델 입력 크기|
|hidden_size|모델 히든 크기 or Proposed(JointMLP 입력 크기, GRU 히든 크기)|
|gru_num_layers|Recurrent 레이어 수|
|jmlp_num_layers|JointMLP Horizontal Layer 수|
|jmlp_layer_size|JointMLP 히든 크기|
|bias|GRU bias 사용 여부|
|batch_first|GRU batch first 입출력 여|
|dropout|GRU Drop 값|
|learning_rate|모델 Learning Rate|
|num_nets|JointMLP 히든 레이어 층 수|
|num_classes|Class 수|
|patiences|Early Stopping patient 수|
|warmups|Early Stopping warmup 수|