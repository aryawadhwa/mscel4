from domain_profiles import create_seed_dataframe
from schemas import SchemaColumn, ColumnConfig

def test_domain_profiles_credit_score_bounds():
    schema = [
        SchemaColumn(name="credit_score", type="numerical", config=ColumnConfig(min=300, max=850)),
        SchemaColumn(name="loan_approved", type="boolean", config=ColumnConfig()),
    ]
    df = create_seed_dataframe(schema, rows=50)
    assert df["credit_score"].min() >= 300
    assert df["credit_score"].max() <= 850
