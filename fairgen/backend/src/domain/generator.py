from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from src.api.schemas import DeBiasConfig, SchemaColumn
from src.domain.domain_profiles import create_seed_dataframe
from src.domain.fallback_synthesizer import augment_dataset

try:
    from sdv.metadata import SingleTableMetadata
    from sdv.single_table import GaussianCopulaSynthesizer

    SDV_AVAILABLE = True
except Exception:
    SingleTableMetadata = None
    GaussianCopulaSynthesizer = None
    SDV_AVAILABLE = False


SDV_VERSION = "unavailable"
if SDV_AVAILABLE:
    try:
        import sdv

        SDV_VERSION = sdv.__version__
    except Exception:
        SDV_VERSION = "installed"


@dataclass
class GenerationArtifacts:
    base_dataset: pd.DataFrame
    source: str


def create_metadata(schema: list[SchemaColumn]):
    if not SDV_AVAILABLE or SingleTableMetadata is None:
        return None

    metadata = SingleTableMetadata()
    seed_df = create_seed_dataframe(schema).drop(columns=["approval_score"], errors="ignore")
    metadata.detect_from_dataframe(data=seed_df)
    return metadata


def sample_base_dataset(config: DeBiasConfig, schema: list[SchemaColumn]) -> GenerationArtifacts:
    """Orchestrates generation, falling back to statistical augmentation if SDV is missing."""
    seed_df = create_seed_dataframe(schema)
    fit_df = seed_df.drop(columns=["approval_score"], errors="ignore")

    if SDV_AVAILABLE and GaussianCopulaSynthesizer is not None:
        try:
            metadata = create_metadata(schema)
            synthesizer = GaussianCopulaSynthesizer(metadata)
            synthesizer.fit(fit_df)
            sampled = synthesizer.sample(num_rows=config.datasetSize)
            sampled["approval_score"] = 0.5
            return GenerationArtifacts(base_dataset=sampled, source="sdv")
        except Exception:
            pass

    sampled = augment_dataset(seed_df, schema, config.datasetSize)
    return GenerationArtifacts(base_dataset=sampled, source="seed-fallback")
