import datetime as dt
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import digest


class DeliveryTests(unittest.TestCase):
    def run_digest(self, state_path, manual=False, result=None):
        argv = ['digest.py'] + (['--manual'] if manual else [])
        paper = {'doi': '10.1/new', 'title': 'New paper'}
        with patch('sys.argv', argv), patch.object(digest, 'STATE', state_path), \
                patch.object(digest, 'load_index', return_value={}), \
                patch.object(digest, 'select', return_value=[('Gene therapy', 'Recent research', paper)]), \
                patch.dict('os.environ', {'TELEGRAM_BOT_TOKEN': 'test', 'TELEGRAM_CHAT_ID': 'test'}), \
                patch.object(digest, 'request_json', return_value=result or {'ok': True}) as send:
            digest.main()
            return send.call_count

    def test_legacy_night_test_does_not_block_morning(self):
        today = str((dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=3)).date())
        with tempfile.TemporaryDirectory() as folder:
            state = Path(folder) / 'state.json'
            state.write_text(json.dumps({'last_date': today, 'seen': []}))
            self.assertEqual(self.run_digest(state), 1)
            self.assertEqual(self.run_digest(state), 0)
            self.assertEqual(json.loads(state.read_text())['last_scheduled_date'], today)

    def test_manual_and_scheduled_slots_are_independent(self):
        with tempfile.TemporaryDirectory() as folder:
            state = Path(folder) / 'state.json'
            self.assertEqual(self.run_digest(state, manual=True), 1)
            self.assertEqual(self.run_digest(state), 1)
            self.assertEqual(self.run_digest(state, manual=True), 0)
            self.assertEqual(self.run_digest(state), 0)
            saved = json.loads(state.read_text())
            self.assertEqual(saved['last_manual_date'], saved['last_scheduled_date'])

    def test_failed_telegram_send_does_not_consume_slot(self):
        with tempfile.TemporaryDirectory() as folder:
            state = Path(folder) / 'state.json'
            with self.assertRaises(SystemExit):
                self.run_digest(state, result={'ok': False})
            self.assertFalse(state.exists())
            self.assertEqual(self.run_digest(state), 1)
