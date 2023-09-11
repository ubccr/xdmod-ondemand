#!/bin/bash
# needs jq, curl, awk and sed

set -e

branch="main"

SED=sed
if command -v gsed > /dev/null;
then
    SED=gsed
fi

version=$(git show refs/remotes/upstream/main:build.json | jq --raw-output .version | cut -f 1,2 -d .)
filelist=$(git ls-tree --name-only -r upstream/$branch docs | egrep '.*\.md$')
for file in $filelist;
do
    outfile=$(echo $file | awk 'BEGIN{FS="/"} { for(i=2; i < NF; i++) { printf "%s/", $i } print "'$version'/" $NF}')
    mkdir -p $(dirname $outfile)
    sedscript='/^redirect_from:$/{N;s/^redirect_from:\n    - ""/redirect_from:\n    - "\/'$version'\/"/}'
    if [ "$branch" = "main" ]; then
        sedscript='/^redirect_from:$/a\    - "\/'$version'\/"'
        basefile=$(basename $outfile .md)
        if [ "docs/${basefile}.md" = "$file" ]; then
            cat > ${basefile}.md << EOF

redirect_to: /$version/${basefile}.html
---
EOF
        fi
    fi
    git show refs/remotes/upstream/$branch:$file | $SED "$sedscript" > $outfile
done
