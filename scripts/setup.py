"""Make local passwords without putting them in source control."""
import argparse
from pathlib import Path
import secrets

parser = argparse.ArgumentParser()
parser.add_argument('--test', action='store_true')
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
target = root / ('.env.test' if args.test else '.env')
if target.exists():
    print(f'{target.name} already exists. Kept the current settings.')
else:
    target.write_text('DB_PASSWORD=' + secrets.token_hex(24) + '\nDEMO_PASSWORD=' + secrets.token_hex(16) + '\nOPENAI_API_KEY=\nOPENAI_MODEL=\nINPUT_COST_PER_MILLION=\nOUTPUT_COST_PER_MILLION=\n')
    print(f'Created {target.name}. Read DEMO_PASSWORD there when signing in.')
