#!/usr/bin/env python3
"""
MLOps Pipeline Script
Logs build metadata, deployment info, and app health metrics to MLflow.
This runs as part of the GitHub Actions workflow.
"""
import mlflow
import os
import sys
import time
import json
import argparse

def run_pipeline(stage: str, app_version: str, build_id: str, environment: str):
    tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment("python-app-deployments")

    run_name = f"{stage}-{environment}-{build_id[:8]}"
    print(f"Starting MLflow run: {run_name}")
    print(f"Tracking URI: {tracking_uri}")

    with mlflow.start_run(run_name=run_name) as run:
        # --- Parameters (inputs to this pipeline run) ---
        mlflow.log_param("stage", stage)
        mlflow.log_param("app_version", app_version)
        mlflow.log_param("build_id", build_id)
        mlflow.log_param("environment", environment)
        mlflow.log_param("python_version", sys.version.split()[0])
        mlflow.log_param("triggered_by", os.getenv("GITHUB_ACTOR", "manual"))
        mlflow.log_param("branch", os.getenv("GITHUB_REF_NAME", "main"))
        mlflow.log_param("commit_sha", os.getenv("GITHUB_SHA", build_id)[:8])

        # --- Tags ---
        mlflow.set_tag("pipeline_stage", stage)
        mlflow.set_tag("deploy_target", "EC2")
        mlflow.set_tag("docker_image", f"sandeeptiwari0206/python-backend:{build_id[:7]}")
        mlflow.set_tag("mlops_tool", "GitHub Actions + MLflow")

        # --- Metrics (simulate real build metrics) ---
        start = time.time()

        if stage == "build":
            mlflow.log_metric("build_start_timestamp", start)
            mlflow.log_metric("backend_image_size_mb", 245.6)
            mlflow.log_metric("frontend_image_size_mb", 28.3)
            mlflow.log_metric("total_image_size_mb", 273.9)
            mlflow.log_metric("build_success", 1.0)
            print("Build metrics logged.")

        elif stage == "test":
            mlflow.log_metric("tests_passed", 12)
            mlflow.log_metric("tests_failed", 0)
            mlflow.log_metric("test_coverage_pct", 87.5)
            mlflow.log_metric("lint_errors", 0)
            mlflow.log_metric("test_success", 1.0)
            print("Test metrics logged.")

        elif stage == "deploy":
            mlflow.log_metric("deploy_start_timestamp", start)
            mlflow.log_metric("deploy_duration_sec", 45.2)
            mlflow.log_metric("containers_deployed", 2)
            mlflow.log_metric("health_check_passed", 1.0)
            mlflow.log_metric("deploy_success", 1.0)
            print("Deploy metrics logged.")

        elif stage == "monitor":
            mlflow.log_metric("api_latency_ms", 12.4)
            mlflow.log_metric("uptime_pct", 99.9)
            mlflow.log_metric("error_rate_pct", 0.01)
            mlflow.log_metric("requests_per_min", 142)
            print("Monitor metrics logged.")

        # --- Log a summary artifact ---
        summary = {
            "run_id": run.info.run_id,
            "stage": stage,
            "version": app_version,
            "build_id": build_id,
            "environment": environment,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "status": "success"
        }
        summary_path = f"/tmp/mlops_summary_{stage}.json"
        with open(summary_path, "w") as f:
            json.dump(summary, f, indent=2)
        mlflow.log_artifact(summary_path, artifact_path="summaries")

        duration = time.time() - start
        mlflow.log_metric("pipeline_duration_sec", duration)

        print(f"MLflow run complete: {run.info.run_id}")
        print(f"Stage '{stage}' logged in {duration:.2f}s")
        print(json.dumps(summary, indent=2))

    return run.info.run_id


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MLOps Pipeline Runner")
    parser.add_argument("--stage", required=True, choices=["build", "test", "deploy", "monitor"])
    parser.add_argument("--version", default=os.getenv("APP_VERSION", "1.0.0"))
    parser.add_argument("--build-id", default=os.getenv("GITHUB_SHA", "local")[:8])
    parser.add_argument("--env", default=os.getenv("ENV", "production"))
    args = parser.parse_args()

    run_id = run_pipeline(args.stage, args.version, args.build_id, args.env)
    print(f"Done. Run ID: {run_id}")
