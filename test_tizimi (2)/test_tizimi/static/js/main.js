// main.js — O'quvchi bosh sahifasi skripti

document.addEventListener("DOMContentLoaded", async () => {
  const groupSelect = document.getElementById("group-select");
  const testListContainer = document.getElementById("test-list");
  const selectedTestInput = document.getElementById("selected-test-id");
  const startBtn = document.getElementById("start-btn");
  const form = document.getElementById("student-entry-form");

  // 1. Guruhlarni yuklash
  async function loadGroups() {
    try {
      const res = await fetch("/api/groups");
      const groups = await res.json();
      groupSelect.innerHTML = '<option value="">Guruhni tanlang...</option>';
      groups.forEach(g => {
        const opt = document.createElement("option");
        opt.value = g.id;
        opt.textContent = g.name;
        groupSelect.appendChild(opt);
      });
    } catch (err) {
      console.error("Guruhlarni yuklashda xatolik:", err);
      groupSelect.innerHTML = '<option value="">Guruhlarni yuklab bo\'lmadi</option>';
    }
  }

  // 2. Faol testlarni yuklash
  async function loadTests() {
    try {
      const res = await fetch("/api/tests?active_only=true");
      const tests = await res.json();
      
      if (!tests || tests.length === 0) {
        testListContainer.innerHTML = `
          <div style="text-align: center; padding: 2rem; color: #64748b; background: #f8fafc; border-radius: 8px;">
            <i class="fa-regular fa-folder-open" style="font-size: 2rem; margin-bottom: 8px; color: #94a3b8;"></i>
            <p>Hozirda topshirish uchun faol testlar mavjud emas.</p>
          </div>
        `;
        return;
      }

      testListContainer.innerHTML = "";
      tests.forEach((t, idx) => {
        const card = document.createElement("div");
        card.className = "test-item-card";
        card.dataset.id = t.id;
        card.innerHTML = `
          <div class="test-info">
            <h3>${t.title}</h3>
            <p>${t.description || "Tavsif mavjud emas"}</p>
            <div class="test-meta">
              <span class="meta-chip"><i class="fa-regular fa-clock"></i> ${t.duration_minutes} daqiqa</span>
              <span class="meta-chip"><i class="fa-solid fa-list-check"></i> ${t.question_count} ta savol</span>
              <span class="meta-chip"><i class="fa-solid fa-bullseye"></i> O'tish bali: ${t.passing_score}%</span>
            </div>
          </div>
          <div style="font-size: 1.5rem; color: var(--border);">
            <i class="fa-regular fa-circle-check check-icon"></i>
          </div>
        `;

        card.addEventListener("click", () => {
          document.querySelectorAll(".test-item-card").forEach(c => {
            c.classList.remove("selected");
            c.querySelector(".check-icon").className = "fa-regular fa-circle-check check-icon";
            c.querySelector(".check-icon").parentElement.style.color = "var(--border)";
          });
          card.classList.add("selected");
          card.querySelector(".check-icon").className = "fa-solid fa-circle-check check-icon";
          card.querySelector(".check-icon").parentElement.style.color = "var(--primary)";
          
          selectedTestInput.value = t.id;
          startBtn.disabled = false;
        });

        testListContainer.appendChild(card);
      });
    } catch (err) {
      console.error("Testlarni yuklashda xatolik:", err);
      testListContainer.innerHTML = '<div style="color: red; text-align: center;">Testlarni yuklab bo\'lmadi.</div>';
    }
  }

  // 3. Form topshirish va test sahifasiga o'tish
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const firstName = document.getElementById("first-name").value.trim();
    const lastName = document.getElementById("last-name").value.trim();
    const groupId = groupSelect.value;
    const groupName = groupSelect.options[groupSelect.selectedIndex].text;
    const testId = selectedTestInput.value;

    if (!testId) {
      alert("Iltimos, avval testlardan birini tanlang!");
      return;
    }

    // Ma'lumotlarni sessionStorage ga saqlash
    sessionStorage.setItem("student_first_name", firstName);
    sessionStorage.setItem("student_last_name", lastName);
    sessionStorage.setItem("student_group_id", groupId);
    sessionStorage.setItem("student_group_name", groupName);

    // Test sahifasiga o'tish
    window.location.href = `/test/${testId}`;
  });

  // Boshlang'ich yuklash
  await loadGroups();
  await loadTests();
});
