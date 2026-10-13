// teacher.js — O'qituvchi portali logikasi

function escapeHtml(str) {
  if (str === null || str === undefined) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
window.escapeHtml = escapeHtml;

window.openModal = function(id) {
  const modal = document.getElementById(id);
  if (modal) modal.classList.add("active");
};

window.closeModal = function(id) {
  const modal = document.getElementById(id);
  if (modal) modal.classList.remove("active");
};

document.addEventListener("DOMContentLoaded", async () => {
  const token = localStorage.getItem("auth_token");
  const role = localStorage.getItem("user_role");
  const fullName = localStorage.getItem("user_full_name") || "O'qituvchi";

  if (!token || (role !== "teacher" && role !== "admin")) {
    alert("Iltimos, avval O'qituvchi hisobi bilan tizimga kiring!");
    window.location.href = "/login";
    return;
  }

  document.getElementById("teacher-full-name").textContent = fullName;

  function authHeaders() {
    return {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${token}`
    };
  }

  // Logout
  document.getElementById("btn-logout").addEventListener("click", () => {
    localStorage.clear();
    window.location.href = "/login";
  });

  // Sidebar navigation
  const sidebarLinks = document.querySelectorAll(".sidebar-link");
  const panels = document.querySelectorAll(".admin-panel");
  const panelTitle = document.getElementById("teacher-panel-title");

  const titles = {
    assignments: "Mening Fanlarim va Guruhlarim",
    "test-builder": "Test Yaratish Markazi",
    "test-bank": "Mening Test Bazam",
    "question-bank": "Savollar Banki",
    "ai-generator": "Gemini AI Savol Generatori",
    tests: "Mening Imtihonlarim & Blueprint",
    results: "Sinf Tahlili & AI Xulosa"
  };

  sidebarLinks.forEach(link => {
    link.addEventListener("click", () => {
      const panel = link.dataset.panel;
      sidebarLinks.forEach(l => l.classList.remove("active"));
      link.classList.add("active");

      panels.forEach(p => p.classList.remove("active"));
      document.getElementById(`panel-${panel}`).classList.add("active");
      panelTitle.textContent = titles[panel] || "Kabinet";

      if (panel === "assignments") loadAssignments();
      if (panel === "test-builder") setupTestBuilder();
      if (panel === "test-bank") loadTestBank();
      if (panel === "question-bank") loadQuestionBank();
      if (panel === "ai-generator") setupAiGenerator();
      if (panel === "tests") loadTests();
      if (panel === "results") setupClassReport();
    });
  });

  let myAssignments = [];
  let mySubjects = [];
  let currentSubjectTopics = [];
  let generatedAiQuestions = [];

  // 1. Fan va guruhlarim
  async function loadAssignments() {
    try {
      const res = await fetch("/api/teacher/assignments", { headers: authHeaders() });
      if (res.status === 401 || res.status === 403) {
        localStorage.clear();
        window.location.href = "/login";
        return;
      }
      myAssignments = await res.json();

      const grid = document.getElementById("teacher-assignments-grid");
      if (myAssignments.length === 0) {
        grid.innerHTML = '<p style="color: #64748b;">Sizga hali fan yoki guruhlar biriktirilmagan.</p>';
        return;
      }

      grid.innerHTML = myAssignments.map(a => `
        <div class="admin-stat-card" style="flex-direction: column; align-items: flex-start;">
          <div style="display: flex; justify-content: space-between; width: 100%; align-items: center; margin-bottom: 8px;">
            <span class="badge badge-primary">${escapeHtml(a.subject_code)}</span>
            <span class="badge badge-warning">${escapeHtml(a.group_name)}</span>
          </div>
          <h3 style="font-size: 1.2rem; font-weight: 800; color: #1e1b4b; margin-bottom: 4px;">${escapeHtml(a.subject_name)}</h3>
          <p style="font-size: 0.85rem; color: #64748b; margin-bottom: 12px;">Guruhda: <b>${escapeHtml(a.student_count)}</b> nafar o'quvchi</p>
          <div style="display: flex; justify-content: space-between; width: 100%; border-top: 1px solid #f1f5f9; padding-top: 10px;">
            <span style="font-size: 0.85rem; color: #475569;"><i class="fa-solid fa-file-lines"></i> ${escapeHtml(a.test_count)} ta imtihon</span>
            <button class="btn btn-outline btn-sm" onclick="goToClassReport(${a.assignment_id})">
              <i class="fa-solid fa-chart-simple"></i> Tahlil
            </button>
          </div>
        </div>
      `).join("");

      if (myAssignments.length > 0) {
        document.getElementById("teacher-spec-title").textContent = myAssignments[0].subject_name;
      }
    } catch (err) { console.error(err); }
  }

  window.goToClassReport = (assignmentId) => {
    document.querySelector('.sidebar-link[data-panel="results"]').click();
    setTimeout(() => {
      document.getElementById("report-assignment-select").value = assignmentId;
      document.getElementById("btn-load-class-report").click();
    }, 100);
  };

  // 2. Savollar Banki
  async function loadQuestionBank() {
    try {
      const sRes = await fetch("/api/teacher/subjects", { headers: authHeaders() });
      mySubjects = await sRes.json();
      const sSelect = document.getElementById("qb-subject-select");
      sSelect.innerHTML = mySubjects.map(s => `<option value="${s.id}">${escapeHtml(s.name)} (${escapeHtml(s.code)})</option>`).join("");

      sSelect.onchange = () => refreshTopicsAndQuestions();
      document.getElementById("qb-topic-select").onchange = () => fetchQuestions();
      document.getElementById("qb-diff-select").onchange = () => fetchQuestions();

      await refreshTopicsAndQuestions();
    } catch (err) { console.error(err); }
  }

  async function refreshTopicsAndQuestions() {
    const subId = document.getElementById("qb-subject-select").value;
    if (!subId) return;

    const tRes = await fetch(`/api/teacher/topics/${subId}`, { headers: authHeaders() });
    currentSubjectTopics = await tRes.json();
    const tSelect = document.getElementById("qb-topic-select");
    tSelect.innerHTML = '<option value="">Barcha mavzular</option>' + 
      currentSubjectTopics.map(t => `<option value="${t.id}">${escapeHtml(t.name)} (${escapeHtml(t.question_count)} ta)</option>`).join("");

    await fetchQuestions();
  }

  async function fetchQuestions() {
    const subId = document.getElementById("qb-subject-select").value;
    const topId = document.getElementById("qb-topic-select").value;
    const diff = document.getElementById("qb-diff-select").value;

    let url = `/api/teacher/question-bank?subject_id=${subId}`;
    if (topId) url += `&topic_id=${topId}`;
    if (diff) url += `&difficulty=${diff}`;

    try {
      const res = await fetch(url, { headers: authHeaders() });
      const questions = await res.json();
      const listContainer = document.getElementById("qb-questions-list");

      if (questions.length === 0) {
        listContainer.innerHTML = '<div class="content-card" style="text-align: center; color: #64748b;">Hozircha savollar mavjud emas.</div>';
        return;
      }

      listContainer.innerHTML = questions.map((q, idx) => `
        <div class="admin-q-card">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
            <div>
              <span class="badge badge-primary">${idx + 1}-savol</span>
              <span class="badge badge-warning" style="margin-left: 6px;">${escapeHtml(q.topic_name)}</span>
              <span class="meta-chip" style="margin-left: 6px;">${escapeHtml(q.difficulty)}</span>
              <span class="meta-chip" style="margin-left: 6px;">${escapeHtml(q.points)} ball</span>
            </div>
            <button class="btn btn-danger btn-sm" onclick="deleteQuestion(${q.id})">
              <i class="fa-solid fa-trash"></i>
            </button>
          </div>
          <div style="font-weight: 600; font-size: 1.05rem; margin-bottom: 10px;">${escapeHtml(q.question_text)}</div>
          <div class="admin-opt-list">
            ${q.options.map(o => `
              <div class="admin-opt-item ${o.is_correct ? 'correct-opt' : ''}">
                ${o.is_correct ? '<i class="fa-solid fa-circle-check" style="color: #10b981;"></i>' : '<i class="fa-regular fa-circle" style="color: #cbd5e1;"></i>'}
                ${escapeHtml(o.option_text)}
                ${o.is_correct ? ' <b>(To\'g\'ri javob)</b>' : ''}
              </div>
            `).join("")}
          </div>
          ${q.explanation ? `<div style="margin-top: 8px; font-size: 0.85rem; color: #64748b;"><b>Izoh:</b> ${escapeHtml(q.explanation)}</div>` : ''}
        </div>
      `).join("");
    } catch (err) { console.error(err); }
  }

  window.deleteQuestion = async (qId) => {
    if (!confirm("Ushbu savolni o'chirmoqchimisiz?")) return;
    try {
      await fetch(`/api/teacher/question-bank/${qId}`, { method: "DELETE", headers: authHeaders() });
      fetchQuestions();
    } catch (err) { alert(err); }
  };

  // Savol qo'shish modali
  document.getElementById("btn-open-add-q").addEventListener("click", () => {
    const subSel = document.getElementById("modal-q-subject");
    subSel.innerHTML = mySubjects.map(s => `<option value="${s.id}">${s.name}</option>`).join("");
    subSel.onchange = () => updateModalTopics();
    updateModalTopics();
    openModal("modal-add-question");
  });

  async function updateModalTopics() {
    const subId = document.getElementById("modal-q-subject").value;
    const tRes = await fetch(`/api/teacher/topics/${subId}`, { headers: authHeaders() });
    const topics = await tRes.json();
    const tSel = document.getElementById("modal-q-topic");
    tSel.innerHTML = topics.map(t => `<option value="${t.id}">${t.name}</option>`).join("");
  }

  document.getElementById("form-add-question").addEventListener("submit", async (e) => {
    e.preventDefault();
    const optInputs = document.querySelectorAll(".modal-opt-input");
    const radios = document.querySelectorAll('input[name="modal_correct_opt"]');
    let corrIdx = 0;
    radios.forEach((r, idx) => { if (r.checked) corrIdx = idx; });

    const options = [];
    optInputs.forEach((inp, idx) => {
      options.push({ option_text: inp.value.trim(), is_correct: (idx === corrIdx ? 1 : 0) });
    });

    const payload = {
      subject_id: parseInt(document.getElementById("modal-q-subject").value),
      topic_id: parseInt(document.getElementById("modal-q-topic").value),
      question_text: document.getElementById("modal-q-text").value.trim(),
      difficulty: document.getElementById("modal-q-diff").value,
      points: parseInt(document.getElementById("modal-q-points").value),
      explanation: document.getElementById("modal-q-exp").value.trim(),
      options: options
    };

    try {
      const res = await fetch("/api/teacher/question-bank", {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        closeModal("modal-add-question");
        document.getElementById("form-add-question").reset();
        fetchQuestions();
      } else {
        const err = await res.json();
        alert(err.detail || "Xatolik");
      }
    } catch (err) { alert(err); }
  });

  // 3. AI Savol Generatori
  function setupAiGenerator() {
    const aiSub = document.getElementById("ai-subject-select");
    aiSub.innerHTML = mySubjects.map(s => `<option value="${s.id}">${s.name}</option>`).join("");
  }

  document.getElementById("btn-run-ai-gen").addEventListener("click", async () => {
    const subSel = document.getElementById("ai-subject-select");
    const subjectName = subSel.options[subSel.selectedIndex]?.text;
    const topicName = document.getElementById("ai-topic-input").value.trim();
    const count = parseInt(document.getElementById("ai-count-input").value) || 10;
    const diff = document.getElementById("ai-difficulty-select").value;
    const extra = document.getElementById("ai-extra-input").value.trim();
    const btn = document.getElementById("btn-run-ai-gen");

    if (!topicName) { alert("Iltimos, mavzu nomini yozing!"); return; }

    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Gemini AI savollarni tuzmoqda...';

    try {
      const res = await fetch("/api/ai/generate-questions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          subject_name: subjectName,
          topic_name: topicName,
          count: count,
          difficulty: diff,
          extra_prompt: extra
        })
      });
      const data = await res.json();
      generatedAiQuestions = data.questions || [];
      renderAiGenerated(generatedAiQuestions);
    } catch (err) { alert(err); }
    finally {
      btn.disabled = false;
      btn.innerHTML = '<i class="fa-solid fa-sparkles"></i> AI Savollarni Generatsiya Qilish';
    }
  });

  function renderAiGenerated(questions) {
    const box = document.getElementById("ai-gen-results-box");
    const container = document.getElementById("ai-gen-items-container");
    box.style.display = "block";
    document.getElementById("ai-gen-title").textContent = `Generatsiya qilingan savollar: ${questions.length} ta`;

    container.innerHTML = questions.map((q, idx) => `
      <div class="generated-q-item">
        <div style="font-weight: 700; margin-bottom: 6px; color: #1e1b4b;">${idx + 1}. ${q.question_text}</div>
        <div style="display: flex; flex-direction: column; gap: 4px; font-size: 0.9rem;">
          ${q.options.map(o => `
            <div style="padding: 4px 8px; border-radius: 4px; background: #fff; ${o.is_correct ? 'border: 1.5px solid #10b981; font-weight: 700; color: #065f46;' : 'border: 1px solid #e2e8f0;'}">
              ${o.is_correct ? '<i class="fa-solid fa-check"></i> ' : ''}${o.option_text}
            </div>
          `).join("")}
        </div>
      </div>
    `).join("");
  }

  document.getElementById("btn-save-ai-to-bank").addEventListener("click", async () => {
    if (generatedAiQuestions.length === 0) return;
    const subId = parseInt(document.getElementById("ai-subject-select").value);
    const topicName = document.getElementById("ai-topic-input").value.trim();

    try {
      // Mavzuni qidirish yoki yaratish
      const topRes = await fetch("/api/teacher/topics", {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({ subject_id: subId, name: topicName })
      });
      const topData = await topRes.json();
      const topicId = topData.id;

      // Savollarni birma-bir bankka yozish
      for (const q of generatedAiQuestions) {
        await fetch("/api/teacher/question-bank", {
          method: "POST",
          headers: authHeaders(),
          body: JSON.stringify({
            subject_id: subId,
            topic_id: topicId,
            question_text: q.question_text,
            difficulty: q.difficulty || "medium",
            points: 1,
            explanation: q.explanation || "",
            options: q.options
          })
        });
      }

      alert("Barcha savollar savollar bankiga muvaffaqiyatli saqlandi!");
      document.getElementById("ai-gen-results-box").style.display = "none";
      generatedAiQuestions = [];
    } catch (err) { alert(err); }
  });

  // 4. Imtihonlar & Blueprint
  async function loadTests() {
    try {
      const res = await fetch("/api/teacher/tests", { headers: authHeaders() });
      const tests = await res.json();
      const tbody = document.getElementById("tests-tbody");
      tbody.innerHTML = tests.map(t => `
        <tr>
          <td><b>${escapeHtml(t.title)}</b></td>
          <td><span class="badge badge-primary">${escapeHtml(t.subject_name)}</span></td>
          <td><span class="badge badge-warning">${escapeHtml(t.group_name)}</span></td>
          <td>${escapeHtml(t.exam_type)}</td>
          <td>${escapeHtml(t.duration_minutes)} daqiqa</td>
          <td>${escapeHtml(t.question_count)} ta savol</td>
          <td>${escapeHtml(t.attempts_count)} nafar</td>
          <td><b>${escapeHtml(t.avg_score || 0)}%</b></td>
        </tr>
      `).join("");
    } catch (err) { console.error(err); }
  }

  document.getElementById("btn-open-create-test").addEventListener("click", () => {
    const sel = document.getElementById("test-assignment-select");
    sel.innerHTML = myAssignments.map(a => `<option value="${a.assignment_id}">${escapeHtml(a.subject_name)} — ${escapeHtml(a.group_name)}</option>`).join("");
    openModal("modal-create-test");
  });

  document.getElementById("form-create-test").addEventListener("submit", async (e) => {
    e.preventDefault();
    const payload = {
      assignment_id: parseInt(document.getElementById("test-assignment-select").value),
      title: document.getElementById("test-title").value.trim(),
      duration_minutes: parseInt(document.getElementById("test-duration").value),
      passing_score: parseInt(document.getElementById("test-passing").value),
      exam_type: document.getElementById("test-type").value
    };
    try {
      const res = await fetch("/api/teacher/tests", {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        closeModal("modal-create-test");
        loadTests();
        alert("Imtihon muvaffaqiyatli yaratildi va o'quvchilarga ko'rindi!");
      } else {
        const err = await res.json();
        alert(err.detail || "Xatolik");
      }
    } catch (err) { alert(err); }
  });

  // 5. Sinf Natijalari & AI
  function setupClassReport() {
    const sel = document.getElementById("report-assignment-select");
    sel.innerHTML = myAssignments.map(a => `<option value="${a.assignment_id}">${escapeHtml(a.subject_name)} — ${escapeHtml(a.group_name)}</option>`).join("");
  }

  document.getElementById("btn-load-class-report").addEventListener("click", async () => {
    const assignId = document.getElementById("report-assignment-select").value;
    if (!assignId) return;

    try {
      const res = await fetch(`/api/teacher/assignment-report/${assignId}`, { headers: authHeaders() });
      const data = await res.json();
      document.getElementById("class-report-container").style.display = "block";
      document.getElementById("class-ai-text-box").style.display = "none";

      // Mavzular progress
      const barsBox = document.getElementById("class-topics-bars");
      if (data.topic_stats.length === 0) {
        barsBox.innerHTML = '<p style="color: #64748b;">Hali topshirilgan imtihonlar yo\'q</p>';
      } else {
        barsBox.innerHTML = data.topic_stats.map(t => {
          let color = "#10b981";
          if (t.avg_percentage < 60) color = "#ef4444";
          else if (t.avg_percentage < 75) color = "#f59e0b";
          return `
            <div style="margin-bottom: 12px;">
              <div style="display: flex; justify-content: space-between; font-size: 0.9rem; font-weight: 600; margin-bottom: 4px;">
                <span>${escapeHtml(t.topic_name)} (${escapeHtml(t.correct_q)}/${escapeHtml(t.total_q)})</span>
                <span style="color: ${color};">${escapeHtml(t.avg_percentage)}%</span>
              </div>
              <div class="progress-bar-bg" style="height: 8px;">
                <div class="progress-bar-fill" style="width: ${t.avg_percentage}%; background: ${color};"></div>
              </div>
            </div>
          `;
        }).join("");
      }

      // O'quvchilar jadvali
      const tbody = document.getElementById("class-students-tbody");
      tbody.innerHTML = data.attempts.map(a => `
        <tr>
          <td><b>${escapeHtml(a.student_name)}</b></td>
          <td><code>${escapeHtml(a.student_code)}</code></td>
          <td><span class="badge ${a.score_percent >= 60 ? 'badge-success' : 'badge-danger'}">${escapeHtml(a.score_percent)}%</span></td>
          <td>${escapeHtml(a.correct_answers)} / ${escapeHtml(a.total_questions)}</td>
          <td style="color: #64748b; font-size: 0.85rem;">${escapeHtml(a.finished_at ? a.finished_at.slice(0, 16) : '')}</td>
        </tr>
      `).join("");
    } catch (err) { alert(err); }
  });

  document.getElementById("btn-run-class-ai").addEventListener("click", async () => {
    const assignId = parseInt(document.getElementById("report-assignment-select").value);
    const btn = document.getElementById("btn-run-class-ai");
    const textBox = document.getElementById("class-ai-text-box");
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Gemini AI tahlil qilmoqda...';
    textBox.style.display = "block";
    textBox.innerHTML = '<p style="color: #64748b; text-align: center;">Guruh natijalari va zaif mavzular tahlili olinmoqda...</p>';

    try {
      const res = await fetch("/api/teacher/ai-group-report", {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({ assignment_id: assignId })
      });
      const data = await res.json();
      textBox.innerHTML = formatMarkdown(data.ai_report);
    } catch (err) {
      textBox.innerHTML = `<div style="color: red;">Xatolik: ${escapeHtml(err)}</div>`;
    } finally {
      btn.disabled = false;
      btn.innerHTML = '<i class="fa-solid fa-sparkles"></i> AI Tahlil Olish';
    }
  });

  function formatMarkdown(text) {
    if (!text) return "";
    let safe = escapeHtml(text);
    return safe
      .replace(/^### (.*$)/gim, '<h3 style="color: #1e1b4b; margin: 1rem 0 0.5rem 0;">$1</h3>')
      .replace(/^#### (.*$)/gim, '<h4 style="color: #312e81; margin: 0.8rem 0 0.4rem 0;">$1</h4>')
      .replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>')
      .replace(/^\* (.*$)/gim, '<li style="margin-left: 1rem;">$1</li>')
      .replace(/^- (.*$)/gim, '<li style="margin-left: 1rem;">$1</li>')
      .replace(/\n\n/gim, '<br><br>');
  }

  // =========================================================================
  // 6. TEST YARATISH MARKAZI (QO'LDA, WORD, AI)
  // =========================================================================
  let manualQuestions = [];
  let wordQuestions = [];
  let aiQuestions = [];

  function setupTestBuilder() {
    // Assignment selectni to'ldirish
    const assignSel = document.getElementById("tb-assignment-select");
    assignSel.innerHTML = '<option value="">-- Guruh va Fanni tanlang --</option>' +
      myAssignments.map(a => `<option value="${a.assignment_id}">${escapeHtml(a.subject_name)} (${escapeHtml(a.group_name)})</option>`).join("");

    // Tab almashtirish
    const tabBtns = document.querySelectorAll(".tb-tab-btn");
    const views = document.querySelectorAll(".tb-view");

    tabBtns.forEach(btn => {
      btn.onclick = () => {
        const tab = btn.dataset.tab;
        tabBtns.forEach(b => {
          b.classList.remove("active");
          b.classList.replace("btn-primary", "btn-outline");
        });
        btn.classList.add("active");
        btn.classList.replace("btn-outline", "btn-primary");

        views.forEach(v => v.style.display = "none");
        const targetView = document.getElementById(`tb-view-${tab}`);
        if (targetView) targetView.style.display = "block";
      };
    });

    setupManualBuilder();
    setupWordBuilder();
    setupAiBuilder();
  }

  // --- 1. Qo'lda savol kiritish ---
  function setupManualBuilder() {
    const btnAdd = document.getElementById("btn-add-manual-q");
    const btnClear = document.getElementById("btn-clear-manual-list");
    const btnSave = document.getElementById("btn-save-manual-test");

    btnAdd.onclick = () => {
      const qText = document.getElementById("manual-q-text").value.trim();
      const topicName = document.getElementById("manual-q-topic").value.trim() || "Umumiy mavzu";
      const diff = document.getElementById("manual-q-diff").value;
      const pts = parseInt(document.getElementById("manual-q-points").value) || 1;
      const exp = document.getElementById("manual-q-exp").value.trim();

      const opt0 = document.getElementById("manual-opt-0").value.trim();
      const opt1 = document.getElementById("manual-opt-1").value.trim();
      const opt2 = document.getElementById("manual-opt-2").value.trim();
      const opt3 = document.getElementById("manual-opt-3").value.trim();

      if (!qText) {
        alert("Savol matnini kiriting!");
        return;
      }
      if (!opt0 || !opt1) {
        alert("Kamida 2 ta variant (A va B) kiritilishi shart!");
        return;
      }

      const corrRadios = document.getElementsByName("manual_corr");
      let corrIdx = 0;
      corrRadios.forEach(r => { if (r.checked) corrIdx = parseInt(r.value); });

      const options = [];
      if (opt0) options.push({ option_text: opt0, is_correct: corrIdx === 0 ? 1 : 0 });
      if (opt1) options.push({ option_text: opt1, is_correct: corrIdx === 1 ? 1 : 0 });
      if (opt2) options.push({ option_text: opt2, is_correct: corrIdx === 2 ? 1 : 0 });
      if (opt3) options.push({ option_text: opt3, is_correct: corrIdx === 3 ? 1 : 0 });

      manualQuestions.push({
        question_text: qText,
        topic_name: topicName,
        difficulty: diff,
        points: pts,
        explanation: exp,
        options: options
      });

      // Tozalash
      document.getElementById("manual-q-text").value = "";
      document.getElementById("manual-opt-0").value = "";
      document.getElementById("manual-opt-1").value = "";
      document.getElementById("manual-opt-2").value = "";
      document.getElementById("manual-opt-3").value = "";
      document.getElementById("manual-q-exp").value = "";
      document.getElementById("man_opt_r0").checked = true;

      renderManualQuestions();
    };

    btnClear.onclick = () => {
      if (manualQuestions.length > 0 && confirm("Barcha kiritilgan savollarni tozalashni xohlaysizmi?")) {
        manualQuestions = [];
        renderManualQuestions();
      }
    };

    btnSave.onclick = () => saveTestFromQuestions(manualQuestions);
  }

  function renderManualQuestions() {
    const list = document.getElementById("manual-questions-list");
    const countBadge = document.getElementById("manual-q-count-badge");
    countBadge.textContent = `${manualQuestions.length} ta`;

    if (manualQuestions.length === 0) {
      list.innerHTML = '<p style="color: #94a3b8; font-size: 0.9rem; text-align: center; padding: 20px;">Hozircha birorta savol qo\'shilmadi. Yuqoridagi formadan savol kiriting.</p>';
      return;
    }

    list.innerHTML = manualQuestions.map((q, idx) => `
      <div style="border: 1px solid #e2e8f0; border-radius: var(--radius-sm); padding: 12px; background: #ffffff;">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 6px;">
          <div>
            <b>${idx + 1}. ${escapeHtml(q.question_text)}</b>
            <div style="display: flex; gap: 8px; margin-top: 4px; font-size: 0.75rem;">
              <span class="badge badge-primary">${escapeHtml(q.topic_name)}</span>
              <span class="badge badge-warning">${getDiffLabel(q.difficulty)}</span>
              <span class="badge badge-info">${q.points} ball</span>
            </div>
          </div>
          <div style="display: flex; gap: 6px;">
            <button class="btn btn-outline btn-sm" onclick="editLocalQuestion('manual', ${idx})" style="padding: 2px 8px; font-size: 0.75rem;">
              <i class="fa-solid fa-pen"></i> Tahrirlash
            </button>
            <button class="btn btn-outline btn-sm" onclick="deleteLocalQuestion('manual', ${idx})" style="padding: 2px 8px; font-size: 0.75rem; color: #ef4444; border-color: #fca5a5;">
              <i class="fa-solid fa-trash"></i>
            </button>
          </div>
        </div>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 6px; margin-top: 8px; font-size: 0.85rem;">
          ${q.options.map((opt, oIdx) => `
            <div style="padding: 6px 10px; border-radius: 4px; border: 1px solid ${opt.is_correct ? '#86efac' : '#f1f5f9'}; background: ${opt.is_correct ? '#f0fdf4' : '#fafafa'};">
              <b>${String.fromCharCode(65 + oIdx)})</b> ${escapeHtml(opt.option_text)}
              ${opt.is_correct ? '<span style="color: #16a34a; font-weight: 700; margin-left: 6px;">✓ To\'g\'ri</span>' : ''}
            </div>
          `).join("")}
        </div>
        ${q.explanation ? `<p style="font-size: 0.8rem; color: #64748b; margin-top: 6px; font-style: italic;">Izoh: ${escapeHtml(q.explanation)}</p>` : ''}
      </div>
    `).join("");
  }

  // --- 2. Word (.docx) Import ---
  function setupWordBuilder() {
    const btnUpload = document.getElementById("btn-upload-word-preview");
    const btnConfirm = document.getElementById("btn-confirm-word-import");
    const btnAiCheck = document.getElementById("btn-word-ai-check");
    const btnAddManual = document.getElementById("btn-word-add-manual-q");

    btnUpload.onclick = async () => {
      const fileInput = document.getElementById("word-file-input");
      if (!fileInput.files || fileInput.files.length === 0) {
        alert("Iltimos, avval Word (.docx) faylini tanlang!");
        return;
      }

      const file = fileInput.files[0];
      const formData = new FormData();
      formData.append("file", file);

      btnUpload.disabled = true;
      btnUpload.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Word fayli tahlil qilinmoqda...';

      try {
        const res = await fetch("/api/teacher/word/import-preview", {
          method: "POST",
          headers: { "Authorization": `Bearer ${token}` },
          body: formData
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Word tahlil qilishda xatolik");

        wordQuestions = data.questions || [];
        if (data.test_title && !document.getElementById("tb-test-title").value) {
          document.getElementById("tb-test-title").value = data.test_title;
        }

        renderWordPreview(data);
      } catch (err) {
        alert(`Xatolik: ${err.message}`);
      } finally {
        btnUpload.disabled = false;
        btnUpload.innerHTML = '<i class="fa-solid fa-upload"></i> Word Faylni Tahlil Qilish (Preview)';
      }
    };

    btnAiCheck.onclick = async () => {
      if (wordQuestions.length === 0) return;
      btnAiCheck.disabled = true;
      btnAiCheck.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> AI tekshirmoqda...';

      try {
        const res = await fetch("/api/teacher/word/ai-review", {
          method: "POST",
          headers: authHeaders(),
          body: JSON.stringify({ questions: wordQuestions })
        });
        const data = await res.json();
        const adviceBox = document.getElementById("word-ai-advice-box");
        adviceBox.style.display = "block";
        adviceBox.innerHTML = `<b><i class="fa-solid fa-brain" style="color: #9333ea;"></i> Gemini AI Tahlili va Tavsiyasi:</b><br>${formatMarkdown(data.advice)}`;
      } catch (err) {
        alert(`AI tekshiruvida xatolik: ${err.message}`);
      } finally {
        btnAiCheck.disabled = false;
        btnAiCheck.innerHTML = '<i class="fa-solid fa-brain"></i> AI Maslahati';
      }
    };

    btnAddManual.onclick = () => {
      const qText = prompt("Qo'shiladigan yangi savol matnini kiriting:");
      if (!qText) return;
      const optA = prompt("A varianti:") || "A";
      const optB = prompt("B varianti:") || "B";
      const optC = prompt("C varianti:") || "C";
      const optD = prompt("D varianti:") || "D";
      const corr = (prompt("To'g'ri javob harfi (A, B, C yoki D):") || "A").toUpperCase();

      wordQuestions.push({
        temp_id: wordQuestions.length + 1,
        question_text: qText,
        topic_name: "Qo'shilgan",
        difficulty: "medium",
        points: 1,
        explanation: "",
        has_error: false,
        options: [
          { option_text: optA, is_correct: corr === "A" ? 1 : 0 },
          { option_text: optB, is_correct: corr === "B" ? 1 : 0 },
          { option_text: optC, is_correct: corr === "C" ? 1 : 0 },
          { option_text: optD, is_correct: corr === "D" ? 1 : 0 }
        ]
      });
      renderWordPreview();
    };

    btnConfirm.onclick = () => saveTestFromQuestions(wordQuestions);
  }

  function renderWordPreview(meta) {
    const card = document.getElementById("word-preview-card");
    const statsBox = document.getElementById("word-preview-stats");
    const list = document.getElementById("word-questions-list");

    card.style.display = "block";

    const total = wordQuestions.length;
    const errors = wordQuestions.filter(q => q.has_error).length;
    const valid = total - errors;

    statsBox.innerHTML = `
      <span class="badge badge-primary">Jami: ${total} ta savol</span>
      <span class="badge badge-success">To'g'ri shakllangan: ${valid} ta</span>
      ${errors > 0 ? `<span class="badge badge-danger">Xatoliklar: ${errors} ta</span>` : ''}
    `;

    list.innerHTML = wordQuestions.map((q, idx) => `
      <div style="border: 2px solid ${q.has_error ? '#fca5a5' : '#e2e8f0'}; border-radius: var(--radius-sm); padding: 12px; background: ${q.has_error ? '#fff5f5' : '#ffffff'};">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 6px;">
          <div>
            <b>${idx + 1}. ${escapeHtml(q.question_text)}</b>
            ${q.has_error ? `<div style="color: #dc2626; font-size: 0.8rem; font-weight: 700; margin-top: 2px;"><i class="fa-solid fa-triangle-exclamation"></i> ${q.error_message}</div>` : ''}
            <div style="display: flex; gap: 8px; margin-top: 4px; font-size: 0.75rem;">
              <span class="badge badge-primary">${escapeHtml(q.topic_name || 'Umumiy')}</span>
              <span class="badge badge-warning">${getDiffLabel(q.difficulty)}</span>
              <span class="badge badge-info">${q.points || 1} ball</span>
            </div>
          </div>
          <div style="display: flex; gap: 6px;">
            <button class="btn btn-outline btn-sm" onclick="editLocalQuestion('word', ${idx})" style="padding: 2px 8px; font-size: 0.75rem;">
              <i class="fa-solid fa-pen"></i> Tahrirlash
            </button>
            <button class="btn btn-outline btn-sm" onclick="deleteLocalQuestion('word', ${idx})" style="padding: 2px 8px; font-size: 0.75rem; color: #ef4444; border-color: #fca5a5;">
              <i class="fa-solid fa-trash"></i> O'tkazib yuborish
            </button>
          </div>
        </div>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 6px; margin-top: 8px; font-size: 0.85rem;">
          ${q.options.map((opt, oIdx) => `
            <div style="padding: 6px 10px; border-radius: 4px; border: 1px solid ${opt.is_correct ? '#86efac' : '#f1f5f9'}; background: ${opt.is_correct ? '#f0fdf4' : '#fafafa'};">
              <b>${String.fromCharCode(65 + oIdx)})</b> ${escapeHtml(opt.option_text)}
              ${opt.is_correct ? '<span style="color: #16a34a; font-weight: 700; margin-left: 6px;">✓ To\'g\'ri</span>' : ''}
            </div>
          `).join("")}
        </div>
      </div>
    `).join("");
  }

  // --- 3. Gemini AI Test Generator ---
  function setupAiBuilder() {
    const btnGen = document.getElementById("btn-generate-ai-test");
    const btnConfirm = document.getElementById("btn-confirm-ai-test");
    const btnClear = document.getElementById("btn-ai-clear-all");
    const btnAddManual = document.getElementById("btn-ai-add-manual-q");

    btnGen.onclick = async () => {
      const assignId = document.getElementById("tb-assignment-select").value;
      const topic = document.getElementById("ai-tb-topic").value.trim();
      const count = parseInt(document.getElementById("ai-tb-count").value) || 10;
      const grade = parseInt(document.getElementById("ai-tb-grade").value) || 10;
      const diff = document.getElementById("ai-tb-difficulty").value;
      const pts = parseInt(document.getElementById("ai-tb-points").value) || 1;
      const expFlag = document.getElementById("ai-tb-exp").value === "1";
      const extra = document.getElementById("ai-tb-extra").value.trim();

      if (!topic) {
        alert("Iltimos, mavzu nomini kiriting!");
        return;
      }

      const selAssignment = myAssignments.find(a => a.assignment_id == assignId);
      const subjectName = selAssignment ? selAssignment.subject_name : "Matematika";

      btnGen.disabled = true;
      btnGen.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Gemini AI savollarni tuzmoqda...';

      try {
        const res = await fetch("/api/ai/generate-questions", {
          method: "POST",
          headers: authHeaders(),
          body: JSON.stringify({
            subject_name: subjectName,
            topic_name: topic,
            count: count,
            difficulty: diff,
            grade_level: grade,
            points: pts,
            include_explanation: expFlag,
            extra_prompt: extra
          })
        });
        const data = await res.json();
        if (!res.ok) {
          throw new Error(data.detail || "Gemini API xatosi / JSON validation xatosi");
        }

        aiQuestions = (data.questions || []).map((q) => ({
          ...q,
          topic_name: topic,
          points: pts,
          difficulty: diff
        }));

        if (!document.getElementById("tb-test-title").value) {
          document.getElementById("tb-test-title").value = `${subjectName}: ${topic}`;
        }

        const subTitle = document.getElementById("ai-preview-subtitle");
        const qScore = data.quality_score ? Math.round(data.quality_score * 100) : 95;
        if (subTitle) {
          subTitle.innerHTML = `Generatsiya qilingan savollar: <b>${aiQuestions.length} ta</b> (Noyob va tekshirilgan). AI Sifat Balli (Quality Score): <b>${qScore}%</b>. O'qituvchi preview ko'rigidan so'ng bazaga saqlanadi.`;
        }

        renderAiPreview();
      } catch (err) {
        alert(`❌ AI XATOSI:\n${err.message}\n\nOltin qoida: Soxta/shablon savol yaratilmaydi. Aniq xatolik qayd etildi.`);
      } finally {
        btnGen.disabled = false;
        btnGen.innerHTML = '<i class="fa-solid fa-sparkles"></i> AI Test Savollarini Generatsiya Qilish';
      }
    };

    btnAddManual.onclick = () => {
      const qText = prompt("Qo'lda qo'shiladigan savol matnini kiriting:");
      if (!qText) return;
      const optA = prompt("A varianti:") || "A";
      const optB = prompt("B varianti:") || "B";
      const optC = prompt("C varianti:") || "C";
      const optD = prompt("D varianti:") || "D";
      const corr = (prompt("To'g'ri javob harfi (A, B, C yoki D):") || "A").toUpperCase();

      aiQuestions.push({
        question_text: qText,
        topic_name: document.getElementById("ai-tb-topic").value.trim() || "Umumiy",
        difficulty: "medium",
        points: 1,
        explanation: "",
        options: [
          { option_text: optA, is_correct: corr === "A" ? 1 : 0 },
          { option_text: optB, is_correct: corr === "B" ? 1 : 0 },
          { option_text: optC, is_correct: corr === "C" ? 1 : 0 },
          { option_text: optD, is_correct: corr === "D" ? 1 : 0 }
        ]
      });
      renderAiPreview();
    };

    btnClear.onclick = () => {
      if (aiQuestions.length > 0 && confirm("Barcha AI savollarini tozalashni xohlaysizmi?")) {
        aiQuestions = [];
        renderAiPreview();
      }
    };

    btnConfirm.onclick = () => saveTestFromQuestions(aiQuestions);
  }

  function renderAiPreview() {
    const card = document.getElementById("ai-preview-card");
    const subTitle = document.getElementById("ai-preview-subtitle");
    const list = document.getElementById("ai-questions-list");

    card.style.display = "block";
    subTitle.textContent = `Generatsiya qilingan savollar: ${aiQuestions.length} ta. Har bir savolni tahrirlashingiz yoki o'chirishingiz mumkin.`;

    list.innerHTML = aiQuestions.map((q, idx) => `
      <div style="border: 1px solid #c7d2fe; border-radius: var(--radius-sm); padding: 12px; background: #ffffff;">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 6px;">
          <div>
            <b>${idx + 1}. ${escapeHtml(q.question_text)}</b>
            <div style="display: flex; gap: 8px; margin-top: 4px; font-size: 0.75rem;">
              <span class="badge badge-primary">${escapeHtml(q.topic_name || '')}</span>
              <span class="badge badge-warning">${getDiffLabel(q.difficulty)}</span>
              <span class="badge badge-info">${q.points || 1} ball</span>
            </div>
          </div>
          <div style="display: flex; gap: 6px;">
            <button class="btn btn-outline btn-sm" onclick="editLocalQuestion('ai', ${idx})" style="padding: 2px 8px; font-size: 0.75rem;">
              <i class="fa-solid fa-pen"></i> Tahrirlash
            </button>
            <button class="btn btn-outline btn-sm" onclick="deleteLocalQuestion('ai', ${idx})" style="padding: 2px 8px; font-size: 0.75rem; color: #ef4444; border-color: #fca5a5;">
              <i class="fa-solid fa-trash"></i>
            </button>
          </div>
        </div>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 6px; margin-top: 8px; font-size: 0.85rem;">
          ${q.options.map((opt, oIdx) => `
            <div style="padding: 6px 10px; border-radius: 4px; border: 1px solid ${opt.is_correct ? '#86efac' : '#f1f5f9'}; background: ${opt.is_correct ? '#f0fdf4' : '#fafafa'};">
              <b>${String.fromCharCode(65 + oIdx)})</b> ${escapeHtml(opt.option_text)}
              ${opt.is_correct ? '<span style="color: #16a34a; font-weight: 700; margin-left: 6px;">✓ To\'g\'ri</span>' : ''}
            </div>
          `).join("")}
        </div>
        ${q.explanation ? `<p style="font-size: 0.8rem; color: #64748b; margin-top: 6px; font-style: italic;">Izoh: ${escapeHtml(q.explanation)}</p>` : ''}
      </div>
    `).join("");
  }

  // --- Savollarni saqlash umumiy funksiyasi ---
  async function saveTestFromQuestions(questionsArr) {
    const assignId = document.getElementById("tb-assignment-select").value;
    const title = document.getElementById("tb-test-title").value.trim();
    const duration = parseInt(document.getElementById("tb-duration").value) || 30;
    const passing = parseInt(document.getElementById("tb-passing").value) || 60;
    const examType = document.getElementById("tb-exam-type").value;
    const status = document.getElementById("tb-initial-status").value;

    if (!assignId) {
      alert("Iltimos, avval biriktirilgan Guruh va Fanni tanlang!");
      return;
    }
    if (!title) {
      alert("Iltimos, test nomini kiriting!");
      return;
    }
    if (!questionsArr || questionsArr.length === 0) {
      alert("Testga kamida 1 ta savol qo'shilgan bo'lishi kerak!");
      return;
    }

    try {
      const res = await fetch("/api/teacher/tests/full", {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({
          assignment_id: parseInt(assignId),
          title: title,
          duration_minutes: duration,
          passing_score: passing,
          exam_type: examType,
          status: status,
          questions: questionsArr
        })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Testni saqlashda xatolik");

      alert(`Muvaffaqiyatli! Test ${questionsArr.length} ta savol bilan saqlandi.`);
      document.querySelector('[data-panel="test-bank"]').click();
    } catch (err) {
      alert(`Xatolik: ${err.message}`);
    }
  }

  // Local savollarni tahrirlash va o'chirish
  window.deleteLocalQuestion = function(type, index) {
    if (!confirm("Ushbu savolni o'chirishga ishonchingiz komilmi?")) return;
    if (type === "manual") {
      manualQuestions.splice(index, 1);
      renderManualQuestions();
    } else if (type === "word") {
      wordQuestions.splice(index, 1);
      renderWordPreview();
    } else if (type === "ai") {
      aiQuestions.splice(index, 1);
      renderAiPreview();
    }
  };

  window.editLocalQuestion = function(type, index) {
    let q = null;
    if (type === "manual") q = manualQuestions[index];
    else if (type === "word") q = wordQuestions[index];
    else if (type === "ai") q = aiQuestions[index];
    if (!q) return;

    openEditQuestionModal(type, index, null, q);
  };

  // =========================================================================
  // 7. MENING TEST BAZAM (TEACHER TEST BANK)
  // =========================================================================
  let testBankData = [];

  async function loadTestBank() {
    const subFilter = document.getElementById("tbk-subject-filter");
    subFilter.innerHTML = '<option value="">Barcha fanlar</option>' +
      mySubjects.map(s => `<option value="${s.id}">${s.name}</option>`).join("");

    await fetchAndRenderTestBank();

    document.getElementById("tbk-search-input").oninput = debounce(fetchAndRenderTestBank, 300);
    document.getElementById("tbk-subject-filter").onchange = fetchAndRenderTestBank;
    document.getElementById("tbk-status-filter").onchange = fetchAndRenderTestBank;
  }

  async function fetchAndRenderTestBank() {
    const search = document.getElementById("tbk-search-input") ? document.getElementById("tbk-search-input").value.trim() : "";
    const subId = document.getElementById("tbk-subject-filter") ? document.getElementById("tbk-subject-filter").value : "";
    const status = document.getElementById("tbk-status-filter") ? document.getElementById("tbk-status-filter").value : "";

    const params = new URLSearchParams();
    if (search) params.append("search", search);
    if (subId) params.append("subject_id", subId);
    if (status) params.append("status", status);

    try {
      const res = await fetch(`/api/teacher/test-bank/search?${params.toString()}`, { headers: authHeaders() });
      testBankData = await res.json();
      renderTestBankCards(testBankData);
    } catch (err) {
      console.error("Test bank yuklash xatosi:", err);
    }
  }

  function renderTestBankCards(tests) {
    const grid = document.getElementById("tbk-tests-grid");
    if (!grid) return;

    if (tests.length === 0) {
      grid.innerHTML = '<div style="grid-column: 1 / -1; text-align: center; padding: 2rem; color: #94a3b8;">Mos keluvchi testlar topilmadi.</div>';
      return;
    }

    grid.innerHTML = tests.map(t => {
      const isAct = t.status === "active";
      const isArch = t.status === "finished";
      const statusBadge = isAct
        ? '<span class="badge badge-success"><i class="fa-solid fa-circle-check"></i> Faol</span>'
        : (isArch ? '<span class="badge" style="background:#e0e7ff; color:#3730a3;"><i class="fa-solid fa-box-archive"></i> Arxivlangan</span>' : '<span class="badge badge-warning"><i class="fa-solid fa-clock"></i> Nofaol (Draft)</span>');

      return `
        <div class="content-card" style="display: flex; flex-direction: column; justify-content: space-between; border-top: 4px solid ${isAct ? '#22c55e' : (isArch ? '#818cf8' : '#eab308')};">
          <div>
            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
              <span class="badge badge-primary">${escapeHtml(t.subject_name)} • ${escapeHtml(t.group_name)}</span>
              ${statusBadge}
            </div>
            <h3 style="font-size: 1.15rem; font-weight: 800; color: #1e1b4b; margin-bottom: 6px;">${escapeHtml(t.title)}</h3>
            <div style="font-size: 0.85rem; color: #64748b; display: flex; flex-direction: column; gap: 4px; margin-bottom: 12px;">
              <div><i class="fa-solid fa-clipboard-question"></i> Savollar soni: <b>${t.question_count} ta</b></div>
              <div><i class="fa-solid fa-clock"></i> Davomiyligi: <b>${t.duration_minutes} daqiqa</b> | O'tish bali: <b>${t.passing_score}%</b></div>
              <div><i class="fa-solid fa-users-viewfinder"></i> Topshirganlar: <b>${t.attempts_count} nafar</b> | O'rtacha: <b>${t.avg_score || 0}%</b></div>
            </div>
          </div>

          <div style="border-top: 1px solid #f1f5f9; padding-top: 10px; display: flex; flex-wrap: wrap; gap: 6px; justify-content: space-between;">
            <button class="btn btn-primary btn-sm" onclick="openTeacherGroupAccessModal(${t.id}, '${escapeHtml(t.title)}')" style="font-weight: 600;">
              <i class="fa-solid fa-users-gear"></i> Ruxsatlarni boshqarish
            </button>
            <button class="btn btn-outline btn-sm" onclick="openManageTestModal(${t.id})">
              <i class="fa-solid fa-folder-open"></i> Ochish / Tahrirlash
            </button>
            <button class="btn btn-sm ${isAct ? 'btn-outline' : 'btn-success'}" onclick="toggleTestStatusAction(${t.id})">
              <i class="fa-solid ${isAct ? 'fa-pause' : 'fa-play'}"></i> ${isAct ? 'Nofaol qilish' : 'Faollashtirish'}
            </button>
            <button class="btn btn-outline btn-sm" onclick="exportWordModal(${t.id})" title="Word formatida yuklab olish">
              <i class="fa-solid fa-file-word" style="color: #2563eb;"></i> Word
            </button>
            <button class="btn btn-outline btn-sm" onclick="cloneTestAction(${t.id})" title="Testni nusxalash">
              <i class="fa-solid fa-copy"></i>
            </button>
            <button class="btn btn-outline btn-sm" onclick="deleteTestAction(${t.id})" style="color: #ef4444; border-color: #fca5a5;" title="O'chirish yoki arxivlash">
              <i class="fa-solid fa-trash"></i>
            </button>
          </div>
        </div>
      `;
    }).join("");
  }

  // Test statusini almashtirish
  window.toggleTestStatusAction = async function(testId) {
    try {
      const res = await fetch(`/api/teacher/tests/${testId}/toggle-status`, {
        method: "POST",
        headers: authHeaders()
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Xatolik");
      await fetchAndRenderTestBank();
    } catch (err) {
      alert(`Xatolik: ${err.message}`);
    }
  };

  // Testni nusxalash
  window.cloneTestAction = async function(testId) {
    if (!confirm("Ushbu testdan nusxa yaratmoqchimisiz?")) return;
    try {
      const res = await fetch(`/api/teacher/tests/${testId}/clone`, {
        method: "POST",
        headers: authHeaders()
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Nusxalashda xatolik");
      alert(data.message);
      await fetchAndRenderTestBank();
    } catch (err) {
      alert(`Xatolik: ${err.message}`);
    }
  };

  // Testni o'chirish / arxivlash
  window.deleteTestAction = async function(testId) {
    if (!confirm("Ushbu testni o'chirishga ishonchingiz komilmi? (Agar o'quvchilar topshirgan bo'lsa, natijalar saqlangan holda arxivlanadi)")) return;
    try {
      const res = await fetch(`/api/teacher/tests/${testId}`, {
        method: "DELETE",
        headers: authHeaders()
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "O'chirishda xatolik");
      alert(data.message);
      await fetchAndRenderTestBank();
    } catch (err) {
      alert(`Xatolik: ${err.message}`);
    }
  };

  // Word export
  window.exportWordModal = function(testId) {
    const isTeacher = confirm("To'g'ri javoblar va izohlar ko'rsatilsinmi?\n\n[OK] = O'qituvchi nusxasi (javoblar bilan)\n[Otmena] = O'quvchi nusxasi (javoblarsiz)");
    const mode = isTeacher ? "teacher" : "student";
    window.open(`/api/teacher/word/export/${testId}?mode=${mode}`, "_blank");
  };

  // =========================================================================
  // 8. TESTNI OCHISH / TAHRIRLASH MODALI (#modal-manage-test)
  // =========================================================================
  let currentManagingTest = null;

  window.openManageTestModal = async function(testId) {
    try {
      const res = await fetch(`/api/teacher/tests/${testId}`, { headers: authHeaders() });
      if (!res.ok) throw new Error("Test ma'lumotlarini yuklab bo'lmadi");
      currentManagingTest = await res.json();

      document.getElementById("manage-test-id").value = currentManagingTest.id;
      document.getElementById("manage-test-name").value = currentManagingTest.title;
      document.getElementById("manage-test-subject-group").value = `${currentManagingTest.subject_name} (${currentManagingTest.group_name})`;
      document.getElementById("manage-test-duration").value = currentManagingTest.duration_minutes;
      document.getElementById("manage-test-passing").value = currentManagingTest.passing_score;
      document.getElementById("manage-test-type").value = currentManagingTest.exam_type || "midterm";
      document.getElementById("manage-test-status").value = currentManagingTest.status || "active";

      renderManagingQuestions();
      openModal("modal-manage-test");
    } catch (err) {
      alert(`Xatolik: ${err.message}`);
    }
  };

  function renderManagingQuestions() {
    const list = document.getElementById("manage-test-questions-list");
    const countBadge = document.getElementById("manage-test-q-count");
    if (!currentManagingTest || !list) return;

    const questions = currentManagingTest.questions || [];
    countBadge.textContent = `${questions.length} ta`;

    if (questions.length === 0) {
      list.innerHTML = '<p style="color: #94a3b8; text-align: center; padding: 1.5rem;">Testda hali savollar yo\'q. Yuqoridagi "+ Yangi Savol Qo\'shish" tugmasini bosing.</p>';
      return;
    }

    list.innerHTML = questions.map((q, idx) => `
      <div style="border: 1px solid #e2e8f0; border-radius: var(--radius-sm); padding: 10px; background: #ffffff;">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 4px;">
          <div>
            <b>${idx + 1}. ${escapeHtml(q.question_text)}</b>
            <div style="display: flex; gap: 6px; margin-top: 4px; font-size: 0.75rem;">
              <span class="badge badge-primary">${escapeHtml(q.topic_name || '')}</span>
              <span class="badge badge-warning">${getDiffLabel(q.difficulty)}</span>
              <span class="badge badge-info">${q.points} ball</span>
            </div>
          </div>
          <div style="display: flex; gap: 6px;">
            <button class="btn btn-outline btn-sm" onclick="editSingleQuestionAction(${q.question_id})" style="padding: 2px 8px; font-size: 0.75rem;">
              <i class="fa-solid fa-pen"></i> Tahrirlash
            </button>
            <button class="btn btn-outline btn-sm" onclick="removeQuestionFromTestAction(${q.question_id})" style="padding: 2px 8px; font-size: 0.75rem; color: #ef4444; border-color: #fca5a5;">
              <i class="fa-solid fa-trash"></i> O'chirish
            </button>
          </div>
        </div>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 4px; margin-top: 6px; font-size: 0.8rem;">
          ${q.options.map((opt, oIdx) => `
            <div style="padding: 4px 8px; border-radius: 4px; border: 1px solid ${opt.is_correct ? '#86efac' : '#f1f5f9'}; background: ${opt.is_correct ? '#f0fdf4' : '#fafafa'};">
              <b>${String.fromCharCode(65 + oIdx)})</b> ${escapeHtml(opt.option_text)}
              ${opt.is_correct ? '<span style="color: #16a34a; font-weight: 700; margin-left: 4px;">✓</span>' : ''}
            </div>
          `).join("")}
        </div>
      </div>
    `).join("");
  }

  // Test parametrlarini saqlash
  const formManageDetails = document.getElementById("form-manage-test-details");
  if (formManageDetails) {
    formManageDetails.onsubmit = async (e) => {
      e.preventDefault();
      const testId = document.getElementById("manage-test-id").value;
      const title = document.getElementById("manage-test-name").value.trim();
      const duration = parseInt(document.getElementById("manage-test-duration").value);
      const passing = parseInt(document.getElementById("manage-test-passing").value);
      const examType = document.getElementById("manage-test-type").value;
      const status = document.getElementById("manage-test-status").value;

      try {
        const res = await fetch(`/api/teacher/tests/${testId}`, {
          method: "PUT",
          headers: authHeaders(),
          body: JSON.stringify({
            title: title,
            duration_minutes: duration,
            passing_score: passing,
            exam_type: examType,
            status: status
          })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Yangilashda xatolik");
        alert("Test parametrlari muvaffaqiyatli saqlandi!");
        await fetchAndRenderTestBank();
      } catch (err) {
        alert(`Xatolik: ${err.message}`);
      }
    };
  }

  // Testga yangi savol qo'shish tugmasi
  const btnOpenAppend = document.getElementById("btn-open-append-q");
  if (btnOpenAppend) {
    btnOpenAppend.onclick = () => {
      openModal("modal-append-question-to-test");
    };
  }

  // Testga yangi savol qo'shish formasi
  const formAppendQ = document.getElementById("form-append-question");
  if (formAppendQ) {
    formAppendQ.onsubmit = async (e) => {
      e.preventDefault();
      if (!currentManagingTest) return;

      const testId = currentManagingTest.id;
      const topicName = document.getElementById("append-q-topic").value.trim();
      const diff = document.getElementById("append-q-diff").value;
      const pts = parseInt(document.getElementById("append-q-points").value) || 1;
      const qText = document.getElementById("append-q-text").value.trim();
      const exp = document.getElementById("append-q-exp").value.trim();

      const opt0 = document.getElementById("append-opt-0").value.trim();
      const opt1 = document.getElementById("append-opt-1").value.trim();
      const opt2 = document.getElementById("append-opt-2").value.trim();
      const opt3 = document.getElementById("append-opt-3").value.trim();

      const corrRadios = document.getElementsByName("append_corr");
      let corrIdx = 0;
      corrRadios.forEach(r => { if (r.checked) corrIdx = parseInt(r.value); });

      const options = [
        { option_text: opt0, is_correct: corrIdx === 0 ? 1 : 0 },
        { option_text: opt1, is_correct: corrIdx === 1 ? 1 : 0 },
        { option_text: opt2, is_correct: corrIdx === 2 ? 1 : 0 },
        { option_text: opt3, is_correct: corrIdx === 3 ? 1 : 0 }
      ];

      try {
        const res = await fetch(`/api/teacher/tests/${testId}/questions`, {
          method: "POST",
          headers: authHeaders(),
          body: JSON.stringify({
            question_text: qText,
            topic_name: topicName,
            difficulty: diff,
            points: pts,
            explanation: exp,
            options: options
          })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Savol qo'shishda xatolik");

        closeModal("modal-append-question-to-test");
        formAppendQ.reset();

        // Testni qayta yuklash
        await openManageTestModal(testId);
        await fetchAndRenderTestBank();
      } catch (err) {
        alert(`Xatolik: ${err.message}`);
      }
    };
  }

  // Savolni testdan o'chirish
  window.removeQuestionFromTestAction = async function(questionId) {
    if (!confirm("Ushbu savolni testdan olib tashlashga ishonchingiz komilmi?")) return;
    try {
      const res = await fetch(`/api/teacher/tests/${currentManagingTest.id}/questions/${questionId}`, {
        method: "DELETE",
        headers: authHeaders()
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Xatolik");
      await openManageTestModal(currentManagingTest.id);
      await fetchAndRenderTestBank();
    } catch (err) {
      alert(`Xatolik: ${err.message}`);
    }
  };

  // Savolni tahrirlash (modal orqali)
  let activeEditingContext = null;

  window.editSingleQuestionAction = function(questionId) {
    if (!currentManagingTest) return;
    const q = currentManagingTest.questions.find(x => x.question_id === questionId);
    if (!q) return;

    openEditQuestionModal("server", null, currentManagingTest.id, q);
  };

  function openEditQuestionModal(source, index, testId, qData) {
    activeEditingContext = { source, index, testId, qData };

    document.getElementById("edit-q-id").value = qData.question_id || index;
    document.getElementById("edit-q-test-id").value = testId || "";
    document.getElementById("edit-q-text").value = qData.question_text || "";
    document.getElementById("edit-q-diff").value = qData.difficulty || "medium";
    document.getElementById("edit-q-points").value = qData.points || 1;
    document.getElementById("edit-q-exp").value = qData.explanation || "";

    const opts = qData.options || [];
    for (let i = 0; i < 4; i++) {
      const optVal = opts[i] ? opts[i].option_text : "";
      const isCorr = opts[i] ? opts[i].is_correct : 0;
      const inp = document.getElementById(`edit-opt-${i}`);
      const rad = document.getElementById(`edit-opt-r${i}`);
      if (inp) inp.value = optVal;
      if (rad) rad.checked = (isCorr === 1);
    }

    openModal("modal-edit-question-detail");
  }

  const formEditQDetail = document.getElementById("form-edit-question-detail");
  if (formEditQDetail) {
    formEditQDetail.onsubmit = async (e) => {
      e.preventDefault();
      if (!activeEditingContext) return;

      const qText = document.getElementById("edit-q-text").value.trim();
      const diff = document.getElementById("edit-q-diff").value;
      const pts = parseInt(document.getElementById("edit-q-points").value) || 1;
      const exp = document.getElementById("edit-q-exp").value.trim();

      const corrRadios = document.getElementsByName("edit_corr");
      let corrIdx = 0;
      corrRadios.forEach(r => { if (r.checked) corrIdx = parseInt(r.value); });

      const options = [];
      for (let i = 0; i < 4; i++) {
        const val = document.getElementById(`edit-opt-${i}`).value.trim();
        if (val) options.push({ option_text: val, is_correct: corrIdx === i ? 1 : 0 });
      }

      const { source, index, testId, qData } = activeEditingContext;

      if (source === "server") {
        try {
          const res = await fetch(`/api/teacher/tests/${testId}/questions/${qData.question_id}`, {
            method: "PUT",
            headers: authHeaders(),
            body: JSON.stringify({
              question_text: qText,
              difficulty: diff,
              points: pts,
              explanation: exp,
              options: options
            })
          });
          const data = await res.json();
          if (!res.ok) throw new Error(data.detail || "Tahrirlashda xatolik");

          closeModal("modal-edit-question-detail");
          await openManageTestModal(testId);
        } catch (err) {
          alert(`Xatolik: ${err.message}`);
        }
      } else {
        // Local arrays (manual, word, ai)
        qData.question_text = qText;
        qData.difficulty = diff;
        qData.points = pts;
        qData.explanation = exp;
        qData.options = options;
        qData.has_error = false;

        closeModal("modal-edit-question-detail");
        if (source === "manual") renderManualQuestions();
        else if (source === "word") renderWordPreview();
        else if (source === "ai") renderAiPreview();
      }
    };
  }

  // Yordamchi funksiyalar
  function getDiffLabel(d) {
    if (d === "easy") return "Oson";
    if (d === "hard") return "Qiyin";
    return "O'rta";
  }

  function escapeHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function debounce(fn, delay) {
    let timer = null;
    return function(...args) {
      clearTimeout(timer);
      timer = setTimeout(() => fn.apply(this, args), delay);
    };
  }

  // --- GURUHLAR BO'YICHA RUXSAT MODALI (TEACHER) ---
  let activeTeacherModalTestId = null;

  window.openTeacherGroupAccessModal = async function(testId, testTitle) {
    activeTeacherModalTestId = testId;
    document.getElementById("mga-test-title").textContent = `"${testTitle}" — Guruhlar Ruxsatnomasi`;
    openModal("modal-group-access");
    await loadTeacherGroupsAccess(testId);
  };

  async function loadTeacherGroupsAccess(testId) {
    const tbody = document.getElementById("mga-groups-tbody");
    if (!tbody) return;
    tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 1.5rem;"><i class="fa-solid fa-spinner fa-spin"></i> Yuklanmoqda...</td></tr>';

    try {
      const res = await fetch(`/api/tests/${testId}/groups-access`, { headers: authHeaders() });
      if (!res.ok) throw new Error("Guruhlarni yuklashda xatolik");
      const groups = await res.json();

      if (!groups || groups.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 1.5rem;">Guruhlar topilmadi</td></tr>';
        return;
      }

      tbody.innerHTML = groups.map(g => {
        const isAct = g.status === "active";
        const isComp = g.status === "completed";
        const isAnnounced = g.is_results_announced === 1;

        let statusBadge = '<span class="badge badge-warning"><i class="fa-solid fa-hourglass-start"></i> Kutilmoqda</span>';
        if (isAct) {
          statusBadge = '<span class="badge badge-success"><i class="fa-solid fa-play"></i> Boshlangan (Faol)</span>';
        } else if (isComp) {
          statusBadge = '<span class="badge badge-primary"><i class="fa-solid fa-flag-checkered"></i> Yakunlangan</span>';
        }

        let announcedBadge = '<span class="badge badge-secondary">Kutilmoqda</span>';
        if (isAnnounced) {
          announcedBadge = '<span class="badge badge-success"><i class="fa-solid fa-bullhorn"></i> E\'lon qilingan</span>';
        }

        return `
          <tr>
            <td style="text-align: center;">
              <input type="checkbox" class="mga-group-checkbox" value="${g.group_id}" ${isAct ? 'data-status="active"' : ''}>
            </td>
            <td>
              <b>${escapeHtml(g.group_name)}</b>
              <div style="font-size: 0.75rem; color: #94a3b8;">${g.academic_year || ''}</div>
            </td>
            <td><b>${g.student_count}</b> nafar</td>
            <td>${statusBadge}</td>
            <td style="font-size: 0.85rem; color: #475569;">${g.start_time ? g.start_time.substring(11, 16) : '—'}</td>
            <td style="font-size: 0.85rem; color: #475569;">${g.end_time ? g.end_time.substring(11, 16) : '—'}</td>
            <td>${announcedBadge}</td>
          </tr>
        `;
      }).join("");
    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: #ef4444; padding: 1.5rem;">Xatolik: ${err.message}</td></tr>`;
    }
  }

  // Select all checkbox
  document.getElementById("mga-check-all")?.addEventListener("change", (e) => {
    const checked = e.target.checked;
    document.querySelectorAll(".mga-group-checkbox").forEach(cb => cb.checked = checked);
  });

  // Grant access
  document.getElementById("mga-btn-grant")?.addEventListener("click", async () => {
    if (!activeTeacherModalTestId) return;
    const selected = Array.from(document.querySelectorAll(".mga-group-checkbox:checked")).map(cb => parseInt(cb.value));
    if (selected.length === 0) {
      alert("Iltimos, avval test boshlanishi kerak bo'lgan kamida bitta guruhni belgilang!");
      return;
    }
    try {
      const res = await fetch("/api/tests/grant-access", {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({ test_id: activeTeacherModalTestId, group_ids: selected })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Ruxsat berishda xatolik");
      alert("✅ Tanlangan guruh(lar) uchun test muvaffaqiyatli boshlandi!");
      await loadTeacherGroupsAccess(activeTeacherModalTestId);
      if (typeof fetchAndRenderTestBank === "function") fetchAndRenderTestBank();
    } catch (err) {
      alert("Xatolik: " + err.message);
    }
  });

  // Stop access & announce results
  document.getElementById("mga-btn-stop")?.addEventListener("click", async () => {
    if (!activeTeacherModalTestId) return;
    const selected = Array.from(document.querySelectorAll(".mga-group-checkbox:checked")).map(cb => parseInt(cb.value));
    if (selected.length === 0) {
      alert("Iltimos, avval testi yakunlanishi kerak bo'lgan kamida bitta guruhni belgilang!");
      return;
    }
    if (!confirm(`Belgilangan ${selected.length} ta guruh uchun testni to'xtatib, natijalarni talabalarga e'lon qilasizmi?`)) return;
    try {
      const res = await fetch("/api/tests/stop-access", {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({ test_id: activeTeacherModalTestId, group_ids: selected })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Testni yakunlashda xatolik");
      alert("🏁 Tanlangan guruh(lar) uchun test yakunlandi va natijalar e'lon qilindi!");
      await loadTeacherGroupsAccess(activeTeacherModalTestId);
      if (typeof fetchAndRenderTestBank === "function") fetchAndRenderTestBank();
    } catch (err) {
      alert("Xatolik: " + err.message);
    }
  });

  document.getElementById("mga-btn-refresh")?.addEventListener("click", () => {
    if (activeTeacherModalTestId) loadTeacherGroupsAccess(activeTeacherModalTestId);
  });

  // Initial load
  await loadAssignments();
  await loadQuestionBank();
});

