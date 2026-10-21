(() => {
  const form = document.getElementById("mobile-intake-form");
  if (!form) {
    return;
  }

  const slotTagMap = {
    box_front: "Box front",
    box_side: "Box side",
    box_back: "Box back",
    completed: "Completed",
  };
  const boxSlotKeys = ["box_front", "box_side", "box_back"];

  const titleInput = document.getElementById("mobile-intake-title");
  const pieceCountInput = document.getElementById("mobile-intake-piece-count");
  const commentInput = document.getElementById("mobile-intake-comment");
  const submitButton = document.getElementById("mobile-intake-submit");
  const statusPanel = document.getElementById("mobile-intake-status");
  const statusText = document.getElementById("mobile-intake-status-text");
  const slotInputs = Array.from(form.querySelectorAll("[data-slot-file]"));

  const authCard = document.getElementById("mobile-capture-auth-card");
  const loginForm = document.getElementById("mobile-capture-login-form");
  const loginEmailInput = document.getElementById("mobile-capture-login-email");
  const loginPasswordInput = document.getElementById("mobile-capture-login-password");
  const stfdLoginButton = document.getElementById("mobile-capture-stfd-login-button");
  const authModeHint = document.getElementById("mobile-capture-auth-mode-hint");
  const logoutButton = document.getElementById("mobile-capture-logout-button");
  const signOutControls = document.getElementById("mobile-capture-sign-out-controls");
  const sessionSummary = document.getElementById("mobile-capture-session-summary");
  const workflowSection = document.getElementById("mobile-capture-workflow");

  const previewObjectUrls = new Map();
  const state = {
    csrfToken: null,
    isSubmitting: false,
    isAdmin: false,
    stfdAuthEnabled: false,
    stfdAllowLocalLogin: true,
    stfdLoginUrl: null,
  };

  function setStatus(message, isError = false) {
    if (!statusPanel) {
      return;
    }
    statusPanel.hidden = !message;
    if (statusText) {
      statusText.textContent = message || "";
    } else {
      statusPanel.textContent = message || "";
    }
    statusPanel.classList.toggle("govuk-notification-banner--success", !isError);
    statusPanel.classList.toggle("govuk-notification-banner--error", Boolean(isError));
  }

  function setWorkflowVisible(isVisible) {
    if (workflowSection) {
      workflowSection.hidden = !isVisible;
    }
  }

  function setSessionSummary(message) {
    if (sessionSummary) {
      sessionSummary.textContent = message;
    }
  }

  function setAuthUiSignedIn(isSignedIn) {
    if (authCard) {
      authCard.hidden = isSignedIn;
    }
    if (signOutControls) {
      signOutControls.hidden = !isSignedIn;
    }
    if (logoutButton) {
      logoutButton.hidden = !isSignedIn;
    }
  }

  function syncLoginUiForAuthMode() {
    if (!loginForm) {
      return;
    }

    const submitButton = loginForm.querySelector("button[type='submit']");
    const credentialGroups = Array.from(loginForm.querySelectorAll(".govuk-form-group"));
    const stfdOnlyMode = state.stfdAuthEnabled && !state.stfdAllowLocalLogin;

    if (stfdOnlyMode) {
      credentialGroups.forEach((group) => {
        group.hidden = true;
      });
      if (loginEmailInput) {
        loginEmailInput.required = false;
        loginEmailInput.disabled = true;
      }
      if (loginPasswordInput) {
        loginPasswordInput.required = false;
        loginPasswordInput.disabled = true;
      }
      if (submitButton) {
        submitButton.textContent = "Sign in with STFD";
      }
      if (stfdLoginButton) {
        stfdLoginButton.hidden = true;
      }
      if (authModeHint) {
        authModeHint.hidden = false;
        authModeHint.textContent = "Sign-in is handled by STFD for this environment.";
      }
      return;
    }

    credentialGroups.forEach((group) => {
      group.hidden = false;
    });
    if (loginEmailInput) {
      loginEmailInput.required = true;
      loginEmailInput.disabled = false;
    }
    if (loginPasswordInput) {
      loginPasswordInput.required = true;
      loginPasswordInput.disabled = false;
    }
    if (submitButton) {
      submitButton.textContent = "Sign in";
    }
    if (stfdLoginButton) {
      stfdLoginButton.hidden = !state.stfdAuthEnabled;
    }
    if (authModeHint) {
      if (state.stfdAuthEnabled) {
        authModeHint.hidden = false;
        authModeHint.textContent = "Use either local credentials or Sign in with STFD.";
      } else {
        authModeHint.hidden = true;
        authModeHint.textContent = "";
      }
    }
  }

  function redirectToStfdLogin() {
    if (!state.stfdAuthEnabled) {
      return;
    }
    if (!state.stfdLoginUrl) {
      setStatus("STFD sign-in is enabled but not configured correctly.", true);
      return;
    }
    window.location.assign(state.stfdLoginUrl);
  }

  function getFileFromSlot(slotKey) {
    const input = form.querySelector(`[data-slot-file="${slotKey}"]`);
    if (!input || !input.files || input.files.length === 0) {
      return null;
    }
    return input.files[0];
  }

  function selectedSlotEntries() {
    return Object.keys(slotTagMap)
      .map((slotKey) => ({ slotKey, file: getFileFromSlot(slotKey) }))
      .filter((item) => Boolean(item.file));
  }

  function clearPreviewObjectUrl(slotKey) {
    const existingUrl = previewObjectUrls.get(slotKey);
    if (existingUrl) {
      URL.revokeObjectURL(existingUrl);
      previewObjectUrls.delete(slotKey);
    }
  }

  function renderSlotPreview(slotKey) {
    const preview = form.querySelector(`[data-slot-preview="${slotKey}"]`);
    if (!preview) {
      return;
    }

    clearPreviewObjectUrl(slotKey);
    preview.innerHTML = "";
    const file = getFileFromSlot(slotKey);
    if (!file) {
      preview.textContent = "No photo selected.";
      return;
    }

    const imageUrl = URL.createObjectURL(file);
    previewObjectUrls.set(slotKey, imageUrl);

    const image = document.createElement("img");
    image.className = "app-mobile-intake-preview__image";
    image.alt = "Selected photo preview";
    image.src = imageUrl;

    const meta = document.createElement("p");
    meta.className = "govuk-body-s govuk-!-margin-bottom-0";
    const fileSizeKb = Math.max(1, Math.round(file.size / 1024));
    meta.textContent = `${file.name} (${fileSizeKb} KB)`;

    preview.appendChild(image);
    preview.appendChild(meta);
  }

  function setSubmitting(isSubmitting) {
    state.isSubmitting = isSubmitting;
    if (submitButton) {
      submitButton.disabled = isSubmitting;
      submitButton.textContent = isSubmitting ? "Processing..." : "Process capture";
    }
    slotInputs.forEach((input) => {
      input.disabled = isSubmitting;
    });
    if (titleInput) {
      titleInput.disabled = isSubmitting;
    }
    if (pieceCountInput) {
      pieceCountInput.disabled = isSubmitting;
    }
    if (commentInput) {
      commentInput.disabled = isSubmitting;
    }
  }

  async function parseJsonSafe(response) {
    const text = await response.text();
    if (!text) {
      return {};
    }
    try {
      return JSON.parse(text);
    } catch (_error) {
      return {};
    }
  }

  async function fetchAuthState() {
    const response = await fetch("/api/v1/auth/me", {
      method: "GET",
      credentials: "same-origin",
      headers: { Accept: "application/json" },
    });
    const payload = await parseJsonSafe(response);
    if (!response.ok) {
      state.csrfToken = null;
      state.isAdmin = false;
      return null;
    }

    const user = payload?.data?.user || null;
    const roles = Array.isArray(user?.roles) ? user.roles : [];
    state.csrfToken = payload?.data?.csrf_token || null;
    state.isAdmin = roles.includes("administrator");
    return user;
  }

  async function fetchStfdLoginInfo() {
    const response = await fetch("/api/v1/auth/stfd/login-url", {
      method: "GET",
      credentials: "same-origin",
      headers: { Accept: "application/json" },
    });
    const payload = await parseJsonSafe(response);
    if (!response.ok) {
      state.stfdAuthEnabled = false;
      state.stfdLoginUrl = null;
      syncLoginUiForAuthMode();
      return;
    }

    state.stfdAuthEnabled = Boolean(payload?.data?.enabled);
    state.stfdAllowLocalLogin = Boolean(payload?.data?.allow_local_login ?? true);
    state.stfdLoginUrl =
      state.stfdAuthEnabled && typeof payload?.data?.login_url === "string" && payload.data.login_url
        ? payload.data.login_url
        : null;
    syncLoginUiForAuthMode();
  }

  async function consumeStfdTokenFromUrl() {
    if (!state.stfdAuthEnabled) {
      return null;
    }

    const url = new URL(window.location.href);
    const token = String(url.searchParams.get("token") || "").trim();
    if (!token) {
      return null;
    }

    const response = await fetch("/api/v1/auth/login", {
      method: "POST",
      credentials: "same-origin",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ token }),
    });
    const payload = await parseJsonSafe(response);
    url.searchParams.delete("token");
    window.history.replaceState({}, document.title, url.pathname + url.search + url.hash);
    if (!response.ok) {
      const message = payload?.error?.message || "Sign in failed.";
      throw new Error(message);
    }

    state.csrfToken = payload?.data?.csrf_token || null;
    return payload?.data?.user || null;
  }

  function syncAuthUi(user) {
    if (!user) {
      setSessionSummary("Not signed in.");
      setAuthUiSignedIn(false);
      setWorkflowVisible(false);
      return;
    }

    const roles = Array.isArray(user.roles) ? user.roles : [];
    const roleLabel = roles.length > 0 ? roles.join(", ") : "none";
    setSessionSummary(`Signed in as ${user.email} (${roleLabel}).`);
    setAuthUiSignedIn(true);

    if (!state.isAdmin) {
      setWorkflowVisible(false);
      setStatus("This page is administrator-only for uploads. Sign in with an administrator account.", true);
      return;
    }

    setWorkflowVisible(true);
  }

  async function ensureCsrfToken() {
    if (state.csrfToken) {
      return state.csrfToken;
    }
    const user = await fetchAuthState();
    syncAuthUi(user);
    if (!state.csrfToken) {
      throw new Error("Please sign in before uploading mobile capture images.");
    }
    if (!state.isAdmin) {
      throw new Error("Administrator access is required for mobile capture upload.");
    }
    return state.csrfToken;
  }

  async function apiRequest(path, options = {}) {
    const headers = new Headers(options.headers || {});
    headers.set("Accept", "application/json");

    const method = String(options.method || "GET").toUpperCase();
    if (!(options.body instanceof FormData) && options.body && !headers.has("Content-Type")) {
      headers.set("Content-Type", "application/json");
    }
    if (["POST", "PATCH", "PUT", "DELETE"].includes(method)) {
      const csrfToken = await ensureCsrfToken();
      headers.set("X-CSRF-Token", csrfToken);
    }

    const response = await fetch(path, {
      credentials: "same-origin",
      ...options,
      method,
      headers,
    });
    const payload = await parseJsonSafe(response);

    if (!response.ok) {
      const details = Array.isArray(payload?.error?.details) ? payload.error.details : [];
      const detailsText = details
        .map((entry) => `${entry?.field || "payload"}: ${entry?.issue || "is invalid"}`)
        .join("; ");
      const message = payload?.error?.message || `Request failed (${response.status}).`;
      throw new Error(detailsText ? `${message} ${detailsText}` : message);
    }
    return payload;
  }

  async function uploadImageLibraryItem(file, tag, comment) {
    const formData = new FormData();
    formData.append("tag", tag);
    if (comment) {
      formData.append("comment", comment);
    }
    formData.append("files", file, file.name || "capture.jpg");
    return apiRequest("/api/v1/image-library/uploads", {
      method: "POST",
      body: formData,
    });
  }

  async function uploadJigsawImage(jigsawId, file, tag, comment) {
    const formData = new FormData();
    formData.append("tag", tag);
    if (comment) {
      formData.append("comment", comment);
    }
    formData.append("image", file, file.name || "capture.jpg");
    return apiRequest(`/api/v1/jigsaws/${Number(jigsawId)}/images`, {
      method: "POST",
      body: formData,
    });
  }

  function buildJigsawCreatePayload() {
    const payload = {};
    const title = String(titleInput?.value || "").trim();
    if (title) {
      payload.title = title;
    }

    const pieceCountValue = String(pieceCountInput?.value || "").trim();
    if (pieceCountValue) {
      const pieceCount = Number.parseInt(pieceCountValue, 10);
      if (!Number.isInteger(pieceCount) || pieceCount <= 0) {
        throw new Error("Piece count must be a positive whole number.");
      }
      payload.piece_count = pieceCount;
    }
    return payload;
  }

  function clearForm() {
    form.reset();
    Object.keys(slotTagMap).forEach((slotKey) => {
      renderSlotPreview(slotKey);
    });
  }

  async function handleSubmit(event) {
    event.preventDefault();
    if (state.isSubmitting) {
      return;
    }
    if (!state.isAdmin) {
      setStatus("Please sign in with an administrator account before uploading.", true);
      return;
    }

    const entries = selectedSlotEntries();
    if (entries.length === 0) {
      setStatus("Add at least one photo before processing capture.", true);
      return;
    }

    const selectedBoxEntries = entries.filter((entry) => boxSlotKeys.includes(entry.slotKey));
    const completedEntry = entries.find((entry) => entry.slotKey === "completed") || null;
    const commentText = String(commentInput?.value || "").trim();

    setSubmitting(true);
    setStatus("Starting mobile capture workflow...");

    try {
      if (selectedBoxEntries.length === 0 && completedEntry) {
        setStatus("Uploading completed image to the unassigned image library...");
        const uploadPayload = await uploadImageLibraryItem(completedEntry.file, slotTagMap.completed, commentText);
        const createdCount = Number(uploadPayload?.data?.created_count || 0);
        const skippedCount = Number(uploadPayload?.data?.skipped_count || 0);
        setStatus(`Completed image stored as unassigned. Added ${createdCount} image(s), skipped ${skippedCount}.`);
        clearForm();
        return;
      }

      setStatus("Creating jigsaw record...");
      const createPayload = buildJigsawCreatePayload();
      const createdJigsaw = await apiRequest("/api/v1/jigsaws", {
        method: "POST",
        body: JSON.stringify(createPayload),
      });
      const jigsawId = createdJigsaw?.data?.id;
      if (!jigsawId) {
        throw new Error("Jigsaw create response did not include an id.");
      }

      const uploadQueue = [...selectedBoxEntries];
      if (completedEntry) {
        uploadQueue.push(completedEntry);
      }
      const hasCompleted = Boolean(completedEntry);

      const duplicateWarnings = [];
      for (let index = 0; index < uploadQueue.length; index += 1) {
        const entry = uploadQueue[index];
        const tag = slotTagMap[entry.slotKey];
        const attachComment = commentText && (entry.slotKey === "completed" || (!hasCompleted && index === 0));
        setStatus(`Uploading ${index + 1}/${uploadQueue.length}: ${tag}...`);
        const payload = await uploadJigsawImage(jigsawId, entry.file, tag, attachComment ? commentText : "");
        const image = payload?.data || {};
        if (Number(image?.jigsaw_id || 0) !== Number(jigsawId)) {
          duplicateWarnings.push(tag);
        }
      }

      setStatus("Running AI enrich from uploaded box images...");
      await apiRequest(`/api/v1/jigsaws/${Number(jigsawId)}/enrich-from-images`, {
        method: "POST",
        body: JSON.stringify({ overwrite_existing: false }),
      });

      const warningSuffix =
        duplicateWarnings.length > 0
          ? ` Duplicate image bytes were detected for ${duplicateWarnings.join(", ")}, so those images may already belong to another jigsaw.`
          : "";
      setStatus(`Mobile capture complete. Created jigsaw #${jigsawId} and started enrichment.${warningSuffix}`);
      clearForm();
    } catch (error) {
      setStatus(error.message || "Mobile capture workflow failed.", true);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleLoginSubmit(event) {
    event.preventDefault();

    if (state.stfdAuthEnabled && !state.stfdAllowLocalLogin) {
      redirectToStfdLogin();
      return;
    }

    const email = String(loginEmailInput?.value || "").trim();
    const password = String(loginPasswordInput?.value || "");

    if (!email || !password) {
      setStatus("Enter email and password to sign in.", true);
      return;
    }

    try {
      const response = await fetch("/api/v1/auth/login", {
        method: "POST",
        credentials: "same-origin",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ email, password }),
      });
      const payload = await parseJsonSafe(response);
      if (!response.ok) {
        const message = payload?.error?.message || "Sign in failed.";
        throw new Error(message);
      }

      state.csrfToken = payload?.data?.csrf_token || null;
      const user = payload?.data?.user || null;
      state.isAdmin = Array.isArray(user?.roles) && user.roles.includes("administrator");
      syncAuthUi(user);
      setStatus("Signed in.");
      if (loginPasswordInput) {
        loginPasswordInput.value = "";
      }
    } catch (error) {
      setStatus(error.message || "Sign in failed.", true);
    }
  }

  async function handleLogoutClick() {
    try {
      await apiRequest("/api/v1/auth/logout", {
        method: "POST",
        body: JSON.stringify({}),
      });
    } catch (_error) {
      // Continue with local reset even when logout call fails.
    }

    state.csrfToken = null;
    state.isAdmin = false;
    syncAuthUi(null);
    setStatus("Signed out.");
  }

  slotInputs.forEach((input) => {
    input.addEventListener("change", () => {
      const slotKey = input.getAttribute("data-slot-file");
      if (slotKey) {
        renderSlotPreview(slotKey);
      }
    });
  });

  if (loginForm) {
    loginForm.addEventListener("submit", handleLoginSubmit);
  }
  if (stfdLoginButton) {
    stfdLoginButton.addEventListener("click", redirectToStfdLogin);
  }
  if (logoutButton) {
    logoutButton.addEventListener("click", handleLogoutClick);
  }
  form.addEventListener("submit", handleSubmit);

  Object.keys(slotTagMap).forEach((slotKey) => {
    renderSlotPreview(slotKey);
  });

  fetchStfdLoginInfo()
    .then(() => consumeStfdTokenFromUrl())
    .then((tokenUser) => {
      if (tokenUser) {
        syncAuthUi(tokenUser);
        if (state.isAdmin) {
          setStatus("Ready to capture images.");
        }
        return null;
      }
      return fetchAuthState();
    })
    .then((user) => {
      if (user === null) {
        return;
      }
      syncAuthUi(user);
      if (user && state.isAdmin) {
        setStatus("Ready to capture images.");
      }
    })
    .catch((error) => {
      syncAuthUi(null);
      if (error?.message) {
        setStatus(error.message, true);
      }
    });
})();
