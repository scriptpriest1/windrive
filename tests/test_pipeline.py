import json
import unittest
from pathlib import Path

import joblib
import pandas as pd

from app.collectors.driver_collector import _parse_pnputil
from app.collectors.event_collector import _parse_rendered_events
from app.features.feature_engineer import FEATURES, build_feature_rows, build_features, validate_raw_evidence_records
from app.ml.preprocessing import DropAllMissingColumns
from app.ml.predictor import load_production_model, predict
from scripts.train_model import load_dataset, validate_engineered_dataset


REFERENCE = "2026-10-03T12:00:00Z"


def record(label="normal", events=None, crashes=None):
    return {"driver": {"driver_name": "sample.sys", "file_name": "sample.sys", "driver_date": "20250115", "device_status": "OK", "driver_start_status": "True", "signature_status": "Signed", "device_category": "Net", "device_error_code": 0}, "events": events or [], "crashes": crashes or [], "reference_time": REFERENCE, "classification": label}


class FeatureAndValidationTests(unittest.TestCase):
    def test_feature_evidence_and_unavailable_update_fields(self):
        normal = build_features(record()["driver"], [], [], REFERENCE)
        suspicious_events = [{"TimeCreated": "2026-10-02T12:00:00Z", "LevelDisplayName": "Warning", "Message": "sample.sys: operation timeout recovered"}]
        faulty_events = [{"TimeCreated": "2026-10-02T12:00:00Z", "LevelDisplayName": "Error", "Message": "sample.sys: driver start failed"}, {"TimeCreated": "2026-10-01T12:00:00Z", "LevelDisplayName": "Error", "Message": "sample.sys: initialization failed"}]
        suspicious = build_features(record()["driver"], suspicious_events, [], REFERENCE)
        faulty = build_features(record()["driver"], faulty_events, [], REFERENCE)
        self.assertEqual(normal["error_count"], 0)
        self.assertEqual(suspicious["timeout_count"], 1)
        self.assertEqual(faulty["driver_start_failure_count"], 1)
        self.assertIsNone(normal["days_since_last_update"])
        self.assertIsNone(normal["recently_updated"])

    def test_raw_validation_rejects_invalid_duplicate_and_missing(self):
        valid = record()
        validate_raw_evidence_records([valid])
        with self.assertRaises(ValueError): validate_raw_evidence_records([valid, valid])
        invalid = record("invalid")
        with self.assertRaises(ValueError): validate_raw_evidence_records([invalid])
        with self.assertRaises(ValueError): validate_raw_evidence_records([{"classification": "normal"}])

    def test_feature_rows_match_declared_schema(self):
        row = build_feature_rows([record()])[0]
        self.assertEqual(set(row), set(FEATURES + ["classification"]))


class PreprocessingAndModelTests(unittest.TestCase):
    def test_all_missing_columns_are_dropped_consistently(self):
        train = pd.DataFrame({"observed": [1, None, 3], "never_observed": [None, None, None]})
        transformer = DropAllMissingColumns().fit(train)
        self.assertEqual(transformer.dropped_columns_, ["never_observed"])
        self.assertEqual(list(transformer.transform(pd.DataFrame({"observed": [2], "never_observed": [None]})).columns), ["observed"])

    def test_production_model_schema_and_inference(self):
        model = load_production_model()
        self.assertEqual(model["feature_schema"], FEATURES)
        features = build_features(record()["driver"], [], [], REFERENCE)
        label, confidence = predict(features, model)
        self.assertIn(label, {"NORMAL", "SUSPICIOUS", "FAULTY"})
        self.assertGreaterEqual(confidence, 0)
        self.assertLessEqual(confidence, 1)

    def test_schema_mismatch_is_rejected(self):
        features = build_features(record()["driver"], [], [], REFERENCE)
        with self.assertRaises(ValueError):
            predict(features, {"feature_schema": ["wrong"], "pipeline": object()})

    def test_json_training_input_is_raw_evidence(self):
        path = Path(__file__).with_name("_raw_input_test.json")
        try:
            records = [
                record("normal"),
                record("suspicious", [{"TimeCreated": "2026-10-01T00:00:00Z", "LevelDisplayName": "Warning", "Message": "sample.sys: timeout"}]),
                record("faulty", [{"TimeCreated": "2026-10-02T00:00:00Z", "LevelDisplayName": "Error", "Message": "sample.sys: driver start failed"}]),
            ]
            # The file only tests the raw JSON loading path; duplicate classes are validated separately.
            path.write_text(json.dumps(records), encoding="utf-8")
            frame = load_dataset(str(path))
            self.assertTrue(set(FEATURES).issubset(frame.columns))
        finally:
            path.unlink(missing_ok=True)


class CollectorParsingTests(unittest.TestCase):
    def test_pnputil_fallback_parser(self):
        rows = _parse_pnputil("Published Name: oem1.inf\nOriginal Name: sample.inf\nProvider Name: Example Corp\nClass Name: Net\nDriver Version: 01/02/2025 1.2.3\nSigner Name: Example Signer\n")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["driver_name"], "sample.inf")
        self.assertEqual(rows[0]["signature_status"], "Signed")

    def test_event_xml_parser_preserves_fields(self):
        xml = """<Event xmlns='http://schemas.microsoft.com/win/2004/08/events/event'><System><Provider Name='Kernel-PnP'/><EventID>219</EventID><Level>3</Level><TimeCreated SystemTime='2026-10-02T00:00:00Z'/></System><RenderingInfo><Message>sample.sys warning</Message><Level>Warning</Level></RenderingInfo></Event>"""
        event = _parse_rendered_events(xml)[0]
        self.assertEqual(event["Id"], 219)
        self.assertEqual(event["Message"], "sample.sys warning")


if __name__ == "__main__":
    unittest.main()
