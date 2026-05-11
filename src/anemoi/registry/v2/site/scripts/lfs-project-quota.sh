#!/bin/bash
# (C) Copyright 2026 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.

# Discover the Lustre project ID for a path and run lfs quota.
#
# Usage: lfs-project-quota.sh <path>
#
# If <path> is a file, its parent directory is used instead (lfs quota
# requires a directory).  The project ID is obtained via `lfs project`.

set -euo pipefail

if [ $# -ne 1 ]; then
    echo "Usage: $0 <path>" >&2
    exit 1
fi

TARGET="$1"

# lfs quota needs a directory
if [ -f "$TARGET" ]; then
    TARGET="$(dirname "$TARGET")"
fi

if [ ! -d "$TARGET" ]; then
    echo "Error: $TARGET is not a directory" >&2
    exit 1
fi

# Discover project ID  (output: "12345 P /some/path")
PROJECT_ID=$(lfs project "$TARGET" | awk 'NR==1{print $1}')

if [ -z "$PROJECT_ID" ]; then
    echo "Error: could not determine project ID for $TARGET" >&2
    exit 1
fi

# Run lfs quota (standard verbose output, parseable by parse_lfs)
lfs quota -p "$PROJECT_ID" "$TARGET"
