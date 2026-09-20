/**
 * Blood Report Analysis AI — Connected Healthcare Platform
 * Frontend Application Logic (app.js)
 */

// Application State
const state = {
  activeRole: 'patient',
  patientId: 'PX123456',
  reports: [
    {
      report_id: "RPT-101",
      patient_id: "PX123456",
      lab_id: "LAB001",
      lab_name: "Apex Diagnostics",
      date: "2026-03-12",
      panel_name: "Complete Blood Count (CBC)",
      version: 1,
      status: "PUBLISHED",
      tests: [
        { name: "Hemoglobin (Hb)", value: "10.0 g/dL", status: "LOW", ref: "13.0 - 17.0" },
        { name: "RBC Count", value: "3.8 M/uL", status: "LOW", ref: "4.5 - 5.9" },
        { name: "WBC Count", value: "6.5 K/uL", status: "NORMAL", ref: "4.5 - 11.0" },
        { name: "Platelet Count", value: "116 K/uL", status: "LOW", ref: "150 - 450" },
        { name: "MCV", value: "74.0 fL", status: "LOW", ref: "80 - 100" }
      ],
      findings: [
        { title: "Microcytic Hypochromic Anemia Pattern", severity: "HIGH", confidence: "88%" }
      ]
    },
    {
      report_id: "RPT-102",
      patient_id: "PX123456",
      lab_id: "LAB002",
      lab_name: "Metro Pathology",
      date: "2026-06-18",
      panel_name: "Comprehensive Blood Panel",
      version: 1,
      status: "PUBLISHED",
      tests: [
        { name: "Hemoglobin (Hb)", value: "11.2 g/dL", status: "LOW", ref: "13.0 - 17.0" },
        { name: "RBC Count", value: "4.1 M/uL", status: "LOW", ref: "4.5 - 5.9" },
        { name: "WBC Count", value: "7.1 K/uL", status: "NORMAL", ref: "4.5 - 11.0" },
        { name: "Platelet Count", value: "142 K/uL", status: "LOW", ref: "150 - 450" },
        { name: "MCV", value: "78.5 fL", status: "LOW", ref: "80 - 100" }
      ],
      findings: [
        { title: "Improving Anemia Trend", severity: "MODERATE", confidence: "82%" }
      ]
    },
    {
      report_id: "RPT-103",
      patient_id: "PX123456",
      lab_id: "LAB001",
      lab_name: "Apex Diagnostics",
      date: "2026-09-15",
      panel_name: "CBC & Iron Follow-up",
      version: 2,
      status: "PUBLISHED",
      tests: [
        { name: "Hemoglobin (Hb)", value: "13.5 g/dL", status: "NORMAL", ref: "13.0 - 17.0" },
        { name: "RBC Count", value: "4.7 M/uL", status: "NORMAL", ref: "4.5 - 5.9" },
        { name: "WBC Count", value: "5.9 K/uL", status: "NORMAL", ref: "4.5 - 11.0" },
        { name: "Platelet Count", value: "210 K/uL", status: "NORMAL", ref: "150 - 450" },
        { name: "MCV", value: "86.0 fL", status: "NORMAL", ref: "80 - 100" }
      ],
      findings: [
        { title: "Complete Resolution of Anemia", severity: "LOW", confidence: "95%" }
      ]
    }
  ],
  doctorConsents: [
    {
      id: "DC-8001",
      doctor_name: "Dr. Aris Thorne (Hematology)",
      scope: "All Reports",
      include_future_reports: false,
      expires_at: "In 60 Days",
      status: "active"
    },
    {
      id: "DC-8002",
      doctor_name: "Dr. Sarah Jenkins (General Physician)",
      scope: "Specific (RPT-101)",
      include_future_reports: true,
      expires_at: "Until Revoked",
      status: "active"
    }
  ],
  auditLogs: [
    {
      timestamp: "2026-09-20 14:32",
      actor_type: "lab",
      actor_name: "Apex Diagnostics (LAB001)",
      patient_id: "PX123456",
      action: "searched",
      details: "Layer A identity check search on PX123456"
    },
    {
      timestamp: "2026-09-20 14:35",
      actor_type: "lab",
      actor_name: "Apex Diagnostics (LAB001)",
      patient_id: "PX123456",
      action: "uploaded",
      details: "Uploaded report RPT-103 under fresh visit consent VC-1001"
    },
    {
      timestamp: "2026-09-20 15:10",
      actor_type: "doctor",
      actor_name: "Dr. Aris Thorne (DOC001)",
      patient_id: "PX123456",
      action: "viewed",
      details: "Viewed patient medical history under active consent DC-8001"
    }
  ]
};

let trendChartInstance = null;

// Initialize on DOM Ready
document.addEventListener('DOMContentLoaded', () => {
  renderPatientReports();
  renderDoctorConsents();
  renderDoctorReports();
  renderAuditLogs();
  initTrendChart();
});

// Role Switcher Navigation
function switchRole(role) {
  state.activeRole = role;

  // Update Nav Buttons
  document.querySelectorAll('.role-btn').forEach(btn => btn.classList.remove('active'));
  const activeBtn = document.getElementById(`btn-role-${role}`);
  if (activeBtn) activeBtn.classList.add('active');

  // Update Views
  document.querySelectorAll('.view-section').forEach(sec => sec.style.display = 'none');
  const activeView = document.getElementById(`view-${role}`);
  if (activeView) activeView.style.display = 'block';

  if (role === 'doctor') {
    setTimeout(initTrendChart, 100);
  }
}

// Patient View: Render Reports Timeline
function renderPatientReports() {
  const container = document.getElementById('patient-reports-list');
  if (!container) return;

  container.innerHTML = state.reports.map(report => `
    <div class="timeline-item">
      <div style="display: flex; justify-content: space-between; align-items: flex-start;">
        <div>
          <h4 style="font-size: 1rem; font-weight: 700; color: #ffffff;">${report.panel_name}</h4>
          <p style="font-size: 0.8rem; color: var(--text-muted);">${report.lab_name} • ${report.date} • Version ${report.version}</p>
        </div>
        <span class="badge badge-emerald">${report.status}</span>
      </div>

      <div style="margin-top: 0.75rem; background: rgba(6, 9, 17, 0.4); padding: 0.75rem; border-radius: var(--radius-sm); border: 1px solid var(--border-glass);">
        <p style="font-size: 0.75rem; font-weight: 600; color: var(--text-secondary); margin-bottom: 0.5rem;">KEY BIOMARKERS:</p>
        <div style="display: flex; flex-wrap: wrap; gap: 0.5rem;">
          ${report.tests.map(t => `
            <span class="badge ${t.status === 'LOW' ? 'badge-rose' : t.status === 'HIGH' ? 'badge-amber' : 'badge-cyan'}">
              ${t.name}: ${t.value} (${t.status})
            </span>
          `).join('')}
        </div>
      </div>
    </div>
  `).join('');
}

// Patient View: Render Doctor Consents Table
function renderDoctorConsents() {
  const tbody = document.getElementById('doctor-consents-tbody');
  if (!tbody) return;

  tbody.innerHTML = state.doctorConsents.map(c => `
    <tr>
      <td><strong>${c.doctor_name}</strong></td>
      <td><span class="badge badge-cyan">${c.scope}</span></td>
      <td>${c.include_future_reports ? '<span class="badge badge-emerald">Yes</span>' : '<span class="badge badge-amber">No (Snapshot)</span>'}</td>
      <td>${c.expires_at}</td>
      <td>
        ${c.status === 'active' ? `
          <button class="btn btn-danger" style="padding: 0.3rem 0.65rem; font-size: 0.75rem;" onclick="revokeDoctorAccess('${c.id}')">
            Revoke Access
          </button>
        ` : `
          <span class="badge badge-rose">Revoked</span>
        `}
      </td>
    </tr>
  `).join('');
}

// Doctor View: Render Patient Record
function renderDoctorReports() {
  const container = document.getElementById('doctor-reports-list');
  if (!container) return;

  container.innerHTML = state.reports.map(report => `
    <div style="background: rgba(6, 9, 17, 0.5); border: 1px solid var(--border-glass); border-radius: var(--radius-sm); padding: 1rem; margin-bottom: 1rem;">
      <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.5rem;">
        <div>
          <h4 style="font-size: 0.95rem; font-weight: 700; color: var(--text-primary);">${report.panel_name}</h4>
          <p style="font-size: 0.75rem; color: var(--text-muted);">${report.lab_name} • ${report.date} (V${report.version})</p>
        </div>
        <span class="badge badge-cyan">Lab ID: ${report.lab_id}</span>
      </div>
      
      <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 0.5rem; margin-top: 0.5rem;">
        ${report.tests.slice(0, 4).map(t => `
          <div style="font-size: 0.75rem; color: var(--text-secondary);">
            ${t.name}: <strong style="color: ${t.status === 'LOW' ? 'var(--rose-primary)' : 'var(--text-primary)'}">${t.value}</strong>
          </div>
        `).join('')}
      </div>
    </div>
  `).join('');
}

// Audit View: Render Access Logs
function renderAuditLogs() {
  const tbody = document.getElementById('audit-log-tbody');
  if (!tbody) return;

  tbody.innerHTML = state.auditLogs.map(log => `
    <tr>
      <td style="font-family: monospace; font-size: 0.8rem; color: var(--text-muted);">${log.timestamp}</td>
      <td><span class="badge ${log.actor_type === 'lab' ? 'badge-cyan' : log.actor_type === 'doctor' ? 'badge-violet' : 'badge-emerald'}">${log.actor_type}</span></td>
      <td><strong>${log.actor_name}</strong></td>
      <td style="font-family: monospace; color: var(--cyan-primary);">${log.patient_id}</td>
      <td><span class="badge badge-amber">${log.action}</span></td>
      <td style="font-size: 0.8rem; color: var(--text-secondary);">${log.details}</td>
    </tr>
  `).join('');
}

// Modal Actions
function openModal(id) {
  const modal = document.getElementById(id);
  if (modal) modal.classList.add('active');
}

function closeModal(id) {
  const modal = document.getElementById(id);
  if (modal) modal.classList.remove('active');
}

function openVisitOtpModal() {
  const randomOtp = Math.floor(100000 + Math.random() * 900000).toString();
  const formatted = `${randomOtp.slice(0, 3)}-${randomOtp.slice(3)}`;
  const display = document.getElementById('otp-code-display');
  if (display) display.innerText = formatted;
  
  // Set in lab input too
  const labInput = document.getElementById('lab-otp-input');
  if (labInput) labInput.value = randomOtp;

  openModal('modal-visit-otp');
}

function openGrantDoctorModal() {
  openModal('modal-grant-doctor');
}

function openCompareModal() {
  openModal('modal-compare-reports');
}

// Form Handlers
function submitDoctorGrant() {
  const docSelect = document.getElementById('grant-doctor-select');
  const scopeSelect = document.getElementById('grant-scope-select');
  const futureSelect = document.getElementById('grant-future-select');
  const durationSelect = document.getElementById('grant-duration-select');

  const newGrant = {
    id: `DC-${Math.floor(8000 + Math.random() * 1000)}`,
    doctor_name: docSelect.options[docSelect.selectedIndex].text,
    scope: scopeSelect.options[scopeSelect.selectedIndex].text,
    include_future_reports: futureSelect.value === 'true',
    expires_at: durationSelect.options[durationSelect.selectedIndex].text,
    status: 'active'
  };

  state.doctorConsents.unshift(newGrant);

  // Add to Audit Log
  state.auditLogs.unshift({
    timestamp: new Date().toISOString().replace('T', ' ').slice(0, 16),
    actor_type: 'patient',
    actor_name: 'Rahul Sharma (PX123456)',
    patient_id: 'PX123456',
    action: 'granted_consent',
    details: `Granted access to ${newGrant.doctor_name}`
  });

  renderDoctorConsents();
  renderAuditLogs();
  closeModal('modal-grant-doctor');
}

function revokeDoctorAccess(id) {
  const target = state.doctorConsents.find(c => c.id === id);
  if (target) {
    target.status = 'revoked';
    state.auditLogs.unshift({
      timestamp: new Date().toISOString().replace('T', ' ').slice(0, 16),
      actor_type: 'patient',
      actor_name: 'Rahul Sharma (PX123456)',
      patient_id: 'PX123456',
      action: 'revoked_consent',
      details: `Revoked access for ${target.doctor_name}`
    });
    renderDoctorConsents();
    renderAuditLogs();
  }
}

// Laboratory View Actions
function performLabPatientSearch() {
  const query = document.getElementById('lab-search-input').value.trim();
  const resContainer = document.getElementById('lab-identity-result');

  if (query === 'PX123456') {
    resContainer.innerHTML = `
      <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.75rem;">
        <strong style="color: var(--emerald-primary); font-size: 0.95rem;">✓ Patient Identity Confirmed (Layer A Onboarding)</strong>
        <span class="badge badge-emerald">IDENTITY CHECK ONLY</span>
      </div>
      <div style="font-family: monospace; font-size: 0.85rem; color: var(--text-primary); line-height: 1.8;">
        Name: Rahul S*****<br>
        DOB: 12-05-1995<br>
        Gender: Male<br>
      </div>
      <p style="font-size: 0.75rem; color: var(--rose-primary); margin-top: 0.75rem; font-weight: 600;">
        ⛔ RESTRICTED BY RULE 4: Phone number, address, previous lab reports, and other labs used are NOT exposed to Lab A!
      </p>
    `;

    // Log search
    state.auditLogs.unshift({
      timestamp: new Date().toISOString().replace('T', ' ').slice(0, 16),
      actor_type: 'lab',
      actor_name: 'Apex Diagnostics (LAB001)',
      patient_id: 'PX123456',
      action: 'searched',
      details: 'Layer A identity check lookup on PX123456'
    });
    renderAuditLogs();
  } else {
    resContainer.innerHTML = `<p style="color: var(--rose-primary); font-size: 0.85rem;">Patient ID not found.</p>`;
  }
}

function verifyVisitConsent() {
  const statusEl = document.getElementById('otp-verify-status');
  statusEl.innerText = "✓ Gate 1 Layer B Consent Verified! 24-Hour Upload Window Active for PX123456.";
  statusEl.style.color = "var(--emerald-primary)";
}

function simulateLabUpload(filename) {
  const preview = document.getElementById('upload-processing-preview');
  if (preview) preview.style.display = 'block';
}

function publishReport() {
  alert("Report Published to Patient PX123456 Central Medical Record!");
}

function correctReportVersion() {
  alert("Corrected Version (V2) Created! Preserved Version 1 in immutable history (Rule 6).");
}

// Doctor View: Chart.js Initialization
function initTrendChart() {
  const ctx = document.getElementById('trendChart');
  if (!ctx) return;

  if (trendChartInstance) {
    trendChartInstance.destroy();
  }

  trendChartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels: ['Mar 2026 (Lab A)', 'Jun 2026 (Lab B)', 'Sep 2026 (Lab A V2)'],
      datasets: [
        {
          label: 'Hemoglobin (g/dL)',
          data: [10.0, 11.2, 13.5],
          borderColor: '#06b6d4',
          backgroundColor: 'rgba(6, 182, 212, 0.1)',
          tension: 0.3,
          fill: true
        },
        {
          label: 'Platelets (K/uL / 10)',
          data: [11.6, 14.2, 21.0],
          borderColor: '#8b5cf6',
          backgroundColor: 'rgba(139, 92, 246, 0.1)',
          tension: 0.3,
          fill: true
        },
        {
          label: 'RBC Count (M/uL)',
          data: [3.8, 4.1, 4.7],
          borderColor: '#10b981',
          tension: 0.3
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          labels: { color: '#94a3b8', font: { family: 'Inter', size: 12 } }
        }
      },
      scales: {
        x: { ticks: { color: '#64748b' }, grid: { color: 'rgba(255,255,255,0.05)' } },
        y: { ticks: { color: '#64748b' }, grid: { color: 'rgba(255,255,255,0.05)' } }
      }
    }
  });
}

// AI Pipeline Engine Interactive Runner
function runInteractivePipeline() {
  const jsonBox = document.getElementById('pipeline-json-output');
  const stageInfo = document.getElementById('pipeline-stage-info');

  const steps = [
    { step: 1, title: "1. Document Ingestion", desc: "Digital PDF reader detected embedded text pages." },
    { step: 2, title: "2. Text Cleaning", desc: "Normalized whitespace and removed PDF page markers." },
    { step: 3, title: "3. Patient Parser", desc: "Extracted patient age: 30 years, sex: male context." },
    { step: 4, title: "4. CBC Marker Parser", desc: "Parsed 6 markers: Hemoglobin, RBC, WBC, Platelets, MCV, Hematocrit." },
    { step: 5, title: "5. Validator & Coverage", desc: "Coverage check: 100% supported markers present. Validation: CAN_ANALYZE = True." },
    { step: 6, title: "6. Extraction Plausibility", desc: "Passed numeric sanity range checks." },
    { step: 7, title: "7. Reference Resolution", desc: "Resolved age/sex specific ranges (e.g. Male Adult Hb: 13.0 - 17.0 g/dL)." },
    { step: 8, title: "8. Knowledge Engine Matcher", desc: "Matched Pattern: Microcytic Hypochromic Anemia (Confidence: 88%)." }
  ];

  let current = 0;
  const interval = setInterval(() => {
    if (current < steps.length) {
      const s = steps[current];
      stageInfo.innerHTML = `<h4 style="color: var(--cyan-primary); font-weight:700;">${s.title}</h4><p style="margin-top:0.5rem;">${s.desc}</p>`;

      // Highlight step node
      document.querySelectorAll('.step-node').forEach((node, idx) => {
        if (idx < current) node.className = 'step-node completed';
        else if (idx === current) node.className = 'step-node active';
        else node.className = 'step-node';
      });

      current++;
    } else {
      clearInterval(interval);
      // Fetch live Python backend response if server is active, else show rich JSON output
      fetch('/api/clinical-pipeline/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sample: 'sample.pdf' })
      })
      .then(res => res.json())
      .then(data => {
        jsonBox.innerText = JSON.stringify(data, null, 2);
      })
      .catch(() => {
        // Fallback JSON output
        jsonBox.innerText = JSON.stringify({
          status: "SUCCESS",
          pipeline_version: "V1.1",
          patient: { sex: "male", age_value: 30, age_unit: "years" },
          extracted_markers: [
            { canonical_name: "hemoglobin", value: 10.0, unit: "g/dL", status: "LOW" },
            { canonical_name: "platelets", value: 116, unit: "K/uL", status: "LOW" }
          ],
          matched_patterns: [
            { title: "Microcytic Hypochromic Anemia Pattern", confidence: 0.88, severity: "HIGH" }
          ]
        }, null, 2);
      });
    }
  }, 400);
}
