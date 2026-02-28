#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# ACL Demo Deployment Script
# Builds the frontend as a static export and uploads to Google Cloud Storage
#
# Prerequisites:
#   - Google Cloud SDK (gcloud, gsutil) installed and authenticated
#   - Node.js 18+ and npm installed
#   - Frontend dependencies installed (npm install in frontend/)
#
# Usage:
#   ./scripts/deploy-acl-demo.sh [BUCKET_NAME]
#
# Default bucket: gamed-ai-acl-demo
# =============================================================================

BUCKET_NAME="${1:-gamed-ai-acl-demo}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
FRONTEND_DIR="$PROJECT_ROOT/frontend"

echo "============================================"
echo "GamED.AI ACL Demo Deployment"
echo "============================================"
echo "Bucket: gs://$BUCKET_NAME"
echo "Frontend: $FRONTEND_DIR"
echo ""

# Step 1: Verify prerequisites
echo "[1/6] Verifying prerequisites..."
command -v gsutil >/dev/null 2>&1 || { echo "ERROR: gsutil not found. Install Google Cloud SDK."; exit 1; }
command -v npx >/dev/null 2>&1 || { echo "ERROR: npx not found. Install Node.js."; exit 1; }

# Verify game data exists
GAME_COUNT=$(find "$FRONTEND_DIR/src/data/acl-demo/games" -name "*.json" 2>/dev/null | wc -l | tr -d ' ')
echo "  Found $GAME_COUNT game JSON files"
if [ "$GAME_COUNT" -eq 0 ]; then
  echo "WARNING: No game JSON files found. Run the pipeline generation first:"
  echo "  cd backend && PYTHONPATH=. python scripts/generate_acl_demo.py"
  echo ""
  echo "Continuing with build anyway (gallery will show 0 games)..."
fi

# Step 2: Type check
echo ""
echo "[2/6] Running TypeScript type check..."
cd "$FRONTEND_DIR"
npx tsc --noEmit || { echo "ERROR: TypeScript errors found. Fix them before deploying."; exit 1; }

# Step 3: Build static export
echo ""
echo "[3/6] Building static export..."
NEXT_CONFIG_FILE=next.config.acl-demo.js npx next build
echo "  Build output: $FRONTEND_DIR/out/"

# Verify build output
if [ ! -d "$FRONTEND_DIR/out" ]; then
  echo "ERROR: Build output directory not found at $FRONTEND_DIR/out/"
  exit 1
fi

# Step 4: Create GCS bucket if needed
echo ""
echo "[4/6] Setting up GCS bucket..."
if gsutil ls "gs://$BUCKET_NAME" >/dev/null 2>&1; then
  echo "  Bucket gs://$BUCKET_NAME already exists"
else
  echo "  Creating bucket gs://$BUCKET_NAME..."
  gsutil mb -l us-central1 "gs://$BUCKET_NAME"
fi

# Configure static website hosting
gsutil web set -m index.html -e 404.html "gs://$BUCKET_NAME"

# Step 5: Upload files
echo ""
echo "[5/6] Uploading to gs://$BUCKET_NAME..."
gsutil -m rsync -r -d "$FRONTEND_DIR/out/" "gs://$BUCKET_NAME/"

# Set caching headers
gsutil -m setmeta -h "Cache-Control:public, max-age=3600" "gs://$BUCKET_NAME/**/*.html"
gsutil -m setmeta -h "Cache-Control:public, max-age=86400" "gs://$BUCKET_NAME/**/*.js"
gsutil -m setmeta -h "Cache-Control:public, max-age=86400" "gs://$BUCKET_NAME/**/*.css"
gsutil -m setmeta -h "Cache-Control:public, max-age=604800" "gs://$BUCKET_NAME/**/*.woff2" 2>/dev/null || true
gsutil -m setmeta -h "Cache-Control:public, max-age=604800" "gs://$BUCKET_NAME/**/*.png" 2>/dev/null || true

# Step 6: Set public access
echo ""
echo "[6/6] Setting public access..."
gsutil iam ch allUsers:objectViewer "gs://$BUCKET_NAME"

echo ""
echo "============================================"
echo "Deployment complete!"
echo "============================================"
echo ""
echo "Access the demo at:"
echo "  https://storage.googleapis.com/$BUCKET_NAME/index.html"
echo ""
echo "Or set up a Cloud CDN load balancer for a custom domain."
echo ""
echo "To update later, just run this script again."
