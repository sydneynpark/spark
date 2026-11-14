# syntax=docker/dockerfile:1
# The Python services in compose.yaml. Only dependencies are installed here:
# compose.yaml mounts the source from the checkout.

FROM python:3.12.12-slim-bookworm AS backend
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_ROOT_USER_ACTION=ignore
# The backend's dependencies are locked in uv.lock, exported to the same
# hashed requirements file scripts/build_lambda.py packages it from. The same
# uv as CI (.github/workflows/deploy.yml).
COPY --from=ghcr.io/astral-sh/uv:0.12.23 /uv /usr/local/bin/uv
COPY backend/pyproject.toml backend/uv.lock /tmp/backend/
RUN --mount=type=cache,target=/root/.cache/pip \
    mkdir -p /tmp/requirements \
    && uv export --project /tmp/backend --frozen --no-dev --no-header --no-emit-project \
        --format requirements-txt --output-file /tmp/requirements/backend.txt \
    && pip install --require-hashes -r /tmp/requirements/backend.txt

# Each content Lambda gets a virtualenv with just its own requirements, as
# its own deployment package has. The trigger that runs them
# (devstack/lambda_trigger.py) uses the backend's packages above.
FROM backend AS lambdas
COPY ContentManagement/UpdateBlogPostMetadata/src/requirements.txt /tmp/requirements/UpdateBlogPostMetadata.txt
COPY ContentManagement/UpdateBookReview/src/requirements.txt /tmp/requirements/UpdateBookReview.txt
COPY ContentManagement/UpdatePhotoMetadata/src/requirements.txt /tmp/requirements/UpdatePhotoMetadata.txt
RUN --mount=type=cache,target=/root/.cache/pip \
    for function in UpdateBlogPostMetadata UpdateBookReview UpdatePhotoMetadata; do \
        python -m venv /lambdas/$function \
        && /lambdas/$function/bin/pip install --require-hashes -r /tmp/requirements/$function.txt \
        || exit 1; \
    done
# In AWS, Pillow comes from a layer: this is the version it has (see
# terraform/content_lambdas.tf).
RUN --mount=type=cache,target=/root/.cache/pip \
    /lambdas/UpdatePhotoMetadata/bin/pip install Pillow==11.0.0
