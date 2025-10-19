#!/bin/bash
# Add #![allow(dead_code)] to files with many dead code warnings

files=(
    "src/config.rs"
    "src/crypto.rs"
    "src/errors.rs"
    "src/handlers/health.rs"
    "src/middleware/rate_limit.rs"
    "src/models.rs"
    "src/monitoring.rs"
    "src/rates.rs"
    "src/utils.rs"
)

for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        # Check if already has allow directive
        if ! grep -q "#!\[allow(dead_code)\]" "$file"; then
            # Add at top of file after any existing #! directives
            sed -i '1i #![allow(dead_code)]' "$file"
            echo "Added #![allow(dead_code)] to $file"
        fi
    fi
done
