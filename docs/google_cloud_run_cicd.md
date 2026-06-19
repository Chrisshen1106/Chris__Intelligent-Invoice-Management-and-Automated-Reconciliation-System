# Google Cloud Run CI/CD Deployment

This project deploys as two Cloud Run services:

- `invoice-backend`: FastAPI, PaddleOCR, Supabase service-role access
- `invoice-frontend`: Vue static app served by Nginx

Supabase remains the database, auth provider, and storage backend.

## Google Cloud setup

Use one GCP project and one region for all resources. The examples below use `asia-east1`.

Enable these APIs:

- Cloud Run API
- Artifact Registry API
- Cloud Build API
- IAM Credentials API
- Secret Manager API

Create an Artifact Registry Docker repository:

```bash
gcloud artifacts repositories create intelligent-invoice \
  --repository-format=docker \
  --location=asia-east1
```

Create Secret Manager secrets used by the backend:

```bash
printf '%s' 'https://your-project.supabase.co' | gcloud secrets create SUPABASE_URL --data-file=-
printf '%s' 'your-service-role-key' | gcloud secrets create SUPABASE_SERVICE_ROLE_KEY --data-file=-
printf '%s' 'your-jwt-secret-if-needed' | gcloud secrets create SUPABASE_JWT_SECRET --data-file=-
```

Create a deployment service account and connect GitHub Actions with Workload Identity Federation. Grant the deployment identity:

- Artifact Registry Writer
- Cloud Run Admin
- Service Account User
- Secret Manager Secret Accessor

## GitHub configuration

Repository variables:

- `GCP_REGION`: `asia-east1`
- `ARTIFACT_REGISTRY_REPOSITORY`: `intelligent-invoice`
- `BACKEND_SERVICE`: `invoice-backend`
- `FRONTEND_SERVICE`: `invoice-frontend`

Repository secrets:

- `GCP_PROJECT_ID`
- `GCP_WORKLOAD_IDENTITY_PROVIDER`
- `GCP_SERVICE_ACCOUNT`
- `FRONTEND_ORIGIN`: frontend Cloud Run URL, or `*` for the first bootstrap deploy
- `VITE_SUPABASE_URL`
- `VITE_SUPABASE_ANON_KEY`

The first deploy has a bootstrap problem: the backend CORS setting wants the frontend URL before the frontend service exists. Use `FRONTEND_ORIGIN=*` for the first run, then update it to the deployed frontend URL and rerun the workflow.

## Runtime configuration

Backend Cloud Run receives:

- `ALLOW_DEV_FALLBACK=0`
- `CORS_ALLOW_ORIGINS`
- `SUPABASE_URL` from Secret Manager
- `SUPABASE_SERVICE_ROLE_KEY` from Secret Manager
- `SUPABASE_JWT_SECRET` from Secret Manager

Frontend Docker build receives:

- `VITE_API_BASE`: resolved backend Cloud Run URL
- `VITE_API_MOCK_ENABLED=false`
- `VITE_DISABLE_ACCESS_MANAGEMENT=false`
- `VITE_SUPABASE_URL`
- `VITE_SUPABASE_ANON_KEY`

## Verification

After the workflow completes:

```bash
curl -i https://BACKEND_URL/
```

Expected backend response:

```json
{"status":"ok","service":"Invoice OCR MVP"}
```

Then open the frontend Cloud Run URL and verify:

- login page renders
- Supabase login/session works
- browser network requests use the backend Cloud Run URL
- production responses do not come from MSW mocks
- OCR upload accepts JPG, PNG, and PDF
