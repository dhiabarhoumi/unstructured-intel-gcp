"""
Spark job to generate text embeddings using Sentence Transformers.

Creates dense vector embeddings for semantic search.
"""

import argparse
from typing import List, Optional

import numpy as np
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import ArrayType, FloatType
from sentence_transformers import SentenceTransformer


# Global model instance (loaded once per executor)
_model = None


def get_model(model_name: str) -> SentenceTransformer:
    """Get or load the embedding model."""
    global _model
    if _model is None:
        _model = SentenceTransformer(model_name)
    return _model


def embed_text(text: Optional[str], model_name: str) -> Optional[List[float]]:
    """Generate embedding for text."""
    if not text or len(text) < 10:
        return None
    
    try:
        model = get_model(model_name)
        embedding = model.encode(text, show_progress_bar=False)
        return embedding.tolist()
    except Exception as e:
        print(f"Error embedding text: {e}")
        return None


def embed_batch(texts: List[Optional[str]], model_name: str) -> List[Optional[List[float]]]:
    """Generate embeddings for batch of texts."""
    if not texts:
        return []
    
    try:
        model = get_model(model_name)
        
        # Filter out None/empty texts
        valid_indices = [i for i, t in enumerate(texts) if t and len(t) >= 10]
        valid_texts = [texts[i] for i in valid_indices]
        
        if not valid_texts:
            return [None] * len(texts)
        
        # Generate embeddings
        embeddings = model.encode(valid_texts, show_progress_bar=False)
        
        # Map back to original positions
        results = [None] * len(texts)
        for idx, emb in zip(valid_indices, embeddings):
            results[idx] = emb.tolist()
        
        return results
    except Exception as e:
        print(f"Error in batch embedding: {e}")
        return [None] * len(texts)


def add_embeddings(df: DataFrame, text_col: str, model_name: str) -> DataFrame:
    """Add embedding column to dataframe."""
    
    # Create UDF
    embed_udf = F.udf(lambda text: embed_text(text, model_name), ArrayType(FloatType()))
    
    # Add embedding column
    df = df.withColumn("embedding", embed_udf(F.col(text_col)))
    
    # Filter out rows where embedding failed
    df = df.filter(F.col("embedding").isNotNull())
    
    # Add embedding dimension
    df = df.withColumn("embedding_dim", F.size(F.col("embedding")))
    
    return df


def main():
    parser = argparse.ArgumentParser(description="Generate text embeddings")
    parser.add_argument("--in", dest="input_path", required=True, help="Input GCS path")
    parser.add_argument("--out", dest="output_path", required=True, help="Output GCS path")
    parser.add_argument("--model", default="all-MiniLM-L6-v2", help="Sentence Transformer model")
    parser.add_argument("--text_col", default="combined_text", help="Text column name")
    
    args = parser.parse_args()
    
    print(f"Starting embedding generation with model: {args.model}")
    print(f"Input: {args.input_path}")
    print(f"Output: {args.output_path}")
    
    spark = SparkSession.builder \
        .appName("EmbedTexts") \
        .config("spark.sql.parquet.compression.codec", "snappy") \
        .config("spark.executor.memory", "8g") \
        .config("spark.driver.memory", "4g") \
        .getOrCreate()
    
    # Read input
    df = spark.read.parquet(args.input_path)
    print(f"Read {df.count()} records from {args.input_path}")
    
    # Generate embeddings
    print(f"Generating embeddings using model: {args.model}")
    df_embedded = add_embeddings(df, args.text_col, args.model)
    
    # Write output
    df_embedded.write.mode("overwrite").parquet(args.output_path)
    embedded_count = df_embedded.count()
    print(f"Wrote {embedded_count} records with embeddings to {args.output_path}")
    
    spark.stop()


if __name__ == "__main__":
    main()
