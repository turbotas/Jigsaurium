(() => {
  const state = {
    csrfToken: null,
    user: null,
  };

  const elements = {
    feedback: document.getElementById("app-feedback"),
    feedbackText: document.getElementById("app-feedback-text"),
    sessionSummary: document.getElementById("session-summary"),
    loginForm: document.getElementById("login-form"),
    adminSections: document.getElementById("admin-sections"),
    logoutButton: document.getElementById("logout-button"),
    userCreateForm: document.getElementById("user-create-form"),
    usersTableBody: document.getElementById("users-table-body"),
    jigsawCreateForm: document.getElementById("jigsaw-create-form"),
    jigsawsTableBody: document.getElementById("jigsaws-table-body"),
  };

  function showFeedback(message, isError = false) {
    if (!elements.feedback || !elements.feedbackText) {
      return;
    }

    elements.feedback.hidden = false;
    elements.feedback.classList.toggle("is-error", isError);
    elements.feedbackText.textContent = message;
  }

  function clearFeedback() {
    if (!elements.feedback) {
      return;
    }

    elements.feedback.hidden = true;
    elements.feedback.classList.remove("is-error");
    if (elements.feedbackText) {
      elements.feedbackText.textContent = "";
    }
  }

  async function apiRequest(path, options = {}) {
    const headers = new Headers(options.headers || {});
    headers.set("Accept", "application/json");

    if (options.body && !headers.has("Content-Type")) {
      headers.set("Content-Type", "application/json");
    }

    const method = (options.method || "GET").toUpperCase();
    if (["POST", "PATCH", "DELETE"].includes(method) && state.csrfToken) {
      headers.set("X-CSRF-Token", state.csrfToken);
    }

    const response = await fetch(path, {
      credentials: "same-origin",
      ...options,
      method,
      headers,
    });

    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      const message = payload?.error?.message || "Request failed.";
      const error = new Error(message);
      error.status = response.status;
      error.payload = payload;
      throw error;
    }

    return payload;
  }

  function setSessionSummary() {
    if (!elements.sessionSummary) {
      return;
    }

    if (!state.user) {
      elements.sessionSummary.textContent = "Not signed in.";
      if (elements.adminSections) {
        elements.adminSections.hidden = true;
      }
      return;
    }

    const roleText = Array.isArray(state.user.roles) ? state.user.roles.join(", ") : "none";
    elements.sessionSummary.textContent = `Signed in as ${state.user.email} (${roleText}).`;

    const isAdministrator = Array.isArray(state.user.roles) && state.user.roles.includes("administrator");
    if (elements.adminSections) {
      elements.adminSections.hidden = !isAdministrator;
    }

    if (!isAdministrator) {
      showFeedback("Signed in, but this account is not an administrator.", true);
    }
  }

  async function refreshSession() {
    try {
      const payload = await apiRequest("/api/v1/auth/me");
      state.user = payload.data.user;
      setSessionSummary();
      return true;
    } catch (error) {
      state.user = null;
      state.csrfToken = null;
      setSessionSummary();
      if (error.status !== 401) {
        showFeedback(error.message, true);
      }
      return false;
    }
  }

  function renderUsers(users) {
    if (!elements.usersTableBody) {
      return;
    }

    if (!Array.isArray(users) || users.length === 0) {
      elements.usersTableBody.innerHTML =
        '<tr class="govuk-table__row"><td class="govuk-table__cell" colspan="6">No users found.</td></tr>';
      return;
    }

    elements.usersTableBody.innerHTML = users
      .map((user) => {
        const isActive = Boolean(user.is_active);
        const roleNames = Array.isArray(user.roles) ? user.roles.join(", ") : "";
        const toggleText = isActive ? "Deactivate" : "Activate";
        return `
          <tr class="govuk-table__row">
            <td class="govuk-table__cell">${user.id}</td>
            <td class="govuk-table__cell">${user.email}</td>
            <td class="govuk-table__cell">${user.display_name || "-"}</td>
            <td class="govuk-table__cell">${roleNames || "-"}</td>
            <td class="govuk-table__cell">${isActive ? "active" : "inactive"}</td>
            <td class="govuk-table__cell"><button class="app-action-link" data-user-toggle="${user.id}" data-current-active="${isActive}">${toggleText}</button></td>
          </tr>
        `;
      })
      .join("");
  }

  function renderJigsaws(jigsaws) {
    if (!elements.jigsawsTableBody) {
      return;
    }

    if (!Array.isArray(jigsaws) || jigsaws.length === 0) {
      elements.jigsawsTableBody.innerHTML =
        '<tr class="govuk-table__row"><td class="govuk-table__cell" colspan="7">No jigsaws found.</td></tr>';
      return;
    }

    elements.jigsawsTableBody.innerHTML = jigsaws
      .map(
        (jigsaw) => `
          <tr class="govuk-table__row">
            <td class="govuk-table__cell">${jigsaw.id}</td>
            <td class="govuk-table__cell">${jigsaw.title}</td>
            <td class="govuk-table__cell">${jigsaw.piece_count}</td>
            <td class="govuk-table__cell">${jigsaw.condition || "-"}</td>
            <td class="govuk-table__cell">${jigsaw.status}</td>
            <td class="govuk-table__cell">${jigsaw.tags || "-"}</td>
            <td class="govuk-table__cell"><button class="app-action-link" data-jigsaw-retire="${jigsaw.id}">Retire</button></td>
          </tr>
        `
      )
      .join("");
  }

  async function loadUsers() {
    if (!state.user) {
      renderUsers([]);
      return;
    }

    try {
      const payload = await apiRequest("/api/v1/users");
      renderUsers(payload.data);
    } catch (error) {
      if (error.status === 403) {
        renderUsers([]);
        return;
      }
      showFeedback(error.message, true);
    }
  }

  async function loadJigsaws() {
    if (!state.user) {
      renderJigsaws([]);
      return;
    }

    try {
      const payload = await apiRequest("/api/v1/jigsaws");
      renderJigsaws(payload.data);
    } catch (error) {
      showFeedback(error.message, true);
    }
  }

  async function handleLoginSubmit(event) {
    event.preventDefault();
    clearFeedback();

    const form = event.currentTarget;
    const formData = new FormData(form);
    const email = String(formData.get("email") || "").trim().toLowerCase();
    const password = String(formData.get("password") || "");

    if (!email || !password) {
      showFeedback("Email and password are required.", true);
      return;
    }

    try {
      const payload = await apiRequest("/api/v1/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      state.user = payload.data.user;
      state.csrfToken = payload.data.csrf_token;
      setSessionSummary();
      showFeedback("Signed in successfully.");
      await Promise.all([loadUsers(), loadJigsaws()]);
    } catch (error) {
      showFeedback(error.message, true);
    }
  }

  async function handleLogout() {
    clearFeedback();

    if (!state.user) {
      showFeedback("You are already signed out.");
      return;
    }

    try {
      await apiRequest("/api/v1/auth/logout", { method: "POST" });
      state.user = null;
      state.csrfToken = null;
      setSessionSummary();
      renderUsers([]);
      renderJigsaws([]);
      showFeedback("Signed out.");
    } catch (error) {
      showFeedback(error.message, true);
    }
  }

  async function handleCreateUser(event) {
    event.preventDefault();
    clearFeedback();

    const form = event.currentTarget;
    const formData = new FormData(form);
    const email = String(formData.get("email") || "").trim();
    const displayName = String(formData.get("display_name") || "").trim();
    const role = String(formData.get("role") || "borrower");
    const isActive = formData.get("is_active") === "on";

    try {
      await apiRequest("/api/v1/users", {
        method: "POST",
        body: JSON.stringify({
          email,
          display_name: displayName || null,
          is_active: isActive,
          roles: [role],
        }),
      });
      form.reset();
      showFeedback("User created.");
      await loadUsers();
    } catch (error) {
      showFeedback(error.message, true);
    }
  }

  async function handleCreateJigsaw(event) {
    event.preventDefault();
    clearFeedback();

    const form = event.currentTarget;
    const formData = new FormData(form);
    const payload = {
      title: String(formData.get("title") || "").trim(),
      piece_count: Number(formData.get("piece_count") || "0"),
      condition: String(formData.get("condition") || "").trim() || null,
      status: String(formData.get("status") || "available"),
      tags: String(formData.get("tags") || "").trim() || null,
    };

    try {
      await apiRequest("/api/v1/jigsaws", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      form.reset();
      showFeedback("Jigsaw created.");
      await loadJigsaws();
    } catch (error) {
      showFeedback(error.message, true);
    }
  }

  async function handleTableActions(event) {
    const toggleButton = event.target.closest("[data-user-toggle]");
    if (toggleButton) {
      event.preventDefault();
      clearFeedback();

      const userId = Number(toggleButton.getAttribute("data-user-toggle"));
      const isCurrentlyActive = toggleButton.getAttribute("data-current-active") === "true";

      try {
        await apiRequest(`/api/v1/users/${userId}`, {
          method: "PATCH",
          body: JSON.stringify({ is_active: !isCurrentlyActive }),
        });
        showFeedback("User status updated.");
        await loadUsers();
      } catch (error) {
        showFeedback(error.message, true);
      }
      return;
    }

    const retireButton = event.target.closest("[data-jigsaw-retire]");
    if (retireButton) {
      event.preventDefault();
      clearFeedback();

      const jigsawId = Number(retireButton.getAttribute("data-jigsaw-retire"));
      try {
        await apiRequest(`/api/v1/jigsaws/${jigsawId}`, { method: "DELETE" });
        showFeedback("Jigsaw retired.");
        await loadJigsaws();
      } catch (error) {
        showFeedback(error.message, true);
      }
    }
  }

  function attachEvents() {
    if (elements.loginForm) {
      elements.loginForm.addEventListener("submit", handleLoginSubmit);
    }

    if (elements.logoutButton) {
      elements.logoutButton.addEventListener("click", handleLogout);
    }

    if (elements.userCreateForm) {
      elements.userCreateForm.addEventListener("submit", handleCreateUser);
    }

    if (elements.jigsawCreateForm) {
      elements.jigsawCreateForm.addEventListener("submit", handleCreateJigsaw);
    }

    if (elements.usersTableBody) {
      elements.usersTableBody.addEventListener("click", handleTableActions);
    }

    if (elements.jigsawsTableBody) {
      elements.jigsawsTableBody.addEventListener("click", handleTableActions);
    }
  }

  async function init() {
    attachEvents();
    const isAuthenticated = await refreshSession();
    if (isAuthenticated) {
      await Promise.all([loadUsers(), loadJigsaws()]);
    } else {
      renderUsers([]);
      renderJigsaws([]);
    }
  }

  init();
})();
