// login.js — Tizimga kirish logikasi va demo hisoblar

let currentTab = "student";

function selectTab(tab) {
  currentTab = tab;
  document.querySelectorAll(".login-tab-btn").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.tab === tab);
  });

  const lblId = document.getElementById("lbl-identifier");
  const inputId = document.getElementById("input-identifier");
  const lblSec = document.getElementById("lbl-secret");
  const inputSec = document.getElementById("input-secret");

  if (tab === "student") {
    lblId.innerHTML = '<i class="fa-regular fa-id-card"></i> O\'quvchi Kodi yoki Login:';
    inputId.placeholder = "Login yoki ID kodi";
    lblSec.innerHTML = '<i class="fa-solid fa-lock"></i> PIN Kod yoki Parol:';
    inputSec.placeholder = "PIN kod yoki parol";
  } else if (tab === "teacher") {
    lblId.innerHTML = '<i class="fa-solid fa-chalkboard-user"></i> O\'qituvchi Logini:';
    inputId.placeholder = "O'qituvchi logini";
    lblSec.innerHTML = '<i class="fa-solid fa-lock"></i> Parol:';
    inputSec.placeholder = "Parol";
  } else {
    lblId.innerHTML = '<i class="fa-solid fa-shield-halved"></i> Administrator Logini:';
    inputId.placeholder = "Admin logini";
    lblSec.innerHTML = '<i class="fa-solid fa-lock"></i> Parol:';
    inputSec.placeholder = "Parol";
  }
}

document.addEventListener("DOMContentLoaded", () => {
  // Avval saqlangan sessiyani tekshirish
  const existingToken = localStorage.getItem("auth_token");
  const existingRole = localStorage.getItem("user_role");
  if (existingToken && existingRole) {
    // Agar foydalanuvchi tizimda bo'lsa, o'z kabinetiga yo'naltirish
    if (existingRole === "admin") window.location.href = "/admin";
    else if (existingRole === "teacher") window.location.href = "/teacher";
    else if (existingRole === "student") window.location.href = "/student";
  }

  document.querySelectorAll(".login-tab-btn").forEach(btn => {
    btn.addEventListener("click", () => selectTab(btn.dataset.tab));
  });

  const form = document.getElementById("login-form");
  const errBox = document.getElementById("login-error-alert");
  const errText = document.getElementById("login-error-text");
  const submitBtn = document.getElementById("btn-submit-login");

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    errBox.style.display = "none";
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Tekshirilmoqda...';

    const identifier = document.getElementById("input-identifier").value.trim();
    const secret = document.getElementById("input-secret").value.trim();

    try {
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ identifier, secret })
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || "Kirish ma'lumotlari noto'g'ri");
      }

      const data = await res.json();
      const user = data.user;
      
      // Token va foydalanuvchi ma'lumotlarini saqlash
      localStorage.setItem("auth_token", data.token);
      localStorage.setItem("user_role", user.role);
      localStorage.setItem("user_full_name", user.full_name);
      localStorage.setItem("user_id", user.id);
      localStorage.setItem("teacher_id", user.teacher_id || "");
      localStorage.setItem("student_id", user.student_id || "");
      localStorage.setItem("group_id", user.group_id || "");
      localStorage.setItem("group_name", user.group_name || "");

      // Rol bo'yicha mos kabinetga yo'naltirish
      if (user.role === "admin") {
        window.location.href = "/admin";
      } else if (user.role === "teacher") {
        window.location.href = "/teacher";
      } else if (user.role === "student") {
        window.location.href = "/student";
      }
    } catch (err) {
      errText.textContent = err.message;
      errBox.style.display = "block";
    } finally {
      submitBtn.disabled = false;
      submitBtn.innerHTML = '<i class="fa-solid fa-right-to-bracket"></i> Tizimga Kirish';
    }
  });
});
