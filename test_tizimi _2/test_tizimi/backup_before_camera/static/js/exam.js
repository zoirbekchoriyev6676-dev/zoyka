// exam.js — Imtihon topshirish va anti-cheat nazorati

document.addEventListener("DOMContentLoaded", async () => {
  const token = localStorage.getItem("auth_token");
  const fullName = localStorage.getItem("user_full_name") || "O'quvchi";
  const groupName = localStorage.getItem("group_name") || "10-A";

  const pathParts = window.location.pathname.split("/").filter(Boolean);
  const testId = pathParts[pathParts.length - 1];

  if (!token || !testId) {
    alert("Iltimos, avval tizimga kiring!");
    window.location.href = "/login";
    return;
  }

  function authHeaders() {
    return {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${token}`
    };
  }

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

  let questions = [];
  let currentIndex = 0;
  let answers = {};
  let tabSwitchCount = 0;
  let timeRemaining = 0;
  let timerInterval = null;
  let timeSpentSeconds = 0;
  let isSubmitting = false;

  hdrStudentName.textContent = fullName;
  hdrStudentGroup.textContent = groupName;

  // 1. Savollarni yuklash
  try {
    const res = await fetch(`/api/student/test/${testId}`, { headers: authHeaders() });
    if (!res.ok) {
      const err = await res.json();
      alert(err.detail || "Imtihonni ochishda xatolik");
      window.location.href = "/student";
      return;
    }
    const data = await res.json();
    const test = data.test;
    questions = data.questions;

    if (!questions || questions.length === 0) {
      alert("Ushbu imtihonda savollar mavjud emas!");
      window.location.href = "/student";
      return;
    }

    hdrTestTitle.textContent = `${test.subject_name} • ${test.title}`;
    timeRemaining = (test.duration_minutes || 30) * 60;

    // Javoblarni saqlash va tiklash (qotish yoki uzilishda javoblar yo'qolmasligi uchun)
    try {
      const savedAns = localStorage.getItem(`exam_answers_${testId}`) || localStorage.getItem(`offline_answers_${testId}`);
      if (savedAns) {
        answers = JSON.parse(savedAns) || {};
      }
    } catch (e) {
      console.warn("Javoblarni tiklashda xatolik:", e);
    }

    initTimer();
    renderPalette();
    renderQuestion(0);
    initAntiCheat();
    initCameraProctoring(test);
  } catch (err) {
    console.error(err);
    alert("Server bilan aloqa uzildi.");
    window.location.href = "/student";
  }

  // Taymer
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
        alert("Vaqt tugadi! Imtihon avtomatik ravishda topshirilmoqda...");
        submitExam();
      }
    }, 1000);
  }

  function updateTimerDisplay() {
    const mins = Math.floor(timeRemaining / 60);
    const secs = timeRemaining % 60;
    timerDisplay.textContent = `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
  }

  // Savolni chiqarish
  function renderQuestion(index) {
    currentIndex = index;
    const q = questions[index];

    qNumberDisplay.textContent = `Savol ${index + 1} / ${questions.length}`;
    qTopicDisplay.textContent = q.topic_name;
    qDifficultyDisplay.textContent = q.difficulty === "easy" ? "Oson" : (q.difficulty === "hard" ? "Qiyin" : "O'rta");
    qTextDisplay.textContent = q.question_text;

    optionsContainer.innerHTML = "";
    const letters = ["A", "B", "C", "D", "E", "F"];
    const currentSelected = answers[q.id];

    q.options.forEach((opt, idx) => {
      const btn = document.createElement("div");
      btn.className = "option-btn";
      if (currentSelected === opt.id) btn.classList.add("selected");

      btn.innerHTML = `
        <div class="opt-badge">${letters[idx] || (idx + 1)}</div>
        <div class="opt-text">${opt.option_text}</div>
      `;

      btn.addEventListener("click", () => {
        answers[q.id] = opt.id;
        try {
          localStorage.setItem(`exam_answers_${testId}`, JSON.stringify(answers));
        } catch (e) {}
        document.querySelectorAll(".option-btn").forEach(b => b.classList.remove("selected"));
        btn.classList.add("selected");
        updatePaletteItem(index, true);
        updateCounts();
      });

      optionsContainer.appendChild(btn);
    });

    btnPrev.disabled = (index === 0);
    btnNext.disabled = (index === questions.length - 1);
    updatePaletteSelection(index);
  }

  function renderPalette() {
    paletteGrid.innerHTML = "";
    questions.forEach((q, idx) => {
      const item = document.createElement("button");
      item.type = "button";
      item.className = "palette-item";
      item.textContent = idx + 1;
      item.id = `palette-item-${idx}`;
      if (answers[q.id]) {
        item.classList.add("answered");
      }
      item.addEventListener("click", () => renderQuestion(idx));
      paletteGrid.appendChild(item);
    });
    updateCounts();
  }

  function updatePaletteItem(idx, answered) {
    const item = document.getElementById(`palette-item-${idx}`);
    if (item) {
      if (answered) item.classList.add("answered");
      else item.classList.remove("answered");
    }
  }

  function updatePaletteSelection(idx) {
    document.querySelectorAll(".palette-item").forEach(item => item.classList.remove("current"));
    const current = document.getElementById(`palette-item-${idx}`);
    if (current) current.classList.add("current");
  }

  function updateCounts() {
    const ansCount = Object.keys(answers).length;
    countAnsweredElem.textContent = ansCount;
    countUnansweredElem.textContent = questions.length - ansCount;
  }

  btnPrev.addEventListener("click", () => { if (currentIndex > 0) renderQuestion(currentIndex - 1); });
  btnNext.addEventListener("click", () => { if (currentIndex < questions.length - 1) renderQuestion(currentIndex + 1); });

  btnClear.addEventListener("click", () => {
    const q = questions[currentIndex];
    delete answers[q.id];
    try {
      localStorage.setItem(`exam_answers_${testId}`, JSON.stringify(answers));
    } catch (e) {}
    document.querySelectorAll(".option-btn").forEach(b => b.classList.remove("selected"));
    updatePaletteItem(currentIndex, false);
    updateCounts();
  });

  // Server-driven Anti-cheat & Proctoring
  let isBlocked = false;
  let statusPollTimer = null;

  async function reportEvent(eventType, details = "") {
    if (isSubmitting) return;
    try {
      const res = await fetch("/api/proctoring/event", {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({
          test_id: parseInt(testId),
          event_type: eventType,
          details: details
        })
      });
      if (!res.ok) return;
      const data = await res.json();
      handleProctoringResponse(data);
    } catch (e) {
      console.warn("Proctoring report error:", e);
    }
  }

  function handleProctoringResponse(data) {
    tabSwitchCount = data.counter;
    tabSwitchCountElem.textContent = tabSwitchCount;
    tabWarningTag.style.display = "inline-flex";

    const modalIcon = document.getElementById("modal-warning-icon");
    const modalTitle = document.getElementById("modal-warning-title");
    const modalText = document.getElementById("modal-warning-text");
    const modalCount = document.getElementById("modal-tab-count");
    const modalBtn = document.getElementById("btn-modal-continue");
    const waitingBlock = document.getElementById("modal-blocked-waiting");

    if (modalCount) modalCount.textContent = `${data.counter} / ${data.limit}`;
    if (modalText) modalText.textContent = data.message || "Qoidabuzarlik qayd etildi!";

    if (data.is_blocked) {
      isBlocked = true;
      if (modalIcon) modalIcon.innerHTML = '<i class="fa-solid fa-lock" style="color: #b91c1c;"></i>';
      if (modalTitle) modalTitle.textContent = "TEST BLOKLANDI";
      if (modalBtn) modalBtn.style.display = "none";
      if (waitingBlock) waitingBlock.style.display = "block";
      antiCheatModal.classList.add("active");

      // Admin qarorini tekshirish uchun har 3 soniyada holatni so'rab turish
      if (!statusPollTimer) {
        statusPollTimer = setInterval(checkStudentStatus, 3000);
      }
    } else {
      if (modalIcon) modalIcon.innerHTML = '<i class="fa-solid fa-triangle-exclamation" style="color: #ea580c;"></i>';
      if (modalTitle) modalTitle.textContent = "OGOHLANTIRISH!";
      if (modalBtn) modalBtn.style.display = "block";
      if (waitingBlock) waitingBlock.style.display = "none";
      antiCheatModal.classList.add("active");
    }
  }

  async function checkStudentStatus() {
    try {
      const res = await fetch(`/api/proctoring/status/${testId}`, { headers: authHeaders() });
      if (!res.ok) return;
      const data = await res.json();
      if (data.status === "ACTIVE" && isBlocked) {
        isBlocked = false;
        clearInterval(statusPollTimer);
        statusPollTimer = null;
        antiCheatModal.classList.remove("active");
        alert("✅ Administrator sizni blokdan chiqardi. Testni davom ettirishingiz mumkin.");
      } else if (data.status === "FINISHED") {
        clearInterval(statusPollTimer);
        statusPollTimer = null;
        alert("Administrator testingizni yakunladi.");
        window.location.href = "/student";
      }
    } catch (e) {
      console.warn("Status check error:", e);
    }
  }

  function initAntiCheat() {
    btnFullscreen.addEventListener("click", () => {
      if (!document.fullscreenElement) {
        document.documentElement.requestFullscreen().catch(() => {});
      } else {
        document.exitFullscreen().catch(() => {});
      }
    });

    document.addEventListener("fullscreenchange", () => {
      if (!document.fullscreenElement && !isSubmitting) {
        reportEvent("fullscreen_exit", "Fullscreen rejimidan chiqildi");
      }
    });

    let leaveTimeout = null;
    function onLeave() {
      if (isSubmitting || isBlocked) return;
      clearTimeout(leaveTimeout);
      leaveTimeout = setTimeout(() => {
        reportEvent("tab_switch", "Oyna yoki ilova almashtirildi");
      }, 250);
    }

    document.addEventListener("visibilitychange", () => {
      if (document.hidden) onLeave();
    });
    window.addEventListener("blur", () => onLeave());

    btnModalContinue.addEventListener("click", () => {
      if (!isBlocked) {
        antiCheatModal.classList.remove("active");
      }
    });

    // Sahifa yangilanishi (F5 / Reload) tekshiruvi
    const navEntries = performance.getEntriesByType && performance.getEntriesByType("navigation");
    const isReload = (navEntries && navEntries[0] && navEntries[0].type === "reload") || (performance.navigation && performance.navigation.type === 1);
    if (isReload) {
      reportEvent("reload", "Test sahifasi qayta yuklandi (F5 / Reload)");
    }

    // Offline / Online nazorati
    const offlineBanner = document.getElementById("offline-status-banner");
    const offlineBannerText = document.getElementById("offline-banner-text");

    window.addEventListener("offline", () => {
      if (offlineBanner && offlineBannerText) {
        offlineBanner.style.background = "#dc2626";
        offlineBannerText.textContent = "⚠️ Internet aloqasi uzildi. Javoblaringiz saqlanishi tekshirilmoqda.";
        offlineBanner.style.display = "block";
      }
      localStorage.setItem(`offline_answers_${testId}`, JSON.stringify(answers));
    });

    window.addEventListener("online", () => {
      if (offlineBanner && offlineBannerText) {
        offlineBanner.style.background = "#16a34a";
        offlineBannerText.textContent = "✓ Aloqa tiklandi.";
        setTimeout(() => { offlineBanner.style.display = "none"; }, 3000);
      }
    });

    document.addEventListener("contextmenu", (e) => e.preventDefault());
    document.addEventListener("copy", (e) => e.preventDefault());
    document.addEventListener("cut", (e) => e.preventDefault());
  }

  // Yakunlash
  btnFinish.addEventListener("click", () => {
    const ansCount = Object.keys(answers).length;
    const unansCount = questions.length - ansCount;
    let msg = `Siz jami <b>${questions.length}</b> ta savoldan <b>${ansCount}</b> tasiga javob berdingiz.`;
    if (unansCount > 0) {
      msg += `<br><span style="color: #b91c1c; font-weight: 700;">Diqqat! ${unansCount} ta savolga javob belgilanmadi!</span>`;
    }
    msg += `<br><br>Imtihonni yakunlab, natijalarni hisoblashga yuborasizmi?`;
    confirmFinishMessage.innerHTML = msg;
    confirmFinishModal.classList.add("active");
  });

  btnCloseConfirm.addEventListener("click", () => confirmFinishModal.classList.remove("active"));
  btnCancelFinish.addEventListener("click", () => confirmFinishModal.classList.remove("active"));

  btnSubmitConfirmed.addEventListener("click", () => {
    confirmFinishModal.classList.remove("active");
    submitExam();
  });

  async function submitExam() {
    if (isSubmitting) return;
    isSubmitting = true;
    if (timerInterval) clearInterval(timerInterval);

    btnFinish.disabled = true;
    btnFinish.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Tekshirilmoqda...';

    const payload = {
      test_id: parseInt(testId),
      answers: answers,
      tab_switch_count: tabSwitchCount,
      time_spent_seconds: timeSpentSeconds
    };

    try {
      const res = await fetch("/api/student/test/submit", {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify(payload)
      });
      if (!res.ok) {
        const err = await res.json();
        alert(err.detail || "Xatolik");
        isSubmitting = false;
        btnFinish.disabled = false;
        return;
      }
      const data = await res.json();
      try {
        localStorage.removeItem(`exam_answers_${testId}`);
        localStorage.removeItem(`offline_answers_${testId}`);
      } catch (e) {}
      window.location.href = `/result/${data.session_id}`;
    } catch (err) {
      console.error(err);
      alert("Xatolik: Server bilan aloqa uzildi.");
      isSubmitting = false;
      btnFinish.disabled = false;
    }
  }

  // ==================== YENGIL VA XAVFSIZ KAMERA AI NAZORATI ====================
  let cameraStream = null;
  let faceWorker = null;
  let cameraInterval = null;
  let isFrameProcessing = false;
  let lastReportedFaceState = "ok"; // "ok", "lost", "multiple"
  let consecutiveFaceLost = 0;
  let consecutiveMultipleFaces = 0;

  async function initCameraProctoring(testConfig) {
    const isCameraEnabled = Boolean(testConfig && (testConfig.enable_camera || testConfig.proctoring?.enable_camera));
    const cameraPolicy = (testConfig && (testConfig.camera_policy || testConfig.proctoring?.camera_policy)) || "allow_without_camera";
    const box = document.getElementById("camera-proctoring-box");
    const videoElem = document.getElementById("proctoring-video");
    const faceBadge = document.getElementById("camera-face-badge");
    const indicator = document.getElementById("camera-status-indicator");

    if (!isCameraEnabled) {
      if (box) box.style.display = "none";
      return;
    }

    if (box) box.style.display = "block";

    // 1. Web Worker'ni bir marta initsializatsiya qilish (Main thread qotmasligi uchun)
    try {
      faceWorker = new Worker("/static/js/face_worker.js");
      faceWorker.onmessage = (e) => {
        isFrameProcessing = false;
        if (e.data && e.data.type === "FACE_RESULT") {
          handleFaceDetectionResult(e.data.faceCount);
        }
      };
      faceWorker.onerror = (err) => {
        console.warn("Face worker error:", err);
        isFrameProcessing = false;
      };
    } catch (e) {
      console.warn("Worker ishga tushmadi, bevosita ishlaydi:", e);
      faceWorker = null;
    }

    // 2. Kamerani 320x240 o'lchamda ochish (Yuklanishni 80% ga kamaytiradi)
    try {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        throw new Error("Kamera API mavjud emas (HTTPS yoki localhost talab etiladi)");
      }
      cameraStream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 320, max: 640 },
          height: { ideal: 240, max: 480 },
          frameRate: { ideal: 15, max: 20 }
        },
        audio: false
      });
      if (videoElem) {
        videoElem.srcObject = cameraStream;
      }
      if (indicator) {
        indicator.innerHTML = '<i class="fa-solid fa-circle"></i> Faol';
        indicator.style.color = "#16a34a";
      }
    } catch (err) {
      console.warn("Kameraga kirish ruxsati berilmadi:", err);
      if (indicator) {
        indicator.innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i> Kamerasiz';
        indicator.style.color = "#ea580c";
      }
      if (cameraPolicy === "block_without_camera") {
        alert("DIQQAT: Ushbu imtihon uchun kamera majburiy! Kameraga ruxsat bermasdan testni topshirib bo'lmaydi.");
        reportEvent("face_lost", "Kamera ochilmadi yoki ruxsat berilmadi");
      }
      return;
    }

    // Yengil Canvas (320x240)
    const offscreenCanvas = document.createElement("canvas");
    offscreenCanvas.width = 320;
    offscreenCanvas.height = 240;
    const offCtx = offscreenCanvas.getContext("2d", { willReadFrequently: true });

    // 3. Tahlilni soniyasiga 1 marta (1000ms) bajarish va oldingi kadr tugamaguncha yangisini boshlamaslik
    cameraInterval = setInterval(async () => {
      if (isSubmitting || isBlocked || isFrameProcessing) return;
      if (!videoElem || videoElem.readyState < 2) return;

      try {
        isFrameProcessing = true;
        offCtx.drawImage(videoElem, 0, 0, 320, 240);

        if (window.createImageBitmap) {
          const bitmap = await createImageBitmap(offscreenCanvas);
          if (faceWorker) {
            try {
              faceWorker.postMessage({ type: "DETECT_FACES", imageBitmap: bitmap }, [bitmap]);
            } catch (e) {
              if (bitmap && bitmap.close) bitmap.close();
              isFrameProcessing = false;
            }
          } else {
            // Worker yo'q bo'lsa
            if (bitmap && bitmap.close) bitmap.close();
            isFrameProcessing = false;
          }
        } else {
          isFrameProcessing = false;
        }
      } catch (e) {
        isFrameProcessing = false;
      }
    }, 1000);
  }

  function handleFaceDetectionResult(faceCount) {
    const faceBadge = document.getElementById("camera-face-badge");
    if (!faceBadge) return;

    if (faceCount === 1) {
      faceBadge.style.background = "rgba(22, 163, 74, 0.85)";
      faceBadge.innerHTML = "✓ Yuz aniqlandi";
      consecutiveFaceLost = 0;
      consecutiveMultipleFaces = 0;
      lastReportedFaceState = "ok";
    } else if (faceCount === 0) {
      consecutiveFaceLost++;
      consecutiveMultipleFaces = 0;
      faceBadge.style.background = "rgba(220, 38, 38, 0.85)";
      faceBadge.innerHTML = "⚠️ Yuz ko'rinmadi";

      // Faqatgina ketma-ket 3 ta tahlilda yuz yo'qolsa va bir xil xabar qayta-qayta yuborilmasligi uchun:
      if (consecutiveFaceLost === 3 && lastReportedFaceState !== "lost") {
        lastReportedFaceState = "lost";
        reportEvent("face_lost", "Kamera kadrida o'quvchi yuzi ko'rinmadi");
      }
    } else if (faceCount > 1) {
      consecutiveMultipleFaces++;
      consecutiveFaceLost = 0;
      faceBadge.style.background = "rgba(234, 88, 12, 0.85)";
      faceBadge.innerHTML = `⚠️ Bir nechta shaxs (${faceCount})`;

      // Ketma-ket 3 ta tahlilda bir nechta yuz bo'lsa:
      if (consecutiveMultipleFaces === 3 && lastReportedFaceState !== "multiple") {
        lastReportedFaceState = "multiple";
        reportEvent("multiple_faces", `Kadrda ${faceCount} ta shaxs aniqlandi`);
      }
    }
  }

  // 4. Test tugaganda yoki sahifadan chiqilganda resurslarni to'liq bo'shatish
  function stopCameraAndProctoring() {
    if (cameraInterval) {
      clearInterval(cameraInterval);
      cameraInterval = null;
    }
    if (cameraStream) {
      cameraStream.getTracks().forEach(track => track.stop());
      cameraStream = null;
    }
    if (faceWorker) {
      faceWorker.terminate();
      faceWorker = null;
    }
  }

  window.addEventListener("beforeunload", () => {
    stopCameraAndProctoring();
  });
});
