#!/bin/bash

count() {
    find $1 -type f -follow | wc -l
}

list() {
    for LINE in $(find $1 -type d -maxdepth 1)
    do
        if [ "$(file "$LINE" | grep -e ": directory$")" != "" ]; then
            echo "$LINE: $(count $LINE)"
        fi
    done
}

list $@
