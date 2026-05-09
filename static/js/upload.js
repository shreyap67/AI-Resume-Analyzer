/* ============================================================
   upload.js – Resume upload + analysis via fetch API.
   Depends on: UPLOAD_URL, ANALYZE_URL, RESULT_BASE, REPORT_BASE
   (injected as <script> vars from resume_analyzer.html)
   ============================================================ */

var currentResumeId = null;

/* ── Stream → Job Role mapping ──────────────────────────────── */
var STREAM_ROLES = {
  "Computer Science": [
    "Python Developer", "Full Stack Developer", "Frontend Developer",
    "Backend Developer", "Database Administrator", "DevOps Engineer",
    "Mobile App Developer", "Cybersecurity Analyst", "Cloud Architect", "QA Engineer"
  ],
  "Civil": [
    "Structural Engineer", "Site Engineer", "Land Surveyor",
    "Construction Manager", "Environmental Engineer", "Geotechnical Engineer",
    "Transportation Engineer", "Urban Planner"
  ],
  "Commerce": [
    "Accountant", "Finance Analyst", "Auditor", "Tax Consultant",
    "Banking Officer", "Investment Analyst", "Financial Controller",
    "Cost Accountant", "Management Consultant"
  ],
  "Mechanical": [
    "Mechanical Design Engineer", "Manufacturing Engineer", "Automotive Engineer",
    "HVAC Engineer", "Quality Control Engineer", "Production Engineer",
    "Maintenance Engineer", "Robotics Engineer"
  ],
  "Electrical": [
    "Power Systems Engineer", "Embedded Systems Engineer", "IoT Engineer",
    "Control Systems Engineer", "Electronics Engineer", "VLSI Design Engineer",
    "Instrumentation Engineer"
  ],
  "Data Science": [
    "Data Analyst", "Data Scientist", "Machine Learning Engineer",
    "Business Intelligence Analyst", "Data Engineer", "AI Research Scientist",
    "NLP Engineer", "Computer Vision Engineer"
  ],
  "Marketing": [
    "Digital Marketing Specialist", "Content Strategist", "SEO Specialist",
    "Brand Manager", "Social Media Manager", "Marketing Analyst",
    "Growth Hacker", "Email Marketing Specialist"
  ],
  "Medicine": [
    "General Physician", "Surgeon", "Clinical Researcher",
    "Pharmacist", "Medical Lab Technician", "Radiologist", "Cardiologist"
  ],
  "Law": [
    "Corporate Lawyer", "Criminal Defense Attorney", "Legal Consultant",
    "Intellectual Property Attorney", "Family Law Attorney", "Paralegal"
  ]
};

/* Called when stream dropdown changes — populates job role dropdown */
function onStreamChange(streamValue) {
  var select = document.getElementById('jobRoleSelect');
  if (!select) return;

  // Reset job role dropdown
  select.innerHTML = '<option value="">— Select a job role —</option>';

  if (!streamValue || !STREAM_ROLES[streamValue]) return;

  STREAM_ROLES[streamValue].forEach(function(title) {
    var opt = document.createElement('option');
    opt.value = title;
    opt.textContent = title;
    select.appendChild(opt);
  });
}

/* DOM refs */
var uploadZone, fileInput, uploadContent, uploadProgress,
    fileLoaded, loadedName, loadedSize, resumeSelect,
    analyzeBtn, jobRoleSelect;

document.addEventListener('DOMContentLoaded', function () {
  uploadZone     = document.getElementById('uploadZone');
  fileInput      = document.getElementById('resumeFile');
  uploadContent  = document.getElementById('uploadContent');
  uploadProgress = document.getElementById('uploadProgress');
  fileLoaded     = document.getElementById('fileLoaded');
  loadedName     = document.getElementById('loadedName');
  loadedSize     = document.getElementById('loadedSize');
  resumeSelect   = document.getElementById('resumeSelect');
  analyzeBtn     = document.getElementById('analyzeBtn');
  jobRoleSelect  = document.getElementById('jobRoleSelect');

  if (!uploadZone) return;

  if (fileInput) {
    fileInput.addEventListener('change', function () {
      if (this.files && this.files[0]) handleFileUpload(this.files[0]);
    });
  }

  /* Click anywhere in zone to trigger file picker */
  uploadZone.addEventListener('click', function (e) {
    if (e.target !== fileInput && fileInput) fileInput.click();
  });

  uploadZone.addEventListener('dragover', function (e) { e.preventDefault(); });
  uploadZone.addEventListener('drop', function (e) {
    e.preventDefault();
    var file = e.dataTransfer.files[0];
    if (file) handleFileUpload(file);
  });

  /* Browse files span */
  var browseTrigger = document.querySelector('.upload-browse');
  if (browseTrigger && fileInput) {
    browseTrigger.addEventListener('click', function (e) {
      e.stopPropagation();
      fileInput.click();
    });
  }
});

/* ── File selection ─────────────────────────────────────────── */
function handleFileUpload(file) {
  if (!file.name.toLowerCase().endsWith('.pdf')) {
    showNotification('❌ Only PDF files are accepted.', 'danger');
    return;
  }
  if (file.size > 10 * 1024 * 1024) {
    showNotification('❌ File too large. Maximum size is 10 MB.', 'danger');
    return;
  }
  showUploadProgress();
  uploadFile(file);
}

/* ── Upload via FormData ─────────────────────────────────────── */
function uploadFile(file) {
  var formData = new FormData();
  formData.append('resume_file', file);

  fetch(UPLOAD_URL, {
    method: 'POST',
    body: formData,
    credentials: 'same-origin'
  })
  .then(function (response) {
    var ct = response.headers.get('content-type') || '';
    if (!ct.includes('application/json')) {
      throw new Error('Server returned non-JSON response (status ' + response.status + '). Are you logged in?');
    }
    return response.json();
  })
  .then(function (data) {
    if (data.success) {
      currentResumeId = data.resume_id;
      showFileLoaded(data.filename, data.file_size);
      /* Add freshly uploaded resume to the saved-resume dropdown */
      if (resumeSelect) {
        var opt = document.createElement('option');
        opt.value = data.resume_id;
        opt.textContent = data.filename;
        resumeSelect.appendChild(opt);
      }
    } else {
      showUploadError(data.error || 'Upload failed. Please try again.');
    }
  })
  .catch(function (err) {
    showUploadError(err.message);
  });
}

/* ── Select existing resume ─────────────────────────────────── */
function selectExisting(resumeId) {
  if (!resumeId) { currentResumeId = null; return; }
  currentResumeId = parseInt(resumeId, 10);
  var selectedText = resumeSelect ? (resumeSelect.options[resumeSelect.selectedIndex] || {}).text || 'Saved resume selected' : 'Saved resume selected';
  if (fileLoaded)     fileLoaded.style.display     = 'flex';
  if (loadedName)     loadedName.textContent        = selectedText;
  if (loadedSize)     loadedSize.textContent        = 'Resume ID: ' + currentResumeId;
  if (uploadContent)  uploadContent.style.display  = 'none';
  if (uploadProgress) uploadProgress.style.display = 'none';
}

/* ── Clear selection ─────────────────────────────────────────── */
function clearUpload() {
  currentResumeId = null;
  if (fileInput)      fileInput.value               = '';
  if (resumeSelect)   resumeSelect.value            = '';
  if (fileLoaded)     fileLoaded.style.display      = 'none';
  if (uploadContent)  uploadContent.style.display   = 'block';
  if (uploadProgress) uploadProgress.style.display  = 'none';
}

/* ── Run analysis ────────────────────────────────────────────── */
function runAnalysis() {
  if (!currentResumeId) {
    showNotification('⚠️ Please upload or select a resume first.', 'warning');
    return;
  }

  var customRoleEl = document.getElementById('customRoleInput');
  var customRole   = customRoleEl ? customRoleEl.value.trim() : '';
  var selectedRole = jobRoleSelect ? jobRoleSelect.value.trim() : '';
  var finalRole    = customRole || selectedRole;

  if (!finalRole) {
    showNotification('⚠️ Please select a stream and job role, or type a custom role.', 'warning');
    return;
  }

  if (analyzeBtn) {
    analyzeBtn.disabled    = true;
    analyzeBtn.textContent = '🤖 Analysing…';
  }

  showResultsLoading();

  var formData = new FormData();
  formData.append('resume_id',   String(currentResumeId));
  formData.append('custom_role', finalRole);   /* send role title; backend resolves it */

  fetch(ANALYZE_URL, {
    method: 'POST',
    body: formData,
    credentials: 'same-origin',
    headers: { 'Accept': 'application/json' }
  })
  .then(function (response) {
    var ct = response.headers.get('content-type') || '';
    if (!ct.includes('application/json')) {
      return response.text().then(function (body) {
        throw new Error(
          'Server returned HTML instead of JSON (HTTP ' + response.status + '). ' +
          'First 200 chars: ' + body.substring(0, 200)
        );
      });
    }
    return response.json();
  })
  .then(function (data) {
    if (data.success) {
      showNotification('✅ Analysis complete! Score: ' + data.ats_score.toFixed(1) + '%', 'success');
      setTimeout(function () {
        window.location.href = RESULT_BASE + data.result_id;
      }, 800);
    } else {
      showAnalysisError(data.error || 'Analysis failed.');
    }
  })
  .catch(function (err) {
    showAnalysisError(err.message);
  })
  .finally(function () {
    if (analyzeBtn) {
      analyzeBtn.disabled    = false;
      analyzeBtn.textContent = '🤖 Analyze Resume';
    }
  });
}

/* ── Inline score rendering ──────────────────────────────────── */
function renderInlineResult(data) {
  var placeholder    = document.getElementById('resultsPlaceholder');
  var resultsContent = document.getElementById('resultsContent');
  if (!resultsContent) return;

  if (placeholder) placeholder.style.display = 'none';
  resultsContent.style.display = 'block';

  var arc = document.getElementById('scoreArc');
  if (arc) animateScoreArc(arc, data.ats_score);

  var scoreEl = document.getElementById('scoreValue');
  if (scoreEl) animateNumber(scoreEl, data.ats_score, '%');

  var descEl = document.getElementById('scoreDescription');
  if (descEl) descEl.textContent = scoreLabel(data.ats_score) + ' match for this role';

  renderSkillTags('matchedTags', data.matched_skills, 'tag-green');
  renderSkillTags('missingTags', data.missing_skills, 'tag-red');
  setTextContent('matchedCount', (data.matched_skills || []).length + ' found');
  setTextContent('missingCount', (data.missing_skills || []).length + ' gaps');
  renderSuggestions(data.suggestions);

  var downloadBtn = document.getElementById('downloadReportBtn');
  var viewBtn     = document.getElementById('viewFullResultBtn');
  if (downloadBtn) downloadBtn.href = REPORT_BASE + data.result_id;
  if (viewBtn)     viewBtn.href     = RESULT_BASE + data.result_id;

  resultsContent.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

/* ── Skill tags ─────────────────────────────────────────────── */
function renderSkillTags(containerId, skills, cssClass) {
  var container = document.getElementById(containerId);
  if (!container) return;
  container.innerHTML = '';
  if (!skills || skills.length === 0) {
    container.innerHTML = '<span class="text-muted" style="font-size:12px">None</span>';
    return;
  }
  skills.forEach(function (skill, idx) {
    var tag = document.createElement('span');
    tag.className = 'tag ' + cssClass + ' tag-animate';
    tag.textContent = skill;
    tag.style.animationDelay = (idx * 0.04) + 's';
    container.appendChild(tag);
  });
}

/* ── Suggestions ────────────────────────────────────────────── */
function renderSuggestions(suggestions) {
  var container = document.getElementById('suggestionsList');
  if (!container) return;
  container.innerHTML = '';
  var icons = ['💡', '🎓', '📈', '🔑', '🚀'];
  (suggestions || []).forEach(function (text, idx) {
    var item = document.createElement('div');
    item.className = 'suggestion-item animate-fadein';
    item.style.animationDelay = (idx * 0.08) + 's';
    item.innerHTML =
      '<span class="suggestion-icon">' + icons[idx % icons.length] + '</span>' +
      '<p>' + escapeHtml(text) + '</p>';
    container.appendChild(item);
  });
}

/* ── Loading / error states ─────────────────────────────────── */
function showUploadProgress() {
  if (uploadContent)  uploadContent.style.display  = 'none';
  if (uploadProgress) uploadProgress.style.display = 'flex';
  if (fileLoaded)     fileLoaded.style.display     = 'none';
}
function showFileLoaded(filename, size) {
  if (uploadContent)  uploadContent.style.display  = 'none';
  if (uploadProgress) uploadProgress.style.display = 'none';
  if (fileLoaded)     fileLoaded.style.display     = 'flex';
  if (loadedName)     loadedName.textContent       = filename;
  if (loadedSize)     loadedSize.textContent       = size;
}
function showUploadError(msg) {
  if (uploadProgress) uploadProgress.style.display = 'none';
  if (uploadContent)  uploadContent.style.display  = 'block';
  showNotification('❌ ' + msg, 'danger');
}
function showResultsLoading() {
  var placeholder = document.getElementById('resultsPlaceholder');
  if (placeholder) {
    placeholder.innerHTML =
      '<div class="dot-loader" style="margin-bottom:16px">' +
        '<span></span><span></span><span></span>' +
      '</div>' +
      '<p style="color:var(--muted);font-size:13px">AI is analysing your resume…</p>';
  }
}
function showAnalysisError(msg) {
  var placeholder = document.getElementById('resultsPlaceholder');
  if (placeholder) {
    placeholder.innerHTML =
      '<div class="empty-icon" style="font-size:44px;opacity:.7">❌</div>' +
      '<h3 style="color:var(--nred,#FC8181);font-size:18px;font-weight:700">Analysis Failed</h3>' +
      '<p class="text-muted" style="font-size:13px;max-width:380px;line-height:1.6">' + escapeHtml(msg) + '</p>';
  }
  showNotification('❌ ' + msg, 'danger');
}

/* ── Notification toast ─────────────────────────────────────── */
function showNotification(msg, type) {
  type = type || 'info';
  var container = document.getElementById('flash-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'flash-container';
    container.style.cssText =
      'position:fixed;top:16px;right:16px;z-index:9999;' +
      'display:flex;flex-direction:column;gap:8px;';
    document.body.appendChild(container);
  }
  var flash = document.createElement('div');
  flash.className = 'flash flash-' + type;
  flash.innerHTML =
    '<span>' + msg + '</span>' +
    '<button class="flash-close" onclick="this.parentElement.remove()">×</button>';
  container.appendChild(flash);
  setTimeout(function () {
    flash.style.opacity    = '0';
    flash.style.transform  = 'translateX(100%)';
    flash.style.transition = 'all 0.3s ease';
    setTimeout(function () { if (flash.parentNode) flash.remove(); }, 320);
  }, 4000);
}

/* ── Number counter ─────────────────────────────────────────── */
function animateNumber(el, target, suffix) {
  suffix = suffix || '';
  var duration = 1000, start = performance.now();
  function step(now) {
    var p = Math.min((now - start) / duration, 1);
    var e = 1 - Math.pow(1 - p, 3);
    el.textContent = Math.round(target * e) + suffix;
    if (p < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}
function scoreLabel(score) {
  if (score >= 90) return 'Excellent';
  if (score >= 75) return 'Good';
  if (score >= 60) return 'Average';
  return 'Needs Work';
}
function setTextContent(id, text) {
  var el = document.getElementById(id); if (el) el.textContent = text;
}
function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}
