"""
Build FAISS index from embeddings.

Creates efficient vector index for semantic search.
"""

import argparse
import logging
import pickle
from pathlib import Path
from typing import List, Tuple

import faiss
import numpy as np
import pandas as pd
from google.cloud import storage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_embeddings_from_gcs(gcs_path: str) -> Tuple[np.ndarray, List[str]]:
    """
    Load embeddings from GCS parquet files.
    
    Args:
        gcs_path: GCS path to parquet files
        
    Returns:
        Tuple of (embeddings array, document IDs)
    """
    logger.info(f"Loading embeddings from {gcs_path}")
    
    # Read parquet files
    df = pd.read_parquet(gcs_path)
    
    # Extract embeddings and IDs
    embeddings = np.array(df['embedding'].tolist(), dtype='float32')
    doc_ids = df['id'].tolist()
    
    logger.info(f"Loaded {len(embeddings)} embeddings with dimension {embeddings.shape[1]}")
    
    return embeddings, doc_ids


def build_faiss_index(
    embeddings: np.ndarray,
    index_type: str = "Flat"
) -> faiss.Index:
    """
    Build FAISS index from embeddings.
    
    Args:
        embeddings: Numpy array of embeddings (n_samples, dimension)
        index_type: Type of FAISS index (Flat, IVF, HNSW)
        
    Returns:
        FAISS index
    """
    n_samples, dimension = embeddings.shape
    logger.info(f"Building {index_type} index for {n_samples} vectors of dimension {dimension}")
    
    if index_type == "Flat":
        # Simple flat index (exhaustive search)
        index = faiss.IndexFlatL2(dimension)
    elif index_type == "IVF":
        # IVF index (faster but approximate)
        quantizer = faiss.IndexFlatL2(dimension)
        nlist = min(100, embeddings.shape[0] // 10)
        index = faiss.IndexIVFFlat(quantizer, dimension, nlist)
        index.train(embeddings)
    elif index_type == "HNSW":
        # HNSW index (fast and accurate)
        index = faiss.IndexHNSWFlat(dimension, 32)
    else:
        raise ValueError(f"Unknown index type: {index_type}")
    
    # Add embeddings to index
    index.add(embeddings)
    
    logger.info(f"Built {index_type} index with {index.ntotal} vectors")
    
    return index


def save_index_to_gcs(
    index: faiss.Index,
    doc_ids: List[str],
    output_path: str,
    index_name: str = "faiss_index"
) -> None:
    """
    Save FAISS index and document IDs to GCS.
    
    Args:
        index: FAISS index
        doc_ids: List of document IDs
        output_path: GCS output path
        index_name: Name for the index files
    """
    # Create temp directory
    temp_dir = Path("/tmp/faiss_temp")
    temp_dir.mkdir(exist_ok=True)
    
    # Save index locally
    index_file = temp_dir / f"{index_name}.index"
    faiss.write_index(index, str(index_file))
    logger.info(f"Saved index to {index_file}")
    
    # Save document IDs locally
    ids_file = temp_dir / f"{index_name}_ids.pkl"
    with open(ids_file, "wb") as f:
        pickle.dump(doc_ids, f)
    logger.info(f"Saved doc IDs to {ids_file}")
    
    # Upload to GCS
    if output_path.startswith("gs://"):
        bucket_name = output_path.replace("gs://", "").split("/")[0]
        prefix = "/".join(output_path.replace("gs://", "").split("/")[1:])
        
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        
        # Upload index
        blob = bucket.blob(f"{prefix}/{index_name}.index")
        blob.upload_from_filename(str(index_file))
        logger.info(f"Uploaded index to {output_path}/{index_name}.index")
        
        # Upload IDs
        blob = bucket.blob(f"{prefix}/{index_name}_ids.pkl")
        blob.upload_from_filename(str(ids_file))
        logger.info(f"Uploaded IDs to {output_path}/{index_name}_ids.pkl")
    else:
        # Local save
        output_dir = Path(output_path)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        import shutil
        shutil.copy(index_file, output_dir / f"{index_name}.index")
        shutil.copy(ids_file, output_dir / f"{index_name}_ids.pkl")
        logger.info(f"Saved to local directory {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Build FAISS index")
    parser.add_argument("--in", dest="input_path", required=True, help="GCS path to embeddings")
    parser.add_argument("--out", dest="output_path", required=True, help="GCS output path")
    parser.add_argument("--index_type", default="Flat", choices=["Flat", "IVF", "HNSW"])
    parser.add_argument("--index_name", default="faiss_index", help="Index name")
    
    args = parser.parse_args()
    
    # Load embeddings
    embeddings, doc_ids = load_embeddings_from_gcs(args.input_path)
    
    # Build index
    index = build_faiss_index(embeddings, args.index_type)
    
    # Save to GCS
    save_index_to_gcs(index, doc_ids, args.output_path, args.index_name)
    
    logger.info("FAISS index build complete!")


if __name__ == "__main__":
    main()
