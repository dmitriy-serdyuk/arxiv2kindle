# arxiv2kindle

A simple script to recompile arxiv papers to kindle-like format.

## How does it work?

This script downloads the LaTeX source from arxiv 
and re-compiles it trying to fit a smaller size.
We also apply some simple transforms such as:
- downsize images;
- add automatic line breaks in formulas;
- allow formulas be placed on the next line;
- try to convert two-sided documents to one-sided format.

All these transformations are automatic, so the success is not guaranteed.
This approach will also not work for papers without the source.
Nevertheless, in most cases the result is readable 
(tested on an old 6.5in x 4.5in Kindle).


## Usage

With your paper of choice run:
```
arxiv2kindle --width 4 --height 6 --margin 0.2 1802.08395 - > out.pdf
```
or 
```
arxiv2kindle --width 6 --height 4 --margin 0.2 --landscape "Towards end-to-end spoken language understanding" ./
```

## Installation

`arxiv2kindle` requires `pip` version 10.0 or greater. 

To install the package, run
```
pip install arxiv2kindle
```

## Acknowledgements

This script is based on this amazing [notebook](https://gist.github.com/bshillingford/6259986edca707ca58dd).

## Related projects

- https://github.com/cerisara/arxiv2kindle
- https://knanagnostopoulos.blogspot.com/2013/03/from-arxiv-directly-to-my-kindle_15.html
- https://dlmf.nist.gov/LaTeXML/