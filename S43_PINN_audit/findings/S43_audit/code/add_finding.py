"""Append a dated research observation without changing generated findings."""
from pathlib import Path
from datetime import datetime,timezone
import argparse
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--run',type=Path,required=True)
for key in ['observation','evidence','interpretation','question']:p.add_argument('--'+key,required=True)
a=p.parse_args()
if not (a.run/'config.json').exists():p.error('Not an audit run')
with (a.run/'research_notes.md').open('a') as f:
    f.write('\n## '+datetime.now(timezone.utc).isoformat()+'\n\n')
    for key in ['observation','evidence','interpretation','question']:f.write(f'**{key.title()}:** {getattr(a,key)}\n\n')
