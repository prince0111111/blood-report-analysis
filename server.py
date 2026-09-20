"""
server.py - Connected Healthcare Platform API Server & Web Host

Integrates Python Clinical Pipeline with the Web Frontend.
Runs on http://localhost:8000 using Python standard library http.server.
"""

from __future__ import annotations

import json
import os
import re
import sys
import traceback
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

# Mock / Live database state in memory
MOCK_PATIENTS = {
    "PX123456": {
        "patient_id": "PX123456",
        "name": "Rahul Sharma",
        "name_masked": "Rahul S*****",
        "dob": "12-05-1995",
        "gender": "Male",
        "phone_masked": "+1 (555) ***-8912",
        "phone_full": "+1 (555) 019-8912",
        "registered_at": "2024-01-15T09:30:00Z",
        "verified": True
    },
    "PX987654": {
        "patient_id": "PX987654",
        "name": "Priya Patel",
        "name_masked": "Priya P*****",
        "dob": "22-09-1988",
        "gender": "Female",
        "phone_masked": "+1 (555) ***-4420",
        "phone_full": "+1 (555) 012-4420",
        "registered_at": "2024-03-10T14:20:00Z",
        "verified": True
    }
}

MOCK_LABS = {
    "LAB001": {
        "lab_id": "LAB001",
        "name": "Apex Diagnostics",
        "status": "approved",
        "license": "LAB-LIC-9942",
        "approved_at": "2024-01-01"
    },
    "LAB002": {
        "lab_id": "LAB002",
        "name": "Metro Pathology",
        "status": "approved",
        "license": "LAB-LIC-8831",
        "approved_at": "2024-02-15"
    },
    "LAB003": {
        "lab_id": "LAB003",
        "name": "HealthLine Labs",
        "status": "approved",
        "license": "LAB-LIC-7712",
        "approved_at": "2024-05-20"
    }
}

MOCK_DOCTORS = {
    "DOC001": {
        "doctor_id": "DOC001",
        "name": "Dr. Aris Thorne",
        "specialty": "Hematology & Internal Medicine",
        "hospital": "Central City Medical Center"
    },
    "DOC002": {
        "doctor_id": "DOC002",
        "name": "Dr. Sarah Jenkins",
        "specialty": "General Physician",
        "hospital": "Metropolitan Health System"
    }
}

MOCK_VISIT_CONSENTS = [
    {
        "id": "VC-1001",
        "patient_id": "PX123456",
        "lab_id": "LAB001",
        "otp": "849210",
        "method": "otp",
        "issued_at": "2026-09-20T10:00:00Z",
        "expires_at": "2026-09-22T10:00:00Z",
        "status": "approved"
    }
]

MOCK_DOCTOR_CONSENTS = [
    {
        "id": "DC-8001",
        "patient_id": "PX123456",
        "doctor_id": "DOC001",
        "scope": "all_reports",
        "include_future_reports": False,
        "granted_at": "2026-08-01T11:00:00Z",
        "expires_at": "2027-02-01T11:00:00Z",
        "status": "active"
    },
    {
        "id": "DC-8002",
        "patient_id": "PX123456",
        "doctor_id": "DOC002",
        "scope": "specific_report_ids",
        "scope_report_ids": ["RPT-101"],
        "include_future_reports": True,
        "granted_at": "2026-06-15T15:30:00Z",
        "expires_at": "until_revoked",
        "status": "active"
    }
]

MOCK_ACCESS_LOGS = [
    {
        "id": "LOG-501",
        "timestamp": "2026-09-20T14:32:10Z",
        "actor_type": "lab",
        "actor_id": "LAB001",
        "actor_name": "Apex Diagnostics",
        "patient_id": "PX123456",
        "action": "searched",
        "details": "Identity confirmation check on PX123456"
    },
    {
        "id": "LOG-502",
        "timestamp": "2026-09-20T14:35:45Z",
        "actor_type": "lab",
        "actor_id": "LAB001",
        "actor_name": "Apex Diagnostics",
        "patient_id": "PX123456",
        "action": "uploaded",
        "details": "Uploaded report RPT-103 (CBC Follow-up)"
    },
    {
        "id": "LOG-503",
        "timestamp": "2026-09-20T15:10:00Z",
        "actor_type": "doctor",
        "actor_id": "DOC001",
        "actor_name": "Dr. Aris Thorne",
        "patient_id": "PX123456",
        "action": "viewed",
        "details": "Viewed patient medical history under active consent DC-8001"
    }
]

MOCK_REPORTS = [
    {
        "report_id": "RPT-101",
        "patient_id": "PX123456",
        "lab_id": "LAB001",
        "lab_name": "Apex Diagnostics",
        "date": "2026-03-12",
        "panel_name": "Complete Blood Count (CBC)",
        "version": 1,
        "status": "PUBLISHED",
        "patient_context": {"sex": "male", "age": 30, "age_unit": "years"},
        "tests": [
            {"canonical_name": "hemoglobin", "raw_name": "Hemoglobin (Hb)", "value": 10.0, "unit": "g/dL", "reference_raw": "13.0-17.0", "status": "LOW", "reference_parsed": {"min": 13.0, "max": 17.0}},
            {"canonical_name": "red_blood_cells", "raw_name": "RBC Count", "value": 3.8, "unit": "M/uL", "reference_raw": "4.5-5.9", "status": "LOW", "reference_parsed": {"min": 4.5, "max": 5.9}},
            {"canonical_name": "hematocrit", "raw_name": "Hematocrit (HCT)", "value": 31.5, "unit": "%", "reference_raw": "40.0-52.0", "status": "LOW", "reference_parsed": {"min": 40.0, "max": 52.0}},
            {"canonical_name": "white_blood_cells", "raw_name": "WBC Count", "value": 6.5, "unit": "K/uL", "reference_raw": "4.5-11.0", "status": "NORMAL", "reference_parsed": {"min": 4.5, "max": 11.0}},
            {"canonical_name": "platelets", "raw_name": "Platelet Count", "value": 116, "unit": "K/uL", "reference_raw": "150-450", "status": "LOW", "reference_parsed": {"min": 150, "max": 450}},
            {"canonical_name": "mcv", "raw_name": "MCV", "value": 74.0, "unit": "fL", "reference_raw": "80-100", "status": "LOW", "reference_parsed": {"min": 80, "max": 100}}
        ],
        "findings": [
            {
                "pattern_id": "anemia_microcytic",
                "title": "Microcytic Hypochromic Anemia Pattern",
                "severity": "HIGH",
                "confidence": 0.88,
                "evidence": ["Hemoglobin 10.0 g/dL (LOW)", "RBC 3.8 M/uL (LOW)", "Hematocrit 31.5% (LOW)", "MCV 74 fL (LOW)"],
                "explanation": "Simultaneous reduction in Hemoglobin, RBC, Hematocrit and MCV strongly indicates microcytic anemia, commonly associated with iron deficiency or chronic blood loss."
            },
            {
                "pattern_id": "thrombocytopenia_mild",
                "title": "Mild Thrombocytopenia",
                "severity": "MODERATE",
                "confidence": 0.76,
                "evidence": ["Platelets 116 K/uL (LOW, Ref 150-450)"],
                "explanation": "Platelet count below 150 K/uL warrants clinical monitoring to evaluate potential production or consumption causes."
            }
        ]
    },
    {
        "report_id": "RPT-102",
        "patient_id": "PX123456",
        "lab_id": "LAB002",
        "lab_name": "Metro Pathology",
        "date": "2026-06-18",
        "panel_name": "Comprehensive Blood Panel",
        "version": 1,
        "status": "PUBLISHED",
        "patient_context": {"sex": "male", "age": 30, "age_unit": "years"},
        "tests": [
            {"canonical_name": "hemoglobin", "raw_name": "Hemoglobin (Hb)", "value": 11.2, "unit": "g/dL", "reference_raw": "13.0-17.0", "status": "LOW", "reference_parsed": {"min": 13.0, "max": 17.0}},
            {"canonical_name": "red_blood_cells", "raw_name": "RBC Count", "value": 4.1, "unit": "M/uL", "reference_raw": "4.5-5.9", "status": "LOW", "reference_parsed": {"min": 4.5, "max": 5.9}},
            {"canonical_name": "white_blood_cells", "raw_name": "WBC Count", "value": 7.1, "unit": "K/uL", "reference_raw": "4.5-11.0", "status": "NORMAL", "reference_parsed": {"min": 4.5, "max": 11.0}},
            {"canonical_name": "platelets", "raw_name": "Platelet Count", "value": 142, "unit": "K/uL", "reference_raw": "150-450", "status": "LOW", "reference_parsed": {"min": 150, "max": 450}},
            {"canonical_name": "mcv", "raw_name": "MCV", "value": 78.5, "unit": "fL", "reference_raw": "80-100", "status": "LOW", "reference_parsed": {"min": 80, "max": 100}}
        ],
        "findings": [
            {
                "pattern_id": "anemia_improving",
                "title": "Improving Anemia Trend",
                "severity": "MODERATE",
                "confidence": 0.82,
                "evidence": ["Hemoglobin increased from 10.0 to 11.2 g/dL", "MCV increased from 74.0 to 78.5 fL"],
                "explanation": "Positive trend in Hemoglobin and MCV compared to prior lab baseline from Apex Diagnostics."
            }
        ]
    },
    {
        "report_id": "RPT-103",
        "patient_id": "PX123456",
        "lab_id": "LAB001",
        "lab_name": "Apex Diagnostics",
        "date": "2026-09-15",
        "panel_name": "CBC & Iron Follow-up",
        "version": 2,
        "status": "PUBLISHED",
        "patient_context": {"sex": "male", "age": 31, "age_unit": "years"},
        "tests": [
            {"canonical_name": "hemoglobin", "raw_name": "Hemoglobin (Hb)", "value": 13.5, "unit": "g/dL", "reference_raw": "13.0-17.0", "status": "NORMAL", "reference_parsed": {"min": 13.0, "max": 17.0}},
            {"canonical_name": "red_blood_cells", "raw_name": "RBC Count", "value": 4.7, "unit": "M/uL", "reference_raw": "4.5-5.9", "status": "NORMAL", "reference_parsed": {"min": 4.5, "max": 5.9}},
            {"canonical_name": "hematocrit", "raw_name": "Hematocrit (HCT)", "value": 42.0, "unit": "%", "reference_raw": "40.0-52.0", "status": "NORMAL", "reference_parsed": {"min": 40.0, "max": 52.0}},
            {"canonical_name": "white_blood_cells", "raw_name": "WBC Count", "value": 5.9, "unit": "K/uL", "reference_raw": "4.5-11.0", "status": "NORMAL", "reference_parsed": {"min": 4.5, "max": 11.0}},
            {"canonical_name": "platelets", "raw_name": "Platelet Count", "value": 210, "unit": "K/uL", "reference_raw": "150-450", "status": "NORMAL", "reference_parsed": {"min": 150, "max": 450}},
            {"canonical_name": "mcv", "raw_name": "MCV", "value": 86.0, "unit": "fL", "reference_raw": "80-100", "status": "NORMAL", "reference_parsed": {"min": 80, "max": 100}}
        ],
        "findings": [
            {
                "pattern_id": "cbc_normal",
                "title": "Complete Resolution of Anemia & Thrombocytopenia",
                "severity": "LOW",
                "confidence": 0.95,
                "evidence": ["All CBC markers within standard age/sex reference intervals"],
                "explanation": "All hematologic parameters have normalized, confirming effective therapeutic response."
            }
        ],
        "version_history": [
            {"version": 1, "updated_at": "2026-09-15T09:00:00Z", "reason": "Initial upload"},
            {"version": 2, "updated_at": "2026-09-15T11:20:00Z", "reason": "Lab correction: Verified Platelet rerun count"}
        ]
    }
]


class PlatformRequestHandler(SimpleHTTPRequestHandler):
    """Custom request handler supporting REST API endpoints and static file serving."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PROJECT_ROOT), **kwargs)

    def _send_json(self, data, status=200):
        body = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        # Serve API routes
        if path == "/api/health":
            return self._send_json({"status": "ok", "platform": "Blood Report Analysis AI V1.1"})

        elif path == "/api/patients/search":
            patient_id = query.get("id", [""])[0]
            actor_type = query.get("actor_type", ["lab"])[0]
            actor_id = query.get("actor_id", ["LAB001"])[0]
            
            if patient_id in MOCK_PATIENTS:
                p = MOCK_PATIENTS[patient_id]
                # Log search action
                MOCK_ACCESS_LOGS.insert(0, {
                    "id": f"LOG-{len(MOCK_ACCESS_LOGS)+501}",
                    "timestamp": "Just now",
                    "actor_type": actor_type,
                    "actor_id": actor_id,
                    "actor_name": "Apex Diagnostics" if actor_id == "LAB001" else actor_id,
                    "patient_id": patient_id,
                    "action": "searched",
                    "details": f"Identity lookup on {patient_id}"
                })
                # Gate 1 Layer A rule: return identity verification ONLY
                if actor_type == "lab":
                    return self._send_json({
                        "found": True,
                        "layer": "identity_check_only",
                        "patient": {
                            "patient_id": p["patient_id"],
                            "name": p["name_masked"],
                            "dob": p["dob"],
                            "gender": p["gender"]
                        },
                        "note": "Rule 4: Lab search returns identity fields only. Does not return phone, address, or other labs' data."
                    })
                return self._send_json({"found": True, "patient": p})
            return self._send_json({"found": False, "error": "Patient ID not found"}, status=404)

        elif path == "/api/reports":
            patient_id = query.get("patient_id", ["PX123456"])[0]
            doctor_id = query.get("doctor_id", [None])[0]

            # Check doctor consent status if requested by a doctor
            if doctor_id:
                active_consents = [c for c in MOCK_DOCTOR_CONSENTS if c["patient_id"] == patient_id and c["doctor_id"] == doctor_id and c["status"] == "active"]
                if not active_consents:
                    return self._send_json({
                        "error": "Access Denied. Active Doctor Consent record required.",
                        "rule": "Gate 2 Doctor Authorization (Section 6 & 7)"
                    }, status=403)

            reports = [r for r in MOCK_REPORTS if r["patient_id"] == patient_id]
            return self._send_json({"patient_id": patient_id, "reports": reports})

        elif path == "/api/doctor-consents":
            patient_id = query.get("patient_id", ["PX123456"])[0]
            consents = [c for c in MOCK_DOCTOR_CONSENTS if c["patient_id"] == patient_id]
            return self._send_json({"consents": consents})

        elif path == "/api/audit-logs":
            return self._send_json({"logs": MOCK_ACCESS_LOGS})

        # Fallback to standard HTTP file server for HTML/JS/CSS
        return super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        content_len = int(self.headers.get("Content-Length", 0))
        post_bytes = self.rfile.read(content_len) if content_len > 0 else b""
        
        try:
            body_data = json.loads(post_bytes.decode("utf-8")) if post_bytes else {}
        except Exception:
            body_data = {}

        if path == "/api/visit-consent/create":
            # Patient generates visit OTP/QR
            otp = str(body_data.get("otp", "849210"))
            lab_id = body_data.get("lab_id", "LAB001")
            patient_id = body_data.get("patient_id", "PX123456")

            consent = {
                "id": f"VC-{len(MOCK_VISIT_CONSENTS)+1001}",
                "patient_id": patient_id,
                "lab_id": lab_id,
                "otp": otp,
                "method": "otp",
                "issued_at": "Just now",
                "expires_at": "In 24 hours",
                "status": "approved"
            }
            MOCK_VISIT_CONSENTS.append(consent)
            return self._send_json({"success": True, "visit_consent": consent})

        elif path == "/api/doctor-consent/grant":
            # Patient grants doctor access
            new_grant = {
                "id": f"DC-{len(MOCK_DOCTOR_CONSENTS)+8001}",
                "patient_id": body_data.get("patient_id", "PX123456"),
                "doctor_id": body_data.get("doctor_id", "DOC001"),
                "scope": body_data.get("scope", "all_reports"),
                "include_future_reports": body_data.get("include_future_reports", False),
                "granted_at": "Just now",
                "expires_at": body_data.get("expires_at", "12_months"),
                "status": "active"
            }
            MOCK_DOCTOR_CONSENTS.append(new_grant)

            # Audit log
            MOCK_ACCESS_LOGS.insert(0, {
                "id": f"LOG-{len(MOCK_ACCESS_LOGS)+501}",
                "timestamp": "Just now",
                "actor_type": "patient",
                "actor_id": new_grant["patient_id"],
                "actor_name": "Rahul Sharma",
                "patient_id": new_grant["patient_id"],
                "action": "granted_consent",
                "details": f"Granted Doctor Consent to {new_grant['doctor_id']} (Scope: {new_grant['scope']}, Future: {new_grant['include_future_reports']})"
            })
            return self._send_json({"success": True, "consent": new_grant})

        elif path == "/api/doctor-consent/revoke":
            consent_id = body_data.get("id")
            for c in MOCK_DOCTOR_CONSENTS:
                if c["id"] == consent_id:
                    c["status"] = "revoked"
                    c["revoked_at"] = "Just now"

                    MOCK_ACCESS_LOGS.insert(0, {
                        "id": f"LOG-{len(MOCK_ACCESS_LOGS)+501}",
                        "timestamp": "Just now",
                        "actor_type": "patient",
                        "actor_id": c["patient_id"],
                        "actor_name": "Rahul Sharma",
                        "patient_id": c["patient_id"],
                        "action": "revoked_consent",
                        "details": f"Revoked Doctor Consent {consent_id} for Doctor {c['doctor_id']}"
                    })
                    return self._send_json({"success": True, "consent": c})
            return self._send_json({"error": "Consent ID not found"}, status=404)

        elif path == "/api/clinical-pipeline/run":
            # Run python clinical pipeline if sample file requested
            sample_file = body_data.get("sample", "sample.pdf")
            sample_path = PROJECT_ROOT / "samples" / "reports" / sample_file

            if not sample_path.exists():
                sample_path = PROJECT_ROOT / "samples" / "reports" / "sample.pdf"

            try:
                from clinical_pipeline import ClinicalPipeline
                from main import build_knowledge_engine
                
                engine = build_knowledge_engine()
                pipeline = ClinicalPipeline(engine=engine)
                res = pipeline.run(sample_path)

                # Format response
                lab_results_data = []
                for lr in res.lab_results:
                    lab_results_data.append({
                        "name": lr.name,
                        "value": lr.value,
                        "unit": lr.unit,
                        "status": lr.status,
                        "reference_interval": str(lr.reference_interval)
                    })

                findings_data = []
                for f in res.findings:
                    findings_data.append({
                        "title": f.title,
                        "severity": f.severity.value if hasattr(f.severity, "value") else str(f.severity),
                        "confidence": getattr(f, "confidence", 0.9),
                        "evidence": list(getattr(f, "evidence", []))
                    })

                return self._send_json({
                    "success": True,
                    "pipeline_output": {
                        "source": res.extraction.source.as_dict() if hasattr(res.extraction.source, "as_dict") else str(res.extraction.source),
                        "patient": res.extraction.patient,
                        "tests": res.extraction.tests,
                        "validation": res.extraction.validation,
                        "coverage": res.extraction.coverage,
                        "plausibility": res.extraction.plausibility,
                        "lab_results": lab_results_data,
                        "findings": findings_data
                    }
                })
            except Exception as e:
                return self._send_json({
                    "success": False,
                    "error": str(e),
                    "traceback": traceback.format_exc()
                }, status=500)

        return self._send_json({"error": "Endpoint not found"}, status=404)


def run_server(port=8000):
    server_address = ("", port)
    httpd = HTTPServer(server_address, PlatformRequestHandler)
    print(f"==================================================")
    print(f" Connected Healthcare Platform Server Running!")
    print(f" Open http://localhost:{port} in your browser")
    print(f"==================================================")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        httpd.server_close()


if __name__ == "__main__":
    run_server()
