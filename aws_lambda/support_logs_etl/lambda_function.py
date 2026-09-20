
import boto3
import pandas as pd
import re
import pyarrow as pa
import pyarrow.parquet as pq
import io


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


def read_log_from_s3(bucket, key):
    """Read raw log data from S3."""

    s3 = boto3.client("s3")

    response = s3.get_object(
        Bucket=bucket,
        Key=key
    )

    log_data = response["Body"].read().decode("utf-8")

    return log_data


def lambda_handler(event, context):
    """AWS Lambda entry point for Support Logs ETL."""

    # Read bucket and object key from the S3 event
    record = event["Records"][0]

    bucket_name = record["s3"]["bucket"]["name"]

    input_key = record["s3"]["object"]["key"]

    print(
        f"Triggered by: s3://{bucket_name}/{input_key}"
    )

    # Read raw log data
    raw_logs = read_log_from_s3(
        bucket_name,
        input_key
    )

    # Split log entries using the delimiter
    entries = [
        entry.strip()
        for entry in raw_logs.split("---")
        if entry.strip()
    ]

    # Regex pattern to extract structured log data
    log_pattern = re.compile(
        r'(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) '
        r'\[(?P<log_level>[A-Za-z0-9_]+)\] '
        r'(?P<component>[^\s]+) - '
        r'TicketID=(?P<ticket_id>[^\s]+) '
        r'SessionID=(?P<session_id>[^\s]+)\s*'
        r'IP=(?P<ip>.*?) \| '
        r'ResponseTime=(?P<response_time>-?\d+)ms \| '
        r'CPU=(?P<cpu>[\d.]+)% \| '
        r'EventType=(?P<event_type>.*?) \| '
        r'Error=(?P<error>\w+)\s*'
        r'UserAgent="(?P<user_agent>.*?)"\s*'
        r'Message="(?P<message>.*?)"\s*'
        r'Debug="(?P<debug>.*?)"\s*'
        r'TraceID=(?P<trace_id>.*)'
    )

    # Extract structured data
    parsed_entries = []

    for entry in entries:
        match = log_pattern.search(entry)

        if match:
            parsed_entries.append(
                match.groupdict()
            )

    # Create DataFrame
    df = pd.DataFrame(parsed_entries)

    # Remove trace_id column
    df = df.drop(
        "trace_id",
        axis=1
    )

    # Remove negative response times
    df = df[
        df["response_time"].astype(int) >= 0
    ]

    # Fix inconsistent log-level values
    fix_log_level = {
        "INF0": "INFO",
        "DEBG": "DEBUG",
        "warnING": "WARNING",
        "EROR": "ERROR"
    }

    df["log_level"] = df[
        "log_level"
    ].replace(fix_log_level)

    # Remove duplicate rows
    df = df.drop_duplicates()

    # Convert data types
    df["response_time"] = df[
        "response_time"
    ].astype(int)

    df["cpu"] = df[
        "cpu"
    ].astype(float)

    df["error"] = df[
        "error"
    ].str.lower().map({
        "true": True,
        "false": False
    })

    # Convert timestamp
    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        format="%Y-%m-%d %H:%M:%S",
        errors="coerce"
    ).astype("datetime64[ms]")

    print("Final shape:", df.shape)
    print(df.head())

    # Generate output file name
    output_file_name = (
        input_key.split("/")[-1]
        .replace(".log", ".parquet")
    )

    output_key = (
        f"support-logs/processed/"
        f"{output_file_name}"
    )

    # Upload processed Parquet file to S3
    save_parquet_to_s3(
        df,
        bucket_name,
        output_key
    )

    return {
        "statusCode": 200,
        "message": (
            "Support logs ETL completed successfully"
        ),
        "output_key": output_key
    }
