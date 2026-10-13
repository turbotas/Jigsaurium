(() => {
  const IMAGE_BROWSER_TAG_BOX = "Box";
  const IMAGE_BROWSER_TAG_COMPLETED = "Completed";
  const IMAGE_BROWSER_TAG_BOX_SIDE = "box-side";
  const IMAGE_BROWSER_TAG_BOX_BACK = "box-back";
  const IMAGE_BROWSER_TAG_IN_PROGRESS = "in-progress";

  const state = {
    csrfToken: null,
    user: null,
    users: [],
    jigsaws: [],
    loans: [],
    jigsawImages: [],
    imageLibraryImages: [],
    diaryEntries: [],
    bulkUploadFiles: [],
    imageBrowser: {
      isOpen: false,
      index: 0,
      sourceDataUrl: null,
      workingDataUrl: null,
      workingImage: null,
      rotationDegrees: 0,
      cropMode: false,
      cropRect: null,
      isDraggingCrop: false,
      dragStart: null,
      mimeType: "image/png",
      filename: "image.png",
    },
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
    imageLibraryUploadForm: document.getElementById("image-library-upload-form"),
    imageLibraryJigsawId: document.getElementById("image-library-jigsaw-id"),
    imageLibraryDropzone: document.getElementById("image-library-dropzone"),
    imageLibraryBrowseButton: document.getElementById("image-library-browse-button"),
    imageLibraryFilesInput: document.getElementById("image-library-files"),
    imageLibraryFilesList: document.getElementById("image-library-files-list"),
    imageLibraryTableBody: document.getElementById("image-library-table-body"),
    imageBrowserOpen: document.getElementById("image-browser-open"),
    imageBrowserModal: document.getElementById("image-browser-modal"),
    imageBrowserStatus: document.getElementById("image-browser-status"),
    imageBrowserCanvas: document.getElementById("image-browser-canvas"),
    imageBrowserPrev: document.getElementById("image-browser-prev"),
    imageBrowserNext: document.getElementById("image-browser-next"),
    imageBrowserRotateLeft: document.getElementById("image-browser-rotate-left"),
    imageBrowserRotateRight: document.getElementById("image-browser-rotate-right"),
    imageBrowserMarkBox: document.getElementById("image-browser-mark-box"),
    imageBrowserMarkCompleted: document.getElementById("image-browser-mark-completed"),
    imageBrowserMarkBoxSide: document.getElementById("image-browser-mark-box-side"),
    imageBrowserMarkBoxBack: document.getElementById("image-browser-mark-box-back"),
    imageBrowserMarkInProgress: document.getElementById("image-browser-mark-in-progress"),
    imageBrowserCropToggle: document.getElementById("image-browser-crop-toggle"),
    imageBrowserCropApply: document.getElementById("image-browser-crop-apply"),
    imageBrowserSave: document.getElementById("image-browser-save"),
    imageBrowserClose: document.getElementById("image-browser-close"),
    diaryEntryForm: document.getElementById("diary-entry-form"),
    diaryJigsawId: document.getElementById("diary-jigsaw-id"),
    diaryCompletedAt: document.getElementById("diary-completed-at"),
    diaryDifficulty: document.getElementById("diary-difficulty"),
    diaryNotes: document.getElementById("diary-notes"),
    diaryEntriesTableBody: document.getElementById("diary-entries-table-body"),
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
    if (["POST", "PUT", "PATCH", "DELETE"].includes(method) && state.csrfToken) {
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

  function populateDiaryJigsawOptions() {
    if (!elements.diaryJigsawId) {
      return;
    }

    const currentJigsawId = elements.diaryJigsawId.value;
    elements.diaryJigsawId.innerHTML = "";

    const placeholder = document.createElement("option");
    placeholder.value = "";
    placeholder.textContent = "Choose jigsaw";
    elements.diaryJigsawId.appendChild(placeholder);

    const sortedJigsaws = [...state.jigsaws].sort((left, right) => String(left.title || "").localeCompare(String(right.title || "")));
    sortedJigsaws.forEach((jigsaw) => {
      const option = document.createElement("option");
      option.value = String(jigsaw.id);
      option.textContent = `${jigsaw.title} (id ${jigsaw.id})`;
      elements.diaryJigsawId.appendChild(option);
    });

    if (currentJigsawId && sortedJigsaws.some((jigsaw) => String(jigsaw.id) === currentJigsawId)) {
      elements.diaryJigsawId.value = currentJigsawId;
    }
  }

  function populateImageLibraryJigsawOptions() {
    if (!elements.imageLibraryJigsawId) {
      return;
    }

    const currentJigsawId = elements.imageLibraryJigsawId.value;
    elements.imageLibraryJigsawId.innerHTML = "";

    const placeholder = document.createElement("option");
    placeholder.value = "";
    placeholder.textContent = "Unassigned (image library only)";
    elements.imageLibraryJigsawId.appendChild(placeholder);

    const sortedJigsaws = [...state.jigsaws].sort((left, right) => String(left.title || "").localeCompare(String(right.title || "")));
    sortedJigsaws.forEach((jigsaw) => {
      const option = document.createElement("option");
      option.value = String(jigsaw.id);
      option.textContent = `${jigsaw.title} (id ${jigsaw.id})`;
      elements.imageLibraryJigsawId.appendChild(option);
    });

    if (currentJigsawId && sortedJigsaws.some((jigsaw) => String(jigsaw.id) === currentJigsawId)) {
      elements.imageLibraryJigsawId.value = currentJigsawId;
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
      populateDiaryJigsawOptions();
      populateImageLibraryJigsawOptions();
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
      actionCell.classList.add("app-cell-actions");

      const controlsWrap = document.createElement("div");
      controlsWrap.className = "app-inline-controls";

      const editButton = document.createElement("button");
      editButton.type = "button";
      editButton.className = "govuk-button govuk-button--secondary app-inline-button";
      editButton.setAttribute("data-module", "govuk-button");
      editButton.dataset.userEdit = String(user.id);
      editButton.textContent = "Edit";
      controlsWrap.appendChild(editButton);

      const actionButton = document.createElement("button");
      actionButton.type = "button";
      actionButton.className = "govuk-button govuk-button--secondary app-inline-button";
      actionButton.setAttribute("data-module", "govuk-button");
      actionButton.dataset.userToggle = String(user.id);
      actionButton.dataset.currentActive = String(isActive);
      actionButton.textContent = toggleText;
      controlsWrap.appendChild(actionButton);

      actionCell.appendChild(controlsWrap);

      row.appendChild(actionCell);
      tableBody.appendChild(row);
    });
  }

  function renderJigsaws(jigsaws) {
    const tableBody = elements.jigsawsTableBody;
    clearTableBody(tableBody);

    if (!Array.isArray(jigsaws) || jigsaws.length === 0) {
      appendEmptyRow(tableBody, 6, "No jigsaws found.");
      return;
    }

    jigsaws.forEach((jigsaw) => {
      const row = document.createElement("tr");
      row.className = "govuk-table__row";

      row.appendChild(buildCell(String(jigsaw.id)));
      row.appendChild(buildCell(String(jigsaw.title || "-")));
      row.appendChild(buildCell(String(jigsaw.piece_count || "-")));
      row.appendChild(buildCell(String(jigsaw.status || "-")));
      row.appendChild(buildCell(toLocalTimestamp(jigsaw.last_completed_at)));

      const actionCell = document.createElement("td");
      actionCell.className = "govuk-table__cell";
      actionCell.classList.add("app-cell-actions");

      const controlsWrap = document.createElement("div");
      controlsWrap.className = "app-inline-controls";

      const editButton = document.createElement("button");
      editButton.type = "button";
      editButton.className = "govuk-button govuk-button--secondary app-inline-button";
      editButton.setAttribute("data-module", "govuk-button");
      editButton.dataset.jigsawEdit = String(jigsaw.id);
      editButton.textContent = "Edit";
      controlsWrap.appendChild(editButton);

      const retireButton = document.createElement("button");
      retireButton.type = "button";
      retireButton.className = "govuk-button govuk-button--secondary app-inline-button";
      retireButton.setAttribute("data-module", "govuk-button");
      retireButton.dataset.jigsawRetire = String(jigsaw.id);
      retireButton.textContent = "Retire";
      controlsWrap.appendChild(retireButton);

      const deleteButton = document.createElement("button");
      deleteButton.type = "button";
      deleteButton.className = "govuk-button govuk-button--secondary app-inline-button";
      deleteButton.setAttribute("data-module", "govuk-button");
      deleteButton.dataset.jigsawDelete = String(jigsaw.id);
      deleteButton.textContent = "Delete";
      controlsWrap.appendChild(deleteButton);

      actionCell.appendChild(controlsWrap);

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
      link.className = "govuk-button govuk-button--secondary app-inline-button";
      link.setAttribute("role", "button");
      link.setAttribute("data-module", "govuk-button");
      link.href = String(image.content_url || "#");
      link.textContent = "Open";
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      actionCell.appendChild(link);

      row.appendChild(actionCell);

      tableBody.appendChild(row);
    });
  }

  function renderImageLibraryImages(images) {
    const tableBody = elements.imageLibraryTableBody;
    clearTableBody(tableBody);

    if (!Array.isArray(images) || images.length === 0) {
      appendEmptyRow(tableBody, 7, "No image library items found.");
      return;
    }

    const sortedJigsaws = [...state.jigsaws].sort((left, right) => String(left.title || "").localeCompare(String(right.title || "")));
    const jigsawsById = new Map(state.jigsaws.map((jigsaw) => [Number(jigsaw.id), jigsaw]));
    images.forEach((image) => {
      const row = document.createElement("tr");
      row.className = "govuk-table__row";

      const associatedJigsaw = image.jigsaw_id ? jigsawsById.get(Number(image.jigsaw_id)) : null;
      const associationLabel = associatedJigsaw
        ? `${associatedJigsaw.title || "(untitled)"} (id ${associatedJigsaw.id})`
        : image.jigsaw_id
          ? `id ${image.jigsaw_id}`
          : "unassigned";

      row.appendChild(buildCell(String(image.id)));
      row.appendChild(buildCell(String(image.filename || "-")));
      row.appendChild(buildCell(associationLabel));
      row.appendChild(buildCell(String(image.tag || "-")));
      row.appendChild(buildCell(toLocalTimestamp(image.created_at)));

      const assignCell = document.createElement("td");
      assignCell.className = "govuk-table__cell";
      if (!image.jigsaw_id && sortedJigsaws.length > 0) {
        const controlsWrap = document.createElement("div");
        controlsWrap.className = "app-inline-controls";

        const select = document.createElement("select");
        select.className = "govuk-select";
        select.dataset.imageAssignSelect = String(image.id);

        const placeholder = document.createElement("option");
        placeholder.value = "";
        placeholder.textContent = "Choose jigsaw";
        select.appendChild(placeholder);

        sortedJigsaws.forEach((jigsaw) => {
          const option = document.createElement("option");
          option.value = String(jigsaw.id);
          option.textContent = `${jigsaw.title || "(untitled)"} (id ${jigsaw.id})`;
          select.appendChild(option);
        });

        const button = document.createElement("button");
        button.type = "button";
        button.className = "govuk-button govuk-button--secondary app-inline-button";
        button.setAttribute("data-module", "govuk-button");
        button.dataset.imageAssign = String(image.id);
        button.textContent = "Assign";

        const createButton = document.createElement("button");
        createButton.type = "button";
        createButton.className = "govuk-button govuk-button--secondary app-inline-button";
        createButton.setAttribute("data-module", "govuk-button");
        createButton.dataset.imageCreate = String(image.id);
        createButton.textContent = "Create jigsaw";

        controlsWrap.appendChild(select);
        controlsWrap.appendChild(button);
        controlsWrap.appendChild(createButton);
        assignCell.appendChild(controlsWrap);
      } else if (!image.jigsaw_id) {
        const controlsWrap = document.createElement("div");
        controlsWrap.className = "app-inline-controls";

        const note = document.createElement("span");
        note.textContent = "No jigsaws available";

        const createButton = document.createElement("button");
        createButton.type = "button";
        createButton.className = "govuk-button govuk-button--secondary app-inline-button";
        createButton.setAttribute("data-module", "govuk-button");
        createButton.dataset.imageCreate = String(image.id);
        createButton.textContent = "Create jigsaw";

        controlsWrap.appendChild(note);
        controlsWrap.appendChild(createButton);
        assignCell.appendChild(controlsWrap);
      } else {
        assignCell.textContent = "Assigned";
      }
      row.appendChild(assignCell);

      const actionCell = document.createElement("td");
      actionCell.className = "govuk-table__cell";
      const link = document.createElement("a");
      link.className = "govuk-button govuk-button--secondary app-inline-button";
      link.setAttribute("role", "button");
      link.setAttribute("data-module", "govuk-button");
      link.href = String(image.content_url || "#");
      link.textContent = "Open";
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      actionCell.appendChild(link);

      row.appendChild(actionCell);
      tableBody.appendChild(row);
    });
  }

  function renderBulkUploadFiles() {
    const list = elements.imageLibraryFilesList;
    if (!list) {
      return;
    }

    while (list.firstChild) {
      list.removeChild(list.firstChild);
    }

    if (!Array.isArray(state.bulkUploadFiles) || state.bulkUploadFiles.length === 0) {
      const item = document.createElement("li");
      item.textContent = "No files selected.";
      list.appendChild(item);
      return;
    }

    state.bulkUploadFiles.forEach((file) => {
      const item = document.createElement("li");
      const sizeKb = Math.max(1, Math.round((Number(file.size) || 0) / 1024));
      item.textContent = `${file.name} (${sizeKb} KB)`;
      list.appendChild(item);
    });
  }

  function normalizeRotationDegrees(value) {
    let normalized = Number(value) || 0;
    normalized %= 360;
    if (normalized < 0) {
      normalized += 360;
    }
    return normalized;
  }

  function getCurrentImageBrowserItem() {
    if (!Array.isArray(state.imageLibraryImages) || state.imageLibraryImages.length === 0) {
      return null;
    }
    const index = Math.max(0, Math.min(state.imageBrowser.index, state.imageLibraryImages.length - 1));
    state.imageBrowser.index = index;
    return state.imageLibraryImages[index] || null;
  }

  function browserHasPendingEdits() {
    return (
      Boolean(state.imageBrowser.sourceDataUrl) &&
      (state.imageBrowser.sourceDataUrl !== state.imageBrowser.workingDataUrl || normalizeRotationDegrees(state.imageBrowser.rotationDegrees) !== 0)
    );
  }

  function blobToDataUrl(blob) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(String(reader.result || ""));
      reader.onerror = () => reject(new Error("Failed to read image data."));
      reader.readAsDataURL(blob);
    });
  }

  function loadImageElementFromDataUrl(dataUrl) {
    return new Promise((resolve, reject) => {
      const image = new Image();
      image.onload = () => resolve(image);
      image.onerror = () => reject(new Error("Failed to load image."));
      image.src = dataUrl;
    });
  }

  async function ensureImageBrowserWorkingImage() {
    if (state.imageBrowser.workingImage) {
      return state.imageBrowser.workingImage;
    }
    if (!state.imageBrowser.workingDataUrl) {
      return null;
    }
    state.imageBrowser.workingImage = await loadImageElementFromDataUrl(state.imageBrowser.workingDataUrl);
    return state.imageBrowser.workingImage;
  }

  function drawRotatedImageToContext(context, image, rotationDegrees, canvasWidth, canvasHeight) {
    const normalized = normalizeRotationDegrees(rotationDegrees);
    context.save();
    if (normalized === 0) {
      context.drawImage(image, 0, 0);
    } else if (normalized === 90) {
      context.translate(canvasWidth, 0);
      context.rotate(Math.PI / 2);
      context.drawImage(image, 0, 0);
    } else if (normalized === 180) {
      context.translate(canvasWidth, canvasHeight);
      context.rotate(Math.PI);
      context.drawImage(image, 0, 0);
    } else if (normalized === 270) {
      context.translate(0, canvasHeight);
      context.rotate(-Math.PI / 2);
      context.drawImage(image, 0, 0);
    }
    context.restore();
  }

  async function renderImageBrowserToCanvas(targetCanvas, includeCropOverlay = true) {
    if (!targetCanvas) {
      return false;
    }

    const image = await ensureImageBrowserWorkingImage();
    if (!image) {
      targetCanvas.width = 1;
      targetCanvas.height = 1;
      const blankContext = targetCanvas.getContext("2d");
      blankContext.clearRect(0, 0, targetCanvas.width, targetCanvas.height);
      return false;
    }

    const normalizedRotation = normalizeRotationDegrees(state.imageBrowser.rotationDegrees);
    const isQuarterTurn = normalizedRotation === 90 || normalizedRotation === 270;
    const canvasWidth = isQuarterTurn ? image.naturalHeight : image.naturalWidth;
    const canvasHeight = isQuarterTurn ? image.naturalWidth : image.naturalHeight;

    targetCanvas.width = canvasWidth;
    targetCanvas.height = canvasHeight;

    const context = targetCanvas.getContext("2d");
    context.clearRect(0, 0, canvasWidth, canvasHeight);
    drawRotatedImageToContext(context, image, normalizedRotation, canvasWidth, canvasHeight);

    if (includeCropOverlay && state.imageBrowser.cropMode && state.imageBrowser.cropRect) {
      const rect = state.imageBrowser.cropRect;
      context.save();
      context.lineWidth = 2;
      context.strokeStyle = "#ffdd00";
      context.setLineDash([8, 4]);
      context.strokeRect(rect.x, rect.y, rect.width, rect.height);
      context.fillStyle = "rgba(255, 221, 0, 0.2)";
      context.fillRect(rect.x, rect.y, rect.width, rect.height);
      context.restore();
    }

    targetCanvas.classList.toggle("is-cropping", Boolean(state.imageBrowser.cropMode));
    return true;
  }

  async function redrawImageBrowserCanvas() {
    await renderImageBrowserToCanvas(elements.imageBrowserCanvas, true);
    updateImageBrowserStatus();
  }

  function updateImageBrowserStatus() {
    if (!elements.imageBrowserStatus) {
      return;
    }

    const item = getCurrentImageBrowserItem();
    if (!item) {
      elements.imageBrowserStatus.textContent = "No images available.";
      return;
    }

    const total = state.imageLibraryImages.length;
    const index = state.imageBrowser.index + 1;
    const association = item.jigsaw_id ? `assigned to jigsaw ${item.jigsaw_id}` : "unassigned";
    const dirty = browserHasPendingEdits() ? " | unsaved edits" : "";
    elements.imageBrowserStatus.textContent = `Image ${index}/${total}: ${item.filename || "(unnamed)"} | tag: ${item.tag || "-"} | ${association}${dirty}`;
  }

  function clearImageBrowserWorkingState() {
    state.imageBrowser.sourceDataUrl = null;
    state.imageBrowser.workingDataUrl = null;
    state.imageBrowser.workingImage = null;
    state.imageBrowser.rotationDegrees = 0;
    state.imageBrowser.cropMode = false;
    state.imageBrowser.cropRect = null;
    state.imageBrowser.isDraggingCrop = false;
    state.imageBrowser.dragStart = null;
    state.imageBrowser.mimeType = "image/png";
    state.imageBrowser.filename = "image.png";
  }

  async function loadCurrentImageIntoBrowser() {
    const item = getCurrentImageBrowserItem();
    clearImageBrowserWorkingState();

    if (!item) {
      await redrawImageBrowserCanvas();
      return;
    }

    const response = await fetch(String(item.content_url || ""), { credentials: "same-origin" });
    if (!response.ok) {
      throw new Error(`Failed to load image content (HTTP ${response.status}).`);
    }

    const blob = await response.blob();
    const dataUrl = await blobToDataUrl(blob);
    state.imageBrowser.sourceDataUrl = dataUrl;
    state.imageBrowser.workingDataUrl = dataUrl;
    state.imageBrowser.workingImage = await loadImageElementFromDataUrl(dataUrl);
    state.imageBrowser.mimeType = String(blob.type || item.mime_type || "image/png").toLowerCase();
    state.imageBrowser.filename = item.filename || `image-${item.id}.png`;

    await redrawImageBrowserCanvas();
  }

  async function openImageBrowser() {
    if (!elements.imageBrowserModal) {
      return;
    }
    if (!Array.isArray(state.imageLibraryImages) || state.imageLibraryImages.length === 0) {
      showFeedback("No images available in the image library yet.", true);
      return;
    }

    state.imageBrowser.isOpen = true;
    elements.imageBrowserModal.hidden = false;

    try {
      await loadCurrentImageIntoBrowser();
    } catch (error) {
      showFeedback(error.message, true);
    }
  }

  function closeImageBrowser() {
    if (!elements.imageBrowserModal) {
      return;
    }
    state.imageBrowser.isOpen = false;
    elements.imageBrowserModal.hidden = true;
    clearImageBrowserWorkingState();
  }

  async function navigateImageBrowser(direction) {
    if (!Array.isArray(state.imageLibraryImages) || state.imageLibraryImages.length === 0) {
      return;
    }

    if (browserHasPendingEdits()) {
      const shouldDiscard = window.confirm("Discard unsaved image edits and navigate?");
      if (!shouldDiscard) {
        return;
      }
    }

    const total = state.imageLibraryImages.length;
    const current = state.imageBrowser.index;
    state.imageBrowser.index = (current + direction + total) % total;

    try {
      await loadCurrentImageIntoBrowser();
    } catch (error) {
      showFeedback(error.message, true);
    }
  }

  async function setImageBrowserTag(tag) {
    const item = getCurrentImageBrowserItem();
    if (!item) {
      return;
    }

    try {
      await apiRequest(`/api/v1/image-library/images/${item.id}/tag`, {
        method: "PATCH",
        body: JSON.stringify({ tag }),
      });
      showFeedback(`Image tagged as ${tag}.`);
      await loadImageLibraryImages();
      const refreshedIndex = state.imageLibraryImages.findIndex((image) => Number(image.id) === Number(item.id));
      if (refreshedIndex >= 0) {
        state.imageBrowser.index = refreshedIndex;
      }
      updateImageBrowserStatus();
    } catch (error) {
      showFeedback(error.message, true);
    }
  }

  function rotateImageBrowser(deltaDegrees) {
    state.imageBrowser.rotationDegrees = normalizeRotationDegrees(state.imageBrowser.rotationDegrees + deltaDegrees);
    redrawImageBrowserCanvas();
  }

  function toggleImageBrowserCropMode() {
    state.imageBrowser.cropMode = !state.imageBrowser.cropMode;
    state.imageBrowser.cropRect = null;
    state.imageBrowser.isDraggingCrop = false;
    state.imageBrowser.dragStart = null;
    redrawImageBrowserCanvas();
  }

  function getCanvasCoordinates(event) {
    const canvas = elements.imageBrowserCanvas;
    if (!canvas) {
      return null;
    }
    const rect = canvas.getBoundingClientRect();
    if (rect.width <= 0 || rect.height <= 0) {
      return null;
    }

    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    const x = Math.max(0, Math.min(canvas.width, (event.clientX - rect.left) * scaleX));
    const y = Math.max(0, Math.min(canvas.height, (event.clientY - rect.top) * scaleY));
    return { x, y };
  }

  function handleImageBrowserCanvasMouseDown(event) {
    if (!state.imageBrowser.isOpen || !state.imageBrowser.cropMode) {
      return;
    }
    const point = getCanvasCoordinates(event);
    if (!point) {
      return;
    }
    state.imageBrowser.isDraggingCrop = true;
    state.imageBrowser.dragStart = point;
    state.imageBrowser.cropRect = { x: point.x, y: point.y, width: 0, height: 0 };
  }

  function handleImageBrowserCanvasMouseMove(event) {
    if (!state.imageBrowser.isOpen || !state.imageBrowser.cropMode || !state.imageBrowser.isDraggingCrop || !state.imageBrowser.dragStart) {
      return;
    }
    const point = getCanvasCoordinates(event);
    if (!point) {
      return;
    }

    const start = state.imageBrowser.dragStart;
    const x = Math.min(start.x, point.x);
    const y = Math.min(start.y, point.y);
    const width = Math.abs(point.x - start.x);
    const height = Math.abs(point.y - start.y);
    state.imageBrowser.cropRect = { x, y, width, height };
    redrawImageBrowserCanvas();
  }

  function handleImageBrowserCanvasMouseUp() {
    state.imageBrowser.isDraggingCrop = false;
    state.imageBrowser.dragStart = null;
  }

  function resolveWritableMimeType(mimeType) {
    const supported = new Set(["image/png", "image/jpeg", "image/webp"]);
    const normalized = String(mimeType || "").toLowerCase();
    if (supported.has(normalized)) {
      return normalized;
    }
    return "image/png";
  }

  async function applyImageBrowserCrop() {
    const cropRect = state.imageBrowser.cropRect;
    if (!cropRect || cropRect.width < 8 || cropRect.height < 8) {
      showFeedback("Select a crop area before applying crop.", true);
      return;
    }

    const renderedCanvas = document.createElement("canvas");
    const rendered = await renderImageBrowserToCanvas(renderedCanvas, false);
    if (!rendered) {
      showFeedback("Unable to crop this image.", true);
      return;
    }

    const outputCanvas = document.createElement("canvas");
    outputCanvas.width = Math.max(1, Math.round(cropRect.width));
    outputCanvas.height = Math.max(1, Math.round(cropRect.height));
    const outputContext = outputCanvas.getContext("2d");
    outputContext.drawImage(
      renderedCanvas,
      Math.round(cropRect.x),
      Math.round(cropRect.y),
      Math.round(cropRect.width),
      Math.round(cropRect.height),
      0,
      0,
      outputCanvas.width,
      outputCanvas.height,
    );

    const writableMimeType = resolveWritableMimeType(state.imageBrowser.mimeType);
    state.imageBrowser.workingDataUrl = outputCanvas.toDataURL(writableMimeType);
    state.imageBrowser.workingImage = await loadImageElementFromDataUrl(state.imageBrowser.workingDataUrl);
    state.imageBrowser.rotationDegrees = 0;
    state.imageBrowser.cropMode = false;
    state.imageBrowser.cropRect = null;
    showFeedback("Crop applied locally. Save overwrite to persist changes.");
    await redrawImageBrowserCanvas();
  }

  function canvasToBlob(canvas, mimeType) {
    return new Promise((resolve, reject) => {
      canvas.toBlob((blob) => {
        if (!blob) {
          reject(new Error("Failed to serialize image."));
          return;
        }
        resolve(blob);
      }, mimeType);
    });
  }

  async function saveImageBrowserOverwrite() {
    const item = getCurrentImageBrowserItem();
    if (!item) {
      return;
    }

    const renderedCanvas = document.createElement("canvas");
    const rendered = await renderImageBrowserToCanvas(renderedCanvas, false);
    if (!rendered) {
      showFeedback("No image to save.", true);
      return;
    }

    const writableMimeType = resolveWritableMimeType(state.imageBrowser.mimeType);
    let blob;
    try {
      blob = await canvasToBlob(renderedCanvas, writableMimeType);
    } catch (error) {
      showFeedback(error.message, true);
      return;
    }

    const formData = new FormData();
    formData.append("image", blob, state.imageBrowser.filename || `image-${item.id}.png`);

    try {
      await apiRequest(`/api/v1/image-library/images/${item.id}/content`, {
        method: "PUT",
        body: formData,
      });
      showFeedback("Image overwritten successfully.");
      await loadImageLibraryImages();
      const refreshedIndex = state.imageLibraryImages.findIndex((image) => Number(image.id) === Number(item.id));
      if (refreshedIndex >= 0) {
        state.imageBrowser.index = refreshedIndex;
      }
      await loadCurrentImageIntoBrowser();
    } catch (error) {
      showFeedback(error.message, true);
    }
  }

  function handleImageBrowserKeyDown(event) {
    if (!state.imageBrowser.isOpen) {
      return;
    }

    const activeTag = String(event.target?.tagName || "").toUpperCase();
    if (activeTag === "INPUT" || activeTag === "TEXTAREA" || activeTag === "SELECT") {
      return;
    }

    if (event.key === "ArrowLeft") {
      event.preventDefault();
      navigateImageBrowser(-1);
      return;
    }
    if (event.key === "ArrowRight") {
      event.preventDefault();
      navigateImageBrowser(1);
      return;
    }
    if (event.code === "BracketLeft" || event.key === "[" || event.key === "{" || event.key === "q" || event.key === "Q") {
      event.preventDefault();
      rotateImageBrowser(-90);
      return;
    }
    if (event.code === "BracketRight" || event.key === "]" || event.key === "}" || event.key === "e" || event.key === "E") {
      event.preventDefault();
      rotateImageBrowser(90);
      return;
    }
    if (event.key === "b" || event.key === "B") {
      event.preventDefault();
      setImageBrowserTag(IMAGE_BROWSER_TAG_BOX);
      return;
    }
    if (event.key === "c" || event.key === "C") {
      event.preventDefault();
      setImageBrowserTag(IMAGE_BROWSER_TAG_COMPLETED);
      return;
    }
    if (event.key === "s" || event.key === "S") {
      event.preventDefault();
      setImageBrowserTag(IMAGE_BROWSER_TAG_BOX_SIDE);
      return;
    }
    if (event.key === "k" || event.key === "K") {
      event.preventDefault();
      setImageBrowserTag(IMAGE_BROWSER_TAG_BOX_BACK);
      return;
    }
    if (event.key === "i" || event.key === "I") {
      event.preventDefault();
      setImageBrowserTag(IMAGE_BROWSER_TAG_IN_PROGRESS);
      return;
    }
    if (event.key === "Escape") {
      event.preventDefault();
      closeImageBrowser();
    }
  }

  function renderDiaryEntries(entries) {
    const tableBody = elements.diaryEntriesTableBody;
    clearTableBody(tableBody);

    if (!Array.isArray(entries) || entries.length === 0) {
      appendEmptyRow(tableBody, 5, "No diary entries found.");
      return;
    }

    entries.forEach((entry) => {
      const row = document.createElement("tr");
      row.className = "govuk-table__row";

      row.appendChild(buildCell(String(entry.id)));
      row.appendChild(buildCell(toLocalTimestamp(entry.completed_at)));
      row.appendChild(buildCell(entry.difficulty === null || entry.difficulty === undefined ? "-" : String(entry.difficulty)));
      row.appendChild(buildCell(String(entry.notes || "-")));

      const actionCell = document.createElement("td");
      actionCell.className = "govuk-table__cell";

      const deleteButton = document.createElement("button");
      deleteButton.type = "button";
      deleteButton.className = "app-action-link";
      deleteButton.dataset.diaryDelete = String(entry.id);
      deleteButton.textContent = "Delete";
      actionCell.appendChild(deleteButton);

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
      renderImageLibraryImages(state.imageLibraryImages);
      populateLoanFormOptions();
      populateJigsawImageOptions();
      populateDiaryJigsawOptions();
      populateImageLibraryJigsawOptions();
    } catch (error) {
      state.jigsaws = [];
      renderJigsaws([]);
      renderImageLibraryImages(state.imageLibraryImages);
      closeJigsawEditor();
      populateLoanFormOptions();
      populateJigsawImageOptions();
      populateDiaryJigsawOptions();
      populateImageLibraryJigsawOptions();
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

  async function loadImageLibraryImages() {
    if (!state.user) {
      state.imageLibraryImages = [];
      renderImageLibraryImages([]);
      return;
    }

    try {
      const payload = await apiRequest("/api/v1/image-library/images?limit=200");
      state.imageLibraryImages = Array.isArray(payload.data) ? payload.data : [];
      renderImageLibraryImages(state.imageLibraryImages);
      if (state.imageBrowser.isOpen) {
        updateImageBrowserStatus();
      }
    } catch (error) {
      if (error.status === 403) {
        state.imageLibraryImages = [];
        renderImageLibraryImages([]);
        return;
      }
      state.imageLibraryImages = [];
      renderImageLibraryImages([]);
      showFeedback(error.message, true);
    }
  }

  async function loadDiaryEntriesForSelected() {
    const selectedJigsawId = Number(elements.diaryJigsawId?.value || "0");
    if (!state.user || !selectedJigsawId) {
      state.diaryEntries = [];
      renderDiaryEntries([]);
      return;
    }

    try {
      const payload = await apiRequest(`/api/v1/jigsaws/${selectedJigsawId}/diary-entries`);
      state.diaryEntries = Array.isArray(payload.data) ? payload.data : [];
      renderDiaryEntries(state.diaryEntries);
    } catch (error) {
      state.diaryEntries = [];
      renderDiaryEntries([]);
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
      await Promise.all([loadUsers(), loadJigsaws(), loadLoans(), loadAuditEvents(), loadImageLibraryImages()]);
      await Promise.all([loadJigsawImagesForSelected(), loadDiaryEntriesForSelected()]);
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
      state.imageLibraryImages = [];
      state.diaryEntries = [];
      renderUsers([]);
      closeUserEditor();
      renderJigsaws([]);
      closeJigsawEditor();
      renderLoans([]);
      renderJigsawImages([]);
      renderImageLibraryImages([]);
      renderDiaryEntries([]);
      clearBulkUploadFiles();
      closeImageBrowser();
      populateLoanFormOptions();
      populateJigsawImageOptions();
      populateDiaryJigsawOptions();
      populateImageLibraryJigsawOptions();
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
      piece_count: parseOptionalIntegerFormValue(formData.get("piece_count")),
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

  async function handleCreateDiaryEntry(event) {
    event.preventDefault();
    clearFeedback();

    const form = event.currentTarget;
    const formData = new FormData(form);
    const jigsawId = Number(formData.get("jigsaw_id") || "0");

    if (!jigsawId) {
      showFeedback("Select a jigsaw before adding a diary entry.", true);
      return;
    }

    const payload = {
      completed_at: normalizeDatetimeLocal(formData.get("completed_at")),
      difficulty: parseOptionalIntegerFormValue(formData.get("difficulty")),
      notes: String(formData.get("notes") || "").trim() || null,
    };

    try {
      await apiRequest(`/api/v1/jigsaws/${jigsawId}/diary-entries`, {
        method: "POST",
        body: JSON.stringify(payload),
      });
      showFeedback("Diary entry added.");
      if (elements.diaryCompletedAt) {
        elements.diaryCompletedAt.value = "";
      }
      if (elements.diaryDifficulty) {
        elements.diaryDifficulty.value = "";
      }
      if (elements.diaryNotes) {
        elements.diaryNotes.value = "";
      }
      await Promise.all([loadDiaryEntriesForSelected(), loadJigsaws(), loadAuditEvents()]);
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

  function addBulkUploadFiles(fileList) {
    if (!fileList || fileList.length === 0) {
      return;
    }

    const existingKeys = new Set(
      state.bulkUploadFiles.map((file) => `${file.name}::${file.size}::${file.lastModified}`),
    );

    Array.from(fileList).forEach((file) => {
      const key = `${file.name}::${file.size}::${file.lastModified}`;
      if (!existingKeys.has(key)) {
        state.bulkUploadFiles.push(file);
        existingKeys.add(key);
      }
    });

    renderBulkUploadFiles();
  }

  function clearBulkUploadFiles() {
    state.bulkUploadFiles = [];
    if (elements.imageLibraryFilesInput) {
      elements.imageLibraryFilesInput.value = "";
    }
    renderBulkUploadFiles();
  }

  function handleImageLibraryBrowseClick() {
    elements.imageLibraryFilesInput?.click();
  }

  function handleImageLibraryFilesInputChange(event) {
    addBulkUploadFiles(event.currentTarget?.files || []);
    if (elements.imageLibraryFilesInput) {
      elements.imageLibraryFilesInput.value = "";
    }
  }

  function handleImageLibraryDropzoneDragOver(event) {
    event.preventDefault();
    event.dataTransfer.dropEffect = "copy";
    elements.imageLibraryDropzone?.classList.add("is-dragover");
  }

  function handleImageLibraryDropzoneDragLeave(event) {
    event.preventDefault();
    elements.imageLibraryDropzone?.classList.remove("is-dragover");
  }

  function handleImageLibraryDropzoneDrop(event) {
    event.preventDefault();
    elements.imageLibraryDropzone?.classList.remove("is-dragover");
    addBulkUploadFiles(event.dataTransfer?.files || []);
  }

  function handleImageLibraryDropzoneKeyDown(event) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      elements.imageLibraryFilesInput?.click();
    }
  }

  async function handleImageLibraryUpload(event) {
    event.preventDefault();
    clearFeedback();

    if (!Array.isArray(state.bulkUploadFiles) || state.bulkUploadFiles.length === 0) {
      showFeedback("Choose one or more files before uploading to the image library.", true);
      return;
    }

    const formData = new FormData();
    const jigsawIdValue = String(elements.imageLibraryJigsawId?.value || "").trim();
    if (jigsawIdValue) {
      formData.append("jigsaw_id", jigsawIdValue);
    }

    state.bulkUploadFiles.forEach((file) => {
      formData.append("files", file, file.name);
    });

    try {
      const payload = await apiRequest("/api/v1/image-library/uploads", {
        method: "POST",
        body: formData,
      });

      const createdCount = Number(payload?.data?.created_count || 0);
      const skippedCount = Number(payload?.data?.skipped_count || 0);
      showFeedback(`Image library upload complete. Added ${createdCount} image(s), skipped ${skippedCount}.`);
      clearBulkUploadFiles();
      await Promise.all([loadImageLibraryImages(), loadJigsaws(), loadAuditEvents()]);
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
      return;
    }

    const deleteButton = event.target.closest("[data-jigsaw-delete]");
    if (deleteButton) {
      event.preventDefault();
      clearFeedback();

      const jigsawId = Number(deleteButton.getAttribute("data-jigsaw-delete"));
      const shouldDelete = window.confirm(
        "Permanently delete this jigsaw and all of its images/diary entries? This cannot be undone.",
      );
      if (!shouldDelete) {
        return;
      }

      try {
        await apiRequest(`/api/v1/jigsaws/${jigsawId}/permanent`, { method: "DELETE" });
        showFeedback("Jigsaw deleted permanently.");
        await Promise.all([
          loadJigsaws(),
          loadJigsawImagesForSelected(),
          loadImageLibraryImages(),
          loadDiaryEntriesForSelected(),
          loadLoans(),
          loadAuditEvents(),
        ]);
      } catch (error) {
        showFeedback(error.message, true);
      }
      return;
    }

    const diaryDeleteButton = event.target.closest("[data-diary-delete]");
    if (diaryDeleteButton) {
      event.preventDefault();
      clearFeedback();

      const entryId = Number(diaryDeleteButton.getAttribute("data-diary-delete"));
      try {
        await apiRequest(`/api/v1/diary-entries/${entryId}`, { method: "DELETE" });
        showFeedback("Diary entry deleted.");
        await Promise.all([loadDiaryEntriesForSelected(), loadJigsaws(), loadAuditEvents()]);
      } catch (error) {
        showFeedback(error.message, true);
      }
      return;
    }

    const imageAssignButton = event.target.closest("[data-image-assign]");
    if (imageAssignButton) {
      event.preventDefault();
      clearFeedback();

      const imageId = Number(imageAssignButton.getAttribute("data-image-assign"));
      const select = elements.imageLibraryTableBody?.querySelector(
        `[data-image-assign-select="${imageId}"]`,
      );
      const selectedJigsawId = Number(select?.value || "0");

      if (!selectedJigsawId) {
        showFeedback("Choose a jigsaw before assigning the image.", true);
        return;
      }

      try {
        await apiRequest(`/api/v1/image-library/images/${imageId}/assign`, {
          method: "PATCH",
          body: JSON.stringify({ jigsaw_id: selectedJigsawId }),
        });
        showFeedback("Image assigned to jigsaw.");
        await Promise.all([loadImageLibraryImages(), loadJigsawImagesForSelected(), loadAuditEvents()]);
      } catch (error) {
        showFeedback(error.message, true);
      }
      return;
    }

    const imageCreateButton = event.target.closest("[data-image-create]");
    if (imageCreateButton) {
      event.preventDefault();
      clearFeedback();

      const imageId = Number(imageCreateButton.getAttribute("data-image-create"));
      try {
        const payload = await apiRequest(`/api/v1/image-library/images/${imageId}/create-jigsaw`, {
          method: "POST",
          body: JSON.stringify({}),
        });
        const createdTitle = payload?.data?.jigsaw?.title || "(untitled)";
        showFeedback(`Jigsaw created from image: ${createdTitle}.`);
        await Promise.all([
          loadJigsaws(),
          loadImageLibraryImages(),
          loadJigsawImagesForSelected(),
          loadAuditEvents(),
        ]);
      } catch (error) {
        showFeedback(error.message, true);
      }
    }
  }

  function handleDiarySelectionChange() {
    clearFeedback();
    loadDiaryEntriesForSelected();
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

    if (elements.imageLibraryUploadForm) {
      elements.imageLibraryUploadForm.addEventListener("submit", handleImageLibraryUpload);
    }

    if (elements.imageLibraryBrowseButton) {
      elements.imageLibraryBrowseButton.addEventListener("click", handleImageLibraryBrowseClick);
    }

    if (elements.imageLibraryFilesInput) {
      elements.imageLibraryFilesInput.addEventListener("change", handleImageLibraryFilesInputChange);
    }

    if (elements.imageLibraryDropzone) {
      elements.imageLibraryDropzone.addEventListener("dragover", handleImageLibraryDropzoneDragOver);
      elements.imageLibraryDropzone.addEventListener("dragleave", handleImageLibraryDropzoneDragLeave);
      elements.imageLibraryDropzone.addEventListener("drop", handleImageLibraryDropzoneDrop);
      elements.imageLibraryDropzone.addEventListener("keydown", handleImageLibraryDropzoneKeyDown);
    }

    if (elements.imageBrowserOpen) {
      elements.imageBrowserOpen.addEventListener("click", () => {
        openImageBrowser();
      });
    }

    if (elements.imageBrowserClose) {
      elements.imageBrowserClose.addEventListener("click", closeImageBrowser);
    }

    if (elements.imageBrowserPrev) {
      elements.imageBrowserPrev.addEventListener("click", () => {
        navigateImageBrowser(-1);
      });
    }

    if (elements.imageBrowserNext) {
      elements.imageBrowserNext.addEventListener("click", () => {
        navigateImageBrowser(1);
      });
    }

    if (elements.imageBrowserRotateLeft) {
      elements.imageBrowserRotateLeft.addEventListener("click", () => {
        rotateImageBrowser(-90);
      });
    }

    if (elements.imageBrowserRotateRight) {
      elements.imageBrowserRotateRight.addEventListener("click", () => {
        rotateImageBrowser(90);
      });
    }

    if (elements.imageBrowserMarkBox) {
      elements.imageBrowserMarkBox.addEventListener("click", () => {
        setImageBrowserTag(IMAGE_BROWSER_TAG_BOX);
      });
    }

    if (elements.imageBrowserMarkCompleted) {
      elements.imageBrowserMarkCompleted.addEventListener("click", () => {
        setImageBrowserTag(IMAGE_BROWSER_TAG_COMPLETED);
      });
    }

    if (elements.imageBrowserMarkBoxSide) {
      elements.imageBrowserMarkBoxSide.addEventListener("click", () => {
        setImageBrowserTag(IMAGE_BROWSER_TAG_BOX_SIDE);
      });
    }

    if (elements.imageBrowserMarkBoxBack) {
      elements.imageBrowserMarkBoxBack.addEventListener("click", () => {
        setImageBrowserTag(IMAGE_BROWSER_TAG_BOX_BACK);
      });
    }

    if (elements.imageBrowserMarkInProgress) {
      elements.imageBrowserMarkInProgress.addEventListener("click", () => {
        setImageBrowserTag(IMAGE_BROWSER_TAG_IN_PROGRESS);
      });
    }

    if (elements.imageBrowserCropToggle) {
      elements.imageBrowserCropToggle.addEventListener("click", toggleImageBrowserCropMode);
    }

    if (elements.imageBrowserCropApply) {
      elements.imageBrowserCropApply.addEventListener("click", () => {
        applyImageBrowserCrop();
      });
    }

    if (elements.imageBrowserSave) {
      elements.imageBrowserSave.addEventListener("click", () => {
        saveImageBrowserOverwrite();
      });
    }

    if (elements.imageBrowserCanvas) {
      elements.imageBrowserCanvas.addEventListener("mousedown", handleImageBrowserCanvasMouseDown);
      elements.imageBrowserCanvas.addEventListener("mousemove", handleImageBrowserCanvasMouseMove);
      elements.imageBrowserCanvas.addEventListener("mouseup", handleImageBrowserCanvasMouseUp);
      elements.imageBrowserCanvas.addEventListener("mouseleave", handleImageBrowserCanvasMouseUp);
    }

    document.addEventListener("keydown", handleImageBrowserKeyDown);

    if (elements.diaryEntryForm) {
      elements.diaryEntryForm.addEventListener("submit", handleCreateDiaryEntry);
    }

    if (elements.diaryJigsawId) {
      elements.diaryJigsawId.addEventListener("change", handleDiarySelectionChange);
    }

    if (elements.diaryEntriesTableBody) {
      elements.diaryEntriesTableBody.addEventListener("click", handleTableActions);
    }

    if (elements.imageLibraryTableBody) {
      elements.imageLibraryTableBody.addEventListener("click", handleTableActions);
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
    renderBulkUploadFiles();
    const isAuthenticated = await refreshSession();
    if (isAuthenticated) {
      await Promise.all([loadUsers(), loadJigsaws(), loadLoans(), loadAuditEvents(), loadImageLibraryImages()]);
      await Promise.all([loadJigsawImagesForSelected(), loadDiaryEntriesForSelected()]);
    } else {
      renderUsers([]);
      renderJigsaws([]);
      renderLoans([]);
      renderJigsawImages([]);
      renderImageLibraryImages([]);
      renderDiaryEntries([]);
      renderAuditEvents([]);
      renderBulkUploadFiles();
      populateLoanFormOptions();
      populateJigsawImageOptions();
      populateDiaryJigsawOptions();
      populateImageLibraryJigsawOptions();
    }
  }

  init();
})();
