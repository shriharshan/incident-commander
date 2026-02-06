#!/bin/bash
set -e

echo "📦 Packaging Incident Commander Lambda..."

# Cleanup
rm -rf package
rm -f lambda-package.zip
mkdir -p package

# Install dependencies
echo "Installing dependencies..."
# If using requirements.txt
if [ -f requirements.txt ]; then
    pip install -r requirements.txt -t package/
elif [ -f pyproject.toml ]; then
    # Simple export if uv is not available or just use pip with pyproject.toml if supported
    # For now, let's try to install key dependencies manually if no lock file, or assume standard libs
    # In this environment, let's just copy src first.
    # Ideally use: uv pip install -r pyproject.toml -t package/
    # But for speed, let's copy src and hope dependencies are in layer or minimal
    echo "⚠️  Skipping dependency install for speed (assume Layer or simple reqs)"
fi

# We really need dependencies like langgraph, openai.
# Let's install them to package dir using pip
pip install "langgraph" "openai" "boto3" "aws-lambda-powertools" "python-dotenv" "langchain-openai" "langchain" --platform manylinux2014_x86_64 --target package/ --implementation cp --python-version 3.12 --only-binary=:all: --upgrade --no-cache-dir --quiet

# Copy src content to root of package
cp -r src/* package/

# Zip it
cd package
zip -r ../lambda-package.zip .
cd ..

echo "✅ Package created: lambda-package.zip"
