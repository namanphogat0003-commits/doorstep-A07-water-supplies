# A7 — Water and Supplies

## What this module does

This module predicts water consumption for mobile car-washing jobs and determines how many jobs can fit within a vehicle's available water-tank capacity. The system aims to support efficient resource usage and provide a sustainability comparison with traditional car washing.

## Team

- Naman Kumar — Team Lead: project coordination, ML pipeline, integration
- Ranu Raj — Data & EDA: data exploration, preprocessing, visualisation
- Vansh Rana — ML Engineer: machine learning models and training
- Priyanshu — Optimisation & Evaluation: tank-capacity optimisation and model evaluation

## Repository Structure

- `data/` — raw and processed datasets
- `src/` — project source code
- `notebooks/` — exploratory analysis
- `results/` — model outputs and plots
- `paper/` — technical paper
- `experiments.csv` — experiment log
- `INTEGRATION.md` — integration details

## How to Run

```bash
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt   # Windows
.venv/Scripts/python.exe src/train.py
```

On macOS or Linux use `.venv/bin/python` instead. `src/train.py` trains both the
planning-time and on-site models, writes `results/consumption_model.csv` and
`results/tank_capacity.csv`, and appends the run to `experiments.csv`.

`notebooks/01_exploration.ipynb` holds the EDA that the modelling choices rest on;
re-run it to refresh `results/plots/`.

## Team Module

**Track:** Doorstep — Track A  
**Module:** A7 — Water and Supplies