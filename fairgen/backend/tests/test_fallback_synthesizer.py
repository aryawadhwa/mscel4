import pandas as pd
from fallback_synthesizer import augment_dataset
from schemas import SchemaColumn, ColumnConfig

def test_augment_dataset_maintains_schema():
    schema = [
        SchemaColumn(name="age", type="numerical", config=ColumnConfig(min=18, max=100)),
        SchemaColumn(name="is_citizen", type="boolean", config=ColumnConfig()),
        SchemaColumn(name="loan_approved", type="boolean", config=ColumnConfig()),
    ]
    seed_df = pd.DataFrame({"age": [25, 45], "is_citizen": [True, False], "loan_approved": [True, False]})
    augmented = augment_dataset(seed_df, schema, target_size=10)
    
    assert len(augmented) == 10
    assert "age" in augmented.columns
    assert "is_citizen" in augmented.columns
    assert augmented["age"].min() >= 18
