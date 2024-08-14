#!/usr/bin/env bash
#
# Create docs in docs/
#

for lang in en ru; do  # en should be the first language as it clears the root of the site
    scripts/docs-render-config.sh $lang
    cp -r ./docs/src/en/images/ ./docs/src/$lang/images/
    mkdocs build --dirty --config-file docs/_mkdocs.yml
    rm docs/_mkdocs.yml
done