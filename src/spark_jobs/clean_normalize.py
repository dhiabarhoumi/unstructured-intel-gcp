"""
Spark job to clean and normalize raw data.

Handles:
- Schema normalization
- Deduplication
- Language detection
- Markup stripping
- Text cleaning
"""

import argparse
import re
from typing import Optional

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import StringType
from langdetect import detect, LangDetectException
from bs4 import BeautifulSoup


def detect_language(text: Optional[str]) -> Optional[str]:
    """Detect language of text using langdetect."""
    if not text or len(text) < 20:
        return None
    try:
        return detect(text)
    except LangDetectException:
        return None


def strip_html(text: Optional[str]) -> Optional[str]:
    """Remove HTML tags and entities."""
    if not text:
        return text
    soup = BeautifulSoup(text, "html.parser")
    return soup.get_text(separator=" ", strip=True)


def clean_text(text: Optional[str]) -> Optional[str]:
    """Clean and normalize text."""
    if not text:
        return text
    
    # Remove URLs
    text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove special characters but keep basic punctuation
    text = re.sub(r'[^\w\s.,!?;:()\-\']', '', text)
    
    return text.strip()


def process_hn_stories(df: DataFrame) -> DataFrame:
    """Process Hacker News stories."""
    # Register UDFs
    detect_lang_udf = F.udf(detect_language, StringType())
    strip_html_udf = F.udf(strip_html, StringType())
    clean_text_udf = F.udf(clean_text, StringType())
    
    # Process text
    df = df.withColumn("text_clean", strip_html_udf(F.col("text")))
    df = df.withColumn("text_clean", clean_text_udf(F.col("text_clean")))
    df = df.withColumn("title_clean", clean_text_udf(F.col("title")))
    
    # Combine title and text for embedding
    df = df.withColumn(
        "combined_text",
        F.when(
            F.col("title").isNotNull() & F.col("text_clean").isNotNull(),
            F.concat_ws(" ", F.col("title_clean"), F.col("text_clean"))
        ).otherwise(
            F.coalesce(F.col("title_clean"), F.col("text_clean"))
        )
    )
    
    # Detect language
    df = df.withColumn("language", detect_lang_udf(F.col("combined_text")))
    
    # Filter: keep only English, non-empty, reasonable length
    df = df.filter(
        (F.col("language") == "en") &
        (F.length(F.col("combined_text")) > 50) &
        (F.length(F.col("combined_text")) < 10000)
    )
    
    # Deduplicate
    df = df.dropDuplicates(["id"])
    
    return df.select(
        "id",
        "time",
        "title",
        "title_clean",
        "text_clean",
        "combined_text",
        "author",
        "score",
        "comment_count",
        "url",
        "language"
    )


def process_hn_comments(df: DataFrame) -> DataFrame:
    """Process Hacker News comments."""
    detect_lang_udf = F.udf(detect_language, StringType())
    strip_html_udf = F.udf(strip_html, StringType())
    clean_text_udf = F.udf(clean_text, StringType())
    
    df = df.withColumn("text_clean", strip_html_udf(F.col("text")))
    df = df.withColumn("text_clean", clean_text_udf(F.col("text_clean")))
    df = df.withColumn("language", detect_lang_udf(F.col("text_clean")))
    
    df = df.filter(
        (F.col("language") == "en") &
        (F.length(F.col("text_clean")) > 50) &
        (F.length(F.col("text_clean")) < 5000)
    )
    
    df = df.dropDuplicates(["id"])
    
    return df.select(
        "id",
        "time",
        "parent",
        "text_clean",
        "author",
        "language"
    )


def process_wikipedia(df: DataFrame) -> DataFrame:
    """Process Wikipedia pageviews."""
    clean_text_udf = F.udf(clean_text, StringType())
    
    # Clean title
    df = df.withColumn("title_clean", clean_text_udf(F.col("title")))
    
    # Remove underscores and decode
    df = df.withColumn(
        "title_display",
        F.regexp_replace(F.col("title"), "_", " ")
    )
    
    # Aggregate by title and day
    df = df.withColumn("date", F.to_date(F.col("datehour")))
    df = df.groupBy("title", "title_clean", "title_display", "date").agg(
        F.sum("views").alias("daily_views"),
        F.count("*").alias("hourly_records")
    )
    
    df = df.filter(F.col("daily_views") > 100)
    df = df.dropDuplicates(["title", "date"])
    
    return df


def process_github(df: DataFrame) -> DataFrame:
    """Process GitHub README files."""
    detect_lang_udf = F.udf(detect_language, StringType())
    strip_html_udf = F.udf(strip_html, StringType())
    clean_text_udf = F.udf(clean_text, StringType())
    
    # Decode content
    df = df.withColumn("content_text", F.col("content").cast("string"))
    df = df.withColumn("content_clean", strip_html_udf(F.col("content_text")))
    df = df.withColumn("content_clean", clean_text_udf(F.col("content_clean")))
    
    df = df.withColumn("text_language", detect_lang_udf(F.col("content_clean")))
    
    df = df.filter(
        (F.col("text_language") == "en") &
        (F.length(F.col("content_clean")) > 100) &
        (F.length(F.col("content_clean")) < 20000)
    )
    
    df = df.dropDuplicates(["repo_name", "path"])
    
    return df.select(
        "id",
        "repo_name",
        "path",
        "content_clean",
        "language",
        "text_language"
    )


def main():
    parser = argparse.ArgumentParser(description="Clean and normalize data")
    parser.add_argument("--in", dest="input_path", required=True, help="Input GCS path")
    parser.add_argument("--out", dest="output_path", required=True, help="Output GCS path")
    parser.add_argument("--dataset", required=True, choices=["hn_stories", "hn_comments", "wikipedia", "github"])
    
    args = parser.parse_args()
    
    spark = SparkSession.builder \
        .appName("CleanNormalize") \
        .config("spark.sql.parquet.compression.codec", "snappy") \
        .getOrCreate()
    
    # Read input
    df = spark.read.parquet(args.input_path)
    print(f"Read {df.count()} records from {args.input_path}")
    
    # Process based on dataset type
    if args.dataset == "hn_stories":
        df_clean = process_hn_stories(df)
    elif args.dataset == "hn_comments":
        df_clean = process_hn_comments(df)
    elif args.dataset == "wikipedia":
        df_clean = process_wikipedia(df)
    elif args.dataset == "github":
        df_clean = process_github(df)
    else:
        raise ValueError(f"Unknown dataset: {args.dataset}")
    
    # Write output
    df_clean.write.mode("overwrite").parquet(args.output_path)
    print(f"Wrote {df_clean.count()} cleaned records to {args.output_path}")
    
    spark.stop()


if __name__ == "__main__":
    main()
