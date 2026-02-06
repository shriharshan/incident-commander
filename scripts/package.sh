#!/bin/bash
set -e

echo "📦 Packaging Incident Commander for AWS Lambda..."

# Clean previous builds
rm -rf package
rm -f lambda-package.zip

# Create package directory
mkdir -p package

# Install dependencies using uv
echo "Installing dependencies..."
uv pip install --target package/ \
    langgraph \
    langchain \
    langchain-openai \
    boto3 \
    pydantic \
    python-dotenv

# Copy source code
echo "Copying source code..."
cp -r src/* package/

# Create deployment package
echo "Creating zip file..."
cd package
zip -r ../lambda-package.zip . -q
cd ..

# Clean up
rm -rf package

# Show package info
echo "✅ Package created: lambda-package.zip"
ls -lh lambda-package.zip
echo ""
echo "Deploy with:"
echo "  cd terraform && terraform apply"
