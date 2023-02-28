## Setup

```bash
sudo apt install python3 python3-pip
python3 -m pip install --upgrade pip
python3 -m pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
python3 -m pip install poetry
poetry install
```

## Run

1. Edit config file `.secrets.toml`
2. Connect to `明御®运维审计与风险控制系统（堡垒机）` via Python.

```
poetry run python main.py
```