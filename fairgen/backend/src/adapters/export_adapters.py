import io
import pandas as pd

class ExportDependencyError(Exception):
    pass

def export_to_huggingface(dataset_records: list[dict], repo_name: str, hf_token: str) -> str:
    try:
        from datasets import Dataset
        from huggingface_hub import HfApi
    except Exception as exc:
        raise ExportDependencyError(f"HuggingFace dependencies unavailable: {exc}") from exc

    df = pd.DataFrame(dataset_records)
    dataset = Dataset.from_pandas(df)
    api = HfApi(token=hf_token)
    api.create_repo(repo_id=repo_name, repo_type="dataset", exist_ok=True)
    with io.BytesIO() as buffer:
        df.to_csv(buffer, index=False)
        buffer.seek(0)
        api.upload_file(
            repo_id=repo_name,
            repo_type="dataset",
            path_in_repo="de.bias_dataset.csv",
            path_or_fileobj=buffer,
        )
    dataset.push_to_hub(repo_name, token=hf_token)
    return f"https://huggingface.co/datasets/{repo_name}"

def export_to_googlesheets(dataset_records: list[dict], access_token: str) -> str:
    try:
        import gspread
        from google.oauth2.credentials import Credentials
    except ImportError as exc:
        raise ExportDependencyError(f"Google Sheets dependencies unavailable: {exc}") from exc

    try:
        credentials = Credentials(token=access_token)
        client = gspread.authorize(credentials)
        from datetime import datetime
        spreadsheet = client.create(f"de.bias Export - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        if not dataset_records:
            return spreadsheet.url
        df = pd.DataFrame(dataset_records).replace([float("inf"), float("-inf")], 0).fillna("")
        spreadsheet.sheet1.update([df.columns.tolist()] + df.values.tolist())
        return spreadsheet.url
    except Exception as exc:
        raise RuntimeError(f"Google Sheets export failed: {exc}") from exc
