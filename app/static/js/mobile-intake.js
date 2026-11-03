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
    reference: "Reference",
  };
  const boxSlotKeys = ["box_front", "box_side", "box_back"];
  const jigsawSeedSlotKeys = ["box_front", "box_side", "box_back", "reference"];

  const titleInput = document.getElementById("mobile-intake-title");
  const pieceCountInput = document.getElementById("mobile-intake-piece-count");
  const commentInput = document.getElementById("mobile-intake-comment");
  const submitButton = document.getElementById("mobile-intake-submit");
  const statusPanel = document.getElementById("mobile-intake-status");
  const statusText = document.getElementById("mobile-intake-status-text");
  const slotInputs = Array.from(form.querySelectorAll("[data-slot-file]"));
  const slotActionButtons = Array.from(form.querySelectorAll("[data-slot-action][data-slot-key]"));

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
  const selectedSlotFiles = new Map();
  const state = {
    csrfToken: null,
    isSubmitting: false,
    capabilities: [],
    stfdAuthEnabled: false,
    stfdAllowLocalLogin: true,
    stfdLoginUrl: null,
  };
  const cameraCaptureState = {
    shell: null,
    title: null,
    video: null,
    captureButton: null,
    cancelButton: null,
    stream: null,
    slotKey: null,
  };

  const fallbackRoleCapabilities = {
    administrator: [
      "image.upload",
      "image.tag",
      "jigsaw.create",
      "jigsaw.enrich",
      "image.manage_library",
    ],
    member: [
      "image.upload",
      "image.tag",
      "jigsaw.create",
      "jigsaw.enrich",
      "image.manage_library",
    ],
    borrower: [
      "image.upload",
      "image.tag",
      "jigsaw.create",
      "jigsaw.enrich",
      "image.manage_library",
    ],
  };

  function hasCapability(capability) {
    return state.capabilities.includes(capability);
  }

  function extractCapabilitiesFromUser(user) {
    const rawCapabilities = Array.isArray(user?.capabilities) ? user.capabilities : [];
    const normalizedCapabilities = rawCapabilities
      .filter((value) => typeof value === "string" && value.trim())
      .map((value) => value.trim());

    if (normalizedCapabilities.length > 0) {
      return Array.from(new Set(normalizedCapabilities));
    }

    const roles = Array.isArray(user?.roles) ? user.roles : [];
    const capabilitySet = new Set();
    roles.forEach((roleName) => {
      const normalizedRole = typeof roleName === "string" ? roleName.trim().toLowerCase() : "";
      const roleCapabilities = fallbackRoleCapabilities[normalizedRole] || [];
      roleCapabilities.forEach((capability) => capabilitySet.add(capability));
    });
    return Array.from(capabilitySet);
  }

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

  function normalizeTagForCompare(value) {
    return String(value || "")
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "");
  }

  function browserCameraSupported() {
    return Boolean(
      window.isSecureContext &&
        navigator.mediaDevices &&
        typeof navigator.mediaDevices.getUserMedia === "function"
    );
  }

  function stopCameraStream() {
    if (!cameraCaptureState.stream) {
      return;
    }
    cameraCaptureState.stream.getTracks().forEach((track) => {
      track.stop();
    });
    cameraCaptureState.stream = null;
    if (cameraCaptureState.video) {
      cameraCaptureState.video.srcObject = null;
    }
  }

  function closeCameraCaptureUi() {
    stopCameraStream();
    cameraCaptureState.slotKey = null;
    if (cameraCaptureState.shell) {
      cameraCaptureState.shell.hidden = true;
    }
  }

  async function capturePhotoFromStream() {
    const video = cameraCaptureState.video;
    if (!video || video.videoWidth <= 0 || video.videoHeight <= 0) {
      throw new Error("Camera stream is not ready yet. Please try capture again.");
    }

    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const context = canvas.getContext("2d");
    if (!context) {
      throw new Error("Unable to capture camera frame.");
    }
    context.drawImage(video, 0, 0, canvas.width, canvas.height);

    const blob = await new Promise((resolve) => {
      canvas.toBlob(resolve, "image/jpeg", 0.92);
    });
    if (!blob) {
      throw new Error("Could not capture photo from camera.");
    }

    const slotKey = String(cameraCaptureState.slotKey || "").trim();
    if (!slotKey) {
      throw new Error("Capture slot is missing.");
    }

    const file = new File([blob], `${slotKey}-${Date.now()}.jpg`, {
      type: blob.type || "image/jpeg",
      lastModified: Date.now(),
    });
    selectedSlotFiles.set(slotKey, {
      file,
      source: "camera",
      inputId: `camera-stream-${slotKey}`,
    });
    slotInputs.forEach((candidate) => {
      if (candidate.getAttribute("data-slot-file") === slotKey) {
        candidate.value = "";
      }
    });
    renderSlotPreview(slotKey);
    closeCameraCaptureUi();
  }

  function ensureCameraCaptureUi() {
    if (cameraCaptureState.shell) {
      return;
    }

    const shell = document.createElement("div");
    shell.className = "app-mobile-camera-capture";
    shell.hidden = true;

    const panel = document.createElement("div");
    panel.className = "app-mobile-camera-capture__panel";

    const heading = document.createElement("h3");
    heading.className = "govuk-heading-m govuk-!-margin-bottom-2";
    heading.textContent = "Capture photo";

    const hint = document.createElement("p");
    hint.className = "govuk-hint govuk-!-margin-bottom-2";
    hint.textContent = "Use your camera, then tap Capture photo.";

    const video = document.createElement("video");
    video.className = "app-mobile-camera-capture__video";
    video.autoplay = true;
    video.playsInline = true;
    video.muted = true;

    const actions = document.createElement("div");
    actions.className = "app-mobile-camera-capture__actions";

    const captureButton = document.createElement("button");
    captureButton.type = "button";
    captureButton.className = "govuk-button govuk-!-margin-bottom-0";
    captureButton.textContent = "Capture photo";

    const cancelButton = document.createElement("button");
    cancelButton.type = "button";
    cancelButton.className = "govuk-button govuk-button--secondary govuk-!-margin-bottom-0";
    cancelButton.textContent = "Cancel";

    actions.appendChild(captureButton);
    actions.appendChild(cancelButton);
    panel.appendChild(heading);
    panel.appendChild(hint);
    panel.appendChild(video);
    panel.appendChild(actions);
    shell.appendChild(panel);
    document.body.appendChild(shell);

    shell.addEventListener("click", (event) => {
      if (event.target === shell) {
        closeCameraCaptureUi();
      }
    });
    cancelButton.addEventListener("click", closeCameraCaptureUi);
    captureButton.addEventListener("click", () => {
      capturePhotoFromStream().catch((error) => {
        setStatus(error.message || "Camera capture failed.", true);
      });
    });

    cameraCaptureState.shell = shell;
    cameraCaptureState.title = heading;
    cameraCaptureState.video = video;
    cameraCaptureState.captureButton = captureButton;
    cameraCaptureState.cancelButton = cancelButton;
  }

  async function openBrowserCamera(slotKey) {
    if (!browserCameraSupported()) {
      return false;
    }

    ensureCameraCaptureUi();
    stopCameraStream();

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: "environment" } },
        audio: false,
      });
      cameraCaptureState.stream = stream;
      cameraCaptureState.slotKey = slotKey;
      if (cameraCaptureState.title) {
        cameraCaptureState.title.textContent = `Capture ${slotTagMap[slotKey] || "photo"}`;
      }
      if (cameraCaptureState.video) {
        cameraCaptureState.video.srcObject = stream;
        await cameraCaptureState.video.play().catch(() => {});
      }
      if (cameraCaptureState.shell) {
        cameraCaptureState.shell.hidden = false;
      }
      return true;
    } catch (_error) {
      closeCameraCaptureUi();
      return false;
    }
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
    const selected = selectedSlotFiles.get(slotKey);
    if (!selected || !selected.file) {
      return null;
    }
    return selected.file;
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
    const selected = selectedSlotFiles.get(slotKey);
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
    const sourceLabel = selected?.source === "camera" ? "Camera" : "Gallery";
    meta.textContent = `${file.name} (${fileSizeKb} KB) | ${sourceLabel}`;

    preview.appendChild(image);
    preview.appendChild(meta);
  }

  function setSubmitting(isSubmitting) {
    state.isSubmitting = isSubmitting;
    if (isSubmitting) {
      closeCameraCaptureUi();
    }
    if (submitButton) {
      submitButton.disabled = isSubmitting;
      submitButton.textContent = isSubmitting ? "Processing..." : "Process capture";
    }
    slotInputs.forEach((input) => {
      input.disabled = isSubmitting;
    });
    slotActionButtons.forEach((button) => {
      button.disabled = isSubmitting;
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
      state.capabilities = [];
      return null;
    }

    const user = payload?.data?.user || null;
    const capabilities = extractCapabilitiesFromUser(user);
    state.csrfToken = payload?.data?.csrf_token || null;
    state.capabilities = capabilities;
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

  function extractStfdTokenFromUrl(url) {
    const parameterNames = ["token", "jwt", "assertion"];
    for (const parameterName of parameterNames) {
      const value = String(url.searchParams.get(parameterName) || "").trim();
      if (value) {
        return value;
      }
    }

    const rawHash = String(url.hash || "").replace(/^#/, "").trim();
    if (!rawHash) {
      return "";
    }

    const hashSegments = [rawHash];
    const questionMarkIndex = rawHash.indexOf("?");
    if (questionMarkIndex >= 0 && questionMarkIndex + 1 < rawHash.length) {
      hashSegments.push(rawHash.slice(questionMarkIndex + 1));
    }

    for (const segment of hashSegments) {
      const params = new URLSearchParams(segment);
      for (const parameterName of parameterNames) {
        const value = String(params.get(parameterName) || "").trim();
        if (value) {
          return value;
        }
      }
    }

    return "";
  }

  function removeStfdTokenFromUrl(url) {
    const parameterNames = ["token", "jwt", "assertion"];
    parameterNames.forEach((parameterName) => {
      url.searchParams.delete(parameterName);
    });

    const rawHash = String(url.hash || "").replace(/^#/, "").trim();
    if (!rawHash) {
      return;
    }

    const questionMarkIndex = rawHash.indexOf("?");
    if (questionMarkIndex >= 0) {
      const hashPath = rawHash.slice(0, questionMarkIndex);
      const query = rawHash.slice(questionMarkIndex + 1);
      const params = new URLSearchParams(query);
      parameterNames.forEach((parameterName) => {
        params.delete(parameterName);
      });
      const nextQuery = params.toString();
      url.hash = nextQuery ? `#${hashPath}?${nextQuery}` : hashPath ? `#${hashPath}` : "";
      return;
    }

    if (rawHash.includes("=") || rawHash.includes("&")) {
      const params = new URLSearchParams(rawHash);
      const hadToken = parameterNames.some((parameterName) => params.has(parameterName));
      if (hadToken) {
        parameterNames.forEach((parameterName) => {
          params.delete(parameterName);
        });
        const nextHash = params.toString();
        url.hash = nextHash ? `#${nextHash}` : "";
      }
    }
  }

  async function consumeStfdTokenFromUrl() {
    const url = new URL(window.location.href);
    const token = extractStfdTokenFromUrl(url);
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
    removeStfdTokenFromUrl(url);
    window.history.replaceState({}, document.title, url.pathname + url.search + url.hash);
    if (!response.ok) {
      const message = payload?.error?.message || "Sign in failed.";
      throw new Error(message);
    }

    state.csrfToken = payload?.data?.csrf_token || null;
    state.capabilities = extractCapabilitiesFromUser(payload?.data?.user || null);
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

    if (!hasCapability("image.upload")) {
      setWorkflowVisible(false);
      setStatus("Your account does not have permission to upload images from this page.", true);
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
    if (!hasCapability("image.upload")) {
      throw new Error("Your account does not have permission to upload images from this page.");
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

  async function ensureExpectedImageTag(image, expectedTag, expectedJigsawId) {
    const imageId = Number(image?.id || 0);
    const imageJigsawId = Number(image?.jigsaw_id || 0);
    if (!imageId || imageJigsawId !== Number(expectedJigsawId)) {
      return;
    }

    const expected = normalizeTagForCompare(expectedTag);
    const current = normalizeTagForCompare(image?.tag);
    if (!expected || expected === current) {
      return;
    }

    if (!hasCapability("image.tag")) {
      throw new Error(
        `Image ${imageId} uploaded with tag "${image?.tag || ""}" instead of "${expectedTag}", and your account cannot retag images.`
      );
    }

    const response = await apiRequest(`/api/v1/image-library/images/${imageId}/tag`, {
      method: "PATCH",
      body: JSON.stringify({ tag: expectedTag }),
    });
    const updatedTag = response?.data?.tag;
    if (normalizeTagForCompare(updatedTag) !== expected) {
      throw new Error(`Image ${imageId} could not be retagged as "${expectedTag}".`);
    }
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
    selectedSlotFiles.clear();
    Object.keys(slotTagMap).forEach((slotKey) => {
      renderSlotPreview(slotKey);
    });
  }

  function getSlotInput(slotKey, source) {
    return form.querySelector(`[data-slot-file="${slotKey}"][data-slot-source="${source}"]`);
  }

  async function handleSlotActionClick(event) {
    const button = event.currentTarget;
    const slotKey = String(button?.getAttribute("data-slot-key") || "").trim();
    const source = String(button?.getAttribute("data-slot-action") || "").trim();
    if (!slotKey || !source) {
      return;
    }

    if (source === "camera") {
      const openedWithBrowserCamera = await openBrowserCamera(slotKey);
      if (openedWithBrowserCamera) {
        return;
      }
    }

    const input = getSlotInput(slotKey, source);
    if (!input || input.disabled) {
      return;
    }
    input.click();
  }

  function handleSlotInputChange(input) {
    const slotKey = String(input.getAttribute("data-slot-file") || "").trim();
    const source = String(input.getAttribute("data-slot-source") || "").trim();
    if (!slotKey || !source) {
      return;
    }

    if (input.files && input.files.length > 0) {
      selectedSlotFiles.set(slotKey, {
        file: input.files[0],
        source,
        inputId: input.id,
      });
      slotInputs.forEach((candidate) => {
        if (candidate === input) {
          return;
        }
        if (candidate.getAttribute("data-slot-file") === slotKey) {
          candidate.value = "";
        }
      });
    } else {
      const selected = selectedSlotFiles.get(slotKey);
      if (selected && selected.inputId === input.id) {
        selectedSlotFiles.delete(slotKey);
      }
    }

    renderSlotPreview(slotKey);
  }

  async function handleSubmit(event) {
    event.preventDefault();
    if (state.isSubmitting) {
      return;
    }
    if (!hasCapability("image.upload")) {
      setStatus("Please sign in with an account that can upload images.", true);
      return;
    }

    const entries = selectedSlotEntries();
    if (entries.length === 0) {
      setStatus("Add at least one photo before processing capture.", true);
      return;
    }

    const selectedBoxEntries = entries.filter((entry) => boxSlotKeys.includes(entry.slotKey));
    const selectedSeedEntries = entries.filter((entry) => jigsawSeedSlotKeys.includes(entry.slotKey));
    const completedEntry = entries.find((entry) => entry.slotKey === "completed") || null;
    const commentText = String(commentInput?.value || "").trim();

    setSubmitting(true);
    setStatus("Starting mobile capture workflow...");

    try {
      if (selectedSeedEntries.length === 0 && completedEntry && entries.length === 1) {
        setStatus("Uploading completed image to the unassigned image library...");
        const uploadPayload = await uploadImageLibraryItem(completedEntry.file, slotTagMap.completed, commentText);
        const createdCount = Number(uploadPayload?.data?.created_count || 0);
        const skippedCount = Number(uploadPayload?.data?.skipped_count || 0);
        setStatus(`Completed image stored as unassigned. Added ${createdCount} image(s), skipped ${skippedCount}.`);
        clearForm();
        return;
      }

      if (!hasCapability("jigsaw.create")) {
        throw new Error("Your account cannot create jigsaws from mobile capture uploads.");
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

      const uploadQueue = [...entries];
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
          continue;
        }
        await ensureExpectedImageTag(image, tag, jigsawId);
      }

      const shouldRunEnrich = hasCapability("jigsaw.enrich") && selectedBoxEntries.length > 0;
      if (shouldRunEnrich) {
        setStatus("Running AI enrich from uploaded box images...");
        await apiRequest(`/api/v1/jigsaws/${Number(jigsawId)}/enrich-from-images`, {
          method: "POST",
          body: JSON.stringify({ overwrite_existing: false }),
        });
      }

      const warningSuffix =
        duplicateWarnings.length > 0
          ? ` Duplicate image bytes were detected for ${duplicateWarnings.join(", ")}, so those images may already belong to another jigsaw.`
          : "";
      const enrichSuffix = shouldRunEnrich ? " and started enrichment" : "";
      setStatus(`Mobile capture complete. Created jigsaw #${jigsawId}${enrichSuffix}.${warningSuffix}`);
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
      state.capabilities = extractCapabilitiesFromUser(user);
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
    state.capabilities = [];
    syncAuthUi(null);
    setStatus("Signed out.");
  }

  slotInputs.forEach((input) => {
    input.addEventListener("change", () => handleSlotInputChange(input));
  });
  slotActionButtons.forEach((button) => {
    button.addEventListener("click", (event) => {
      void handleSlotActionClick(event);
    });
  });
  window.addEventListener("beforeunload", closeCameraCaptureUi);

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
        if (hasCapability("image.upload")) {
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
      if (user && hasCapability("image.upload")) {
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
