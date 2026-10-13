// result.js — Imtihon natijalari va Gemini AI tahlili

document.addEventListener("DOMContentLoaded", async () => {
  const token = localStorage.getItem("auth_token");
  const pathParts = window.location.pathname.split("/").filter(Boolean);
  const sessionId = pathParts[pathParts.length - 1];

  if (!sessionId) {
    alert("Natija ID topilmadi");
    window.location.href = "/student";
    return;
  }

  function authHeaders() {
    return {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${token}`
    };
  }

  const resStudentName = document.getElementById("res-student-name");
  const resTestAndGroup = document.getElementById("res-test-and-group");
  const resScorePercent = document.getElementById("res-score-percent");
  const resGradeBadge = document.getElementById("res-grade-badge");

  const statTotalQ = document.getElementById("stat-total-q");
  const statCorrectQ = document.getElementById("stat-correct-q");
  const statIncorrectQ = document.getElementById("stat-incorrect-q");
  const statTimeSpent = document.getElementById("stat-time-spent");
  const antiCheatAlertBox = document.getElementById("anti-cheat-alert-box");
  const statTabSwitches = document.getElementById("stat-tab-switches");

  const aiAnalysisContent = document.getElementById("ai-analysis-content");
  const btnRefreshAi = document.getElementById("btn-refresh-ai");
  const topicsBarsContainer = document.getElementById("topics-bars-container");
  const questionsDetailContainer = document.getElementById("questions-detail-container");

  let currentResult = null;
  let chartInstance = null;

  async function loadResult() {
    try {
      const res = await fetch(`/api/student/result/${sessionId}`, { headers: authHeaders() });
      if (!res.ok) {
        alert("Natija topilmadi!");
        window.location.href = "/student";
        return;
      }
      currentResult = await res.json();

      if (currentResult.is_published === false) {
        const pendingBanner = document.getElementById("result-pending-banner");
        const detailsWrap = document.getElementById("result-details-wrap");
        if (pendingBanner) pendingBanner.style.display = "block";
        if (detailsWrap) detailsWrap.style.display = "none";
        return;
      }

      const pendingBanner = document.getElementById("result-pending-banner");
      const detailsWrap = document.getElementById("result-details-wrap");
      if (pendingBanner) pendingBanner.style.display = "none";
      if (detailsWrap) detailsWrap.style.display = "block";

      renderOverview(currentResult);
      renderTopicStats(currentResult.topics || []);
      renderQuestions(currentResult.questions || []);

      if (currentResult.ai_analysis) {
        renderAiReport(currentResult.ai_analysis);
      } else {
        fetchAiAnalysis(false);
      }
    } catch (err) { console.error(err); }
  }

  function renderOverview(data) {
    resStudentName.textContent = data.student_name;
    resTestAndGroup.textContent = `${data.subject_name} • ${data.test_title} • ${data.group_name}`;
    resScorePercent.textContent = `${data.score_percent}%`;

    statTotalQ.textContent = data.total_questions;
    statCorrectQ.textContent = data.correct_answers;
    statIncorrectQ.textContent = data.incorrect_answers;

    const mins = Math.floor(data.time_spent_seconds / 60);
    const secs = data.time_spent_seconds % 60;
    statTimeSpent.textContent = `${mins} daq ${secs} son`;

    if (data.tab_switch_count > 0) {
      antiCheatAlertBox.style.display = "flex";
      statTabSwitches.textContent = data.tab_switch_count;
    }

    const score = data.score_percent;
    const passing = data.passing_score || 60;

    if (score >= 86) {
      resGradeBadge.textContent = "A'lo (5 baho) • Muvaffaqiyatli topshirdi";
      resGradeBadge.style.background = "#dcfce7";
      resGradeBadge.style.color = "#166534";
    } else if (score >= 71) {
      resGradeBadge.textContent = "Yaxshi (4 baho) • Muvaffaqiyatli topshirdi";
      resGradeBadge.style.background = "#e0f2fe";
      resGradeBadge.style.color = "#0369a1";
    } else if (score >= passing) {
      resGradeBadge.textContent = "Qoniqarli (3 baho) • O'tish chegarasidan o'tdi";
      resGradeBadge.style.background = "#fef3c7";
      resGradeBadge.style.color = "#92400e";
    } else {
      resGradeBadge.textContent = "Qoniqarsiz (2 baho) • O'tish chegarasidan o'tolmadi";
      resGradeBadge.style.background = "#fee2e2";
      resGradeBadge.style.color = "#991b1b";
    }
  }

  function renderTopicStats(topics) {
    topicsBarsContainer.innerHTML = "";
    const labels = [];
    const percentages = [];
    const colors = [];

    topics.forEach(t => {
      labels.push(t.topic_name);
      percentages.push(t.percentage);

      let color = "#10b981";
      if (t.percentage < 50) color = "#ef4444";
      else if (t.percentage < 75) color = "#f59e0b";
      colors.push(color);

      const row = document.createElement("div");
      row.className = "topic-row";
      row.innerHTML = `
        <div class="topic-row-header">
          <span>${t.topic_name} (${t.correct_answers}/${t.total_questions})</span>
          <span style="font-weight: 700; color: ${color};">${t.percentage}%</span>
        </div>
        <div class="progress-bar-bg">
          <div class="progress-bar-fill" style="width: ${t.percentage}%; background: ${color};"></div>
        </div>
      `;
      topicsBarsContainer.appendChild(row);
    });

    const ctx = document.getElementById("topicsChart").getContext("2d");
    if (chartInstance) chartInstance.destroy();

    chartInstance = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{
          label: 'O\'zlashtirish (%)',
          data: percentages,
          backgroundColor: colors,
          borderRadius: 6
        }]
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: { min: 0, max: 100, ticks: { callback: v => v + '%' } }
        },
        plugins: { legend: { display: false } }
      }
    });
  }

  async function fetchAiAnalysis(force = false) {
    aiAnalysisContent.innerHTML = `
      <div style="text-align: center; padding: 2rem; color: #475569;">
        <i class="fa-solid fa-sparkles fa-spin" style="font-size: 2rem; color: #6366f1; margin-bottom: 1rem;"></i>
        <p><b>Gemini AI o'quvchi xatolarini pedagogik jihatdan tahlil qilmoqda...</b></p>
      </div>
    `;

    try {
      const url = `/api/student/ai-analysis/${sessionId}${force ? '?force_regenerate=true' : ''}`;
      const res = await fetch(url, { method: "POST", headers: authHeaders() });
      const data = await res.json();
      renderAiReport(data.ai_analysis);
    } catch (err) {
      aiAnalysisContent.innerHTML = `<div style="color: red; padding: 1rem;">AI tahlilida xatolik. Qaytadan urinib ko'ring.</div>`;
    }
  }

  btnRefreshAi.addEventListener("click", () => fetchAiAnalysis(true));

  function renderAiReport(markdownText) {
    if (!markdownText) return;
    let html = markdownText
      .replace(/^### (.*$)/gim, '<h3 style="font-size: 1.15rem; font-weight: 700; color: #1e1b4b; margin: 1.25rem 0 0.5rem 0;">$1</h3>')
      .replace(/^#### (.*$)/gim, '<h4 style="font-size: 1.05rem; font-weight: 700; color: #312e81; margin: 1rem 0 0.4rem 0;">$1</h4>')
      .replace(/\*\*(.*?)\*\*/gim, '<strong style="color: #0f172a;">$1</strong>')
      .replace(/^\* (.*$)/gim, '<li style="margin-bottom: 4px;">$1</li>')
      .replace(/^- (.*$)/gim, '<li style="margin-bottom: 4px;">$1</li>')
      .replace(/^\d+\. (.*$)/gim, '<li style="margin-bottom: 6px;">$1</li>')
      .replace(/\n\n/gim, '<br><br>');
    aiAnalysisContent.innerHTML = html;
  }

  function renderQuestions(questions) {
    questionsDetailContainer.innerHTML = "";
    questions.forEach((q, idx) => {
      const item = document.createElement("div");
      item.className = `question-review-item ${q.is_correct ? 'correct' : 'incorrect'}`;

      let statusBadge = q.is_correct 
        ? '<span class="badge badge-success"><i class="fa-solid fa-check"></i> To\'g\'ri</span>'
        : '<span class="badge badge-danger"><i class="fa-solid fa-xmark"></i> Noto\'g\'ri</span>';

      let optionsHtml = "";
      q.options.forEach(opt => {
        const isUserChoice = (opt.id === q.selected_option_id);
        const isCorrectChoice = (opt.is_correct === 1);
        let optClass = "q-review-opt";
        let optIcon = '<i class="fa-regular fa-circle" style="color: #cbd5e1; margin-right: 8px;"></i>';

        if (isCorrectChoice) {
          optClass += " is-correct";
          optIcon = '<i class="fa-solid fa-circle-check" style="color: #059669; margin-right: 8px;"></i>';
        } else if (isUserChoice && !isCorrectChoice) {
          optClass += " user-wrong";
          optIcon = '<i class="fa-solid fa-circle-xmark" style="color: #dc2626; margin-right: 8px;"></i>';
        }

        optionsHtml += `
          <div class="${optClass}">
            ${optIcon} ${opt.option_text}
            ${isUserChoice ? ' <small style="font-weight: 700; margin-left: 6px;">(O\'quvchi tanlagan)</small>' : ''}
            ${isCorrectChoice ? ' <small style="font-weight: 700; margin-left: 6px;">(To\'g\'ri javob)</small>' : ''}
          </div>
        `;
      });

      let expHtml = q.explanation ? `
        <div style="margin-top: 10px; padding: 10px; background: #f8fafc; border-radius: 6px; font-size: 0.85rem; color: #475569; border-left: 3px solid var(--primary);">
          <b><i class="fa-solid fa-circle-info"></i> Tushuntirish:</b> ${q.explanation}
        </div>
      ` : '';

      item.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
          <span style="font-weight: 700; color: #334155;">${idx + 1}-savol • <small style="color: var(--text-muted);">${q.topic_name}</small></span>
          ${statusBadge}
        </div>
        <div style="font-size: 1.05rem; font-weight: 600; color: #1e293b; margin-bottom: 12px;">${q.question_text}</div>
        <div style="display: flex; flex-direction: column; gap: 4px;">${optionsHtml}</div>
        ${expHtml}
      `;
      questionsDetailContainer.appendChild(item);
    });
  }

  await loadResult();
});
