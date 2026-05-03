#!/bin/bash
# Deploy newsletter dashboard to Netlify via GitHub push
# Usage: ./deploy.sh "optional commit message"

cd "$(dirname "$0")"

# Re-generate dashboard data from latest research before deploying
echo "Regenerating dashboard data..."
cd ../../../.. && python3 Scripts/newsletter-research.py > /dev/null 2>&1 && cd Clients/joseph-khateri/newsletter-dashboard

git add index.html dashboard-data.json
git commit -m "${1:-Update newsletter dashboard}"
git push origin main
echo "Deployed. Netlify will be live in ~30 seconds."
