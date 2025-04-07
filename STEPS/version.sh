#!/bin/bash

FILES="
app.py
static/style.css
static/script.js
templates/users.html.j2
templates/messages.html.j2
"

function -adopt() {
    local num="$1"; shift
    for file in $FILES; do
        if [ -f $num/$file ]; then
            echo "Overwriting $file"
            ln -sf "$num/$file" "$file"
        elif [ -f $file ]; then
            echo $file non existent in $num - cleaning up
            rm -f "$file"
        fi
    done
}

function update-one-link() {
    local num="$1"; shift
    if [ -f $num/app.py ]; then
        ln -sf "$num/app.py" app-${num}.py
    else
        rm app-${num}.py
    fi
}

function update-links() {
    local nums=$(ls -d [0-9][0-9])
    for num in $nums; do
        update-one-link $num
    done
}

function adopt() {
    update-links
    [ -n "$1" ] && -adopt $1
}

# prepare version n from n-1
function prep() {
    local num="$1"; shift
    # bloody octal notation
    local rawnum=$(printf "%d" "${num#0}")
    local prev=$((rawnum-1))
    prev=$(printf "%02d" "${prev#0}")
    echo "Scaffolding $num from $prev"
    mkdir -p $num/static $num/templates
    for file in $FILES; do
        if [ -f $prev/$file -a ! -f $num/$file ]; then
            echo scaffolding $num/$file from $prev/$file
            cp $prev/"$file" $num/$file
        fi
    done
    update-one-link $num
}

function summary() {
    local nums=$(ls -d [0-9]*)
    for num in $nums; do
        [ ! -f $num/app.py ] && continue
        echo -n "| $num | "
        head -2 $num/app.py | tail -1 | cut -d\" -f2
    done
}

# use either
# version.sh update-links
# version.sh summary
# version.sh prep 01
# version.sh adopt 01

"$@"
