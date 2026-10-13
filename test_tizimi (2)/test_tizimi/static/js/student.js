// student.js — O'quvchi kabineti logikasi

function escapeHtml(str) {
  if (str === null || str === undefined) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function escapeStr(str) {
  return (str || '').replace(/'/g, "\\'").replace(/"/g, '&quot;');
}

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
  const fullName = localStorage.getItem("user_full_name") || "O'quvchi";
  const groupName = localStorage.getItem("group_name") || "10-A";

  if (!token || role !== "student") {
    alert("Iltimos, avval O'quvchi hisobi bilan tizimga kiring!");
    window.location.href = "/login";
    return;
  }

  document.getElementById("hero-student-name").textContent = `Assalomu alaykum, ${fullName}!`;
  document.getElementById("hero-group-name").textContent = groupName;
  document.getElementById("nav-student-tag").innerHTML = `<i class="fa-solid fa-user-graduate"></i> ${escapeHtml(fullName)}`;

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

  // 1. Mening Fanlarim
  async function loadMySubjects() {
    try {
      const res = await fetch("/api/student/my-subjects", { headers: authHeaders() });
      if (res.status === 401 || res.status === 403) {
        localStorage.clear();
        window.location.href = "/login";
        return;
      }
      const subjects = await res.json();
      const grid = document.getElementById("subjects-grid");

      if (subjects.length === 0) {
        grid.innerHTML = '<p style="color: #64748b;">Sizning guruhingizga hozircha fanlar biriktirilmagan.</p>';
        return;
      }

      grid.innerHTML = subjects.map(s => `
        <div class="subject-card" onclick="openSubjectExams(${s.subject_id}, '${escapeStr(s.subject_name)}', '${escapeStr(s.teacher_name)}')">
          <div>
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
              <span class="badge badge-primary">${escapeHtml(s.subject_code)}</span>
              <span class="badge ${s.active_exams_count > 0 ? 'badge-success' : 'badge-warning'}">
                ${s.active_exams_count > 0 ? escapeHtml(s.active_exams_count) + ' ta faol imtihon' : 'Imtihon yo\'q'}
              </span>
            </div>
            <h3 style="font-size: 1.25rem; font-weight: 800; color: #1e1b4b; margin-bottom: 6px;">${escapeHtml(s.subject_name)}</h3>
            <p style="font-size: 0.85rem; color: #64748b; margin-bottom: 12px;">${escapeHtml(s.subject_description || 'Muntazam o\'quv kursi')}</p>
          </div>
          <div style="border-top: 1px solid #f1f5f9; padding-top: 10px; font-size: 0.85rem; color: #475569; display: flex; justify-content: space-between; align-items: center;">
            <span><i class="fa-solid fa-chalkboard-user"></i> ${escapeHtml(s.teacher_name)}</span>
            <i class="fa-solid fa-chevron-right" style="color: var(--primary);"></i>
          </div>
        </div>
      `).join("");
    } catch (err) { console.error(err); }
  }

  // Fan imtihonlari modali
  window.openSubjectExams = async (subjectId, subjectName, teacherName) => {
    document.getElementById("modal-sub-title").textContent = subjectName;
    document.getElementById("modal-teacher-name").textContent = `O'qituvchi: ${teacherName}`;
    const list = document.getElementById("modal-exams-list");
    list.innerHTML = '<p style="text-align: center; color: #64748b;"><i class="fa-solid fa-spinner fa-spin"></i> Yuklanmoqda...</p>';
    openModal("modal-subject-exams");

    try {
      const res = await fetch(`/api/student/subjects/${subjectId}/exams`, { headers: authHeaders() });
      const exams = await res.json();

      if (exams.length === 0) {
        list.innerHTML = '<p style="color: #64748b; text-align: center; padding: 1.5rem;">Ushbu fandan hozircha faol imtihonlar mavjud emas.</p>';
        return;
      }

      list.innerHTML = exams.map(e => {
        const canTake = e.completed_attempts < e.max_attempts;
        const gStatus = (e.group_access_status || "pending").toLowerCase();
        const isAnnounced = e.is_results_announced === 1;
        let actionBtn = "";
        let statusBadge = "";

        if (gStatus === "active") {
          statusBadge = '<span class="badge badge-success" style="font-size:0.75rem;"><i class="fa-solid fa-circle-dot"></i> Boshlangan (Faol)</span>';
          if (canTake) {
            actionBtn = `
              <a href="/exam/${e.id}" class="btn btn-success btn-sm" style="padding: 8px 16px;">
                <i class="fa-solid fa-play"></i> Testni Boshlash
              </a>
            `;
          } else {
            actionBtn = `
              <span class="badge badge-info" style="padding: 8px 12px; font-size: 0.85rem;">
                <i class="fa-solid fa-check"></i> Topshirildi (Natija kutilmoqda)
              </span>
            `;
          }
        } else if (gStatus === "completed") {
          statusBadge = '<span class="badge badge-primary" style="font-size:0.75rem;"><i class="fa-solid fa-flag-checkered"></i> Yakunlangan</span>';
          if (isAnnounced && e.last_session_id) {
            actionBtn = `
              <a href="/result/${e.last_session_id}" class="btn btn-primary btn-sm" style="padding: 8px 16px;">
                <i class="fa-solid fa-square-poll-vertical"></i> Natijani Ko'rish (${e.best_score || 0}%)
              </a>
            `;
          } else if (e.last_session_id) {
            actionBtn = `
              <span class="badge badge-warning" style="padding: 8px 12px; font-size: 0.85rem;">
                <i class="fa-solid fa-clock"></i> Natijalar e'lon qilinishi kutilmoqda
              </span>
            `;
          } else {
            actionBtn = `
              <span class="badge badge-secondary" style="padding: 8px 12px; font-size: 0.85rem;">
                <i class="fa-solid fa-lock"></i> Test yakunlangan
              </span>
            `;
          }
        } else {
          statusBadge = '<span class="badge badge-warning" style="font-size:0.75rem;"><i class="fa-solid fa-hourglass-start"></i> Boshlanish kutilmoqda</span>';
          actionBtn = `
            <button class="btn btn-sm" disabled style="background: #f1f5f9; color: #94a3b8; cursor: not-allowed; padding: 8px 16px; border: 1px solid #cbd5e1;">
              <i class="fa-solid fa-clock"></i> Test hali boshlanmadi
            </button>
          `;
        }

        return `
          <div class="test-item-card" style="margin-bottom: 12px; cursor: default;">
            <div class="test-info">
              <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">
                <h3 style="margin: 0;">${e.title}</h3>
                ${statusBadge}
              </div>
              <div class="test-meta">
                <span class="meta-chip"><i class="fa-regular fa-clock"></i> ${e.duration_minutes} daqiqa</span>
                <span class="meta-chip"><i class="fa-solid fa-list-check"></i> ${e.question_count} ta savol</span>
                <span class="meta-chip"><i class="fa-solid fa-bullseye"></i> O'tish bali: ${e.passing_score}%</span>
                <span class="meta-chip"><i class="fa-solid fa-rotate-right"></i> Urinishlar: ${e.completed_attempts}/${e.max_attempts}</span>
              </div>
            </div>
            <div>${actionBtn}</div>
          </div>
        `;
      }).join("");
    } catch (err) { console.error(err); }
  };

  // 2. Ta'lim Xaritasi (Knowledge Map)
  let trendChartInstance = null;

  document.getElementById("btn-view-map").addEventListener("click", () => {
    document.getElementById("section-my-subjects").style.display = "none";
    document.getElementById("section-learning-map").style.display = "block";
    loadLearningMap();
  });

  document.getElementById("btn-back-to-subjects").addEventListener("click", () => {
    document.getElementById("section-learning-map").style.display = "none";
    document.getElementById("section-my-subjects").style.display = "block";
  });

  async function loadLearningMap() {
    try {
      const res = await fetch("/api/student/learning-map", { headers: authHeaders() });
      const data = await res.json();

      // Fanlar progress bar
      const subBox = document.getElementById("map-subject-bars");
      if (data.subject_mastery.length === 0) {
        subBox.innerHTML = '<p style="color: #64748b;">Hali topshirilgan imtihonlar yo\'q.</p>';
      } else {
        subBox.innerHTML = data.subject_mastery.map(s => {
          let color = "#10b981";
          if (s.avg_score < 60) color = "#ef4444";
          else if (s.avg_score < 75) color = "#f59e0b";
          return `
            <div style="margin-bottom: 12px;">
              <div style="display: flex; justify-content: space-between; font-size: 0.9rem; font-weight: 600; margin-bottom: 4px;">
                <span>${s.subject_name} (${s.tests_taken} ta test)</span>
                <span style="color: ${color};">${s.avg_score}%</span>
              </div>
              <div class="progress-bar-bg" style="height: 10px;">
                <div class="progress-bar-fill" style="width: ${s.avg_score}%; background: ${color};"></div>
              </div>
            </div>
          `;
        }).join("");
      }

      // Mavzular progress bar
      const topBox = document.getElementById("map-topic-bars");
      if (data.topic_mastery.length === 0) {
        topBox.innerHTML = '<p style="color: #64748b;">Mavzular statistikasi hali shakllanmagan.</p>';
      } else {
        topBox.innerHTML = data.topic_mastery.map(t => {
          let color = "#10b981";
          let alertTag = "";
          if (t.avg_percentage < 60) {
            color = "#ef4444";
            alertTag = '<span class="badge badge-danger" style="margin-left: 8px;">Qayta o\'qish kerak</span>';
          } else if (t.avg_percentage >= 80) {
            alertTag = '<span class="badge badge-success" style="margin-left: 8px;">Mustahkam</span>';
          }

          return `
            <div style="margin-bottom: 12px;">
              <div style="display: flex; justify-content: space-between; font-size: 0.9rem; font-weight: 600; margin-bottom: 4px;">
                <span>${t.topic_name} <small style="color: #64748b;">(${t.subject_name})</small> ${alertTag}</span>
                <span style="color: ${color};">${t.avg_percentage}%</span>
              </div>
              <div class="progress-bar-bg" style="height: 8px;">
                <div class="progress-bar-fill" style="width: ${t.avg_percentage}%; background: ${color};"></div>
              </div>
            </div>
          `;
        }).join("");
      }

      // Dinamika grafigi (Trend Chart)
      if (data.trend_history && data.trend_history.length > 0) {
        const labels = data.trend_history.map((h, i) => `${i + 1}-test (${h.subject_name})`);
        const scores = data.trend_history.map(h => h.score_percent);

        const canvas = document.getElementById("trendChart");
        if (canvas && typeof Chart !== "undefined") {
          const ctx = canvas.getContext("2d");
          if (trendChartInstance) trendChartInstance.destroy();

          trendChartInstance = new Chart(ctx, {
            type: 'line',
            data: {
              labels: labels,
              datasets: [{
                label: 'Ball (%)',
                data: scores,
                borderColor: '#4f46e5',
                backgroundColor: 'rgba(79, 70, 229, 0.1)',
                tension: 0.3,
                fill: true,
                pointRadius: 5
              }]
            },
            options: {
              responsive: true,
              maintainAspectRatio: false,
              scales: {
                y: { min: 0, max: 100 }
              }
            }
          });
        }
      }
    } catch (err) { console.error(err); }
  }

  await loadMySubjects();
});
