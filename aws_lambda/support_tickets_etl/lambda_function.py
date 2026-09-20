
import boto3
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import io
import urllib.parse


def save_parquet_to_s3(df, bucket, key):
    """Convert DataFrame to Parquet and upload it to S3."""

    table = pa.Table.from_pandas(
        df,
        preserve_index=False
    )

    parquet_buffer = io.BytesIO()

    pq.write_table(
        table,
        parquet_buffer
    )

    s3 = boto3.client("s3")

    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=parquet_buffer.getvalue()
    )

    print(f"Parquet saved to s3://{bucket}/{key}")


def read_tickets_from_s3(bucket, key):
    """Read the raw CSV file from S3."""

    s3 = boto3.client("s3")

    response = s3.get_object(
        Bucket=bucket,
        Key=key
    )

    df = pd.read_csv(response["Body"])

    return df


def lambda_handler(event, context):
    """AWS Lambda entry point for Support Tickets ETL."""

    record = event["Records"][0]

    bucket_name = record["s3"]["bucket"]["name"]

    input_key = urllib.parse.unquote_plus(
        record["s3"]["object"]["key"]
    )

    print(
        f"Triggered by: s3://{bucket_name}/{input_key}"
    )

    # Read raw ticket data
    df = read_tickets_from_s3(
        bucket_name,
        input_key
    )

    print("Original shape:", df.shape)

    # Standardize column names
    df = df.rename(
        columns={
            "IssUeCat": "issue_category"
        }
    )

    # Fix inconsistent priority values
    priority_fixes = {
        "Medum": "Medium",
        "Lw": "Low",
        "Hgh": "High"
    }

    df["priority"] = df["priority"].replace(
        priority_fixes
    )

    # Remove invalid interaction records
    df = df[df["num_interactions"] >= 0]

    # Remove duplicate records
    df = df.drop_duplicates()

    # Convert date columns
    df["created_at"] = pd.to_datetime(
        df["created_at"],
        errors="coerce"
    )

    df["resolved_at"] = pd.to_datetime(
        df["resolved_at"],
        errors="coerce"
    )

    # Convert interaction count to integer
    df["num_interactions"] = df[
        "num_interactions"
    ].astype(int)

    # Handle missing feedback values
    df["agent_feedback"] = df[
        "agent_feedback"
    ].fillna("").astype(str)

    # Generate output file name
    file_name = input_key.split("/")[-1]

    output_file_name = file_name.replace(
        ".csv",
        ".parquet"
    )

    output_key = (
        "support-tickets/processed/"
        + output_file_name
    )

    # Save transformed data as Parquet
    save_parquet_to_s3(
        df,
        bucket_name,
        output_key
    )

    print("Final shape:", df.shape)

    return {
        "statusCode": 200,
        "message": (
            "Support ticket ETL completed successfully"
        ),
        "output_key": output_key
    }
