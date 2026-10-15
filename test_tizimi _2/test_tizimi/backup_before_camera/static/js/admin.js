// admin.js — Enterprise Admin boshqaruv paneli logikasi

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
  const fullName = localStorage.getItem("user_full_name") || "Administrator";

  if (!token || role !== "admin") {
    alert("Iltimos, avval Administrator hisobi bilan tizimga kiring!");
    window.location.href = "/login";
    return;
  }

  document.getElementById("admin-user-title").textContent = fullName;

  function authHeaders() {
    return {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${token}`
    };
  }

  // Global Keshlar va Holat
  let teachersCache = [];
  let groupsCache = [];
  let subjectsCache = [];
  let currentDetailGroupId = null;
  let currentProfileStudentId = null;

  // --- Topbar Global O'quvchi Qidiruv ---
  const globalSearchInput = document.getElementById("global-student-search-input");
  const globalSearchResults = document.getElementById("global-search-results");
  let searchDebounceTimer = null;

  if (globalSearchInput && globalSearchResults) {
    globalSearchInput.addEventListener("input", () => {
      clearTimeout(searchDebounceTimer);
      const query = globalSearchInput.value.trim();
      if (!query) {
        globalSearchResults.style.display = "none";
        globalSearchResults.innerHTML = "";
        return;
      }

      searchDebounceTimer = setTimeout(async () => {
        try {
          const res = await fetch(`/api/admin/students/search?q=${encodeURIComponent(query)}`, { headers: authHeaders() });
          if (!res.ok) return;
          const items = await res.json();
          if (!items || items.length === 0) {
            globalSearchResults.innerHTML = '<div style="padding: 12px 16px; color: #94a3b8; font-size: 0.85rem; text-align: center;">O\'quvchi topilmadi</div>';
          } else {
            globalSearchResults.innerHTML = items.map(st => `
              <div class="global-search-item" style="padding: 10px 14px; border-bottom: 1px solid #f1f5f9; cursor: pointer; display: flex; justify-content: space-between; align-items: center; transition: background 0.15s;" onmouseover="this.style.background='#f8fafc'" onmouseout="this.style.background='transparent'" onclick="openStudentProfileModal(${st.student_id}); document.getElementById('global-search-results').style.display='none';">
                <div>
                  <div style="font-weight: 700; color: #1e1b4b; font-size: 0.9rem;">${st.full_name}</div>
                  <div style="font-size: 0.75rem; color: #64748b; margin-top: 2px;">
                    <span class="badge badge-primary" style="font-size: 0.7rem; padding: 2px 6px;">${st.group_name}</span>
                    <span style="margin-left: 4px;">ID: <code>${st.student_code}</code></span>
                    <span style="margin-left: 4px;">Login: <code>${st.username}</code></span>
                  </div>
                </div>
                <div style="text-align: right;">
                  <span class="badge ${st.is_active ? 'badge-success' : 'badge-danger'}" style="font-size: 0.7rem;">${st.is_active ? 'Faol' : 'Bloklangan'}</span>
                  <div style="font-size: 0.75rem; color: #4f46e5; font-weight: 600; margin-top: 3px;">${st.exam_count} ta test</div>
                </div>
              </div>
            `).join("");
          }
          globalSearchResults.style.display = "block";
        } catch (err) {
          console.error(err);
        }
      }, 250);
    });

    document.addEventListener("click", (e) => {
      if (!globalSearchInput.contains(e.target) && !globalSearchResults.contains(e.target)) {
        globalSearchResults.style.display = "none";
      }
    });
  }

  // Logout
  document.getElementById("btn-logout").addEventListener("click", () => {
    localStorage.clear();
    window.location.href = "/login";
  });

  // Sidebar navigation
  const sidebarLinks = document.querySelectorAll(".sidebar-link");
  const panels = document.querySelectorAll(".admin-panel");
  const panelTitle = document.getElementById("panel-title");

  const titles = {
    dashboard: "Dashboard & Umumiy Tahlil",
    teachers: "O'qituvchilar Boshqaruvi",
    students: "O'quvchilar Boshqaruvi",
    subjects: "Fanlar Boshqaruvi",
    groups: "Guruhlar Boshqaruvi",
    assignments: "O'qituvchi-Fan-Guruh Biriktirishlari",
    "test-control": "Test Nazorati va Hayot Sikli",
    audit: "Tizim Audit Tarixi (Logs)",
    settings: "Gemini AI Sozlamalari"
  };

  sidebarLinks.forEach(link => {
    link.addEventListener("click", () => {
      const panel = link.dataset.panel;
      sidebarLinks.forEach(l => l.classList.remove("active"));
      link.classList.add("active");

      panels.forEach(p => p.classList.remove("active"));
      document.getElementById(`panel-${panel}`).classList.add("active");
      panelTitle.textContent = titles[panel] || "Boshqaruv";

      if (panel === "dashboard") loadDashboard();
      if (panel === "teachers") loadTeachers();
      if (panel === "students") loadStudents();
      if (panel === "subjects") loadSubjects();
      if (panel === "groups") loadGroups();
      if (panel === "assignments") loadAssignments();
      if (panel === "test-control") loadTestControl();
      if (panel === "audit") loadAudit();
    });
  });

  // 1. Dashboard
  async function loadDashboard() {
    try {
      const res = await fetch("/api/admin/dashboard", { headers: authHeaders() });
      if (res.status === 401 || res.status === 403) {
        localStorage.clear();
        window.location.href = "/login";
        return;
      }
      const data = await res.json();
      document.getElementById("dash-total-students").textContent = data.total_students;
      document.getElementById("dash-total-teachers").textContent = data.total_teachers;
      document.getElementById("dash-total-subjects").textContent = data.total_subjects;
      document.getElementById("dash-avg-score").textContent = data.avg_score + "%";

      const recentTbody = document.getElementById("dash-recent-tbody");
      if (!data.recent_attempts || data.recent_attempts.length === 0) {
        recentTbody.innerHTML = '<tr><td colspan="4" style="text-align: center; color: #94a3b8;">Hozircha natijalar yo\'q</td></tr>';
      } else {
        recentTbody.innerHTML = data.recent_attempts.map(a => `
          <tr>
            <td><b>${a.student_name}</b></td>
            <td><span class="badge badge-primary">${a.group_name}</span></td>
            <td>${a.subject_name} • <small style="color: #64748b;">${a.test_title}</small></td>
            <td><span class="badge ${a.score_percent >= 60 ? 'badge-success' : 'badge-danger'}">${a.score_percent}%</span></td>
          </tr>
        `).join("");
      }

      const subAnalytics = document.getElementById("dash-subject-analytics");
      if (!data.subject_analytics || data.subject_analytics.length === 0) {
        subAnalytics.innerHTML = '<p style="color: #94a3b8; font-size: 0.9rem;">Fanlar statistikasi mavjud emas</p>';
      } else {
        subAnalytics.innerHTML = data.subject_analytics.map(s => `
          <div style="margin-bottom: 12px;">
            <div style="display: flex; justify-content: space-between; font-size: 0.9rem; font-weight: 600; margin-bottom: 4px;">
              <span>${s.subject_name} (${s.attempts_count} ta)</span>
              <span style="color: var(--primary);">${s.avg_score}%</span>
            </div>
            <div class="progress-bar-bg" style="height: 8px;">
              <div class="progress-bar-fill" style="width: ${s.avg_score}%; background: var(--primary);"></div>
            </div>
          </div>
        `).join("");
      }
    } catch (err) {
      console.error(err);
    }
  }

  // Maktab AI Tahlili
  document.getElementById("btn-run-school-ai").addEventListener("click", async () => {
    const btn = document.getElementById("btn-run-school-ai");
    const resultBox = document.getElementById("school-ai-result-box");
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Gemini AI tahlil qilmoqda...';
    resultBox.style.display = "block";
    resultBox.innerHTML = '<p style="text-align: center; color: #64748b;">Muassasa bo\'yicha fanlararo ta\'lim sifati chuqur tahlil qilinmoqda...</p>';

    try {
      const res = await fetch("/api/admin/ai-school-report", {
        method: "POST",
        headers: authHeaders()
      });
      const data = await res.json();
      resultBox.innerHTML = formatMarkdown(data.report);
    } catch (err) {
      resultBox.innerHTML = `<div style="color: red;">Xatolik: ${err}</div>`;
    } finally {
      btn.disabled = false;
      btn.innerHTML = '<i class="fa-solid fa-sparkles"></i> AI Tahlilni Ishga Tushirish';
    }
  });

  // 2. O'qituvchilar
  async function loadTeachers() {
    try {
      const res = await fetch("/api/admin/teachers", { headers: authHeaders() });
      teachersCache = await res.json();
      const tbody = document.getElementById("teachers-tbody");
      tbody.innerHTML = teachersCache.map(t => `
        <tr>
          <td><b>${t.full_name}</b></td>
          <td><code>${t.username}</code></td>
          <td>${t.specialty || '-'}</td>
          <td>${t.phone || '-'}</td>
          <td><span class="badge badge-primary">${t.assignment_count} ta biriktirish</span></td>
          <td><span class="badge ${t.is_active ? 'badge-success' : 'badge-danger'}">${t.is_active ? 'Faol' : 'Bloklangan'}</span></td>
          <td>
            <button class="btn btn-outline btn-sm" onclick="toggleUser(${t.user_id})">
              ${t.is_active ? '<i class="fa-solid fa-lock"></i> Bloklash' : '<i class="fa-solid fa-lock-open"></i> Ochish'}
            </button>
          </td>
        </tr>
      `).join("");
    } catch (err) { console.error(err); }
  }

  window.toggleUser = async (userId) => {
    try {
      await fetch(`/api/admin/toggle-user/${userId}`, { method: "POST", headers: authHeaders() });
      loadTeachers();
      loadStudents();
      if (currentDetailGroupId) {
        openGroupDetail(currentDetailGroupId);
      }
      if (currentProfileStudentId) {
        openStudentProfileModal(currentProfileStudentId);
      }
    } catch (err) { alert(err); }
  };

  document.getElementById("btn-open-add-teacher").addEventListener("click", () => openModal("modal-add-teacher"));
  document.getElementById("form-add-teacher").addEventListener("submit", async (e) => {
    e.preventDefault();
    const payload = {
      full_name: document.getElementById("t-fullname").value.trim(),
      username: document.getElementById("t-username").value.trim(),
      password: document.getElementById("t-password").value.trim(),
      specialty: document.getElementById("t-specialty").value.trim()
    };
    try {
      const res = await fetch("/api/admin/teachers", {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        closeModal("modal-add-teacher");
        document.getElementById("form-add-teacher").reset();
        loadTeachers();
      } else {
        const err = await res.json();
        alert(err.detail || "Xatolik");
      }
    } catch (err) { alert(err); }
  });

  // 3. O'quvchilar Boshqaruvi
  async function loadGroupStatsCards() {
    try {
      const res = await fetch("/api/admin/groups-with-stats", { headers: authHeaders() });
      if (!res.ok) return;
      const groups = await res.json();
      const grid = document.getElementById("admin-group-cards-grid");
      if (!grid) return;

      if (!groups || groups.length === 0) {
        grid.innerHTML = '<p style="color: #94a3b8; font-size: 0.9rem;">Hozircha guruhlar mavjud emas</p>';
        return;
      }

      grid.innerHTML = groups.map(g => `
        <div class="content-card group-card-item" style="cursor: pointer; border: 1px solid #e2e8f0; border-radius: 10px; padding: 1.1rem; transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1); background: #ffffff;"
             onmouseover="this.style.borderColor='#6366f1'; this.style.boxShadow='0 8px 20px -4px rgba(99,102,241,0.15)'; this.style.transform='translateY(-2px)'"
             onmouseout="this.style.borderColor='#e2e8f0'; this.style.boxShadow='none'; this.style.transform='translateY(0)'"
             onclick="openGroupDetail(${g.id})">
          <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px;">
            <div>
              <h4 style="font-size: 1.15rem; font-weight: 800; color: #1e1b4b; margin: 0 0 2px 0;">${g.name}</h4>
              <span style="font-size: 0.75rem; color: #64748b;">O'quv yili: ${g.academic_year || '2026/2027'}</span>
            </div>
            <span class="badge badge-primary" style="font-size: 0.8rem; padding: 4px 8px;">
              <i class="fa-solid fa-users"></i> ${g.student_count} nafar
            </span>
          </div>

          <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; background: #f8fafc; padding: 10px 8px; border-radius: 8px; margin-bottom: 12px; text-align: center;">
            <div>
              <div style="font-size: 0.7rem; color: #64748b; font-weight: 500;">O'rtacha</div>
              <b style="font-size: 0.95rem; color: #4f46e5;">${g.avg_score}%</b>
            </div>
            <div>
              <div style="font-size: 0.7rem; color: #64748b; font-weight: 500;">Eng yuqori</div>
              <b style="font-size: 0.95rem; color: #16a34a;">${g.max_score}%</b>
            </div>
            <div>
              <div style="font-size: 0.7rem; color: #64748b; font-weight: 500;">Topshirgan</div>
              <b style="font-size: 0.95rem; color: #0284c7;">${g.tested_students}/${g.student_count}</b>
            </div>
          </div>

          <div style="display: flex; justify-content: space-between; align-items: center; font-size: 0.8rem; font-weight: 600; color: #6366f1;">
            <span>Guruh tarkibini ko'rish <i class="fa-solid fa-arrow-right" style="font-size: 0.75rem; margin-left: 4px;"></i></span>
            <span class="badge ${g.is_active ? 'badge-success' : 'badge-danger'}" style="font-size: 0.7rem;">${g.is_active ? 'Faol' : 'Nofaol'}</span>
          </div>
        </div>
      `).join("");

      // Guruhlar filterini yangilash
      const filterSelect = document.getElementById("students-table-group-filter");
      if (filterSelect) {
        const curVal = filterSelect.value;
        filterSelect.innerHTML = '<option value="">Barcha guruhlar</option>' +
          groups.map(g => `<option value="${g.id}" ${curVal == g.id ? 'selected' : ''}>${g.name}</option>`).join("");
      }
    } catch (err) {
      console.error(err);
    }
  }

  window.openGroupDetail = async (groupId) => {
    currentDetailGroupId = groupId;
    try {
      const res = await fetch(`/api/admin/groups/${groupId}/detail`, { headers: authHeaders() });
      if (!res.ok) {
        alert("Guruh ma'lumotlarini yuklashda xatolik");
        return;
      }
      const data = await res.json();

      const detailBox = document.getElementById("admin-group-detail-box");
      const titleElem = document.getElementById("group-detail-title");
      const kpisElem = document.getElementById("group-detail-kpis");
      const tbody = document.getElementById("group-students-tbody");

      titleElem.textContent = `${data.name} Guruhi (${data.academic_year || '2026/2027'})`;
      kpisElem.innerHTML = `
        <span class="badge badge-primary"><i class="fa-solid fa-users"></i> Jami: ${data.student_count} nafar</span>
        <span class="badge badge-success"><i class="fa-solid fa-user-check"></i> Faol: ${data.active_students} nafar</span>
        <span class="badge badge-info"><i class="fa-solid fa-chart-line"></i> Topshirgan: ${data.tested_students} nafar</span>
        <span class="badge badge-warning"><i class="fa-solid fa-award"></i> O'rtacha: ${data.avg_score}%</span>
        <span class="badge badge-success"><i class="fa-solid fa-star"></i> Max: ${data.max_score}%</span>
      `;

      if (!data.students || data.students.length === 0) {
        tbody.innerHTML = '<tr><td colspan="9" style="text-align: center; color: #94a3b8; padding: 2rem;">Ushbu guruhda hozircha o\'quvchilar mavjud emas</td></tr>';
      } else {
        tbody.innerHTML = data.students.map((s, idx) => `
          <tr>
            <td>${idx + 1}</td>
            <td><b>${s.full_name}</b></td>
            <td><code>${s.username}</code></td>
            <td><span class="badge badge-warning"><code>${s.student_code}</code></span></td>
            <td><b>${s.pin}</b></td>
            <td>${s.phone || '-'}</td>
            <td>${s.exam_count} ta test</td>
            <td><span class="badge ${s.is_active ? 'badge-success' : 'badge-danger'}">${s.is_active ? 'Faol' : 'Bloklangan'}</span></td>
            <td style="white-space: nowrap;">
              <button class="btn btn-outline btn-sm" onclick="openStudentProfileModal(${s.id})" title="Profil va Natijalar" style="padding: 4px 8px;">
                <i class="fa-solid fa-id-card"></i> Profil
              </button>
              <button class="btn btn-outline btn-sm" onclick="openEditStudentModal(${s.id})" title="Tahrirlash" style="padding: 4px 8px;">
                <i class="fa-solid fa-pen"></i>
              </button>
              <button class="btn btn-outline btn-sm" onclick="toggleUser(${s.user_id})" title="${s.is_active ? 'Bloklash' : 'Ochish'}" style="padding: 4px 8px;">
                <i class="fa-solid ${s.is_active ? 'fa-lock' : 'fa-lock-open'}"></i>
              </button>
            </td>
          </tr>
        `).join("");
      }

      detailBox.style.display = "block";
      detailBox.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (err) {
      console.error(err);
    }
  };

  // Guruh ichidan orqaga qaytish
  const btnBackAllGroups = document.getElementById("btn-back-to-all-groups");
  if (btnBackAllGroups) {
    btnBackAllGroups.addEventListener("click", () => {
      const detailBox = document.getElementById("admin-group-detail-box");
      if (detailBox) detailBox.style.display = "none";
      currentDetailGroupId = null;
    });
  }

  // Tanlangan guruhga to'g'ridan-to'g'ri o'quvchi qo'shish
  const btnAddStToGroup = document.getElementById("btn-add-student-to-this-group");
  if (btnAddStToGroup) {
    btnAddStToGroup.addEventListener("click", () => {
      updateGroupDropdownForStudent();
      if (currentDetailGroupId) {
        const groupSel = document.getElementById("st-group-select");
        if (groupSel) groupSel.value = currentDetailGroupId;
      }
      openModal("modal-add-student");
    });
  }

  // Umumiy o'quvchilar ro'yxatini yuklash
  async function loadStudents() {
    await loadGroupStatsCards();
    try {
      const groupFilter = document.getElementById("students-table-group-filter")?.value || "";
      const searchQuery = document.getElementById("students-table-search")?.value.trim() || "";

      let url = "/api/admin/students";
      const params = new URLSearchParams();
      if (groupFilter) params.append("group_id", groupFilter);
      if (searchQuery) params.append("search", searchQuery);
      if (params.toString()) url += `?${params.toString()}`;

      const res = await fetch(url, { headers: authHeaders() });
      const students = await res.json();
      const tbody = document.getElementById("students-tbody");

      if (!students || students.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" style="text-align: center; color: #94a3b8; padding: 1.5rem;">O\'quvchilar topilmadi</td></tr>';
        return;
      }

      tbody.innerHTML = students.map(s => `
        <tr>
          <td><b>${s.full_name}</b></td>
          <td><span class="badge badge-primary">${s.group_name}</span></td>
          <td><span class="badge badge-warning"><code>${s.student_code}</code></span></td>
          <td><b>${s.pin}</b></td>
          <td><code>${s.username}</code></td>
          <td>${s.exam_count} ta test</td>
          <td><span class="badge ${s.is_active ? 'badge-success' : 'badge-danger'}">${s.is_active ? 'Faol' : 'Bloklangan'}</span></td>
          <td style="white-space: nowrap;">
            <button class="btn btn-outline btn-sm" onclick="openStudentProfileModal(${s.id})" title="Profil va Natijalar" style="padding: 4px 8px;">
              <i class="fa-solid fa-id-card"></i> Profil
            </button>
            <button class="btn btn-outline btn-sm" onclick="openEditStudentModal(${s.id})" title="Tahrirlash" style="padding: 4px 8px;">
              <i class="fa-solid fa-pen"></i>
            </button>
            <button class="btn btn-outline btn-sm" onclick="toggleUser(${s.user_id})" title="${s.is_active ? 'Bloklash' : 'Ochish'}" style="padding: 4px 8px;">
              <i class="fa-solid ${s.is_active ? 'fa-lock' : 'fa-lock-open'}"></i>
            </button>
          </td>
        </tr>
      `).join("");
    } catch (err) {
      console.error(err);
    }
  }

  // O'quvchilar qidiruv & filter tinglovchilari
  const stTableSearch = document.getElementById("students-table-search");
  if (stTableSearch) {
    let tSearchTimer = null;
    stTableSearch.addEventListener("input", () => {
      clearTimeout(tSearchTimer);
      tSearchTimer = setTimeout(() => loadStudents(), 300);
    });
  }

  const stTableGroupFilter = document.getElementById("students-table-group-filter");
  if (stTableGroupFilter) {
    stTableGroupFilter.addEventListener("change", () => loadStudents());
  }

  document.getElementById("btn-open-add-student").addEventListener("click", () => {
    updateGroupDropdownForStudent();
    openModal("modal-add-student");
  });

  document.getElementById("form-add-student").addEventListener("submit", async (e) => {
    e.preventDefault();
    const payload = {
      full_name: document.getElementById("st-fullname").value.trim(),
      username: document.getElementById("st-username").value.trim(),
      password: document.getElementById("st-password").value,
      group_id: parseInt(document.getElementById("st-group-select").value),
      student_code: document.getElementById("st-code").value.trim(),
      pin: document.getElementById("st-pin").value.trim()
    };
    try {
      const res = await fetch("/api/admin/students", {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        closeModal("modal-add-student");
        document.getElementById("form-add-student").reset();
        loadStudents();
        if (currentDetailGroupId) {
          openGroupDetail(currentDetailGroupId);
        }
      } else {
        const err = await res.json();
        alert(err.detail || "Xatolik");
      }
    } catch (err) { alert(err); }
  });

  // O'quvchi Profili Modali
  window.openStudentProfileModal = async (studentId) => {
    currentProfileStudentId = studentId;
    try {
      const res = await fetch(`/api/admin/students/${studentId}/profile`, { headers: authHeaders() });
      if (!res.ok) {
        alert("O'quvchi profilini yuklashda xatolik");
        return;
      }
      const data = await res.json();

      // Header ma'lumotlari
      document.getElementById("prof-student-name").textContent = data.full_name;
      document.getElementById("prof-student-group-badge").textContent = data.group_name;
      const statusBadge = document.getElementById("prof-student-status-badge");
      statusBadge.textContent = data.is_active ? "Faol" : "Bloklangan";
      statusBadge.className = `badge ${data.is_active ? "badge-success" : "badge-danger"}`;

      // Shaxsiy ma'lumotlar
      document.getElementById("prof-username").textContent = data.username;
      document.getElementById("prof-student-code").textContent = data.student_code;
      document.getElementById("prof-pin").textContent = data.pin;
      document.getElementById("prof-phone").textContent = data.phone || "Kiritilmagan";
      document.getElementById("prof-registered").textContent = data.registered_at ? data.registered_at.substring(0, 10) : "-";

      // Amallar tugmalari
      const btnProfEdit = document.getElementById("btn-prof-edit-student");
      btnProfEdit.onclick = () => openEditStudentModal(data.id);

      const btnProfToggle = document.getElementById("btn-prof-toggle-active");
      btnProfToggle.innerHTML = data.is_active
        ? '<i class="fa-solid fa-lock"></i> Bloklash'
        : '<i class="fa-solid fa-lock-open"></i> Ochish';
      btnProfToggle.onclick = async () => {
        await toggleUser(data.user_id);
        openStudentProfileModal(data.id);
      };

      // KPI kartalar
      document.getElementById("prof-stat-total").textContent = data.stats.total_exams;
      document.getElementById("prof-stat-avg").textContent = `${data.stats.overall_avg}%`;
      document.getElementById("prof-stat-max").textContent = `${data.stats.highest_score}%`;
      document.getElementById("prof-stat-passed").textContent = `${data.stats.passed_exams} ta`;

      // Fanlar bo'yicha ko'rsatkichlar
      const subBarsContainer = document.getElementById("prof-subject-bars");
      if (!data.subject_stats || data.subject_stats.length === 0) {
        subBarsContainer.innerHTML = '<p style="color: #94a3b8; font-size: 0.85rem; margin: 0;">Hozircha fanlar bo\'yicha imtihon topshirilmagan</p>';
      } else {
        subBarsContainer.innerHTML = data.subject_stats.map(s => {
          const color = s.avg_score >= 80 ? '#16a34a' : (s.avg_score >= 60 ? '#4f46e5' : '#ef4444');
          return `
            <div style="background: #f8fafc; padding: 10px 12px; border-radius: 8px; border: 1px solid #e2e8f0;">
              <div style="display: flex; justify-content: space-between; align-items: center; font-size: 0.85rem; font-weight: 600; margin-bottom: 5px;">
                <span>${s.subject_name} (${s.subject_code}) <small style="color: #64748b; font-weight: 400;">• ${s.exam_count} ta test</small></span>
                <span style="color: ${color}; font-weight: 700;">O'rtacha: ${s.avg_score}% <small style="color: #64748b; font-weight: 500;">(Max: ${s.max_score}%)</small></span>
              </div>
              <div class="progress-bar-bg" style="height: 8px; background: #e2e8f0; border-radius: 4px; overflow: hidden;">
                <div class="progress-bar-fill" style="width: ${Math.min(100, Math.max(0, s.avg_score))}%; background: ${color}; height: 100%; border-radius: 4px;"></div>
              </div>
            </div>
          `;
        }).join("");
      }

      // Progress Trend Grafigi
      const trendContainer = document.getElementById("prof-trend-chart-box");
      if (!data.trend || data.trend.length === 0) {
        trendContainer.innerHTML = '<p style="color: #94a3b8; font-size: 0.85rem; margin: 0;">Natijalar dinamikasini ko\'rsatish uchun imtihonlar tarixi yetarli emas</p>';
      } else {
        const points = data.trend;
        const width = 600;
        const height = 150;
        const padding = { top: 20, right: 30, bottom: 30, left: 40 };
        const chartW = width - padding.left - padding.right;
        const chartH = height - padding.top - padding.bottom;

        const coords = points.map((p, i) => {
          const x = points.length === 1 ? padding.left + chartW / 2 : padding.left + (i / (points.length - 1)) * chartW;
          const y = padding.top + chartH - (p.score / 100) * chartH;
          return { x, y, ...p };
        });

        const polylinePoints = coords.map(c => `${c.x},${c.y}`).join(" ");

        let dotsSvg = coords.map(c => {
          const fill = c.score >= 60 ? '#16a34a' : '#ef4444';
          return `
            <circle cx="${c.x}" cy="${c.y}" r="5" fill="${fill}" stroke="#ffffff" stroke-width="2" />
            <text x="${c.x}" y="${c.y - 10}" text-anchor="middle" font-size="11" font-weight="700" fill="#1e1b4b">${c.score}%</text>
          `;
        }).join("");

        trendContainer.innerHTML = `
          <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px; margin-bottom: 10px;">
            <svg viewBox="0 0 ${width} ${height}" style="width: 100%; max-height: 160px; overflow: visible;">
              <line x1="${padding.left}" y1="${padding.top}" x2="${width - padding.right}" y2="${padding.top}" stroke="#e2e8f0" stroke-dasharray="3,3" />
              <text x="${padding.left - 8}" y="${padding.top + 4}" text-anchor="end" font-size="10" fill="#94a3b8">100%</text>

              <line x1="${padding.left}" y1="${padding.top + chartH / 2}" x2="${width - padding.right}" y2="${padding.top + chartH / 2}" stroke="#e2e8f0" stroke-dasharray="3,3" />
              <text x="${padding.left - 8}" y="${padding.top + chartH / 2 + 4}" text-anchor="end" font-size="10" fill="#94a3b8">50%</text>

              <line x1="${padding.left}" y1="${padding.top + chartH}" x2="${width - padding.right}" y2="${padding.top + chartH}" stroke="#cbd5e1" />
              <text x="${padding.left - 8}" y="${padding.top + chartH + 4}" text-anchor="end" font-size="10" fill="#94a3b8">0%</text>

              ${points.length > 1 ? `<polyline fill="none" stroke="#6366f1" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" points="${polylinePoints}" />` : ''}

              ${dotsSvg}
            </svg>
          </div>
          <div style="display: flex; gap: 8px; overflow-x: auto; padding-bottom: 6px;">
            ${points.map(p => `
              <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 6px 10px; font-size: 0.75rem; white-space: nowrap; flex-shrink: 0;">
                <span style="font-weight: 700; color: #1e1b4b;">#${p.step} ${p.subject_name}</span>: 
                <span class="badge ${p.score >= 60 ? 'badge-success' : 'badge-danger'}" style="font-size: 0.7rem; padding: 1px 5px;">${p.score}%</span>
                <div style="color: #64748b; font-size: 0.7rem; margin-top: 2px;">${p.date || '-'}</div>
              </div>
            `).join("")}
          </div>
        `;
      }

      // Gemini AI Pedagogik Tahlil
      const aiBox = document.getElementById("prof-ai-box");
      if (data.latest_ai_analysis) {
        aiBox.innerHTML = formatMarkdown(data.latest_ai_analysis);
      } else {
        aiBox.innerHTML = '<div style="color: #64748b; font-style: italic;"><i class="fa-solid fa-sparkles"></i> O\'quvchi kamida bitta imtihon topshirgach, bu yerda Gemini AI uning individual o\'sish sur\'ati, zaif mavzulari va takliflar bo\'yicha pedagogik tahlil beradi.</div>';
      }

      // Imtihonlar tarixi jadvali
      const historyTbody = document.getElementById("prof-history-tbody");
      if (!data.history || data.history.length === 0) {
        historyTbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: #94a3b8; padding: 1.5rem;">Hozircha topshirilgan imtihonlar mavjud emas</td></tr>';
      } else {
        historyTbody.innerHTML = data.history.map(h => `
          <tr>
            <td><b>${h.subject_name}</b> <small style="color: #64748b;">(${h.subject_code})</small></td>
            <td>${h.test_title} <span class="badge badge-primary" style="font-size: 0.7rem;">${h.exam_type}</span></td>
            <td><span class="badge ${h.score_percent >= 60 ? 'badge-success' : 'badge-danger'}"><b>${h.score_percent}%</b></span></td>
            <td>${h.correct_answers} / ${h.total_questions}</td>
            <td style="color: #64748b; font-size: 0.85rem;">${h.finished_at ? h.finished_at.substring(0, 16) : '-'}</td>
            <td><small>${h.teacher_name}</small></td>
          </tr>
        `).join("");
      }

      openModal("modal-student-profile");
    } catch (err) {
      console.error(err);
    }
  };

  // O'quvchini Tahrirlash Modali
  window.openEditStudentModal = async (studentId) => {
    try {
      if (!groupsCache || groupsCache.length === 0) {
        await loadGroups();
      }
      const res = await fetch(`/api/admin/students/${studentId}/profile`, { headers: authHeaders() });
      if (!res.ok) {
        alert("O'quvchi ma'lumotlarini yuklab bo'lmadi");
        return;
      }
      const data = await res.json();

      document.getElementById("edit-st-id").value = data.id;
      document.getElementById("edit-st-fullname").value = data.full_name;
      document.getElementById("edit-st-username").value = data.username;
      document.getElementById("edit-st-code").value = data.student_code;
      document.getElementById("edit-st-pin").value = data.pin;
      document.getElementById("edit-st-phone").value = data.phone || "";
      document.getElementById("edit-st-active").value = data.is_active ? "1" : "0";
      document.getElementById("edit-st-password").value = "";

      const groupSel = document.getElementById("edit-st-group");
      groupSel.innerHTML = groupsCache.map(g => `
        <option value="${g.id}" ${g.id === data.group_id ? 'selected' : ''}>${g.name}</option>
      `).join("");

      openModal("modal-edit-student");
    } catch (err) {
      console.error(err);
    }
  };

  // Tahrirlash formasini saqlash
  const formEditStudent = document.getElementById("form-edit-student");
  if (formEditStudent) {
    formEditStudent.addEventListener("submit", async (e) => {
      e.preventDefault();
      const studentId = document.getElementById("edit-st-id").value;
      const pwd = document.getElementById("edit-st-password").value;

      const payload = {
        full_name: document.getElementById("edit-st-fullname").value.trim(),
        username: document.getElementById("edit-st-username").value.trim(),
        group_id: parseInt(document.getElementById("edit-st-group").value),
        student_code: document.getElementById("edit-st-code").value.trim(),
        pin: document.getElementById("edit-st-pin").value.trim(),
        phone: document.getElementById("edit-st-phone").value.trim(),
        is_active: parseInt(document.getElementById("edit-st-active").value)
      };
      if (pwd && pwd.trim().length > 0) {
        payload.password = pwd.trim();
      }

      try {
        const res = await fetch(`/api/admin/students/${studentId}`, {
          method: "PUT",
          headers: authHeaders(),
          body: JSON.stringify(payload)
        });
        if (res.ok) {
          closeModal("modal-edit-student");
          alert("O'quvchi ma'lumotlari muvaffaqiyatli yangilandi");
          loadStudents();
          if (currentDetailGroupId) {
            openGroupDetail(currentDetailGroupId);
          }
          if (currentProfileStudentId == studentId) {
            openStudentProfileModal(studentId);
          }
        } else {
          const err = await res.json();
          alert(err.detail || "Xatolik yuz berdi");
        }
      } catch (err) {
        alert(err);
      }
    });
  }

  // 4. Fanlar
  async function loadSubjects() {
    try {
      const res = await fetch("/api/admin/subjects", { headers: authHeaders() });
      subjectsCache = await res.json();
      const tbody = document.getElementById("subjects-tbody");
      tbody.innerHTML = subjectsCache.map(s => `
        <tr>
          <td><span class="badge badge-primary">${s.code}</span></td>
          <td><b>${s.name}</b></td>
          <td style="color: #64748b;">${s.description || '-'}</td>
          <td>${s.topic_count} ta mavzu</td>
          <td>${s.question_count} ta savol</td>
        </tr>
      `).join("");
    } catch (err) { console.error(err); }
  }

  document.getElementById("btn-open-add-subject").addEventListener("click", () => openModal("modal-add-subject"));
  document.getElementById("form-add-subject").addEventListener("submit", async (e) => {
    e.preventDefault();
    const payload = {
      name: document.getElementById("sub-name").value.trim(),
      code: document.getElementById("sub-code").value.trim(),
      description: document.getElementById("sub-desc").value.trim()
    };
    try {
      const res = await fetch("/api/admin/subjects", {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        closeModal("modal-add-subject");
        document.getElementById("form-add-subject").reset();
        loadSubjects();
      } else {
        const err = await res.json();
        alert(err.detail || "Xatolik");
      }
    } catch (err) { alert(err); }
  });

  // 5. Guruhlar
  async function loadGroups() {
    try {
      const res = await fetch("/api/admin/groups", { headers: authHeaders() });
      groupsCache = await res.json();
      const tbody = document.getElementById("groups-tbody");
      tbody.innerHTML = groupsCache.map(g => `
        <tr>
          <td><b>${g.name}</b></td>
          <td>${g.academic_year}</td>
          <td><span class="badge badge-primary">${g.student_count} nafar o'quvchi</span></td>
        </tr>
      `).join("");
    } catch (err) { console.error(err); }
  }

  document.getElementById("btn-open-add-group").addEventListener("click", () => openModal("modal-add-group"));
  document.getElementById("form-add-group").addEventListener("submit", async (e) => {
    e.preventDefault();
    const payload = {
      name: document.getElementById("grp-name").value.trim(),
      academic_year: document.getElementById("grp-year").value.trim()
    };
    try {
      const res = await fetch("/api/admin/groups", {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        closeModal("modal-add-group");
        document.getElementById("form-add-group").reset();
        await loadGroups();
        if (typeof loadGroupStatsCards === "function") {
          loadGroupStatsCards();
        }
      } else {
        const err = await res.json();
        alert(err.detail || "Xatolik");
      }
    } catch (err) { alert(err); }
  });

  // 6. Biriktirishlar (Assignments)
  async function loadAssignments() {
    try {
      const res = await fetch("/api/admin/assignments", { headers: authHeaders() });
      const list = await res.json();
      const tbody = document.getElementById("assignments-tbody");
      tbody.innerHTML = list.map(a => `
        <tr>
          <td><b>${a.teacher_name}</b></td>
          <td><span class="badge badge-primary">${a.subject_name} (${a.subject_code})</span></td>
          <td><span class="badge badge-warning">${a.group_name}</span></td>
          <td>${a.academic_year} (${a.semester}-semestr)</td>
          <td>${a.test_count} ta test</td>
          <td>
            <button class="btn btn-danger btn-sm" onclick="deleteAssignment(${a.id})">
              <i class="fa-solid fa-trash"></i> Bekor qilish
            </button>
          </td>
        </tr>
      `).join("");
    } catch (err) { console.error(err); }
  }

  window.deleteAssignment = async (id) => {
    if (!confirm("Ushbu biriktirishni o'chirishni xohlaysizmi?")) return;
    try {
      await fetch(`/api/admin/assignments/${id}`, { method: "DELETE", headers: authHeaders() });
      loadAssignments();
    } catch (err) { alert(err); }
  };

  document.getElementById("btn-open-add-assignment").addEventListener("click", async () => {
    await loadTeachers();
    await loadSubjects();
    await loadGroups();

    const tSel = document.getElementById("as-teacher-select");
    tSel.innerHTML = teachersCache.map(t => `<option value="${t.id}">${t.full_name} (${t.specialty || 'O\'qituvchi'})</option>`).join("");

    const sSel = document.getElementById("as-subject-select");
    sSel.innerHTML = subjectsCache.map(s => `<option value="${s.id}">${s.name} (${s.code})</option>`).join("");

    const gSel = document.getElementById("as-group-select");
    gSel.innerHTML = groupsCache.map(g => `<option value="${g.id}">${g.name}</option>`).join("");

    openModal("modal-add-assignment");
  });

  document.getElementById("form-add-assignment").addEventListener("submit", async (e) => {
    e.preventDefault();
    const payload = {
      teacher_id: parseInt(document.getElementById("as-teacher-select").value),
      subject_id: parseInt(document.getElementById("as-subject-select").value),
      group_id: parseInt(document.getElementById("as-group-select").value),
      academic_year: "2026/2027",
      semester: 1
    };
    try {
      const res = await fetch("/api/admin/assignments", {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        closeModal("modal-add-assignment");
        loadAssignments();
      } else {
        const err = await res.json();
        alert(err.detail || "Xatolik");
      }
    } catch (err) { alert(err); }
  });

  function updateGroupDropdownForStudent() {
    const sel = document.getElementById("st-group-select");
    sel.innerHTML = groupsCache.map(g => `<option value="${g.id}">${g.name}</option>`).join("");
  }

  // 7. Audit Logs
  async function loadAudit() {
    try {
      const res = await fetch("/api/admin/audit-logs", { headers: authHeaders() });
      const logs = await res.json();
      const tbody = document.getElementById("audit-tbody");
      tbody.innerHTML = logs.map(l => `
        <tr>
          <td style="color: #64748b; font-size: 0.85rem;">${l.created_at}</td>
          <td><b>${l.user_name || 'Tizim'}</b> (${l.user_role || '-'})</td>
          <td><span class="badge badge-primary">${l.action}</span></td>
          <td>${l.details || '-'}</td>
        </tr>
      `).join("");
    } catch (err) { console.error(err); }
  }

  // 8. Gemini Key Sozlamalari
  async function checkKeyStatus() {
    try {
      const res = await fetch("/api/ai/key-status", { headers: authHeaders() });
      if (!res.ok) return;
      const d = await res.json();
      const badge = document.getElementById("gemini-key-status");
      if (d.has_key) {
        badge.className = "key-badge active";
        badge.innerHTML = `<i class="fa-solid fa-circle-check"></i> Gemini AI: Ulangan (${d.masked_key})`;
      } else {
        badge.className = "key-badge inactive";
        badge.innerHTML = `<i class="fa-solid fa-circle-exclamation"></i> Gemini AI: Kalit yo'q`;
      }
    } catch (err) { console.error(err); }
  }

  document.getElementById("admin-key-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const key = document.getElementById("input-admin-gemini-key").value.trim();
    try {
      const res = await fetch("/api/ai/set-key", {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({ api_key: key })
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        alert(data.detail || `Xatolik yuz berdi (${res.status})`);
        return;
      }
      alert(data.message || "Saqlandi");
      document.getElementById("input-admin-gemini-key").value = "";
      checkKeyStatus();
    } catch (err) { alert(err); }
  });

  function formatMarkdown(text) {
    if (!text) return "";
    return text
      .replace(/^### (.*$)/gim, '<h3 style="color: #1e1b4b; margin: 1rem 0 0.5rem 0;">$1</h3>')
      .replace(/^#### (.*$)/gim, '<h4 style="color: #312e81; margin: 0.8rem 0 0.4rem 0;">$1</h4>')
      .replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>')
      .replace(/^\* (.*$)/gim, '<li style="margin-left: 1rem;">$1</li>')
      .replace(/^- (.*$)/gim, '<li style="margin-left: 1rem;">$1</li>')
      .replace(/\n\n/gim, '<br><br>');
  }

  // ================= 9. TEST NAZORATI & STATE MACHINE =================
  let testControlList = [];
  let currentControlTest = null;
  let testControlInterval = null;

  async function loadTestControl() {
    try {
      const res = await fetch("/api/admin/tests-control", { headers: authHeaders() });
      if (!res.ok) return;
      testControlList = await res.json();

      const select = document.getElementById("tc-select-test");
      if (!select) return;
      select.innerHTML = "";

      if (!testControlList || testControlList.length === 0) {
        select.innerHTML = '<option value="">Testlar mavjud emas</option>';
        document.getElementById("tc-display-title").textContent = "Testlar mavjud emas";
        return;
      }

      testControlList.forEach((t) => {
        const opt = document.createElement("option");
        opt.value = t.test_id;
        opt.textContent = `${t.group_name || 'Guruhsiz'} • ${t.subject_name || 'Fan'} • ${t.test_title} [${(t.current_status || 'DRAFT').toUpperCase()}]`;
        select.appendChild(opt);
      });

      select.onchange = () => {
        const selectedId = parseInt(select.value);
        const item = testControlList.find(x => x.test_id === selectedId);
        if (item) selectControlTest(item);
      };

      if (testControlList.length > 0) {
        select.value = testControlList[0].test_id;
        selectControlTest(testControlList[0]);
      }
    } catch (err) {
      console.error("Test control yuklashda xatolik:", err);
    }
  }

  async function selectControlTest(item) {
    currentControlTest = item;
    document.getElementById("tc-display-title").textContent = item.test_title;
    document.getElementById("tc-display-info").textContent = 
      `Guruh: ${item.group_name || '—'} • Fan: ${item.subject_name || '—'} • Vaqt: ${item.duration_minutes} daqiqa • O'qituvchi: ${item.teacher_name || '—'}`;

    await refreshControlTestDetails();
    await loadProctoringSettings(item.test_id);

    let isRefreshingControl = false;

    if (testControlInterval) {
      clearTimeout(testControlInterval);
      testControlInterval = null;
    }

    function scheduleNextRefresh() {
      if (testControlInterval) clearTimeout(testControlInterval);
      testControlInterval = setTimeout(async () => {
        const activePanel = document.querySelector(".sidebar-link.active")?.dataset.panel;
        if (activePanel === "test-control" && currentControlTest) {
          await refreshControlTestDetails(true);
          scheduleNextRefresh();
        } else {
          testControlInterval = null;
        }
      }, 4000);
    }

    scheduleNextRefresh();
  }

  let isControlRequestPending = false;
  async function refreshControlTestDetails(isSilent = false) {
    if (!currentControlTest || isControlRequestPending) return;
    isControlRequestPending = true;
    const { test_id, group_id } = currentControlTest;

    try {
      const sRes = await fetch(`/api/groups/${group_id || 0}/tests/${test_id}/stats`, { headers: authHeaders() });
      if (sRes.ok) {
        const stats = await sRes.json();
        updateTestControlStatsUI(stats);
      }

      const pRes = await fetch(`/api/proctoring/dashboard/${test_id}`, { headers: authHeaders() });
      if (pRes.ok) {
        const students = await pRes.json();
        renderProctoringStudents(students, test_id);
      }

      await loadTestGroupsAccess(test_id);
    } catch (err) {
      if (!isSilent) console.error("Holatni yangilashda xatolik:", err);
    } finally {
      isControlRequestPending = false;
    }
  }

  function updateTestControlStatsUI(stats) {
    const status = (stats.status || "DRAFT").toUpperCase();
    const badge = document.getElementById("tc-badge-status");
    if (!badge) return;
    badge.textContent = status;

    badge.className = "badge";
    if (status === "STARTED") badge.classList.add("badge-success");
    else if (status === "FINISHED") badge.classList.add("badge-info");
    else if (status === "RESULTS_APPROVED" || status === "RESULTS_PUBLISHED") badge.classList.add("badge-primary");
    else badge.classList.add("badge-warning");

    document.getElementById("tc-stat-total").textContent = stats.total_students;
    document.getElementById("tc-stat-active").textContent = stats.active_count;
    document.getElementById("tc-stat-finished").textContent = stats.finished_count;
    document.getElementById("tc-stat-blocked").textContent = stats.blocked_count;

    const btnStart = document.getElementById("tc-btn-start");
    const btnFinish = document.getElementById("tc-btn-finish");
    const btnView = document.getElementById("tc-btn-view-results");
    const btnPublish = document.getElementById("tc-btn-publish");

    if (btnStart) btnStart.style.display = (status === "DRAFT" || status === "READY") ? "inline-flex" : "none";
    if (btnFinish) btnFinish.style.display = (status === "STARTED") ? "inline-flex" : "none";
    if (btnView) btnView.style.display = (status === "FINISHED" || status === "RESULTS_APPROVED" || status === "RESULTS_PUBLISHED") ? "inline-flex" : "none";
    if (btnPublish) btnPublish.style.display = (status === "FINISHED" || status === "RESULTS_APPROVED") ? "inline-flex" : "none";
  }

  function renderProctoringStudents(students, testId) {
    const tbody = document.getElementById("tc-students-tbody");
    if (!tbody) return;
    if (!students || students.length === 0) {
      tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 2rem;">Ushbu guruhda o\'quvchilar yo\'q</td></tr>';
      return;
    }

    tbody.innerHTML = students.map(st => {
      const isBlocked = st.test_state === "BLOCKED";
      const isFinished = st.test_state === "FINISHED";
      const rowStyle = isBlocked ? 'background: #fef2f2; font-weight: 600;' : '';

      let stateBadge = `<span class="badge badge-success">ACTIVE</span>`;
      if (isBlocked) {
        stateBadge = `<span class="badge badge-danger">🔒 BLOKLANGAN</span>`;
      } else if (isFinished) {
        stateBadge = `<span class="badge badge-secondary">YAKUNLAGAN</span>`;
      }

      let actions = '—';
      if (isBlocked) {
        actions = `
          <div style="display: flex; gap: 6px;">
            <button class="btn btn-success btn-sm btn-resume-st" data-student="${st.student_id}" data-test="${testId}" title="Blokdan chiqarish">
              <i class="fa-solid fa-play"></i> Davom ettirish
            </button>
            <button class="btn btn-danger btn-sm btn-term-st" data-student="${st.student_id}" data-test="${testId}" title="Testni yakunlash">
              <i class="fa-solid fa-stop"></i> Yakunlash
            </button>
          </div>
        `;
      }

      return `
        <tr style="${rowStyle}">
          <td>
            <b>${st.student_name}</b>
            <div style="font-size: 0.8rem; color: var(--text-muted);">${st.student_code}</div>
          </td>
          <td>${stateBadge}</td>
          <td><span style="${st.tab_switches > 0 ? 'color: #b91c1c; font-weight: 700;' : ''}">${st.tab_switches}</span></td>
          <td><span style="${st.fullscreen_exits > 0 ? 'color: #b91c1c; font-weight: 700;' : ''}">${st.fullscreen_exits}</span></td>
          <td><span style="${st.reloads > 0 ? 'color: #b91c1c; font-weight: 700;' : ''}">${st.reloads}</span></td>
          <td><span style="${st.face_losts > 0 ? 'color: #b91c1c; font-weight: 700;' : ''}">${st.face_losts}</span></td>
          <td>${actions}</td>
        </tr>
      `;
    }).join("");

    tbody.querySelectorAll(".btn-resume-st").forEach(b => {
      b.onclick = async () => {
        const sid = b.dataset.student;
        const tid = b.dataset.test;
        try {
          const res = await fetch(`/api/proctoring/${sid}/resume?test_id=${tid}`, {
            method: "POST",
            headers: authHeaders()
          });
          if (res.ok) {
            refreshControlTestDetails();
          } else {
            const err = await res.json();
            alert(err.detail || "Xatolik");
          }
        } catch (e) { alert(e); }
      };
    });

    tbody.querySelectorAll(".btn-term-st").forEach(b => {
      b.onclick = async () => {
        const sid = b.dataset.student;
        const tid = b.dataset.test;
        if (!confirm("O'quvchining testini butunlay yakunlamoqchimisiz?")) return;
        try {
          const res = await fetch(`/api/proctoring/${sid}/terminate?test_id=${tid}`, {
            method: "POST",
            headers: authHeaders()
          });
          if (res.ok) {
            refreshControlTestDetails();
          } else {
            const err = await res.json();
            alert(err.detail || "Xatolik");
          }
        } catch (e) { alert(e); }
      };
    });
  }

  async function loadProctoringSettings(testId) {
    try {
      const res = await fetch(`/api/proctoring/settings/${testId}`, { headers: authHeaders() });
      if (!res.ok) return;
      const s = await res.json();
      document.getElementById("tc-set-tab-switch").checked = true;
      document.getElementById("tc-set-tab-limit").value = s.tab_switch_limit || 3;
      document.getElementById("tc-set-fullscreen").checked = true;
      document.getElementById("tc-set-fullscreen-limit").value = s.fullscreen_limit || 3;
      document.getElementById("tc-set-reload").checked = true;
      document.getElementById("tc-set-reload-limit").value = s.reload_limit || 3;
      document.getElementById("tc-set-camera").checked = Boolean(s.enable_camera);
      document.getElementById("tc-set-camera-policy").value = s.camera_policy || "allow_without_camera";
      document.getElementById("tc-set-face-lost").checked = Boolean(s.face_lost_limit);
      document.getElementById("tc-set-face-limit").value = s.face_lost_limit || 5;
      document.getElementById("tc-set-multiple-faces").checked = Boolean(s.multiple_faces_limit);
      document.getElementById("tc-set-multiple-limit").value = s.multiple_faces_limit || 2;
      document.getElementById("tc-set-suspicious").checked = Boolean(s.track_suspicious);
    } catch (e) { console.error(e); }
  }

  document.getElementById("tc-form-settings")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!currentControlTest) return;
    const tid = currentControlTest.test_id;

    const payload = {
      tab_switch_limit: parseInt(document.getElementById("tc-set-tab-limit").value) || 3,
      fullscreen_limit: parseInt(document.getElementById("tc-set-fullscreen-limit").value) || 3,
      reload_limit: parseInt(document.getElementById("tc-set-reload-limit").value) || 3,
      enable_camera: document.getElementById("tc-set-camera").checked ? 1 : 0,
      camera_policy: document.getElementById("tc-set-camera-policy").value,
      face_lost_limit: parseInt(document.getElementById("tc-set-face-limit").value) || 5,
      multiple_faces_limit: parseInt(document.getElementById("tc-set-multiple-limit").value) || 2,
      track_exit: 1,
      track_suspicious: document.getElementById("tc-set-suspicious").checked ? 1 : 0
    };

    try {
      const res = await fetch(`/api/proctoring/settings/${tid}`, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        alert("✅ Nazorat sozlamalari muvaffaqiyatli saqlandi!");
      }
    } catch (err) { alert(err); }
  });

  document.getElementById("tc-btn-refresh")?.addEventListener("click", () => {
    refreshControlTestDetails();
  });

  document.getElementById("tc-btn-start")?.addEventListener("click", async () => {
    if (!currentControlTest) return;
    const { test_id, group_id } = currentControlTest;
    try {
      const res = await fetch(`/api/groups/${group_id || 0}/tests/${test_id}/start`, {
        method: "POST",
        headers: authHeaders()
      });
      if (!res.ok) {
        const err = await res.json();
        alert(err.detail || "Xatolik");
        return;
      }
      alert("✅ Test muvaffaqiyatli boshlandi! Guruhdagi barcha o'quvchilar testni ishlashlari mumkin.");
      refreshControlTestDetails();
    } catch (e) { alert(e); }
  });

  document.getElementById("tc-btn-finish")?.addEventListener("click", async () => {
    if (!currentControlTest) return;
    const { test_id, group_id } = currentControlTest;
    if (!confirm("Diqqat! Test yakunlanganda hali ishlayotgan barcha o'quvchilarning testi yopiladi va yangi javob qabul qilinmaydi. Yakunlaysizmi?")) return;

    try {
      const res = await fetch(`/api/groups/${group_id || 0}/tests/${test_id}/finish`, {
        method: "POST",
        headers: authHeaders()
      });
      if (!res.ok) {
        const err = await res.json();
        alert(err.detail || "Xatolik");
        return;
      }
      alert("🏁 Test yakunlandi. Endi natijalarni tekshirishingiz va e'lon qilishingiz mumkin.");
      refreshControlTestDetails();
    } catch (e) { alert(e); }
  });

  // --- GURUHLAR KESIMIDA TESTGA RUXSAT VA NATIJALAR BOSHQARUVI ---
  let currentTestGroupsAccessList = [];

  async function loadTestGroupsAccess(testId) {
    const tbody = document.getElementById("tc-groups-access-tbody");
    if (!tbody) return;

    try {
      const res = await fetch(`/api/tests/${testId}/groups-access`, { headers: authHeaders() });
      if (!res.ok) return;
      currentTestGroupsAccessList = await res.json();

      if (!currentTestGroupsAccessList || currentTestGroupsAccessList.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" style="text-align: center; color: var(--text-muted); padding: 1.5rem;">Guruhlar topilmadi</td></tr>';
        return;
      }

      tbody.innerHTML = currentTestGroupsAccessList.map(g => {
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

        let actionBtn = '';
        if (!isAct) {
          actionBtn = `
            <button class="btn btn-success btn-sm btn-action-single-group" data-action="grant" data-group="${g.group_id}" style="padding: 4px 10px; font-size: 0.8rem;">
              <i class="fa-solid fa-play"></i> Boshlash
            </button>
          `;
        } else {
          actionBtn = `
            <button class="btn btn-danger btn-sm btn-action-single-group" data-action="stop" data-group="${g.group_id}" style="padding: 4px 10px; font-size: 0.8rem;">
              <i class="fa-solid fa-flag-checkered"></i> Yakunlash
            </button>
          `;
        }

        return `
          <tr>
            <td style="text-align: center;">
              <input type="checkbox" class="tc-group-checkbox" value="${g.group_id}" ${isAct ? 'data-status="active"' : ''}>
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
            <td>${actionBtn}</td>
          </tr>
        `;
      }).join("");

      // Single group buttons
      tbody.querySelectorAll(".btn-action-single-group").forEach(btn => {
        btn.onclick = async () => {
          const action = btn.dataset.action;
          const gid = parseInt(btn.dataset.group);
          if (action === "grant") {
            await grantGroupsAccess([gid]);
          } else {
            if (confirm("Ushbu guruh uchun testni yakunlab, natijalarni e'lon qilasizmi?")) {
              await stopGroupsAccess([gid]);
            }
          }
        };
      });

    } catch (e) {
      console.error("Guruhlar ruxsatini yuklashda xatolik:", e);
    }
  }

  async function grantGroupsAccess(groupIds) {
    if (!currentControlTest) return;
    const testId = currentControlTest.test_id;
    try {
      const res = await fetch("/api/tests/grant-access", {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({ test_id: testId, group_ids: groupIds })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Ruxsat berishda xatolik");
      alert("✅ Tanlangan guruh(lar) uchun test muvaffaqiyatli boshlandi!");
      await refreshControlTestDetails();
    } catch (err) {
      alert("Xatolik: " + err.message);
    }
  }

  async function stopGroupsAccess(groupIds) {
    if (!currentControlTest) return;
    const testId = currentControlTest.test_id;
    try {
      const res = await fetch("/api/tests/stop-access", {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({ test_id: testId, group_ids: groupIds })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Testni yakunlashda xatolik");
      alert("🏁 Tanlangan guruh(lar) uchun test yakunlandi va natijalar e'lon qilindi!");
      await refreshControlTestDetails();
    } catch (err) {
      alert("Xatolik: " + err.message);
    }
  }

  // Select all checkbox
  document.getElementById("tc-groups-check-all")?.addEventListener("change", (e) => {
    const checked = e.target.checked;
    document.querySelectorAll(".tc-group-checkbox").forEach(cb => cb.checked = checked);
  });

  // Batch grant access
  document.getElementById("tc-btn-grant-groups")?.addEventListener("click", async () => {
    const selected = Array.from(document.querySelectorAll(".tc-group-checkbox:checked")).map(cb => parseInt(cb.value));
    if (selected.length === 0) {
      alert("Iltimos, avval test boshlanishi kerak bo'lgan kamida bitta guruhni belgilang!");
      return;
    }
    await grantGroupsAccess(selected);
  });

  // Batch stop access and announce results
  document.getElementById("tc-btn-stop-groups")?.addEventListener("click", async () => {
    const selected = Array.from(document.querySelectorAll(".tc-group-checkbox:checked")).map(cb => parseInt(cb.value));
    if (selected.length === 0) {
      alert("Iltimos, avval testi yakunlanishi kerak bo'lgan kamida bitta guruhni belgilang!");
      return;
    }
    if (!confirm(`Belgilangan ${selected.length} ta guruh uchun testni to'xtatib, barcha talabalarga natijalarni e'lon qilasizmi?`)) return;
    await stopGroupsAccess(selected);
  });

  // Reload groups
  document.getElementById("tc-btn-reload-groups")?.addEventListener("click", () => {
    if (currentControlTest) loadTestGroupsAccess(currentControlTest.test_id);
  });


  async function publishResults() {
    if (!currentControlTest) return;
    const { test_id, group_id } = currentControlTest;
    if (!confirm("Natijalarni o'quvchilarga e'lon qilasizmi? Shundan keyin o'quvchilar o'z balli va tahlillarini ko'ra oladilar.")) return;

    try {
      const res = await fetch(`/api/groups/${group_id || 0}/tests/${test_id}/publish`, {
        method: "POST",
        headers: authHeaders()
      });
      if (!res.ok) {
        const err = await res.json();
        alert(err.detail || "Xatolik");
        return;
      }
      alert("📢 Natijalar muvaffaqiyatli e'lon qilindi!");
      closeModal("modal-test-results-view");
      refreshControlTestDetails();
    } catch (e) { alert(e); }
  }

  document.getElementById("tc-btn-publish")?.addEventListener("click", publishResults);
  document.getElementById("m-res-btn-publish")?.addEventListener("click", publishResults);

  document.getElementById("tc-btn-view-results")?.addEventListener("click", async () => {
    if (!currentControlTest) return;
    const { test_id } = currentControlTest;
    openModal("modal-test-results-view");

    const tbody = document.getElementById("m-res-tbody");
    tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: var(--text-muted); padding: 2rem;">Yuklanmoqda...</td></tr>';

    try {
      const res = await fetch(`/api/admin/tests/${test_id}/group-results`, { headers: authHeaders() });
      if (!res.ok) return;
      const list = await res.json();
      if (!list || list.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: var(--text-muted); padding: 2rem;">Topshirilgan natijalar mavjud emas</td></tr>';
        return;
      }

      tbody.innerHTML = list.map(item => `
        <tr>
          <td>
            <b>${item.student_name}</b>
            <div style="font-size: 0.8rem; color: var(--text-muted);">${item.student_code}</div>
          </td>
          <td><b>${item.correct_answers}</b> / ${item.total_questions}</td>
          <td>
            <span style="font-weight: 800; font-size: 1.05rem; color: ${item.score_percent >= 60 ? '#15803d' : '#b91c1c'};">
              ${item.score_percent}%
            </span>
          </td>
          <td>
            <span style="${item.violations_count > 0 ? 'color: #b91c1c; font-weight: 700;' : 'color: var(--text-muted);'}">
              ${item.violations_count} ta hodisa
            </span>
          </td>
          <td>
            <span class="badge ${item.student_state === 'BLOCKED' ? 'badge-danger' : 'badge-success'}">
              ${item.student_state}
            </span>
          </td>
        </tr>
      `).join("");
    } catch (e) {
      tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: red;">Xatolik: ${e}</td></tr>`;
    }
  });

  // Initial load
  await checkKeyStatus();
  await loadDashboard();
  await loadGroups();
  await loadSubjects();
});
