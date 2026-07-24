#!/usr/bin/env python3
"""
Single entry point for deploying spark.wiki's separate projects: frontend,
backend, and the ContentManagement lambdas.

Usage:
    python deploy.py frontend backend
    python deploy.py UpdatePhotoMetadata
    python deploy.py frontend backend UpdatePhotoMetadata UpdateBlogPostMetadata

Credentials:
    The AWS access key and secret access key are read from
    scripts/.accesskey and scripts/.secretaccesskey (the same files used by
    scripts/refreshPhotoMetadata.py) and used for all S3, CloudFront, and
    Lambda calls.
"""

import argparse
import mimetypes
import shutil
import subprocess
import sys
import uuid
import zipfile
from pathlib import Path

import boto3

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

ROOT = Path(__file__).resolve().parent
AWS_REGION = "us-east-1"

ACCESS_KEY_FILE = ROOT / "scripts" / ".accesskey"
SECRET_KEY_FILE = ROOT / "scripts" / ".secretaccesskey"

FRONTEND_BUCKET = "spark.wiki.frontend"
FRONTEND_DISTRIBUTION_ID = "E2JO5BSJ5WRP9P"

CONTENT_API_FUNCTION = "ContentAPI"
UPDATE_PHOTO_METADATA_FUNCTION = "UpdatePhotoMetadata"
UPDATE_BLOG_POST_METADATA_FUNCTION = "UpdateBlogPostMetadata"

# ─────────────────────────────────────────────────────────────────────────────
# CREDENTIALS / AWS SESSION
# ─────────────────────────────────────────────────────────────────────────────


def read_secret(path):
    """Read a single-line secret/value from a local file."""
    if not path.exists():
        sys.exit(f"Required file not found: {path}")
    value = path.read_text(encoding="utf-8").strip()
    if not value:
        sys.exit(f"File is empty: {path}")
    return value


def make_session():
    return boto3.Session(
        aws_access_key_id=read_secret(ACCESS_KEY_FILE),
        aws_secret_access_key=read_secret(SECRET_KEY_FILE),
        region_name=AWS_REGION,
    )


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────


def run(cmd, cwd):
    """Run a command in cwd, streaming output, raising on failure.

    shell=True so Windows resolves .cmd shims (e.g. npm) the same way a
    user's own shell would.
    """
    print(f"  $ {' '.join(str(c) for c in cmd)}")
    subprocess.run(cmd, cwd=cwd, shell=True, check=True)


def build_lambda_zip(project_dir, copy_into_package):
    """Install requirements and copy source into project_dir/.build/packages,
    then zip its contents into project_dir/.build/lambda.zip.

    copy_into_package(packages_dir) copies this project's own source files
    into the freshly created packages directory; each project's file list
    differs (see its README's "Zipping for upload to Lambda" section).
    """
    build_dir = project_dir / ".build"
    packages_dir = build_dir / "packages"

    if build_dir.exists():
        shutil.rmtree(build_dir)
    packages_dir.mkdir(parents=True)

    run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--target",
            str(packages_dir),
            "-r",
            str(project_dir / "src" / "requirements.txt"),
        ],
        cwd=project_dir,
    )

    copy_into_package(packages_dir)

    zip_path = build_dir / "lambda.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in packages_dir.rglob("*"):
            if path.is_file():
                zf.write(path, path.relative_to(packages_dir))

    return zip_path


def update_lambda_code(session, function_name, zip_path):
    print(f"  Updating Lambda function {function_name} from {zip_path} ...")
    lambda_client = session.client("lambda")
    lambda_client.update_function_code(
        FunctionName=function_name,
        ZipFile=zip_path.read_bytes(),
    )
    lambda_client.get_waiter("function_updated").wait(FunctionName=function_name)
    print(f"  {function_name} updated.")


# ─────────────────────────────────────────────────────────────────────────────
# PER-TARGET DEPLOY STEPS
# ─────────────────────────────────────────────────────────────────────────────


def deploy_frontend(session):
    frontend_dir = ROOT / "frontend"

    print("Building frontend ...")
    run(["npm", "run", "build"], cwd=frontend_dir)

    build_dir = frontend_dir / "build"
    if not build_dir.is_dir():
        sys.exit(f"Build output not found: {build_dir}")

    s3 = session.client("s3")

    print(f"Clearing s3://{FRONTEND_BUCKET} ...")
    paginator = s3.get_paginator("list_objects_v2")
    keys = [
        obj["Key"]
        for page in paginator.paginate(Bucket=FRONTEND_BUCKET)
        for obj in page.get("Contents", [])
    ]
    for i in range(0, len(keys), 1000):
        batch = keys[i : i + 1000]
        resp = s3.delete_objects(
            Bucket=FRONTEND_BUCKET,
            Delete={"Objects": [{"Key": k} for k in batch]},
        )
        errors = resp.get("Errors")
        if errors:
            for err in errors:
                print(f"  [FAIL] delete {err['Key']}: {err['Message']}")
            sys.exit(f"Failed to delete {len(errors)} object(s) from {FRONTEND_BUCKET}")
    print(f"  Deleted {len(keys)} object(s).")

    files = [p for p in build_dir.rglob("*") if p.is_file()]
    print(f"Uploading {len(files)} object(s) to s3://{FRONTEND_BUCKET} ...")
    for path in files:
        key = path.relative_to(build_dir).as_posix()
        content_type, _ = mimetypes.guess_type(path.name)
        extra_args = {"ContentType": content_type} if content_type else {}
        s3.upload_file(str(path), FRONTEND_BUCKET, key, ExtraArgs=extra_args)
    print("  Upload complete.")

    print(f"Creating CloudFront invalidation for /* on {FRONTEND_DISTRIBUTION_ID} ...")
    cf = session.client("cloudfront")
    resp = cf.create_invalidation(
        DistributionId=FRONTEND_DISTRIBUTION_ID,
        InvalidationBatch={
            "Paths": {"Quantity": 1, "Items": ["/*"]},
            "CallerReference": str(uuid.uuid4()),
        },
    )
    print(f"  Invalidation {resp['Invalidation']['Id']} created.")


def deploy_backend(session):
    project_dir = ROOT / "backend"

    def copy_into_package(packages_dir):
        for py_file in (project_dir / "src").glob("*.py"):
            shutil.copy(py_file, packages_dir)
        shutil.copytree(
            project_dir / "src" / "handlers",
            packages_dir / "handlers",
            ignore=shutil.ignore_patterns("__pycache__"),
        )
        shutil.copytree(
            project_dir / "src" / "utils",
            packages_dir / "utils",
            ignore=shutil.ignore_patterns("__pycache__"),
        )

    print("Building backend Lambda package ...")
    zip_path = build_lambda_zip(project_dir, copy_into_package)
    update_lambda_code(session, CONTENT_API_FUNCTION, zip_path)


def deploy_update_photo_metadata(session):
    project_dir = ROOT / "ContentManagement" / "UpdatePhotoMetadata"

    def copy_into_package(packages_dir):
        for py_file in (project_dir / "src").glob("*.py"):
            shutil.copy(py_file, packages_dir)
        shutil.copy(project_dir / "src" / "Bird keywords.txt", packages_dir)

    print("Building UpdatePhotoMetadata Lambda package ...")
    zip_path = build_lambda_zip(project_dir, copy_into_package)
    update_lambda_code(session, UPDATE_PHOTO_METADATA_FUNCTION, zip_path)

    print("Refreshing photo metadata for every photo in the bucket ...")
    run([sys.executable, "refreshPhotoMetadata.py"], cwd=ROOT / "scripts")


def deploy_update_blog_post_metadata(session):
    project_dir = ROOT / "ContentManagement" / "UpdateBlogPostMetadata"

    def copy_into_package(packages_dir):
        for py_file in (project_dir / "src").glob("*.py"):
            shutil.copy(py_file, packages_dir)

    print("Building UpdateBlogPostMetadata Lambda package ...")
    zip_path = build_lambda_zip(project_dir, copy_into_package)
    update_lambda_code(session, UPDATE_BLOG_POST_METADATA_FUNCTION, zip_path)
    # No scripts/refreshBlogPostMetadata.py exists yet, so there's nothing
    # further to run after this lambda's code is updated.


TARGETS = {
    "frontend": deploy_frontend,
    "backend": deploy_backend,
    "UpdatePhotoMetadata": deploy_update_photo_metadata,
    "UpdateBlogPostMetadata": deploy_update_blog_post_metadata,
}

# ─────────────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="Deploy one or more spark.wiki projects.")
    parser.add_argument(
        "targets",
        nargs="+",
        choices=list(TARGETS),
        help="Which project(s) to deploy",
    )
    args = parser.parse_args()

    session = make_session()

    for target in args.targets:
        print(f"\n=== Deploying {target} ===")
        TARGETS[target](session)

    print("\nAll deployments complete.")


if __name__ == "__main__":
    main()
