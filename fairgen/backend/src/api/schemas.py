from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class RepresentationConfig(BaseModel):
    femalePct: float = Field(default=40, ge=0, le=100)
    minorityPct: float = Field(default=35, ge=0, le=100)
    ruralPct: float = Field(default=20, ge=0, le=100)


class MeasurementNoiseConfig(BaseModel):
    enabled: bool = True
    creditScoreSigma: float = Field(default=15, ge=0, le=100)
    incomeSigma: float = Field(default=2000, ge=0, le=50000)


class CustomFilter(BaseModel):
    group: str
    incomeMin: float = Field(default=0, ge=0)
    targetMinRepresentationPct: float = Field(default=0, ge=0, le=100)


class DeBiasConfig(BaseModel):
    datasetSize: int = Field(default=500, ge=100, le=10000)
    representation: RepresentationConfig = Field(default_factory=RepresentationConfig)
    historicalCorrection: float = Field(default=80, ge=0, le=100)
    labelCorrection: float = Field(default=70, ge=0, le=100)
    measurementNoise: MeasurementNoiseConfig = Field(default_factory=MeasurementNoiseConfig)
    customFilters: list[CustomFilter] = Field(default_factory=list)


ColumnType = Literal["numerical", "categorical", "boolean"]
DistributionType = Literal["normal", "log-normal", "uniform", "weighted"]


class ColumnConfig(BaseModel):
    min: float | None = None
    max: float | None = None
    distribution: DistributionType | None = None
    nullable: bool = False
    options: list[str] = Field(default_factory=list)
    weights: list[float] = Field(default_factory=list)
    base_rate: float | None = None

    @model_validator(mode="after")
    def validate_config(self) -> "ColumnConfig":
      if self.min is not None and self.max is not None and self.min > self.max:
          raise ValueError("min must be less than or equal to max")
      if self.weights and self.options and len(self.weights) != len(self.options):
          raise ValueError("weights must match options length")
      return self


class SchemaColumn(BaseModel):
    name: str = Field(min_length=1)
    type: ColumnType
    config: ColumnConfig = Field(default_factory=ColumnConfig)
    fairness_sensitive: bool = False


class GenerateRequest(BaseModel):
    schema: list[SchemaColumn] = Field(default_factory=list)
    config: DeBiasConfig = Field(default_factory=DeBiasConfig)


class PromptRequest(BaseModel):
    instruction: str = Field(min_length=1)
    currentConfig: DeBiasConfig = Field(default_factory=DeBiasConfig)


class SuggestColumnsRequest(BaseModel):
    description: str = Field(min_length=1)
    alreadySelected: list[str] = Field(default_factory=list)


class SuggestionColumn(BaseModel):
    name: str = Field(min_length=1)
    type: ColumnType
    config: ColumnConfig = Field(default_factory=ColumnConfig)
    fairness_sensitive: bool = False
    reason: str = Field(min_length=1)


class SuggestColumnsResponse(BaseModel):
    suggestions: list[SuggestionColumn] = Field(default_factory=list)


class ExportHuggingFaceRequest(BaseModel):
    dataset: list[dict[str, Any]]
    hfToken: str = Field(min_length=1)
    repoName: str = Field(min_length=1)


class ExportGoogleSheetsRequest(BaseModel):
    dataset: list[dict[str, Any]]
    accessToken: str = Field(min_length=1)


class ModelEvalRequest(BaseModel):
    """Request body for POST /model/evaluate."""
    dataset: list[dict[str, Any]]        # after-mitigation records
    beforeDataset: list[dict[str, Any]]  # biased baseline records
    schema: list[SchemaColumn]


class APIConnectionStatus(BaseModel):
    connected: bool
    message: str
