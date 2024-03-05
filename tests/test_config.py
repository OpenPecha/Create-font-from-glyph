import pytest
import os
import sys
import boto3

# Add the directory containing config.py to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

# Set the path to the CSV file containing AWS credentials
CSV_FILE_PATH = "create_font_from_glyph\aws\credential\tenkal_accessKeys.csv"

# Set environment variable to the CSV file path
os.environ["AWS_CREDENTIALS_FILE"] = CSV_FILE_PATH

# Import config.py after setting the environment variable
from create_font_from_glyph.config import (
    MONLAM_AI_OCR_BUCKET,
    aws_access_key_id,
    aws_secret_access_key,
    monlam_ai_ocr_s3_client,
    monlam_ai_ocr_s3_resource,
    monlam_ai_ocr_bucket
)

# Fixture for mocking Boto3 session
@pytest.fixture
def mock_boto3_session(mocker):
    mock_session = mocker.MagicMock()
    mocker.patch("boto3.Session", return_value=mock_session)
    return mock_session

# Test cases
def test_boto3_session_created_successfully(mock_boto3_session, mocker):
    assert monlam_ai_ocr_s3_client is not None
    assert monlam_ai_ocr_s3_resource is not None
    assert monlam_ai_ocr_bucket is not None
    mock_boto3_session.assert_called_once_with(
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key
    )

def test_boto3_session_creation_failure(mocker):
    mock_session = mocker.MagicMock()
    mocker.patch("boto3.Session", side_effect=Exception("Test exception"))
    with pytest.raises(Exception):
        mock_session = boto3.Session(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key
        )

def test_s3_client_created_successfully(mock_boto3_session, mocker):
    assert monlam_ai_ocr_s3_client is not None

def test_s3_resource_created_successfully(mock_boto3_session, mocker):
    assert monlam_ai_ocr_s3_resource is not None

def test_s3_bucket_created_successfully(mock_boto3_session, mocker):
    assert monlam_ai_ocr_bucket is not None
    assert monlam_ai_ocr_bucket.name == MONLAM_AI_OCR_BUCKET
