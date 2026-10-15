// test.js — Test topshirish interfeysi va anti-cheat nazorati

document.addEventListener("DOMContentLoaded", async () => {
  // 1. O'quvchi ma'lumotlarini tekshirish
  const firstName = sessionStorage.getItem("student_first_name");
  const lastName = sessionStorage.getItem("student_last_name");
  const groupId = sessionStorage.getItem("student_group_id");
  const groupName = sessionStorage.getItem("student_group_name") || "Guruh";

  const pathParts = window.location.pathname.split("/").filter(Boolean);
  const testId = pathParts[pathParts.length - 1];

  if (!firstName || !lastName || !groupId || !testId) {
    alert("Iltimos, avval test boshlash sahifasidan o'ting!");
    window.location.href = "/";
    return;
  }

  // DOM Elementlari
  const hdrStudentName = document.getElementById("hdr-student-name");
  const hdrStudentGroup = document.getElementById("hdr-student-group");
  const hdrTestTitle = document.getElementById("hdr-test-title");
  const timerDisplay = document.getElementById("timer-display");
  const timerBox = document.getElementById("timer-box");
  const tabWarningTag = document.getElementById("tab-warning-tag");
  const tabSwitchCountElem = document.getElementById("tab-switch-count");
  const btnFullscreen = document.getElementById("btn-fullscreen");

  const qNumberDisplay = document.getElementById("q-number-display");
  const qTopicDisplay = document.getElementById("q-topic-display");
  const qDifficultyDisplay = document.getElementById("q-difficulty-display");
  const qTextDisplay = document.getElementById("q-text-display");
  const optionsContainer = document.getElementById("options-container");
  const paletteGrid = document.getElementById("palette-grid");
  const countAnsweredElem = document.getElementById("count-answered");
  const countUnansweredElem = document.getElementById("count-unanswered");

  const btnPrev = document.getElementById("btn-prev");
  const btnNext = document.getElementById("btn-next");
  const btnClear = document.getElementById("btn-clear");
  const btnFinish = document.getElementById("btn-finish");

  const antiCheatModal = document.getElementById("anti-cheat-modal");
  const modalTabCount = document.getElementById("modal-tab-count");
  const btnModalContinue = document.getElementById("btn-modal-continue");

  const confirmFinishModal = document.getElementById("confirm-finish-modal");
  const confirmFinishMessage = document.getElementById("confirm-finish-message");
  const btnCloseConfirm = document.getElementById("btn-close-confirm");
  const btnCancelFinish = document.getElementById("btn-cancel-finish");
  const btnSubmitConfirmed = document.getElementById("btn-submit-confirmed");

  // Holat (State)
  let testData = null;
  let questions = [];
  let currentIndex = 0;
  let answers = {}; // { question_id: selected_option_id }
  let tabSwitchCount = 0;
  let timeRemaining = 0; // soniya
  let timerInterval = null;
  let timeSpentSeconds = 0;
  let isSubmitting = false;

  hdrStudentName.textContent = `${firstName} ${lastName}`;
  hdrStudentGroup.textContent = groupName;

  // 2. Savollarni serverdan yuklash
  try {
    const res = await fetch(`/api/tests/${testId}/student-questions`);
    if (!res.ok) {
      const err = await res.json();
      alert(err.detail || "Testni yuklab bo'lmadi");
      window.location.href = "/";
      return;
    }
    const data = await res.json();
    testData = data.test;
    questions = data.questions;

    if (!questions || questions.length === 0) {
      alert("Ushbu testda hali savollar mavjud emas!");
      window.location.href = "/";
      return;
    }

    hdrTestTitle.textContent = testData.title;
    timeRemaining = (testData.duration_minutes || 30) * 60;

    initTimer();
    renderPalette();
    renderQuestion(0);
    initAntiCheat();
  } catch (err) {
    console.error("Savollarni yuklashda xatolik:", err);
    alert("Server bilan aloqa uzildi.");
    window.location.href = "/";
  }

  // 3. Taymer
  function initTimer() {
    updateTimerDisplay();
    timerInterval = setInterval(() => {
      timeRemaining--;
      timeSpentSeconds++;
      updateTimerDisplay();

      if (timeRemaining <= 300) {
        timerBox.classList.add("warning");
      }

      if (timeRemaining <= 0) {
        clearInterval(timerInterval);
        alert("Vaqt tugadi! Test avtomatik tarzda topshirilmoqda...");
        submitTestToServer();
      }
    }, 1000);
  }

  function updateTimerDisplay() {
    const mins = Math.floor(timeRemaining / 60);
    const secs = timeRemaining % 60;
    timerDisplay.textContent = `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
  }

  // 4. Savolni ekranga chiqarish
  function renderQuestion(index) {
    currentIndex = index;
    const q = questions[index];

    qNumberDisplay.textContent = `Savol ${index + 1} / ${questions.length}`;
    qTopicDisplay.textContent = q.topic_name || "Mavzu";
    
    // Qiyinlik darajasi
    let diffName = "O'rta";
    if (q.difficulty === "easy") diffName = "Oson";
    if (q.difficulty === "hard") diffName = "Qiyin";
    qDifficultyDisplay.textContent = diffName;

    qTextDisplay.textContent = q.question_text;

    // Variantlar
    optionsContainer.innerHTML = "";
    const letters = ["A", "B", "C", "D", "E", "F"];
    const currentSelectedId = answers[q.id];

    q.options.forEach((opt, idx) => {
      const optBtn = document.createElement("div");
      optBtn.className = "option-btn";
      if (currentSelectedId === opt.id) {
        optBtn.classList.add("selected");
      }

      const optTextSafe = String(opt.option_text || "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");

      optBtn.innerHTML = `
        <div class="opt-badge">${letters[idx] || (idx + 1)}</div>
        <div class="opt-text">${optTextSafe}</div>
      `;

      optBtn.addEventListener("click", () => {
        answers[q.id] = opt.id;
        document.querySelectorAll(".option-btn").forEach(b => b.classList.remove("selected"));
        optBtn.classList.add("selected");
        updatePaletteItem(index, true);
        updateSummaryCounts();
      });

      optionsContainer.appendChild(optBtn);
    });

    // Tugmalar holati
    btnPrev.disabled = (index === 0);
    btnNext.disabled = (index === questions.length - 1);

    updatePaletteSelection(index);
  }

  // 5. Palitra
  function renderPalette() {
    paletteGrid.innerHTML = "";
    questions.forEach((q, idx) => {
      const item = document.createElement("button");
      item.type = "button";
      item.className = "palette-item";
      item.textContent = idx + 1;
      item.id = `palette-item-${idx}`;

      item.addEventListener("click", () => {
        renderQuestion(idx);
      });

      paletteGrid.appendChild(item);
    });
    updateSummaryCounts();
  }

  function updatePaletteItem(index, isAnswered) {
    const item = document.getElementById(`palette-item-${index}`);
    if (item) {
      if (isAnswered) {
        item.classList.add("answered");
      } else {
        item.classList.remove("answered");
      }
    }
  }

  function updatePaletteSelection(index) {
    document.querySelectorAll(".palette-item").forEach(item => item.classList.remove("current"));
    const current = document.getElementById(`palette-item-${index}`);
    if (current) current.classList.add("current");
  }

  function updateSummaryCounts() {
    const answeredCount = Object.keys(answers).length;
    countAnsweredElem.textContent = answeredCount;
    countUnansweredElem.textContent = questions.length - answeredCount;
  }

  // 6. Navigatsiya tugmalari
  btnPrev.addEventListener("click", () => {
    if (currentIndex > 0) renderQuestion(currentIndex - 1);
  });

  btnNext.addEventListener("click", () => {
    if (currentIndex < questions.length - 1) renderQuestion(currentIndex + 1);
  });

  btnClear.addEventListener("click", () => {
    const q = questions[currentIndex];
    delete answers[q.id];
    document.querySelectorAll(".option-btn").forEach(b => b.classList.remove("selected"));
    updatePaletteItem(currentIndex, false);
    updateSummaryCounts();
  });

  // 7. Anti-Cheat nazorati
  function initAntiCheat() {
    // To'liq ekran
    btnFullscreen.addEventListener("click", () => {
      if (!document.fullscreenElement) {
        document.documentElement.requestFullscreen().catch(err => console.log(err));
      } else {
        document.exitFullscreen().catch(err => console.log(err));
      }
    });

    // Oynani almashtirishni qayd qilish (Tab switch / blur)
    function onUserLeaveWindow() {
      if (isSubmitting) return;
      tabSwitchCount++;
      tabSwitchCountElem.textContent = tabSwitchCount;
      tabWarningTag.style.display = "inline-flex";
      modalTabCount.textContent = tabSwitchCount;
      antiCheatModal.classList.add("active");
    }

    document.addEventListener("visibilitychange", () => {
      if (document.hidden) {
        onUserLeaveWindow();
      }
    });

    window.addEventListener("blur", () => {
      onUserLeaveWindow();
    });

    btnModalContinue.addEventListener("click", () => {
      antiCheatModal.classList.remove("active");
    });

    // Nusxa olish va sichqoncha o'ng tugmasini taqiqlash
    document.addEventListener("contextmenu", (e) => e.preventDefault());
    document.addEventListener("copy", (e) => e.preventDefault());
    document.addEventListener("cut", (e) => e.preventDefault());
    document.addEventListener("keydown", (e) => {
      if ((e.ctrlKey && (e.key === "c" || e.key === "v" || e.key === "u")) || e.key === "F12") {
        e.preventDefault();
      }
    });
  }

  // 8. Yakunlash modali va jo'natish
  btnFinish.addEventListener("click", () => {
    const answeredCount = Object.keys(answers).length;
    const unansweredCount = questions.length - answeredCount;

    let msg = `Siz jami <b>${questions.length}</b> ta savoldan <b>${answeredCount}</b> tasiga javob berdingiz.`;
    if (unansweredCount > 0) {
      msg += `<br><span style="color: #b91c1c; font-weight: 600;">Diqqat! ${unansweredCount} ta savolga javob belgilanmadi!</span>`;
    }
    msg += `<br><br>Testni yakunlab, natijalarni hisoblashga yuborasizmi?`;

    confirmFinishMessage.innerHTML = msg;
    confirmFinishModal.classList.add("active");
  });

  btnCloseConfirm.addEventListener("click", () => confirmFinishModal.classList.remove("active"));
  btnCancelFinish.addEventListener("click", () => confirmFinishModal.classList.remove("active"));

  btnSubmitConfirmed.addEventListener("click", () => {
    confirmFinishModal.classList.remove("active");
    submitTestToServer();
  });

  async function submitTestToServer() {
    if (isSubmitting) return;
    isSubmitting = true;
    if (timerInterval) clearInterval(timerInterval);

    btnFinish.disabled = true;
    btnFinish.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Tekshirilmoqda...';

    const payload = {
      first_name: firstName,
      last_name: lastName,
      group_id: parseInt(groupId),
      test_id: parseInt(testId),
      answers: answers,
      tab_switch_count: tabSwitchCount,
      time_spent_seconds: timeSpentSeconds
    };

    try {
      const res = await fetch("/api/results/submit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        const err = await res.json();
        alert("Xatolik: " + (err.detail || "Natijani saqlab bo'lmadi"));
        btnFinish.disabled = false;
        btnFinish.innerHTML = '<i class="fa-solid fa-check-double"></i> Qayta topshirish';
        isSubmitting = false;
        return;
      }

      const resData = await res.json();
      // Natija sahifasiga yo'naltirish
      window.location.href = `/result/${resData.attempt_id}`;
    } catch (err) {
      console.error("Testni yuborishda xatolik:", err);
      alert("Internet yoki server bilan aloqa uzildi. Iltimos qaytadan urinib ko'ring.");
      isSubmitting = false;
      btnFinish.disabled = false;
    }
  }
});
