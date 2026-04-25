import pandas as pd
from schemas import SchemaColumn, ColumnConfig
from scoring_engine import compute_approval_score, calculate_systemic_penalties

def test_compute_approval_score_pure_financial():
    schema = [
        SchemaColumn(name="credit_score", type="numerical", config=ColumnConfig(min=300, max=850)),
        SchemaColumn(name="debt_to_income", type="numerical", config=ColumnConfig(min=0, max=1)),
    ]
    df = pd.DataFrame({"credit_score": [850, 300, 575], "debt_to_income": [0.1, 0.9, 0.5]})
    
    scores = compute_approval_score(df, schema)
    
    # 850 CS is 1.0 logic, 0.1 DTI is 0.9 logic.
    assert len(scores) == 3
    assert scores.iloc[0] > 0.8
    assert scores.iloc[1] < 0.2

def test_calculate_systemic_penalties():
    schema = [
        SchemaColumn(name="race", type="categorical", config=ColumnConfig(), fairness_sensitive=True),
        SchemaColumn(name="gender", type="categorical", config=ColumnConfig(), fairness_sensitive=True),
    ]
    df = pd.DataFrame({"race": ["Black", "White", "Hispanic"], "gender": ["Female", "Male", "Male"]})
    
    penalties = calculate_systemic_penalties(df, schema)
    assert len(penalties) == 3
    # Black Female penalty = 0.12 + 0.07 = 0.19
    assert abs(penalties.iloc[0] - 0.19) < 0.001
    # White Male penalty = 0.0 + 0.0 = 0.0
    assert abs(penalties.iloc[1] - 0.0) < 0.001
