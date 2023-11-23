# README

## Development

1. `python -m venv env`
2. `env\Scripts\activate.ps1`
3. `pip install -r requirements.txt`
4. `python main.py`

## Installing Operator

1. `kubectl apply -f manifests/crd`
2. `kubectl apply -f manifests/operator.yml`