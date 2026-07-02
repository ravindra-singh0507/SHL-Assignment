#!/usr/bin/env python
"""Setup and testing utility for SHL AI Hiring Assistant."""

import os
import sys
import subprocess
from pathlib import Path


def install_dependencies():
    """Install Python dependencies."""
    print("Installing dependencies...")
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
        check=True
    )
    print("Dependencies installed successfully!")


def build_vector_index():
    """Build FAISS vector index."""
    print("Building vector index...")
    from app.catalog import Catalog
    from app.retrieval import Retrieval

    catalog = Catalog("data/shl_product_catalog.json")
    print(f"Loaded {catalog.size()} assessments")

    retrieval = Retrieval(catalog)
    retrieval.build_index()
    retrieval.save_index()
    print("Vector index built and saved!")


def run_tests():
    """Run test suite."""
    print("Running tests...")
    subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-v"],
        cwd="."
    )


def main():
    """Main setup and testing."""
    import argparse

    parser = argparse.ArgumentParser(description="SHL AI Hiring Assistant Setup")
    parser.add_argument("command", choices=["install", "build-index", "test", "run"], 
                        help="Command to run")

    args = parser.parse_args()

    try:
        if args.command == "install":
            install_dependencies()
        elif args.command == "build-index":
            build_vector_index()
        elif args.command == "test":
            run_tests()
        elif args.command == "run":
            print("Starting FastAPI server...")
            print("Visit http://localhost:8000/docs for API documentation")
            subprocess.run(
                [sys.executable, "-m", "uvicorn", "app.main:app", "--reload"],
                check=True
            )
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
