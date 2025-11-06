document.addEventListener("DOMContentLoaded", function () {
  const templateSelect = document.getElementById("email_template");
  const subjectInput = document.getElementById("custom_subject");
  const messageTextarea = document.getElementById("custom_message");

  const toContainer = document.getElementById("to-input-container");
  const toInput = document.getElementById("to-input");
  const hiddenRecipients = document.getElementById("recipients-hidden");
  const autocompleteList = document.getElementById("autocomplete-list");

  // Get users from Django context (includes "(Me)")
  const users = window.availableUsers || [];
  let recipients = [];

  function updateHiddenInput() {
    hiddenRecipients.value = recipients.join(",");
  }

  function createTag(name) {
    const tag = document.createElement("span");
    tag.className = "badge bg-primary me-1 mb-1";
    tag.textContent = name;

    const remove = document.createElement("span");
    remove.className = "ms-1";
    remove.innerHTML = "&times;";
    remove.style.cursor = "pointer";
    remove.onclick = () => {
      recipients = recipients.filter(r => r !== name);
      tag.remove();
      updateHiddenInput();
    };

    tag.appendChild(remove);
    toContainer.insertBefore(tag, toInput);
  }

  function addRecipient(name) {
    if (!recipients.includes(name)) {
      recipients.push(name);
      createTag(name);
      updateHiddenInput();
      toInput.value = "";
      autocompleteList.innerHTML = "";
    }
  }

  function showAutocomplete(value) {
    autocompleteList.innerHTML = "";
    if (!value) return;

    const matches = users
      .filter(u => u.toLowerCase().includes(value.toLowerCase()) && !recipients.includes(u))
      .sort((a, b) => (a.includes("(Me)") ? -1 : b.includes("(Me)") ? 1 : 0));

    matches.forEach(m => {
      const item = document.createElement("div");
      item.className = "p-1 autocomplete-item";
      item.style.cursor = "pointer";
      item.textContent = m;
      item.onclick = () => addRecipient(m);
      autocompleteList.appendChild(item);
    });
  }

  toInput.addEventListener("input", () => showAutocomplete(toInput.value));

  toInput.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && toInput.value.trim() !== "") {
      e.preventDefault();
      const value = toInput.value.trim();

      // Map "(Me)" to the correct user
      const meUser = users.find(u => u.includes("(Me)") && u.toLowerCase().includes(value.toLowerCase()));
      if (meUser) {
        addRecipient(meUser);
      } else {
        addRecipient(value);
      }
    }
  });

  document.addEventListener("click", function (e) {
    if (!toContainer.contains(e.target)) {
      autocompleteList.innerHTML = "";
    }
  });

  // Autofill subject + body when selecting email template
  if (templateSelect) {
    templateSelect.addEventListener("change", function () {
      const selected = this.options[this.selectedIndex];
      if (selected.value) {
        const templateSubject = selected.getAttribute("data-subject");
        const templateBody = selected.getAttribute("data-body");
        if (templateSubject) subjectInput.value = templateSubject;
        if (templateBody) messageTextarea.value = templateBody;
      }
    });
  }
});
