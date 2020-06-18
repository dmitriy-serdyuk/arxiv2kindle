# arxiv2kindle

A simple script to recompile arxiv papers to kindle-like format.

## Usage

With your paper of choice run:
```
arxiv2kindle --width 4 --height 6 --margin 0.2 https://arxiv.org/abs/1802.08395 > out.pdf
```
or 
```
arxiv2kindle --width 6 --height 4 --margin 0.2 --landscape --dest-dir ./ https://arxiv.org/abs/1802.08395
```

## Acknowledgements

This script is based on this amazing [notebook](https://gist.github.com/bshillingford/6259986edca707ca58dd).