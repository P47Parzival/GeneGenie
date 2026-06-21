#!/usr/bin/env bash
# Step 3 — install genomics tooling on the EC2 (Ubuntu 24.04) box.
set -euo pipefail

echo "==> apt update + system genomics tools"
sudo apt-get update -y
sudo apt-get install -y tabix samtools bcftools python3-pip python3-venv unzip

echo "==> AWS CLI v2 (if missing)"
if ! command -v aws >/dev/null 2>&1; then
  curl -fsSL "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o /tmp/awscliv2.zip
  unzip -q /tmp/awscliv2.zip -d /tmp
  sudo /tmp/aws/install
  rm -rf /tmp/awscliv2.zip /tmp/aws
fi

echo "==> versions"
tabix --version | head -1 || true
samtools --version | head -1 || true
bcftools --version | head -1 || true
aws --version || true

echo "==> done. Next: scripts/02_fetch_clinvar.sh"
