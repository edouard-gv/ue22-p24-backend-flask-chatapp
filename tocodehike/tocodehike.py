"""
given a list of folders - typically successive steps in building an app
produce a markdown fragment for insertion in a codehike input

it starts with comparing the first and second folder,
then the second and third, etc.

for each step it compares the files (under git) in the two folders
and produces a diff-like markdown fragment for each file
"""

import sys
import difflib
from pathlib import Path
from argparse import ArgumentParser
import subprocess as sp

import click

# when generating for scrolly coding, the output syntax is a little different
SCROLLY = False


EXTENSIONS = {
    '.py' : { 'lang': 'python', 'comment': lambda line: f"# {line}"},
    '.js' : { 'lang': 'js', 'comment': lambda line: f"// {line}"},
    '.css': { 'lang': 'css', 'comment': lambda line: f"/* {line} */"},
    '.html': { 'lang': 'html', 'comment': lambda line: f"<!-- {line} -->"},
    '.text': { 'lang': 'text', 'comment': lambda line: f"{line}"},
    # quick and dirty - need only for html at this point
    # xxx should probably need to support e.g. .html/j2 and .js.j2
    '.j2': { 'lang': 'html', 'comment': lambda line: f"<!-- {line} -->"},
}

def add_lang_index():
    global EXTENSIONS
    for ext, info in list(EXTENSIONS.items()):
        lang = info['lang']
        if lang not in EXTENSIONS:
            EXTENSIONS[lang] = info

add_lang_index()


def defaults(path, filename, lang, comment):
    """
    Assign defaults for filename, lang, and comment based on the file extension.
    """
    if filename is None:
        filename = path.name
    suffix = Path(filename).suffix
    extension = EXTENSIONS.get(suffix, {}) or EXTENSIONS.get(lang, {})
    lang = lang or extension.get('lang', 'text')
    if comment and isinstance(comment, str):
        comment_str = comment
        comment = lambda line: f"{comment_str} {line}"
    comment = comment or extension.get('comment', lambda line: line)
    return filename, lang, comment


class DiffWriter:

    def __init__(self, comment):
        self.comment = comment
        self.mode = ' '  # could be '+', '-', ' ', or '@'
        self.lines = []

    def flush(self):
        match self.mode:
            case ' ':
                for line in self.lines:
                    print(line)
            case '+' | '-':
                if self.lines:
                    print(self.comment(f"!diff(1:{len(self.lines)}) {self.mode}"))
                    for line in self.lines:
                        print(line)
            case '@':
                if self.lines:
                    print(self.comment(f"!className separator"))
                    print(30*'.')
        self.lines = []

    def add_line(self, line, mode):
        if self.mode != mode:
            self.flush()
        self.mode = mode
        self.lines.append(line)


def onefile_cat(file1, *, filename=None, lang=None, comment=None, added=True):
    """
    Print the contents of a file as a triple-fenced code block.
    if added is True, print the added lines with a green + sign
    otherwise use a red - sign
    """
    path1 = Path(file1)
    if not path1.exists():
        print(f"File {path1} does not exist.", sys.stderr)
        return
    # assign from args or compute defaults
    filename, lang, comment = defaults(path1, filename, lang, comment)
    sign = '+' if added else '-'
    diff_writer = DiffWriter(comment)
    if not SCROLLY:
        print(f"```{lang} {filename}")
    else:
        print(f"```{lang} ! {filename}")
    with path1.open() as f:
        for line in f:
            line = line.rstrip()
            diff_writer.add_line(line, sign)
    diff_writer.flush()
    print("```")
    print()


def onefile_diff(file1, file2, *, filename=None, lang=None, comment=None):
    """
    Compare two files and print the differences as one triple-fenced code block.
    """
    path1, path2 = Path(file1), Path(file2)
    for path in [path1, path2]:
        if not path.exists():
            print(f"File {path} does not exist.", sys.stderr)
            return
    # assign from args or compute defaults
    filename, lang, comment = defaults(path1, filename, lang, comment)

    lines1, lines2 = path1.read_text().splitlines(), path2.read_text().splitlines()
    if not SCROLLY:
        print(f"```{lang} {filename}")
    else:
        print(f"```{lang} ! {filename}")
    diff_writer = DiffWriter(comment)
    for line in difflib.unified_diff(lines1, lines2, str(file1), str(file2)):
        if line.startswith('---') or line.startswith('+++') or not line.strip():
            continue
        if line.startswith('@@'):
            diff_writer.add_line(line, '@')
            continue
        start, end = line[:1], line[1:]
        if start == ' ':
            diff_writer.add_line(line[1:], ' ')
            continue
        if start in ['-', '+']:
            diff_writer.add_line(end, start)
    diff_writer.flush()
    print("```")
    print()


def files_equal(file1, file2):
    """
    Check if two files are equal.
    """
    path1, path2 = Path(file1), Path(file2)
    if not path1.exists() or not path2.exists():
        return False
    return path1.read_text() == path2.read_text()


def onedir_diff(dir1, dir2):
    """
    compare two folders
    - files that appear in both: use onefile_diff
    - files that appear in one but not the other: print a simple code block
    """
    path1, path2 = Path(dir1), Path(dir2)
    for path in [path1, path2]:
        if not path.exists():
            print(f"Directory {path} does not exist.", sys.stderr)
            return
    d1, d2 = path1.name, path2.name
    # consider only files under git
    sp1 = sp.run(['git', 'ls-files'], cwd=path1, capture_output=True)
    files1 = sorted(set(sp1.stdout.decode().splitlines()))
    sp2 = sp.run(['git', 'ls-files'], cwd=path2, capture_output=True)
    files2 = sorted(set(sp2.stdout.decode().splitlines()))

    # ignore README.md in the list of files
    files1 = [f for f in files1 if not f.lower().endswith('readme.md')]
    files2 = [f for f in files2 if not f.lower().endswith('readme.md')]

    same_files =  sorted(set(files1) & set(files2))
    new_files = sorted(set(files2) - set(files1))
    deleted_files = sorted(set(files1) - set(files2))

    def handle_first_line(line, name, d1, d2):
        if not line.startswith('## '):
            print(f"!!! WARNING !!! README file {readme} does not start with ##", file=sys.stderr)
            title = "!!! MISSING TITLE in {d2}/{name} !!!"
        else:
            title = line[3:].strip()
        if SCROLLY:
            print(f"## !!steps step {d2}: {title}")
        else:
            print(f"## step {d2}: {title}")

        if d1:
            print(f"### {d1} -> {d2} - changes in {name}")
        else:
            print(f"### new in {d2} - file {name}")

    def handle_readme(path, *, new_dir, old_dir=None):
        """
        d1=None mean it's a new file in d2
        """
        readme = path.parent / (path.name + '-readme.md')
        if readme.exists():
            with readme.open() as f:
                for lineno, line in enumerate(f, 1):
                    if lineno == 1:
                        handle_first_line(line, path.name, old_dir, new_dir)
                    else:
                        print(line, end="")
                if not line.endswith('\n'):
                    print()
        else:
            print(f"!!! WARNING !!! File {readme} does not exist!", file=sys.stderr)
            print(f"!!! WARNING !!! output likely broken !!!", file=sys.stderr)


    # open the possibility to specify an order
    def handle_same_file(file):
        # if the files are equal, we don't need to show them
        if not files_equal(path1 / file, path2 / file):
            print(f"changes in file: {file}", file=sys.stderr)
            # md_title(f"{d1} -> {d2} - changes in file: {file}", level=3, not_a_step=True)
            handle_readme(path2 / file, old_dir=d1, new_dir=d2)
            onefile_diff(path1 / file, path2 / file)

    def handle_new_file(file):
        print(f"new file: {file2}", file=sys.stderr)
        # md_title(f"in {d2} - new file: {file2}", level=3, not_a_step=True)
        handle_readme(path2 / file, new_dir=d2)
        onefile_cat(path2 / file2, added=True)

    # md_title(f"changes in {d1} -> {d2}", level=2)
    for file in same_files:
        handle_same_file(file)
    for file2 in new_files:
        handle_new_file(file2)

    for file1 in deleted_files:
        print(f"deleted file: {file1}", file=sys.stderr)
        # ignore such cases for now, might mess with the scrolly logic
        # md_title(f"in {d2} - deleted file: {file1}", level=3)

def chaindirs(paths):
    """
    accepts a sequence of at least 2 paths
    then will run onefile_diff on each pair of successive paths
    """
    for a, b in zip(paths, paths[1:]):
        print(f"==== comparing {a} and {b}", file=sys.stderr)
        onedir_diff(a, b)


# using click to expose one command per function

@click.group(chain=True, help=sys.modules[__name__].__doc__)
def cli():
    pass

@cli.command('diff-files', help="write out diff between two files")
@click.option('-f', '--filename', type=str, help='Filename for the output')
@click.option('-l', '--lang', type=str, default='python', help='Language for syntax highlighting')
@click.option('-c', '--comment', type=str, default=None, help='Comment character for the language')
@click.argument('file1', type=Path)
@click.argument('file2', type=Path)
def onefile_cli(filename, lang, comment, file1, file2):
    onefile_diff(
        file1, file2, filename=filename, lang=lang, comment=comment,
    )


@cli.command('diff-dirs', help="write out diff between two directories")
@click.argument('dir1', type=Path)
@click.argument('dir2', type=Path)
def onedir_cli(dir1, dir2):
    onedir_diff(dir1, dir2)


@cli.command('chain-dirs', help="write out diff between a succession of directories")
@click.option('-s', '--scrolly', is_flag=True, help='Use scrolly mode')
@click.argument('dirs', type=Path, nargs=-1)
def chaindirs_cli(scrolly, dirs):
    if len(dirs) < 2:
        print("At least two directories are required for comparison.")
        return
    global SCROLLY
    SCROLLY = scrolly

    chaindirs(dirs)

if __name__ == "__main__":
    cli()
