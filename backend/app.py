from flask import Flask, jsonify, request
from flask_cors import CORS
import mlflow
import mlflow.sklearn
import os
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")
mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
mlflow.set_experiment("python-app-experiment")

APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
BUILD_ID    = os.getenv("BUILD_ID", "local")

@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "healthy",
        "version": APP_VERSION,
        "build_id": BUILD_ID,
        "mlflow_uri": MLFLOW_TRACKING_URI
    })

@app.route("/api/info", methods=["GET"])
def info():
    return jsonify({
        "app": "Python MLOps Demo",
        "version": APP_VERSION,
        "build_id": BUILD_ID,
        "environment": os.getenv("ENV", "production")
    })

@app.route("/api/predict", methods=["POST"])
def predict():
    data = request.get_json()
    input_value = data.get("input", 0)

    with mlflow.start_run(run_name=f"prediction-{int(time.time())}"):
        mlflow.log_param("input_value", input_value)
        mlflow.log_param("app_version", APP_VERSION)

        result = float(input_value) * 2.5
        confidence = 0.95

        mlflow.log_metric("result", result)
        mlflow.log_metric("confidence", confidence)
        mlflow.log_metric("latency_ms", 12.5)

        mlflow.set_tag("endpoint", "/api/predict")
        mlflow.set_tag("build_id", BUILD_ID)

    return jsonify({
        "input": input_value,
        "result": result,
        "confidence": confidence,
        "tracked_in_mlflow": True
    })

@app.route("/api/log-event", methods=["POST"])
def log_event():
    data = request.get_json()
    event_name = data.get("event", "unknown")
    metrics    = data.get("metrics", {})

    with mlflow.start_run(run_name=f"event-{event_name}-{int(time.time())}"):
        mlflow.set_tag("event_type", event_name)
        mlflow.set_tag("build_id", BUILD_ID)
        for key, value in metrics.items():
            try:
                mlflow.log_metric(key, float(value))
            except Exception:
                mlflow.log_param(key, value)

    return jsonify({"status": "logged", "event": event_name})

@app.route("/api/runs", methods=["GET"])
def get_runs():
    try:
        client = mlflow.tracking.MlflowClient()
        experiments = client.search_experiments()
        runs_summary = []
        for exp in experiments[:3]:
            runs = client.search_runs(exp.experiment_id, max_results=5)
            for run in runs:
                runs_summary.append({
                    "run_id": run.info.run_id[:8],
                    "experiment": exp.name,
                    "status": run.info.status,
                    "metrics": run.data.metrics,
                    "tags": dict(list(run.data.tags.items())[:3])
                })
        return jsonify({"runs": runs_summary, "total": len(runs_summary)})
    except Exception as e:
        return jsonify({"runs": [], "error": str(e)}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)
