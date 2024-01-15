"""
Run Great Expectations data quality checks.

Validates data quality and generates HTML reports.
"""

import argparse
import json
import logging
from pathlib import Path
from typing import Dict, Any

import great_expectations as gx
from great_expectations.core.batch import RuntimeBatchRequest
from great_expectations.checkpoint import SimpleCheckpoint

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_suite_config(suite_path: str) -> Dict[str, Any]:
    """Load expectation suite configuration from YAML/JSON."""
    with open(suite_path, "r") as f:
        if suite_path.endswith(".json"):
            return json.load(f)
        else:
            import yaml
            return yaml.safe_load(f)


def create_expectation_suite(
    context: gx.DataContext,
    suite_name: str,
    expectations: list
) -> None:
    """Create an expectation suite with given expectations."""
    
    suite = context.add_expectation_suite(
        expectation_suite_name=suite_name,
    )
    
    # Add expectations
    for exp in expectations:
        exp_type = exp.pop("expectation_type")
        suite.add_expectation(
            expectation_type=exp_type,
            **exp
        )
    
    context.save_expectation_suite(suite)
    logger.info(f"Created expectation suite: {suite_name}")


def run_validation(
    target_path: str,
    suite_config_path: str,
    output_path: str = "./ge_reports"
) -> bool:
    """
    Run Great Expectations validation on data.
    
    Args:
        target_path: GCS path to data
        suite_config_path: Path to suite configuration
        output_path: Path to save HTML reports
        
    Returns:
        True if validation passed, False otherwise
    """
    
    # Initialize context
    context = gx.get_context()
    
    # Load suite config
    suite_config = load_suite_config(suite_config_path)
    suite_name = suite_config.get("suite_name", "default_suite")
    expectations = suite_config.get("expectations", [])
    
    # Create expectation suite
    try:
        context.delete_expectation_suite(suite_name)
    except:
        pass
    
    create_expectation_suite(context, suite_name, expectations)
    
    # Create datasource
    datasource_config = {
        "name": "gcs_datasource",
        "class_name": "Datasource",
        "execution_engine": {
            "class_name": "PandasExecutionEngine"
        },
        "data_connectors": {
            "default_runtime_data_connector": {
                "class_name": "RuntimeDataConnector",
                "batch_identifiers": ["default_identifier"],
            }
        }
    }
    
    context.add_datasource(**datasource_config)
    
    # Create batch request
    batch_request = RuntimeBatchRequest(
        datasource_name="gcs_datasource",
        data_connector_name="default_runtime_data_connector",
        data_asset_name="target_data",
        runtime_parameters={"path": target_path},
        batch_identifiers={"default_identifier": "default"}
    )
    
    # Create and run checkpoint
    checkpoint_config = {
        "name": "validation_checkpoint",
        "config_version": 1.0,
        "class_name": "SimpleCheckpoint",
        "validations": [
            {
                "batch_request": batch_request,
                "expectation_suite_name": suite_name,
            }
        ],
    }
    
    checkpoint = SimpleCheckpoint(
        f"validation_checkpoint_{suite_name}",
        context,
        **checkpoint_config
    )
    
    # Run validation
    results = checkpoint.run()
    
    # Generate data docs
    context.build_data_docs()
    
    # Check results
    success = results["success"]
    logger.info(f"Validation {'passed' if success else 'failed'}")
    
    # Print summary
    for validation_result in results.run_results.values():
        stats = validation_result["validation_result"]["statistics"]
        logger.info(f"Evaluated expectations: {stats['evaluated_expectations']}")
        logger.info(f"Successful expectations: {stats['successful_expectations']}")
        logger.info(f"Success percentage: {stats['success_percent']:.2f}%")
    
    return success


def main():
    parser = argparse.ArgumentParser(description="Run Great Expectations validation")
    parser.add_argument("--suite", required=True, help="Path to suite config file")
    parser.add_argument("--target", required=True, help="GCS path to data")
    parser.add_argument("--output", default="./ge_reports", help="Output path for reports")
    
    args = parser.parse_args()
    
    success = run_validation(
        target_path=args.target,
        suite_config_path=args.suite,
        output_path=args.output
    )
    
    if not success:
        logger.error("Validation failed!")
        exit(1)
    else:
        logger.info("Validation passed!")


if __name__ == "__main__":
    main()
