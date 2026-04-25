import pytest
from unittest.mock import patch, MagicMock
from src.adapters.export_adapters import export_to_huggingface, ExportDependencyError

@patch('src.adapters.export_adapters.HfApi')
@patch('src.adapters.export_adapters.Dataset')
def test_export_to_huggingface_success(mock_dataset, mock_hf_api):
    # Setup mock
    mock_api_instance = MagicMock()
    mock_hf_api.return_value = mock_api_instance
    mock_dataset_instance = MagicMock()
    mock_dataset.from_pandas.return_value = mock_dataset_instance

    # Execute
    url = export_to_huggingface([{"col1": 1}], "test_repo", "fake_token")

    # Assert
    assert url == "https://huggingface.co/datasets/test_repo"
    mock_api_instance.create_repo.assert_called_once_with(repo_id="test_repo", repo_type="dataset", exist_ok=True)
    mock_api_instance.upload_file.assert_called_once()
    mock_dataset_instance.push_to_hub.assert_called_once_with("test_repo", token="fake_token")
