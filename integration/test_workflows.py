"""HTTP and database tests. Use compose.test.yaml and its separate test database."""
import concurrent.futures
from contextlib import contextmanager
import json
import os
import re
from pathlib import Path
import subprocess
import sys
import uuid
import httpx
import psycopg
import pytest
PROJECTS = Path(__file__).resolve().parents[1]
CONFIG = dict((line.split('=', 1) for line in (PROJECTS / os.getenv('TEST_ENV_FILE', '.env.test')).read_text().splitlines() if '=' in line and (not line.startswith('#'))))
PASSWORD = CONFIG['DEMO_PASSWORD']
BASE = {name: os.getenv(name.upper() + '_TEST_URL', f'http://127.0.0.1:{port}') for name, port in (('stockroom', 5501), ('importdesk', 5512), ('sourcenotes', 5503))}

def database(name):
    return psycopg.connect(host=os.getenv('TEST_DB_HOST', '127.0.0.1'), port=int(os.getenv('TEST_DB_PORT', '54402')), user='portfolio', password=CONFIG['DB_PASSWORD'], dbname=name + '_test')

@contextmanager
def client(name, user='demo'):
    c = httpx.Client(base_url=BASE[name], timeout=20)
    session = c.get('/api/session').json()
    if name == 'stockroom':
        r = c.post('/api/login', data={'username': user, 'password': PASSWORD}, headers={'X-CSRF-TOKEN': session['csrf']})
        assert r.status_code == 204, r.text
        session = c.get('/api/session').json()
    else:
        r = c.post('/api/login', json={'username': user, 'password': PASSWORD})
        assert r.status_code == 200, r.text
        session = r.json()
    c.headers['X-CSRF-TOKEN'] = session['csrf']
    try:
        yield c
    finally:
        c.close()

@pytest.mark.parametrize('app,path', [('importdesk', '/api/dashboard')])
def test_private_data_needs_sign_in(app, path):
    assert httpx.get(BASE[app] + path).status_code == 401

@pytest.mark.parametrize('app,user,path,payload', [('importdesk', 'demo', '/api/sample', {})])
def test_writes_need_csrf(app, user, path, payload):
    with client(app, user) as c:
        del c.headers['X-CSRF-TOKEN']
        assert c.post(path, json=payload).status_code == 403

def run_import_worker():
    url = f"postgresql://portfolio:{CONFIG['DB_PASSWORD']}@{os.getenv('TEST_DB_HOST', '127.0.0.1')}:{os.getenv('TEST_DB_PORT', '54402')}/importdesk_test"
    env = os.environ | {'DATABASE_URL': url}
    subprocess.run([sys.executable, '-c', 'from app.importer import run_once;\nwhile run_once(): pass'], cwd=PROJECTS, env=env, check=True, capture_output=True, timeout=40)

def test_import_reports_rejections_and_reuses_identical_file():
    unique = uuid.uuid4().hex[:10]
    raw = f'reading_id,vehicle_id,recorded_at,miles,fuel_gallons\n{unique},VAN-01,2026-09-23T08:00:00Z,10,1\n{unique},VAN-01,2026-09-23T08:00:00Z,10,1\nBAD-{unique},,not-date,-5,2\n'
    with client('importdesk') as c:
        first = c.post('/api/imports', json={'name': 'Mixed rows.csv', 'csv': raw}).json()
        second = c.post('/api/imports', json={'name': 'Mixed rows.csv', 'csv': raw}).json()
        assert first['id'] == second['id'] and second['reused']
        run_import_worker()
        result = c.get(f"/api/jobs/{first['id']}").json()
        assert (result['accepted'], result['duplicates'], result['rejected']) == (1, 1, 1)
        assert result['rejections'][0]['row_number'] == 4
        assert c.get(f"/api/jobs/{first['id']}/raw").text == raw

def test_changed_columns_fail_without_partial_records():
    with client('importdesk') as c:
        raw = 'wrong,columns\n' + uuid.uuid4().hex + ',1\n'
        job = c.post('/api/imports', json={'name': 'Changed.csv', 'csv': raw}).json()
        run_import_worker()
        row = c.get(f"/api/jobs/{job['id']}").json()
        assert row['status'] == 'failed' and 'Columns changed' in row['error']
        assert c.post(f"/api/jobs/{job['id']}/retry", json={}).status_code == 200
        run_import_worker()
        assert c.get(f"/api/jobs/{job['id']}").json()['attempts'] == 2

def test_abandoned_import_is_recovered():
    unique = uuid.uuid4().hex[:10]
    with client('importdesk') as c:
        raw = f'reading_id,vehicle_id,recorded_at,miles,fuel_gallons\n{unique},VAN-02,2026-09-23T08:00:00Z,5,1\n'
        job = c.post('/api/imports', json={'name': 'Interrupted.csv', 'csv': raw}).json()
        with database('importdesk') as db:
            db.execute("UPDATE jobs SET status='running',attempts=1,started_at=now()-interval '6 minutes' WHERE id=%s", (job['id'],))
        run_import_worker()
        row = c.get(f"/api/jobs/{job['id']}").json()
        assert row['status'] == 'completed' and row['attempts'] == 2 and (row['accepted'] == 1)

def test_changed_reading_is_rejected_without_overwriting():
    unique = uuid.uuid4().hex[:10]
    with client('importdesk') as c:
        header = 'reading_id,vehicle_id,recorded_at,miles,fuel_gallons\n'
        for miles in (10, 20):
            raw = header + f'{unique},VAN-03,2026-09-23T08:00:00Z,{miles},1\n'
            job = c.post('/api/imports', json={'name': 'Corrected values.csv', 'csv': raw}).json()
            run_import_worker()
        result = c.get(f"/api/jobs/{job['id']}").json()
        assert result['accepted'] == 0 and result['rejected'] == 1
        with database('importdesk') as db:
            assert db.execute('SELECT miles FROM readings WHERE reading_id=%s', (unique,)).fetchone()[0] == 10

def test_malformed_csv_rolls_back_earlier_rows():
    unique = uuid.uuid4().hex[:10]
    raw = f'reading_id,vehicle_id,recorded_at,miles,fuel_gallons\n{unique},VAN-03,2026-09-23T08:00:00Z,10,1\n"unclosed field'
    with client('importdesk') as c:
        job = c.post('/api/imports', json={'name': 'Malformed.csv', 'csv': raw}).json()
        run_import_worker()
        assert c.get(f"/api/jobs/{job['id']}").json()['status'] == 'failed'
        with database('importdesk') as db:
            assert db.execute('SELECT count(*) FROM readings WHERE reading_id=%s', (unique,)).fetchone()[0] == 0

@pytest.mark.parametrize('name,title', [('importdesk', 'Import Desk')])
def test_sign_in_page_and_script_are_public(name, title):
    response = httpx.get(BASE[name] + '/')
    assert response.status_code == 200
    assert title in response.text
    script = re.search('<script[^>]*src="([^"]+)"', response.text)
    assert script
    asset = httpx.get(BASE[name] + script.group(1))
    assert asset.status_code == 200 and 'javascript' in asset.headers['content-type']

@pytest.mark.parametrize('name', ['importdesk'])
def test_non_ascii_wrong_password_is_rejected(name):
    assert httpx.post(BASE[name] + '/api/login', json={'username': 'demo', 'password': 'incorrect-é'}).status_code == 401
