#!/bin/sh
# Starts the frontend's dev server in its container, first installing its
# dependencies whenever package-lock.json has changed since they last were.
set -eu

lock_hash=$(sha1sum package-lock.json)
if [ "$lock_hash" != "$(cat node_modules/.package-lock.sha1 2>/dev/null)" ]; then
    npm ci --no-audit --no-fund
    echo "$lock_hash" > node_modules/.package-lock.sha1
fi

exec npm start
