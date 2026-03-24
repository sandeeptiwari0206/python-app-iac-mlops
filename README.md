# Python App — MLOps Deployment Guide
## Stack: MLflow + GitHub Actions + AWS EKS + EC2

---

## What MLOps means in this project

Every push to `main` runs a **6-stage MLOps pipeline** where each stage is tracked as an MLflow experiment run. You get full audit history: who deployed, which commit, what metrics, how long it took — all visible in the MLflow UI.

```
Git push → GitHub Actions →
  Stage 1: Docker Build  (images pushed to Docker Hub)
  Stage 2: MLflow logs build metrics
  Stage 3: MLflow logs test results
  Stage 4: Deploy to EKS (Kubernetes on AWS)
  Stage 5: MLflow logs deploy results
  Stage 6: MLflow logs health metrics
```

---

## Architecture

```
GitHub (code)
     │  push to main
     ▼
GitHub Actions ──────────────────────────────────────────────┐
  Stage 1: docker build → Docker Hub                         │
  Stage 2: mlflow log (build)   ──► MLflow EC2 (port 5000)  │
  Stage 3: mlflow log (test)    ──► MLflow EC2               │
  Stage 4: kubectl apply        ──► EKS Cluster              │
  Stage 5: mlflow log (deploy)  ──► MLflow EC2               │
  Stage 6: mlflow log (monitor) ──► MLflow EC2               │
                                                             │
AWS EKS Cluster (python-app namespace)                       │
  ├── backend pods (x2)  — Flask + MLflow client             │
  ├── frontend pods (x2) — Nginx                             │
  ├── mlflow pod         — Tracking server                   │
  └── ALB Ingress        — public URL                        │
                                                             │
AWS EC2 (MLflow standalone, for GitHub Actions to log to)   ◄┘
  └── mlflow server (port 5000)
```

---

## Tools and their MLOps role

| Tool | MLOps Role |
|---|---|
| MLflow | Tracks every pipeline stage as an experiment run. Stores params, metrics, artifacts. |
| GitHub Actions | Orchestrates the full 6-stage pipeline on every git push. |
| AWS EKS | Runs the app in Kubernetes with auto-scaling and rolling deploys. |
| AWS EC2 | Hosts the standalone MLflow tracking server. |
| Docker Hub | Stores versioned images (tagged by Git SHA). |
| CloudFormation | Provisions EKS cluster + MLflow EC2 as code. |
| HPA | Auto-scales backend pods based on CPU/memory. |

---

## STEP-BY-STEP DEPLOYMENT

### Prerequisites — install these on your laptop

```bash
# AWS CLI
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o awscliv2.zip
unzip awscliv2.zip && sudo ./aws/install
aws --version

# eksctl (EKS cluster tool)
curl --location "https://github.com/weaveworks/eksctl/releases/latest/download/eksctl_Linux_amd64.tar.gz" | tar xz
sudo mv eksctl /usr/local/bin
eksctl version

# kubectl
curl -LO "https://dl.k8s.io/release/v1.30.0/bin/linux/amd64/kubectl"
chmod +x kubectl && sudo mv kubectl /usr/local/bin
kubectl version --client
```

Configure AWS:
```bash
aws configure
# Enter: AWS Access Key ID
# Enter: AWS Secret Access Key
# Enter: ap-south-1  (default region)
# Enter: json         (output format)
```

---

### Step 1 — Deploy infrastructure with CloudFormation

This creates your EKS cluster AND an EC2 for MLflow in one command.

```bash
aws cloudformation deploy \
  --template-file infra/eks-cluster.yml \
  --stack-name python-app-mlops-stack \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides \
    KeyPairName=your-keypair-name \
  --region ap-south-1
```

Wait 15-20 minutes for EKS to provision. Then get the outputs:

```bash
# Get MLflow EC2 IP
aws cloudformation describe-stacks \
  --stack-name python-app-mlops-stack \
  --query "Stacks[0].Outputs[?OutputKey=='MLflowServerIP'].OutputValue" \
  --output text

# Should print something like: 13.235.45.12
# Save this — it is your MLFLOW_TRACKING_URI host
```

---

### Step 2 — Connect kubectl to your EKS cluster

```bash
aws eks update-kubeconfig \
  --region ap-south-1 \
  --name python-app-eks

# Verify connection
kubectl get nodes
# Should show 2 nodes in Ready state
```

---

### Step 3 — Install AWS Load Balancer Controller on EKS

This is needed for the Ingress (ALB) to work.

```bash
# Create IAM policy for ALB controller
curl -O https://raw.githubusercontent.com/kubernetes-sigs/aws-load-balancer-controller/v2.7.2/docs/install/iam_policy.json

aws iam create-policy \
  --policy-name AWSLoadBalancerControllerIAMPolicy \
  --policy-document file://iam_policy.json

# Get your AWS account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Create service account
eksctl create iamserviceaccount \
  --cluster=python-app-eks \
  --namespace=kube-system \
  --name=aws-load-balancer-controller \
  --role-name AmazonEKSLoadBalancerControllerRole \
  --attach-policy-arn=arn:aws:iam::${AWS_ACCOUNT_ID}:policy/AWSLoadBalancerControllerIAMPolicy \
  --approve

# Install controller via Helm
helm repo add eks https://aws.github.io/eks-charts
helm repo update
helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName=python-app-eks \
  --set serviceAccountName=aws-load-balancer-controller
```

---

### Step 4 — Verify MLflow server is running on EC2

```bash
MLFLOW_IP=<your-mlflow-ec2-ip>
curl http://$MLFLOW_IP:5000/health
# Should return: {"status": "OK"}

# Open in browser
open http://$MLFLOW_IP:5000
```

---

### Step 5 — Add GitHub Secrets and Variables

Go to: GitHub repo → Settings → Secrets and variables → Actions

**Secrets** (encrypted):

| Secret name | Value |
|---|---|
| `DOCKERHUB_USERNAME` | `sandeeptiwari0206` |
| `DOCKERHUB_TOKEN` | Docker Hub access token |
| `EC2_SSH_KEY` | Full contents of your `.pem` file |
| `AWS_ACCESS_KEY_ID` | AWS access key |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key |

**Variables** (plain text):

| Variable name | Value |
|---|---|
| `EC2_HOST` | MLflow EC2 public IP |
| `EC2_USER` | `ubuntu` |
| `MLFLOW_TRACKING_URI` | `http://YOUR_MLFLOW_EC2_IP:5000` |

---

### Step 6 — Push code to trigger the pipeline

```bash
git add .
git commit -m "feat: MLOps pipeline — MLflow + EKS"
git push origin main
```

Go to GitHub repo → Actions tab. Watch all 6 stages run in sequence:

```
✅ Stage 1 — Docker Build & Push     ~2 min
✅ Stage 2 — MLflow Log Build        ~30 sec
✅ Stage 3 — MLflow Log Tests        ~1 min
✅ Stage 4 — Deploy to EKS           ~3 min
✅ Stage 5 — MLflow Log Deploy       ~30 sec
✅ Stage 6 — MLflow Log Monitor      ~30 sec
```

---

### Step 7 — Get your app's public URL

After Stage 4 completes, run:

```bash
kubectl get ingress -n python-app
```

Output will look like:
```
NAME                  CLASS   HOSTS   ADDRESS                                          PORTS
python-app-ingress    alb     *       k8s-abc123.ap-south-1.elb.amazonaws.com          80
```

Open that ADDRESS in your browser. That is your live app.

---

## Access all dashboards

| Dashboard | URL |
|---|---|
| Frontend App | `http://<ALB-ADDRESS>` |
| Backend API health | `http://<ALB-ADDRESS>/health` |
| MLflow UI | `http://<MLFLOW_EC2_IP>:5000` |

---

## What you see in MLflow UI

Every pipeline run creates experiment entries like:

```
Experiment: python-app-deployments
  Run: build-production-abc1234
    Params:  stage=build, version=1.0.5, branch=main, triggered_by=sandeep
    Metrics: build_success=1.0, backend_image_size_mb=245.6
    Tags:    deploy_target=EKS, mlops_tool=GitHub Actions + MLflow

  Run: test-production-abc1234
    Params:  stage=test, version=1.0.5
    Metrics: tests_passed=12, coverage=87.5, lint_errors=0

  Run: deploy-production-abc1234
    Params:  stage=deploy, version=1.0.5
    Metrics: deploy_success=1.0, containers_deployed=2, health_check_passed=1.0

  Run: monitor-production-abc1234
    Metrics: api_latency_ms=12.4, uptime_pct=99.9, error_rate_pct=0.01
```

Every API call also logs a run via /api/predict.

---

## Rollback to a previous version

```bash
# Find the previous image tag from MLflow or Docker Hub
PREV_TAG=abc1234

# Update the deployment image
kubectl set image deployment/backend \
  backend=sandeeptiwari0206/python-backend:${PREV_TAG} \
  -n python-app

kubectl set image deployment/frontend \
  frontend=sandeeptiwari0206/python-frontend:${PREV_TAG} \
  -n python-app

# Watch rollout
kubectl rollout status deployment/backend -n python-app
```

---

## Useful kubectl commands

```bash
# See all pods
kubectl get pods -n python-app

# See logs from backend
kubectl logs -l app=backend -n python-app --tail=50

# Scale backend manually
kubectl scale deployment backend --replicas=4 -n python-app

# Check HPA (auto-scaling) status
kubectl get hpa -n python-app

# Describe a pod (for debugging)
kubectl describe pod <pod-name> -n python-app

# Delete everything (teardown)
kubectl delete namespace python-app
```

---

## Project File Structure

```
python-app-mlops/
├── .github/
│   └── workflows/
│       └── mlops-pipeline.yml     ← 6-stage MLOps pipeline (GitHub Actions)
├── backend/
│   ├── app.py                     ← Flask API with MLflow tracking on every request
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── index.html                 ← MLOps dashboard UI
│   ├── nginx.conf
│   └── Dockerfile
├── mlops/
│   └── pipelines/
│       └── pipeline.py            ← MLflow logging script (called by each stage)
├── k8s/
│   ├── 00-namespace.yml           ← Kubernetes namespace
│   ├── 01-configmap-secret.yml    ← App config and secrets
│   ├── 02-mlflow.yml              ← MLflow tracking server on EKS
│   ├── 03-backend.yml             ← Backend deployment + service
│   ├── 04-frontend.yml            ← Frontend deployment + service
│   ├── 05-ingress.yml             ← ALB ingress (public URL)
│   └── 06-hpa.yml                 ← Auto-scaling (2-6 pods)
├── infra/
│   └── eks-cluster.yml            ← CloudFormation: EKS + MLflow EC2
├── monitoring/
│   ├── prometheus.yml
│   └── grafana/provisioning/
│       └── datasources/prometheus.yml
├── tests/
│   └── test_app.py
├── MLproject                      ← MLflow project definition
├── conda.yml
├── docker-compose.yml             ← Local dev / EC2 fallback
└── README.md
```
