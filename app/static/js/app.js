(() => {
  const state = {
    csrfToken: null,
    user: null,
    users: [],
    jigsaws: [],
    loans: [],
    jigsawImages: [],
  };

  const elements = {
    feedback: document.getElementById("app-feedback"),
    feedbackText: document.getElementById("app-feedback-text"),
    sessionSummary: document.getElementById("session-summary"),
    loginForm: document.getElementById("login-form"),
    authCredentialsWrap: document.getElementById("auth-credentials-wrap"),
    signInControls: document.getElementById("sign-in-controls"),
    signOutControls: document.getElementById("sign-out-controls"),
    accountSection: document.getElementById("account-section"),
    accountForm: document.getElementById("account-form"),
    accountUsername: document.getElementById("account-username"),
    accountCurrentPassword: document.getElementById("account-current-password"),
    accountNewPassword: document.getElementById("account-new-password"),
    accountConfirmPassword: document.getElementById("account-confirm-password"),
    adminSections: document.getElementById("admin-sections"),
    logoutButton: document.getElementById("logout-button"),
    userCreateForm: document.getElementById("user-create-form"),
    userEditForm: document.getElementById("user-edit-form"),
    userEditSaveButton: document.getElementById("user-edit-save"),
    userEditCancelButton: document.getElementById("user-edit-cancel"),
    editUserId: document.getElementById("edit-user-id"),
    editUserEmail: document.getElementById("edit-user-email"),
    editUserDisplayName: document.getElementById("edit-user-display-name"),
    userRoleBorrower: document.getElementById("user-role-borrower"),
    userRoleAdministrator: document.getElementById("user-role-administrator"),
    editUserRoleBorrower: document.getElementById("edit-user-role-borrower"),
    editUserRoleAdministrator: document.getElementById("edit-user-role-administrator"),
    editUserActive: document.getElementById("edit-user-active"),
    editUserPassword: document.getElementById("edit-user-password"),
    usersTableBody: document.getElementById("users-table-body"),
    jigsawCreateForm: document.getElementById("jigsaw-create-form"),
    jigsawEditForm: document.getElementById("jigsaw-edit-form"),
    jigsawEditSaveButton: document.getElementById("jigsaw-edit-save"),
    jigsawEditCancelButton: document.getElementById("jigsaw-edit-cancel"),
    editJigsawId: document.getElementById("edit-jigsaw-id"),
    editJigsawTitle: document.getElementById("edit-jigsaw-title"),
    jigsawManufacturer: document.getElementById("jigsaw-manufacturer"),
    jigsawArtist: document.getElementById("jigsaw-artist"),
    jigsawDimensionsCm: document.getElementById("jigsaw-dimensions-cm"),
    jigsawDescription: document.getElementById("jigsaw-description"),
    jigsawLastCompletedAt: document.getElementById("jigsaw-last-completed-at"),
    editJigsawPieceCount: document.getElementById("edit-jigsaw-piece-count"),
    editJigsawManufacturer: document.getElementById("edit-jigsaw-manufacturer"),
    editJigsawArtist: document.getElementById("edit-jigsaw-artist"),
    editJigsawDimensionsCm: document.getElementById("edit-jigsaw-dimensions-cm"),
    editJigsawDescription: document.getElementById("edit-jigsaw-description"),
    editJigsawLastCompletedAt: document.getElementById("edit-jigsaw-last-completed-at"),
    editJigsawCondition: document.getElementById("edit-jigsaw-condition"),
    editJigsawStatus: document.getElementById("edit-jigsaw-status"),
    editJigsawTags: document.getElementById("edit-jigsaw-tags"),
    jigsawsTableBody: document.getElementById("jigsaws-table-body"),
    jigsawImageForm: document.getElementById("jigsaw-image-form"),
    jigsawImageJigsawId: document.getElementById("jigsaw-image-jigsaw-id"),
    jigsawImageTag: document.getElementById("jigsaw-image-tag"),
    jigsawImageFile: document.getElementById("jigsaw-image-file"),
    jigsawImagesTableBody: document.getElementById("jigsaw-images-table-body"),
    loanCreateForm: document.getElementById("loan-create-form"),
    loanBorrowerUserId: document.getElementById("loan-borrower-user-id"),
    loanJigsawId: document.getElementById("loan-jigsaw-id"),
    loansTableBody: document.getElementById("loans-table-body"),
    auditTableBody: document.getElementById("audit-table-body"),
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
    if (!elements.feedback || !elements.feedbackText) {
      return;
    }

    elements.feedback.hidden = true;
    elements.feedback.classList.remove("is-error");
    elements.feedbackText.textContent = "";
  }

  async function apiRequest(path, options = {}) {
    const headers = new Headers(options.headers || {});
    headers.set("Accept", "application/json");

    if (options.body && !(options.body instanceof FormData) && !headers.has("Content-Type")) {
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

    const responseText = await response.text();
    let payload = {};
    if (responseText) {
      try {
        payload = JSON.parse(responseText);
      } catch (_error) {
        payload = {};
      }
    }

    if (!response.ok) {
      const details = Array.isArray(payload?.error?.details) ? payload.error.details : [];
      const detailMessage = details
        .map((entry) => {
          const field = typeof entry?.field === "string" && entry.field ? entry.field : "payload";
          const issue = typeof entry?.issue === "string" && entry.issue ? entry.issue : "is invalid";
          return `${field}: ${issue}`;
        })
        .join("; ");
      const baseMessage = payload?.error?.message || "Request failed.";
      const fallbackSnippet = responseText ? responseText.replace(/\s+/g, " ").trim().slice(0, 180) : "";
      const fallbackMessage = fallbackSnippet ? `HTTP ${response.status}: ${fallbackSnippet}` : `HTTP ${response.status}`;
      const message = detailMessage ? `${baseMessage} ${detailMessage}` : payload?.error?.message ? baseMessage : fallbackMessage;
      const error = new Error(message);
      error.status = response.status;
      error.payload = payload;
      throw error;
    }

    return payload;
  }

  function clearTableBody(tableBody) {
    if (!tableBody) {
      return;
    }

    while (tableBody.firstChild) {
      tableBody.removeChild(tableBody.firstChild);
    }
  }

  function appendEmptyRow(tableBody, columnCount, text) {
    if (!tableBody) {
      return;
    }

    const row = document.createElement("tr");
    row.className = "govuk-table__row";

    const cell = document.createElement("td");
    cell.className = "govuk-table__cell";
    cell.colSpan = columnCount;
    cell.textContent = text;

    row.appendChild(cell);
    tableBody.appendChild(row);
  }

  function buildCell(text) {
    const cell = document.createElement("td");
    cell.className = "govuk-table__cell";
    cell.textContent = text;
    return cell;
  }

  function toLocalTimestamp(value) {
    if (!value) {
      return "-";
    }

    const parsedDate = new Date(value);
    if (Number.isNaN(parsedDate.valueOf())) {
      return "-";
    }

    return parsedDate.toLocaleString();
  }

  function toDatetimeLocalValue(value) {
    if (!value) {
      return "";
    }

    const parsedDate = new Date(value);
    if (Number.isNaN(parsedDate.valueOf())) {
      return "";
    }

    const year = parsedDate.getFullYear();
    const month = String(parsedDate.getMonth() + 1).padStart(2, "0");
    const day = String(parsedDate.getDate()).padStart(2, "0");
    const hours = String(parsedDate.getHours()).padStart(2, "0");
    const minutes = String(parsedDate.getMinutes()).padStart(2, "0");
    return `${year}-${month}-${day}T${hours}:${minutes}`;
  }

  function normalizeDatetimeLocal(value) {
    const rawValue = String(value || "").trim();
    if (!rawValue) {
      return null;
    }
    return rawValue;
  }

  function parseOptionalIntegerFormValue(value) {
    const rawValue = String(value || "").trim();
    if (!rawValue) {
      return null;
    }

    const parsed = Number(rawValue);
    if (!Number.isFinite(parsed)) {
      return rawValue;
    }

    return Math.trunc(parsed);
  }

  function getSelectedRoles(formData) {
    return formData
      .getAll("roles")
      .map((value) => String(value || "").trim())
      .filter((value, index, values) => value && values.indexOf(value) === index);
  }

  function populateLoanFormOptions() {
    if (!elements.loanBorrowerUserId || !elements.loanJigsawId) {
      return;
    }

    const currentBorrowerId = elements.loanBorrowerUserId.value;
    const currentJigsawId = elements.loanJigsawId.value;

    elements.loanBorrowerUserId.innerHTML = "";
    elements.loanJigsawId.innerHTML = "";

    const borrowerPlaceholder = document.createElement("option");
    borrowerPlaceholder.value = "";
    borrowerPlaceholder.textContent = "Choose borrower";
    elements.loanBorrowerUserId.appendChild(borrowerPlaceholder);

    const borrowers = state.users
      .filter(
        (user) =>
          Boolean(user.is_active) &&
          Array.isArray(user.roles) &&
          (user.roles.includes("borrower") || user.roles.includes("administrator")),
      )
      .sort((left, right) => String(left.email || "").localeCompare(String(right.email || "")));

    borrowers.forEach((borrower) => {
      const option = document.createElement("option");
      option.value = String(borrower.id);
      option.textContent = `${borrower.email} (id ${borrower.id})`;
      elements.loanBorrowerUserId.appendChild(option);
    });

    const jigsawPlaceholder = document.createElement("option");
    jigsawPlaceholder.value = "";
    jigsawPlaceholder.textContent = "Choose available jigsaw";
    elements.loanJigsawId.appendChild(jigsawPlaceholder);

    const availableJigsaws = state.jigsaws
      .filter((jigsaw) => jigsaw.status === "available")
      .sort((left, right) => String(left.title || "").localeCompare(String(right.title || "")));

    availableJigsaws.forEach((jigsaw) => {
      const option = document.createElement("option");
      option.value = String(jigsaw.id);
      option.textContent = `${jigsaw.title} (id ${jigsaw.id})`;
      elements.loanJigsawId.appendChild(option);
    });

    if (currentBorrowerId && borrowers.some((borrower) => String(borrower.id) === currentBorrowerId)) {
      elements.loanBorrowerUserId.value = currentBorrowerId;
    }

    if (currentJigsawId && availableJigsaws.some((jigsaw) => String(jigsaw.id) === currentJigsawId)) {
      elements.loanJigsawId.value = currentJigsawId;
    }
  }

  function populateJigsawImageOptions() {
    if (!elements.jigsawImageJigsawId) {
      return;
    }

    const currentJigsawId = elements.jigsawImageJigsawId.value;
    elements.jigsawImageJigsawId.innerHTML = "";

    const placeholder = document.createElement("option");
    placeholder.value = "";
    placeholder.textContent = "Choose jigsaw";
    elements.jigsawImageJigsawId.appendChild(placeholder);

    const sortedJigsaws = [...state.jigsaws].sort((left, right) => String(left.title || "").localeCompare(String(right.title || "")));
    sortedJigsaws.forEach((jigsaw) => {
      const option = document.createElement("option");
      option.value = String(jigsaw.id);
      option.textContent = `${jigsaw.title} (id ${jigsaw.id})`;
      elements.jigsawImageJigsawId.appendChild(option);
    });

    if (currentJigsawId && sortedJigsaws.some((jigsaw) => String(jigsaw.id) === currentJigsawId)) {
      elements.jigsawImageJigsawId.value = currentJigsawId;
    }
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
      if (elements.userEditForm) {
        elements.userEditForm.hidden = true;
      }
      if (elements.jigsawEditForm) {
        elements.jigsawEditForm.hidden = true;
      }
      if (elements.accountSection) {
        elements.accountSection.hidden = true;
      }
      if (elements.signInControls) {
        elements.signInControls.hidden = false;
      }
      if (elements.signOutControls) {
        elements.signOutControls.hidden = true;
      }
      if (elements.authCredentialsWrap) {
        elements.authCredentialsWrap.hidden = false;
      }
      populateLoanFormOptions();
      populateJigsawImageOptions();
      return;
    }

    const roleText = Array.isArray(state.user.roles) ? state.user.roles.join(", ") : "none";
    elements.sessionSummary.textContent = `Signed in as ${state.user.email} (${roleText}).`;

    const isAdministrator = Array.isArray(state.user.roles) && state.user.roles.includes("administrator");
    if (elements.adminSections) {
      elements.adminSections.hidden = !isAdministrator;
    }
    if (elements.signInControls) {
      elements.signInControls.hidden = true;
    }
    if (elements.signOutControls) {
      elements.signOutControls.hidden = false;
    }
    if (elements.authCredentialsWrap) {
      elements.authCredentialsWrap.hidden = true;
    }
    if (elements.accountSection) {
      elements.accountSection.hidden = false;
    }
    if (elements.accountUsername) {
      elements.accountUsername.value = state.user.display_name || "";
    }

    if (!isAdministrator) {
      showFeedback("Signed in, but this account is not an administrator.", true);
    }

    const loginPasswordInput = document.getElementById("login-password");
    if (loginPasswordInput) {
      loginPasswordInput.value = "";
    }
  }

  function closeUserEditor() {
    if (elements.userEditForm) {
      elements.userEditForm.hidden = true;
    }
    if (elements.editUserId) {
      elements.editUserId.value = "";
    }
    if (elements.editUserEmail) {
      elements.editUserEmail.value = "";
    }
    if (elements.editUserDisplayName) {
      elements.editUserDisplayName.value = "";
    }
    if (elements.editUserRoleBorrower) {
      elements.editUserRoleBorrower.checked = true;
    }
    if (elements.editUserRoleAdministrator) {
      elements.editUserRoleAdministrator.checked = false;
    }
    if (elements.editUserActive) {
      elements.editUserActive.checked = false;
    }
    if (elements.editUserPassword) {
      elements.editUserPassword.value = "";
    }
    if (elements.userEditSaveButton) {
      elements.userEditSaveButton.disabled = false;
    }
  }

  function closeJigsawEditor() {
    if (elements.jigsawEditForm) {
      elements.jigsawEditForm.hidden = true;
    }
    if (elements.editJigsawId) {
      elements.editJigsawId.value = "";
    }
    if (elements.editJigsawTitle) {
      elements.editJigsawTitle.value = "";
    }
    if (elements.editJigsawManufacturer) {
      elements.editJigsawManufacturer.value = "";
    }
    if (elements.editJigsawArtist) {
      elements.editJigsawArtist.value = "";
    }
    if (elements.editJigsawDimensionsCm) {
      elements.editJigsawDimensionsCm.value = "";
    }
    if (elements.editJigsawDescription) {
      elements.editJigsawDescription.value = "";
    }
    if (elements.editJigsawLastCompletedAt) {
      elements.editJigsawLastCompletedAt.value = "";
    }
    if (elements.editJigsawPieceCount) {
      elements.editJigsawPieceCount.value = "";
    }
    if (elements.editJigsawCondition) {
      elements.editJigsawCondition.value = "";
    }
    if (elements.editJigsawStatus) {
      elements.editJigsawStatus.value = "available";
    }
    if (elements.editJigsawTags) {
      elements.editJigsawTags.value = "";
    }
    if (elements.jigsawEditSaveButton) {
      elements.jigsawEditSaveButton.disabled = false;
    }
  }

  function renderUsers(users) {
    const tableBody = elements.usersTableBody;
    clearTableBody(tableBody);

    if (!Array.isArray(users) || users.length === 0) {
      appendEmptyRow(tableBody, 6, "No users found.");
      return;
    }

    users.forEach((user) => {
      const row = document.createElement("tr");
      row.className = "govuk-table__row";

      const isActive = Boolean(user.is_active);
      const roleNames = Array.isArray(user.roles) ? user.roles.join(", ") : "-";
      const toggleText = isActive ? "Deactivate" : "Activate";

      row.appendChild(buildCell(String(user.id)));
      row.appendChild(buildCell(String(user.email || "-")));
      row.appendChild(buildCell(String(user.display_name || "-")));
      row.appendChild(buildCell(roleNames || "-"));
      row.appendChild(buildCell(isActive ? "active" : "inactive"));

      const actionCell = document.createElement("td");
      actionCell.className = "govuk-table__cell";

      const editButton = document.createElement("button");
      editButton.type = "button";
      editButton.className = "app-action-link";
      editButton.dataset.userEdit = String(user.id);
      editButton.textContent = "Edit";
      actionCell.appendChild(editButton);

      actionCell.appendChild(document.createTextNode(" | "));

      const actionButton = document.createElement("button");
      actionButton.type = "button";
      actionButton.className = "app-action-link";
      actionButton.dataset.userToggle = String(user.id);
      actionButton.dataset.currentActive = String(isActive);
      actionButton.textContent = toggleText;
      actionCell.appendChild(actionButton);

      row.appendChild(actionCell);
      tableBody.appendChild(row);
    });
  }

  function renderJigsaws(jigsaws) {
    const tableBody = elements.jigsawsTableBody;
    clearTableBody(tableBody);

    if (!Array.isArray(jigsaws) || jigsaws.length === 0) {
      appendEmptyRow(tableBody, 10, "No jigsaws found.");
      return;
    }

    jigsaws.forEach((jigsaw) => {
      const row = document.createElement("tr");
      row.className = "govuk-table__row";

      row.appendChild(buildCell(String(jigsaw.id)));
      row.appendChild(buildCell(String(jigsaw.title || "-")));
      row.appendChild(buildCell(String(jigsaw.manufacturer || "-")));
      row.appendChild(buildCell(String(jigsaw.artist || "-")));
      row.appendChild(buildCell(String(jigsaw.dimensions_cm || "-")));
      row.appendChild(buildCell(String(jigsaw.piece_count || "-")));
      row.appendChild(buildCell(String(jigsaw.condition || "-")));
      row.appendChild(buildCell(String(jigsaw.status || "-")));
      row.appendChild(buildCell(toLocalTimestamp(jigsaw.last_completed_at)));

      const actionCell = document.createElement("td");
      actionCell.className = "govuk-table__cell";

      const editButton = document.createElement("button");
      editButton.type = "button";
      editButton.className = "app-action-link";
      editButton.dataset.jigsawEdit = String(jigsaw.id);
      editButton.textContent = "Edit";
      actionCell.appendChild(editButton);

      actionCell.appendChild(document.createTextNode(" | "));

      const retireButton = document.createElement("button");
      retireButton.type = "button";
      retireButton.className = "app-action-link";
      retireButton.dataset.jigsawRetire = String(jigsaw.id);
      retireButton.textContent = "Retire";
      actionCell.appendChild(retireButton);

      row.appendChild(actionCell);
      tableBody.appendChild(row);
    });
  }

  function renderAuditEvents(events) {
    const tableBody = elements.auditTableBody;
    clearTableBody(tableBody);

    if (!Array.isArray(events) || events.length === 0) {
      appendEmptyRow(tableBody, 5, "No audit events found.");
      return;
    }

    events.forEach((event) => {
      const row = document.createElement("tr");
      row.className = "govuk-table__row";

      row.appendChild(buildCell(String(event.id)));
      row.appendChild(buildCell(String(event.action || "-")));
      row.appendChild(buildCell(`${event.entity_type || "-"}:${event.entity_id || "-"}`));
      row.appendChild(buildCell(String(event.actor_user_id || "system")));

      const timestamp = event.created_at ? new Date(event.created_at).toLocaleString() : "-";
      row.appendChild(buildCell(timestamp));

      tableBody.appendChild(row);
    });
  }

  function renderLoans(loans) {
    const tableBody = elements.loansTableBody;
    clearTableBody(tableBody);

    if (!Array.isArray(loans) || loans.length === 0) {
      appendEmptyRow(tableBody, 6, "No loans found.");
      return;
    }

    const usersById = new Map(state.users.map((user) => [Number(user.id), user]));
    const jigsawsById = new Map(state.jigsaws.map((jigsaw) => [Number(jigsaw.id), jigsaw]));

    loans.forEach((loan) => {
      const row = document.createElement("tr");
      row.className = "govuk-table__row";

      const borrower = usersById.get(Number(loan.borrower_user_id));
      const jigsaw = jigsawsById.get(Number(loan.jigsaw_id));

      const borrowerLabel = borrower ? `${borrower.email} (id ${borrower.id})` : `id ${loan.borrower_user_id}`;
      const jigsawLabel = jigsaw ? `${jigsaw.title} (id ${jigsaw.id})` : `id ${loan.jigsaw_id}`;

      row.appendChild(buildCell(String(loan.id)));
      row.appendChild(buildCell(borrowerLabel));
      row.appendChild(buildCell(jigsawLabel));
      row.appendChild(buildCell(toLocalTimestamp(loan.checked_out_at)));
      row.appendChild(buildCell(toLocalTimestamp(loan.due_at)));
      row.appendChild(buildCell(String(loan.status || "-")));

      tableBody.appendChild(row);
    });
  }

  function renderJigsawImages(images) {
    const tableBody = elements.jigsawImagesTableBody;
    clearTableBody(tableBody);

    if (!Array.isArray(images) || images.length === 0) {
      appendEmptyRow(tableBody, 5, "No images found.");
      return;
    }

    images.forEach((image) => {
      const row = document.createElement("tr");
      row.className = "govuk-table__row";

      row.appendChild(buildCell(String(image.id)));
      row.appendChild(buildCell(String(image.tag || "-")));
      row.appendChild(buildCell(String(image.filename || "-")));
      row.appendChild(buildCell(toLocalTimestamp(image.created_at)));

      const actionCell = document.createElement("td");
      actionCell.className = "govuk-table__cell";
      const link = document.createElement("a");
      link.className = "govuk-link";
      link.href = String(image.content_url || "#");
      link.textContent = "Open";
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      actionCell.appendChild(link);
      row.appendChild(actionCell);

      tableBody.appendChild(row);
    });
  }

  async function refreshSession() {
    try {
      const payload = await apiRequest("/api/v1/auth/me");
      state.user = payload.data.user;
      state.csrfToken = payload.data.csrf_token || null;
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

  async function loadUsers() {
    if (!state.user) {
      state.users = [];
      renderUsers([]);
      closeUserEditor();
      return;
    }

    try {
      const payload = await apiRequest("/api/v1/users");
      state.users = Array.isArray(payload.data) ? payload.data : [];
      renderUsers(state.users);
      populateLoanFormOptions();
    } catch (error) {
      if (error.status === 403) {
        state.users = [];
        renderUsers([]);
        closeUserEditor();
        populateLoanFormOptions();
        return;
      }
      showFeedback(error.message, true);
    }
  }

  async function loadJigsaws() {
    if (!state.user) {
      state.jigsaws = [];
      renderJigsaws([]);
      closeJigsawEditor();
      return;
    }

    try {
      const payload = await apiRequest("/api/v1/jigsaws");
      state.jigsaws = Array.isArray(payload.data) ? payload.data : [];
      renderJigsaws(state.jigsaws);
      populateLoanFormOptions();
      populateJigsawImageOptions();
    } catch (error) {
      state.jigsaws = [];
      renderJigsaws([]);
      closeJigsawEditor();
      populateLoanFormOptions();
      populateJigsawImageOptions();
      showFeedback(error.message, true);
    }
  }

  async function loadJigsawImagesForSelected() {
    const selectedJigsawId = Number(elements.jigsawImageJigsawId?.value || "0");
    if (!selectedJigsawId) {
      state.jigsawImages = [];
      renderJigsawImages([]);
      return;
    }

    try {
      const payload = await apiRequest(`/api/v1/jigsaws/${selectedJigsawId}/images`);
      state.jigsawImages = Array.isArray(payload.data) ? payload.data : [];
      renderJigsawImages(state.jigsawImages);
    } catch (error) {
      state.jigsawImages = [];
      renderJigsawImages([]);
      showFeedback(error.message, true);
    }
  }

  async function loadLoans() {
    if (!state.user) {
      state.loans = [];
      renderLoans([]);
      return;
    }

    try {
      const payload = await apiRequest("/api/v1/loans");
      state.loans = Array.isArray(payload.data) ? payload.data : [];
      renderLoans(state.loans);
    } catch (error) {
      if (error.status === 403) {
        state.loans = [];
        renderLoans([]);
        return;
      }
      showFeedback(error.message, true);
    }
  }

  async function loadAuditEvents() {
    if (!state.user) {
      renderAuditEvents([]);
      return;
    }

    try {
      const payload = await apiRequest("/api/v1/audit-events?limit=50");
      renderAuditEvents(payload.data);
    } catch (error) {
      if (error.status === 403) {
        renderAuditEvents([]);
        return;
      }
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
      await Promise.all([loadUsers(), loadJigsaws(), loadLoans(), loadAuditEvents()]);
      await loadJigsawImagesForSelected();
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
      state.users = [];
      state.jigsaws = [];
      state.loans = [];
      state.jigsawImages = [];
      renderUsers([]);
      closeUserEditor();
      renderJigsaws([]);
      closeJigsawEditor();
      renderLoans([]);
      renderJigsawImages([]);
      populateLoanFormOptions();
      populateJigsawImageOptions();
      renderAuditEvents([]);
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
    const password = String(formData.get("password") || "");
    const roles = getSelectedRoles(formData);
    const isActive = formData.get("is_active") === "on";

    if (roles.length === 0) {
      showFeedback("Select at least one role.", true);
      return;
    }

    if (!password) {
      showFeedback("Initial password is required.", true);
      return;
    }

    try {
      await apiRequest("/api/v1/users", {
        method: "POST",
        body: JSON.stringify({
          email,
          password,
          display_name: displayName || null,
          is_active: isActive,
          roles,
        }),
      });
      form.reset();
      showFeedback("User created.");
      await Promise.all([loadUsers(), loadAuditEvents()]);
    } catch (error) {
      showFeedback(error.message, true);
    }
  }

  function openUserEditor(userId) {
    const selectedUser = state.users.find((entry) => Number(entry.id) === Number(userId));
    if (!selectedUser || !elements.userEditForm) {
      return;
    }

    elements.userEditForm.hidden = false;
    if (elements.editUserId) {
      elements.editUserId.value = String(selectedUser.id);
    }
    if (elements.editUserEmail) {
      elements.editUserEmail.value = selectedUser.email || "";
    }
    if (elements.editUserDisplayName) {
      elements.editUserDisplayName.value = selectedUser.display_name || "";
    }
    if (elements.editUserRoleBorrower) {
      const roles = Array.isArray(selectedUser.roles) ? selectedUser.roles : [];
      elements.editUserRoleBorrower.checked = roles.includes("borrower");
    }
    if (elements.editUserRoleAdministrator) {
      const roles = Array.isArray(selectedUser.roles) ? selectedUser.roles : [];
      elements.editUserRoleAdministrator.checked = roles.includes("administrator");
    }
    if (elements.editUserActive) {
      elements.editUserActive.checked = Boolean(selectedUser.is_active);
    }
    if (elements.editUserPassword) {
      elements.editUserPassword.value = "";
    }
  }

  async function handleEditUser(event) {
    event.preventDefault();
    clearFeedback();

    const formData = new FormData(event.currentTarget);
    const userId = Number(formData.get("user_id") || "0");
    const email = String(formData.get("email") || "").trim();
    const displayName = String(formData.get("display_name") || "").trim();
    const roles = getSelectedRoles(formData);
    const isActive = formData.get("is_active") === "on";
    const password = String(formData.get("password") || "");

    if (!userId) {
      showFeedback("Select a user to edit first.", true);
      return;
    }

    if (roles.length === 0) {
      showFeedback("Select at least one role.", true);
      return;
    }

    if (elements.userEditSaveButton) {
      elements.userEditSaveButton.disabled = true;
    }

    const payload = {
      email,
      display_name: displayName || null,
      roles,
      is_active: isActive,
    };
    if (password) {
      payload.password = password;
    }

    try {
      await apiRequest(`/api/v1/users/${userId}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      });
      showFeedback("User updated.");
      await Promise.all([loadUsers(), loadAuditEvents()]);
      openUserEditor(userId);
    } catch (error) {
      showFeedback(error.message, true);
    } finally {
      if (elements.userEditSaveButton) {
        elements.userEditSaveButton.disabled = false;
      }
    }
  }

  function handleCancelUserEdit() {
    clearFeedback();
    closeUserEditor();
  }

  async function handleAccountUpdate(event) {
    event.preventDefault();
    clearFeedback();

    if (!state.user) {
      showFeedback("You must be signed in to update your account.", true);
      return;
    }

    const form = event.currentTarget;
    const formData = new FormData(form);
    const displayName = String(formData.get("display_name") || "").trim();
    const currentPassword = String(formData.get("current_password") || "");
    const newPassword = String(formData.get("new_password") || "");
    const confirmPassword = String(formData.get("confirm_password") || "");

    const payload = {};
    const currentDisplayName = state.user.display_name || "";
    if (displayName !== currentDisplayName) {
      payload.display_name = displayName || null;
    }

    if (currentPassword || newPassword || confirmPassword) {
      if (!currentPassword || !newPassword || !confirmPassword) {
        showFeedback("Provide current, new, and confirmation passwords to change password.", true);
        return;
      }
      if (newPassword !== confirmPassword) {
        showFeedback("New password and confirmation do not match.", true);
        return;
      }

      payload.current_password = currentPassword;
      payload.new_password = newPassword;
    }

    if (Object.keys(payload).length === 0) {
      showFeedback("No account changes to save.");
      return;
    }

    try {
      const response = await apiRequest("/api/v1/auth/me", {
        method: "PATCH",
        body: JSON.stringify(payload),
      });

      state.user = response.data.user;
      if (response.data.csrf_token) {
        state.csrfToken = response.data.csrf_token;
      }

      setSessionSummary();

      if (elements.accountCurrentPassword) {
        elements.accountCurrentPassword.value = "";
      }
      if (elements.accountNewPassword) {
        elements.accountNewPassword.value = "";
      }
      if (elements.accountConfirmPassword) {
        elements.accountConfirmPassword.value = "";
      }

      showFeedback("Account updated.");
      await loadAuditEvents();
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
      manufacturer: String(formData.get("manufacturer") || "").trim() || null,
      artist: String(formData.get("artist") || "").trim() || null,
      dimensions_cm: String(formData.get("dimensions_cm") || "").trim() || null,
      description: String(formData.get("description") || "").trim() || null,
      last_completed_at: normalizeDatetimeLocal(formData.get("last_completed_at")),
      piece_count: parseOptionalIntegerFormValue(formData.get("piece_count")),
      condition: String(formData.get("condition") || "").trim() || null,
      status: String(formData.get("status") || "").trim() || null,
      tags: String(formData.get("tags") || "").trim() || null,
    };

    try {
      await apiRequest("/api/v1/jigsaws", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      form.reset();
      showFeedback("Jigsaw created.");
      await Promise.all([loadJigsaws(), loadJigsawImagesForSelected(), loadLoans(), loadAuditEvents()]);
    } catch (error) {
      showFeedback(error.message, true);
    }
  }

  async function handleCreateJigsawImage(event) {
    event.preventDefault();
    clearFeedback();

    const form = event.currentTarget;
    const formData = new FormData(form);
    const jigsawId = Number(formData.get("jigsaw_id") || "0");

    if (!jigsawId) {
      showFeedback("Select a jigsaw before uploading an image.", true);
      return;
    }

    try {
      await apiRequest(`/api/v1/jigsaws/${jigsawId}/images`, {
        method: "POST",
        body: formData,
      });
      showFeedback("Jigsaw image uploaded.");
      if (elements.jigsawImageTag) {
        elements.jigsawImageTag.value = "";
      }
      if (elements.jigsawImageFile) {
        elements.jigsawImageFile.value = "";
      }
      await Promise.all([loadJigsawImagesForSelected(), loadAuditEvents()]);
    } catch (error) {
      showFeedback(error.message, true);
    }
  }

  async function handleCreateLoan(event) {
    event.preventDefault();
    clearFeedback();

    const form = event.currentTarget;
    const formData = new FormData(form);
    const borrowerUserId = Number(formData.get("borrower_user_id") || "0");
    const jigsawId = Number(formData.get("jigsaw_id") || "0");

    if (!borrowerUserId || !jigsawId) {
      showFeedback("Select a borrower and an available jigsaw.", true);
      return;
    }

    try {
      await apiRequest("/api/v1/loans", {
        method: "POST",
        body: JSON.stringify({
          borrower_user_id: borrowerUserId,
          jigsaw_id: jigsawId,
        }),
      });

      showFeedback("Loan created.");
      form.reset();
      await Promise.all([loadJigsaws(), loadLoans(), loadAuditEvents()]);
    } catch (error) {
      showFeedback(error.message, true);
    }
  }

  function openJigsawEditor(jigsawId) {
    const selectedJigsaw = state.jigsaws.find((entry) => Number(entry.id) === Number(jigsawId));
    if (!selectedJigsaw || !elements.jigsawEditForm) {
      return;
    }

    elements.jigsawEditForm.hidden = false;
    if (elements.editJigsawId) {
      elements.editJigsawId.value = String(selectedJigsaw.id);
    }
    if (elements.editJigsawTitle) {
      elements.editJigsawTitle.value = selectedJigsaw.title || "";
    }
    if (elements.editJigsawManufacturer) {
      elements.editJigsawManufacturer.value = selectedJigsaw.manufacturer || "";
    }
    if (elements.editJigsawArtist) {
      elements.editJigsawArtist.value = selectedJigsaw.artist || "";
    }
    if (elements.editJigsawDimensionsCm) {
      elements.editJigsawDimensionsCm.value = selectedJigsaw.dimensions_cm || "";
    }
    if (elements.editJigsawDescription) {
      elements.editJigsawDescription.value = selectedJigsaw.description || "";
    }
    if (elements.editJigsawLastCompletedAt) {
      elements.editJigsawLastCompletedAt.value = toDatetimeLocalValue(selectedJigsaw.last_completed_at);
    }
    if (elements.editJigsawPieceCount) {
      elements.editJigsawPieceCount.value = String(selectedJigsaw.piece_count || "");
    }
    if (elements.editJigsawCondition) {
      elements.editJigsawCondition.value = selectedJigsaw.condition || "";
    }
    if (elements.editJigsawStatus) {
      elements.editJigsawStatus.value = selectedJigsaw.status || "available";
    }
    if (elements.editJigsawTags) {
      elements.editJigsawTags.value = selectedJigsaw.tags || "";
    }
  }

  async function handleEditJigsaw(event) {
    event.preventDefault();
    clearFeedback();

    const formData = new FormData(event.currentTarget);
    const jigsawId = Number(formData.get("jigsaw_id") || "0");
    if (!jigsawId) {
      showFeedback("Select a jigsaw to edit first.", true);
      return;
    }

    if (elements.jigsawEditSaveButton) {
      elements.jigsawEditSaveButton.disabled = true;
    }

    const payload = {
      title: String(formData.get("title") || "").trim(),
      manufacturer: String(formData.get("manufacturer") || "").trim() || null,
      artist: String(formData.get("artist") || "").trim() || null,
      dimensions_cm: String(formData.get("dimensions_cm") || "").trim() || null,
      description: String(formData.get("description") || "").trim() || null,
      last_completed_at: normalizeDatetimeLocal(formData.get("last_completed_at")),
      piece_count: Number(formData.get("piece_count") || "0"),
      condition: String(formData.get("condition") || "").trim() || null,
      status: String(formData.get("status") || "available"),
      tags: String(formData.get("tags") || "").trim() || null,
    };

    try {
      await apiRequest(`/api/v1/jigsaws/${jigsawId}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      });
      showFeedback("Jigsaw updated.");
      await Promise.all([loadJigsaws(), loadJigsawImagesForSelected(), loadLoans(), loadAuditEvents()]);
      openJigsawEditor(jigsawId);
    } catch (error) {
      showFeedback(error.message, true);
    } finally {
      if (elements.jigsawEditSaveButton) {
        elements.jigsawEditSaveButton.disabled = false;
      }
    }
  }

  function handleCancelJigsawEdit() {
    clearFeedback();
    closeJigsawEditor();
  }

  async function handleTableActions(event) {
    const editJigsawButton = event.target.closest("[data-jigsaw-edit]");
    if (editJigsawButton) {
      event.preventDefault();
      clearFeedback();

      const jigsawId = Number(editJigsawButton.getAttribute("data-jigsaw-edit"));
      openJigsawEditor(jigsawId);
      return;
    }

    const editButton = event.target.closest("[data-user-edit]");
    if (editButton) {
      event.preventDefault();
      clearFeedback();

      const userId = Number(editButton.getAttribute("data-user-edit"));
      openUserEditor(userId);
      return;
    }

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
        await Promise.all([loadUsers(), loadAuditEvents()]);
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
        await Promise.all([loadJigsaws(), loadJigsawImagesForSelected(), loadLoans(), loadAuditEvents()]);
      } catch (error) {
        showFeedback(error.message, true);
      }
    }
  }

  function handleJigsawImageSelectionChange() {
    clearFeedback();
    loadJigsawImagesForSelected();
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

    if (elements.userEditForm) {
      elements.userEditForm.addEventListener("submit", handleEditUser);
    }

    if (elements.jigsawCreateForm) {
      elements.jigsawCreateForm.addEventListener("submit", handleCreateJigsaw);
    }

    if (elements.loanCreateForm) {
      elements.loanCreateForm.addEventListener("submit", handleCreateLoan);
    }

    if (elements.jigsawImageForm) {
      elements.jigsawImageForm.addEventListener("submit", handleCreateJigsawImage);
    }

    if (elements.jigsawImageJigsawId) {
      elements.jigsawImageJigsawId.addEventListener("change", handleJigsawImageSelectionChange);
    }

    if (elements.jigsawEditForm) {
      elements.jigsawEditForm.addEventListener("submit", handleEditJigsaw);
    }

    if (elements.jigsawEditCancelButton) {
      elements.jigsawEditCancelButton.addEventListener("click", handleCancelJigsawEdit);
    }

    if (elements.accountForm) {
      elements.accountForm.addEventListener("submit", handleAccountUpdate);
    }

    if (elements.userEditCancelButton) {
      elements.userEditCancelButton.addEventListener("click", handleCancelUserEdit);
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
      await Promise.all([loadUsers(), loadJigsaws(), loadLoans(), loadAuditEvents()]);
      await loadJigsawImagesForSelected();
    } else {
      renderUsers([]);
      renderJigsaws([]);
      renderLoans([]);
      renderJigsawImages([]);
      renderAuditEvents([]);
      populateLoanFormOptions();
      populateJigsawImageOptions();
    }
  }

  init();
})();
