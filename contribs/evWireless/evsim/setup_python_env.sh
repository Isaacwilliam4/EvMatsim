eval "$(conda shell.bash hook)"
conda create -n matsimenv python=3.10 -y
conda activate matsimenv
conda install -c conda-forge pandas numpy matplotlib tqdm bidict gymnasium requests tensorboard rich osmnx cython seaborn -y
git clone https://github.com/Isaacwilliam4/stable-baselines3-gnn.git ~/.local/stable_baselines3_gnn
cd ~/.local/stable_baselines3_gnn
pip install -e .
cd -
if python -c "import torch; print(torch.cuda.is_available())" | grep -q "True"; then
    echo "GPU detected: Installing CUDA version"
    conda install pytorch torchvision torchaudio pytorch-cuda=12.4 -c pytorch -c nvidia -y
else
    echo "No GPU detected: Installing CPU version"
    pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
fi

# change pytorch-cuda= to match your cuda version, you can check your cuda version by running nvidia-smi
# conda install pytorch torchvision torchaudio pytorch-cuda=12.4 -c pytorch -c nvidia -y
conda install pyg -c pyg -y
conda activate matsimenv
