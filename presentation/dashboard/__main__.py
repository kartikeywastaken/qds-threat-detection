"""Launch the live dashboard: python -m presentation.dashboard --log PATH."""
import argparse
from presentation.dashboard import draw

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--log',default='artifacts/events.jsonl');args=parser.parse_args()
    draw(args.log,live=True)
