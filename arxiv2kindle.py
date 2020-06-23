#!/usr/bin/env python3

import argparse
import arxiv
import logging
import re
import os
import sys
import subprocess
import tempfile
import tarfile
from pathlib import Path


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

HELP_EPILOG = """\
Example usage:

  %(prog)s --width 4 --height 6 --margin 0.2 1802.08395 - > out.pdf
  %(prog)s --width 6 --height 4 --margin 0.2 --landscape 1802.08395 ./
"""


def parse_args():
    parser = argparse.ArgumentParser(
        description="Convert arxiv paper to kindle-like size",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=HELP_EPILOG
        )
    parser.add_argument("query", help="arxiv paper url")
    parser.add_argument(
        "dest", type=Path,
        help="destination dir, if `-` provided, the file is streamed to stdout")
    group = parser.add_argument_group("Geometry")
    group.add_argument(
        '-W', "--width", default=4, type=float,
        help="width of the output pdf (inches)")
    group.add_argument(
        '-H', "--height", default=6, type=float,
        help="height of the output pdf (inches)")
    group.add_argument(
        '-m', "--margin", default=0.2, type=float,
        help="margin for the output pdf (inches)")
    group.add_argument(
        "--landscape", action='store_true',
        help="produce a landscape file")
    group.add_argument(
        "--portrait", dest='landscape', action='store_false',
        help="produce a portrait file (default option)")
    args = parser.parse_args()
    return args


def download(query):
    try:
        paper, = arxiv.query(query, max_results=1)
    except ValueError:
        raise SystemError('Paper not found')
    arxiv_id = paper['id']
    arxiv_title = paper['title']

    logger.info(f"Converting paper: [{arxiv_id}] {arxiv_title}")

    temp_dir = Path(tempfile.mkdtemp(prefix='arxiv2kindle_'))

    logger.info(f"Downloading the source...")
    arxiv.arxiv.download(
        paper, slugify=lambda _: 'src', dirpath=str(temp_dir),
        prefer_source_tarfile=True)

    logger.info(f'Extracting the source...')
    tar_file = temp_dir / 'src.tar.gz'
    if not tar_file.exists():
        raise SystemError('Paper sources are not available')

    with tarfile.open(tar_file) as f:
        f.extractall(temp_dir)

    def is_main_file(file_name):
        with open(file_name, 'rt') as f:
            if '\\documentclass' in f.read():
                return True
        return False

    main_files = [tex_file for tex_file in temp_dir.glob('*.tex')
                  if is_main_file(tex_file)]
    assert len(main_files) == 1
    main_file, = main_files
    logger.info(f'Fount the main tex file: {main_file.name}')
    return temp_dir, main_file, arxiv_title


def change_size(main_file, geom_settings, landscape):
    with open(main_file, 'rt') as f:
        src = f.readlines()

    # documentclass line index
    dclass_idx = next(idx for idx, line in enumerate(src)
                      if '\\documentclass' in line)

    # filter comments/newlines for easier debugging:
    src = [line for line in src if line[0] != '%' and len(line.strip()) > 0]

    # strip font size, column stuff, and paper size stuff in documentclass line:
    src[dclass_idx] = re.sub(r'\b\d+pt\b', '', src[dclass_idx])
    src[dclass_idx] = re.sub(r'\b\w+column\b', '', src[dclass_idx])
    src[dclass_idx] = re.sub(r'\b\w+paper\b', '', src[dclass_idx])
    # remove extraneous starting commas
    src[dclass_idx] = re.sub(r'(?<=\[),', '', src[dclass_idx])
    # remove extraneous middle/ending commas
    src[dclass_idx] = re.sub(r',(?=[\],])', '', src[dclass_idx])

    # find begin{document}:
    begindocs = [i for i, line in enumerate(src) if line.startswith(r'\begin{document}')]
    assert(len(begindocs) == 1)
    geom_settings_str = ",".join(k+"="+v for k, v in geom_settings.items())
    geom_settings_str += ",landscape" if landscape else ""
    src.insert(
        begindocs[0],
        f'\\usepackage[{geom_settings_str}]{{geometry}}\n')
    src.insert(begindocs[0], '\\usepackage{times}\n')
    src.insert(begindocs[0], '\\pagestyle{empty}\n')
    src.insert(begindocs[0], '\\usepackage{breqn}\n')
    if landscape:
        src.insert(begindocs[0], '\\usepackage{pdflscape}\n')

    # shrink figures to be at most the size of the page:
    for i in range(len(src)):
        line = src[i]
        m = re.search(r'\\includegraphics\[width=([.\d]+)\\(line|text)width\]', line)
        if m:
            mul = m.group(1)
            src[i] = re.sub(
                r'\\includegraphics\[width=([.\d]+)\\(line|text)width\]',
                f'\\\\includegraphics[width={mul}\\\\textwidth,height={mul}\\\\textheight,keepaspectratio]',
                line)
            continue
        # deal with figures which do not have sizes specified
        if '\\includegraphics{' in line:
            src[i] = re.sub(
                r'\\includegraphics{',
                r'\\includegraphics[scale=0.5]{',
                line)
            continue
        # deal with scaled figures
        m = re.search(r'\\includegraphics\[scale=([.\d]+)\]', line)
        if m:
            mul = float(m.group(1))
            src[i] = re.sub(
                r'\\includegraphics\[scale=([.\d]+)\]',
                f'\\\\includegraphics\\[scale={mul / 2}\\]',
                line)
            continue

    # allow placing inline equations on new line
    for i in range(len(src)):
        line = src[i]
        m = re.search(r'\$.+\$', line)
        if m:
            src[i] = "\\sloppy " + line

    os.rename(main_file, main_file.with_suffix('.tex.bak'))
    with open(main_file, 'wt') as f:
        f.writelines(src)


def compile_tex(file_name):
    # Compile 3 times
    for _ in range(3):
        subprocess.run(['pdflatex', file_name],
                       stdout=sys.stderr,
                       cwd=file_name.parent)


def rotate_pdf(pdf_file):
    os.rename(pdf_file, pdf_file.with_suffix('.pdf.bak'))
    subprocess.run(
        ['pdftk', pdf_file.with_suffix('.pdf.bak'),
         'rotate', '1-endeast', 'output', pdf_file],
        stdout=sys.stderr,
        cwd=pdf_file.parent)


def make_single_column(work_dir):
    for filename in work_dir.glob('*.sty'):
        with open(filename, 'rt') as f:
            src = f.readlines()
        out_src = []
        for line in src:
            if line.strip() == '\\twocolumn':
                continue
            out_src.append(line)
        with open(filename, 'wt') as f:
            f.writelines(out_src)


def check_prerec(landscape):
    result = subprocess.run(["pdflatex", "--version"], stdout=None, stderr=None)
    if result.returncode != 0:
        raise SystemError("no pdflatex found")
    if landscape:
        result = subprocess.run(["pdftk", "--version"], stdout=None, stderr=None)
        if result.returncode != 0:
            raise SystemError("no pdftk found (required for landscape mode)")


def main(query, dest, width, height, margin, landscape):
    check_prerec(landscape)
    
    tmp_dir, main_file, title = download(query)
    if landscape:
        width, height = height, width
    geom_settings = dict(
        paperwidth=f'{width}in',
        paperheight=f'{height}in',
        margin=f'{margin}in')

    change_size(main_file, geom_settings, landscape)
    make_single_column(tmp_dir)
    compile_tex(main_file)
    pdf_file = main_file.with_suffix('.pdf')
    if landscape:
        rotate_pdf(pdf_file)

    if dest.is_dir():
        os.rename(pdf_file, dest / (title + '.pdf'))
    elif str(dest) == '-':
        with open(main_file.with_suffix('.pdf'), 'rb') as fin:
            sys.stdout.buffer.write(fin.read())
    else:
        os.rename(pdf_file, dest)


def run():
    main(**vars(parse_args()))


if __name__ == "__main__":
    run()
