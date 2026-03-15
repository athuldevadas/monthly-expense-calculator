# Monthly Expense Calculator

A production-minded Streamlit application for tracking monthly family/shared expenses, individual member expenses, income sources, and budgets with local SQLite persistence.

## Features

- Dashboard with income, expenses, savings, and budget insights
- Family/shared and individual expense tracking
- Member and category management
- Monthly reports with charts and CSV export
- Overall and category budget tracking with overspend warnings
- Local SQLite storage for persistent data
- Docker support for containerized local runs

## Project Structure

```text
expense-calculator/
├── app.py
├── database.py
├── models.py
├── utils.py
├── requirements.txt
├── Dockerfile
└── README.md
```

## Database Schema

The app uses SQLite with the following tables:

- `members`: family members and active/inactive state
- `categories`: default and custom spending categories
- `incomes`: income entries linked to family or a member
- `expenses`: family/shared or individual expenses
- `budgets`: monthly overall and category-specific budgets

## Local Setup

1. Create and activate a virtual environment.
2. Install dependencies.
3. Run the Streamlit app.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

The app will start on `http://localhost:8501`.

## Docker

Build and run with Docker:

```bash
docker build -t expense-tracker .
docker run -p 8501:8501 expense-tracker
```

## Docker Desktop Kubernetes

This project includes Kubernetes manifests in [`k8s/`](./k8s) for Docker Desktop's built-in Kubernetes.

### 1. Enable Kubernetes in Docker Desktop

- Open Docker Desktop.
- Go to the Kubernetes view and create a cluster.
- For the simplest local workflow, use `kubeadm` if you want Kubernetes to use an image you build locally with `docker build`.
- Make sure your `kubectl` context is `docker-desktop`.

```bash
kubectl config use-context docker-desktop
kubectl get nodes
```

### 2. Build the image locally

From the project folder:

```bash
docker build -t expense-tracker:local .
```

### 3. Deploy to Kubernetes

```bash
kubectl apply -k k8s
kubectl get all -n expense-tracker
```

### 4. Open the app

The included service uses `NodePort` on `30501`, so you can open:

```text
http://localhost:30501
```

### 4a. Optional: Use Ingress for a cleaner URL

An Ingress gives you a cleaner local entry point than a raw NodePort. This project includes [`k8s/ingress.yaml`](./k8s/ingress.yaml) and supports both:

```text
http://localhost
http://expense.localdev.me
```

Before it works, install an Ingress controller. A common local choice is `ingress-nginx`:

```bash
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.14.3/deploy/static/provider/cloud/deploy.yaml
kubectl rollout status deployment/ingress-nginx-controller -n ingress-nginx
```

Then apply the app manifests:

```bash
kubectl apply -k k8s
kubectl get ingress -n expense-tracker
```

If Docker Desktop exposes the Ingress controller on port `80`, open:

```text
http://localhost
http://expense.localdev.me
```

If your machine does not expose it directly, forward the controller service:

```bash
kubectl port-forward -n ingress-nginx service/ingress-nginx-controller 8080:80
```

Then open:

```text
http://localhost:8080
http://expense.localdev.me:8080
```

If `expense.localdev.me` does not resolve on your machine, use `http://localhost` instead or add a hosts entry for it.

### 5. See it in Docker Desktop

- Open Docker Desktop.
- Go to `Kubernetes`.
- Select the `expense-tracker` namespace.
- You should see the deployment, pod, service, and PVC there.
- If Ingress is installed, you will also see the `expense-tracker` ingress resource.

### 6. Useful commands

Check pod status:

```bash
kubectl get pods -n expense-tracker
```

View logs:

```bash
kubectl logs -n expense-tracker deployment/expense-tracker
```

Delete the deployment:

```bash
kubectl delete -k k8s
```

## Data Storage

- SQLite database path: `data/expense_tracker.db`
- Data persists locally between app runs

## Notes

- Default members and categories are seeded automatically on first run.
- The app is intended for local usage and personal/family budgeting workflows.
