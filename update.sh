#!/bin/bash
# needs jq, curl, awk and sed

set -e

tags="v11.0.0-1.0 v10.5.0-1.0 v10.0.0 v9.5.0"
latest="v11.0.0-1.0"

SED=sed
if command -v gsed > /dev/null;
then
    SED=gsed
fi

for tag in $tags;
do
    version=$(git show $tag:build.json | jq --raw-output .version | cut -f 1,2 -d .)
    filelist=$(git ls-tree --name-only -r $tag docs | egrep '.*\.md$')
    for file in $filelist;
    do
        outfile=$(echo $file | awk 'BEGIN{FS="/"} { for(i=2; i < NF; i++) { printf "%s/", $i } print "'$version'/" $NF}')
        mkdir -p $(dirname $outfile)
        sedscript='/^redirect_from:$/{N;s/^redirect_from:\n    - ""/redirect_from:\n    - "\/'$version'\/"/}'
        if [ "$tag" = "$latest" ]; then
            sedscript='/^redirect_from:$/a\    - "\/'$version'\/"'
            basefile=$(basename $outfile .md)
            if [ "docs/${basefile}.md" = "$file" ]; then
                cat > ${basefile}.md << EOF
---
redirect_to: /$version/${basefile}.html
---
EOF
            fi
        fi
        git show $tag:$file | $SED "$sedscript" > $outfile
    done
done
