eval "$(conda shell.bash hook)"
conda create -n matsimenv python=3.10 -y
conda activate matsimenv
conda install -c conda-forge pandas numpy matplotlib tqdm bidict gymnasium requests tensorboard stable-baselines3 rich tensorflow -y
conda install pytorch torchvision torchaudio pytorch-cuda=12.4 -c pytorch -c nvidia -y
conda install pyg -c pyg -y
conda activate matsimenv