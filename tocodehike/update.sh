BIN=$(dirname $(realpath $0))
ROOT=$(dirname $BIN)
APP=${ROOT}/app



function redo-1() {
    local out=$APP/singlecolumn/AUTO
    python $BIN/tocodehike.py chain-dirs $ROOT/STEPS/[0-9]* > $out
    echo single column output written in $out
}

function redo-2() {
    local out=$APP/scrollycoding/AUTO
    python $BIN/tocodehike.py chain-dirs -s $ROOT/STEPS/[0-9]* > $out
    echo double column output written in $out
}

function redo() {
    redo-1
    redo-2
}

# create 2 symlinks inside to the -hike repo
function fill() {
    python $BIN/fillauto.py $APP/scrollycoding $APP/singlecolumn
}

function all() {
    redo
    fill
}

for subcommand in "$@"; do
    $subcommand
done
