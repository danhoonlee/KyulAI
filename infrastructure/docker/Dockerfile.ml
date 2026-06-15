FROM pytorch/pytorch:2.2.0-cuda12.1-cudnn8-runtime

WORKDIR /workspace

# System dependencies for CAE data parsing
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    build-essential \
    libhdf5-dev \
    libvtk9-dev \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements-ml.txt .
RUN pip install --no-cache-dir -r requirements-ml.txt

# Install project in editable mode
COPY . .
RUN pip install --no-cache-dir -e .

ENV PYTHONPATH=/workspace/src
ENV MLFLOW_TRACKING_URI=http://mlflow:5000

CMD ["python", "-m", "src.ml.train"]
