(() => {
  const IMAGE_BROWSER_TAG_BOX = "Box";
  const IMAGE_BROWSER_TAG_COMPLETED = "Completed";
  const IMAGE_BROWSER_TAG_BOX_FRONT = "Box front";
  const IMAGE_BROWSER_TAG_BOX_SIDE = "Box side";
  const IMAGE_BROWSER_TAG_BOX_BACK = "Box back";
  const IMAGE_BROWSER_TAG_REFERENCE = "Reference";
  const IMAGE_BROWSER_TAG_IN_PROGRESS = "In progress";
  const IMAGE_LIBRARY_STANDARD_TAGS = [
    "untagged",
    IMAGE_BROWSER_TAG_BOX,
    IMAGE_BROWSER_TAG_BOX_FRONT,
    IMAGE_BROWSER_TAG_BOX_SIDE,
    IMAGE_BROWSER_TAG_BOX_BACK,
    IMAGE_BROWSER_TAG_REFERENCE,
    IMAGE_BROWSER_TAG_COMPLETED,
    IMAGE_BROWSER_TAG_IN_PROGRESS,
  ];
  const THUMBNAIL_DISPLAY_WIDTH_PX = 150;
  const ADMIN_LIST_PAGE_SIZE = 25;
  const BROWSER_FILTER_MODE_IGNORE = "ignore";
  const BROWSER_FILTER_MODE_INCLUDE = "include";
  const BROWSER_FILTER_MODE_EXCLUDE = "exclude";
  const DIARY_VIEW_MODE_LIST = "list";
  const DIARY_VIEW_MODE_CALENDAR = "calendar";

  function createDefaultTableSortState() {
    return {
      users: { field: "id", direction: "asc" },
      jigsaws: { field: "title", direction: "asc" },
      jigsawImages: { field: "created_at", direction: "desc" },
      imageLibrary: { field: "captured_at", direction: "desc" },
      diary: { field: "completed_at", direction: "desc" },
      loans: { field: "checked_out_at", direction: "desc" },
      aiRecent: { field: "created_at", direction: "desc" },
      audit: { field: "created_at", direction: "desc" },
    };
  }

  const state = {
    csrfToken: null,
    user: null,
    authProvider: null,
    stfdAuthEnabled: false,
    stfdAllowLocalLogin: true,
    stfdLoginUrl: null,
    authDialogOpen: false,
    activeWorkspaceTab: null,
    workspaceTabVisibility: {
      account: false,
      collection: false,
      admin: false,
      "activity-log": false,
      loans: false,
    },
    activeCollectionTab: null,
    collectionTabVisibility: {
      "quick-create": false,
      jigsaws: false,
      images: false,
      "image-browser": false,
      diary: false,
    },
    activeAdminTab: null,
    adminTabVisibility: {
      users: false,
      ai: false,
      embeddings: false,
      "ip-blocks": false,
    },
    workspaceSectionAccess: {
      account: false,
      collection: false,
      admin: false,
      activityLog: false,
      loans: false,
    },
    roleDefinitions: [],
    users: [],
    jigsaws: [],
    jigsawSearchQuery: "",
    jigsawFilterWithoutDiaryEntries: false,
    loans: [],
    blockedIps: [],
    auditEvents: [],
    auditEventsMeta: null,
    jigsawThumbnailImages: [],
    jigsawImages: [],
    imageLibraryImages: [],
    imageLibraryFilterAssigned: true,
    imageLibraryFilterUnassigned: true,
    imageLibraryFilterTagSelections: {},
    aiUsageDiagnostics: null,
    imageEmbeddingDiagnostics: null,
    aiUsageRecentById: {},
    imageBrowserContentCacheByImageId: {},
    imageBrowserSavingImageIds: {},
    diaryEntries: [],
    diaryEditingEntryId: null,
    diarySelectionTouchedByUser: false,
    diaryViewMode: DIARY_VIEW_MODE_LIST,
    diaryCalendar: createInitialDiaryCalendarState(),
    bulkUploadFiles: [],
    bulkCreateJobId: null,
    bulkCreateJobPollTimer: null,
    imageEmbeddingBackfillJobId: null,
    imageEmbeddingBackfillPollTimer: null,
    jigsawExpandedImageRowsById: {},
    editorScrollPositions: {
      user: null,
      jigsaw: null,
      diary: null,
    },
    tableSorts: createDefaultTableSortState(),
    pagination: {
      jigsaws: 1,
      imageLibrary: 1,
      diary: 1,
      aiRecent: 1,
      audit: 1,
    },
    imageBrowser: {
      isOpen: false,
      index: 0,
      filterShowAll: false,
      filterModes: {
        unassigned: BROWSER_FILTER_MODE_INCLUDE,
        box: BROWSER_FILTER_MODE_IGNORE,
        reference: BROWSER_FILTER_MODE_IGNORE,
        completed: BROWSER_FILTER_MODE_IGNORE,
        inProgress: BROWSER_FILTER_MODE_IGNORE,
      },
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
      suggestionsImageId: null,
      nameAssignImageId: null,
    },
  };

  const elements = {
    feedback: document.getElementById("app-feedback"),
    feedbackText: document.getElementById("app-feedback-text"),
    sessionSummary: document.getElementById("session-summary"),
    authSection: document.getElementById("auth-section"),
    loginForm: document.getElementById("login-form"),
    loginSubmitButton: document.querySelector("#login-form button[type='submit']"),
    stfdLoginButton: document.getElementById("stfd-login-button"),
    loginEmail: document.getElementById("login-email"),
    loginPassword: document.getElementById("login-password"),
    authCredentialsWrap: document.getElementById("auth-credentials-wrap"),
    signInControls: document.getElementById("sign-in-controls"),
    signOutControls: document.getElementById("sign-out-controls"),
    signInHeaderControls: document.getElementById("sign-in-header-controls"),
    loginOpenButton: document.getElementById("login-open-button"),
    authDialogBackdrop: document.getElementById("auth-dialog-backdrop"),
    authDialogCloseButton: document.getElementById("auth-dialog-close"),
    accountNavButton: document.getElementById("account-nav-button"),
    workspaceTabs: document.getElementById("workspace-tabs"),
    workspaceTabButtons: Array.from(document.querySelectorAll("[data-workspace-tab]")),
    collectionSubtabs: document.getElementById("collection-subtabs"),
    collectionTabButtons: Array.from(document.querySelectorAll("[data-collection-tab]")),
    adminSubtabs: document.getElementById("admin-subtabs"),
    adminTabButtons: Array.from(document.querySelectorAll("[data-admin-tab]")),
    accountSection: document.getElementById("account-section"),
    accountForm: document.getElementById("account-form"),
    accountUsername: document.getElementById("account-username"),
    accountCurrentPassword: document.getElementById("account-current-password"),
    accountNewPassword: document.getElementById("account-new-password"),
    accountConfirmPassword: document.getElementById("account-confirm-password"),
    adminSections: document.getElementById("admin-sections"),
    usersSection: document.getElementById("users-section"),
    jigsawsSection: document.getElementById("jigsaws-section"),
    collectionQuickCreatePanel: document.getElementById("collection-quick-create-panel"),
    collectionJigsawsPanel: document.getElementById("collection-jigsaws-panel"),
    collectionImagesPanel: document.getElementById("collection-images-panel"),
    collectionImageBrowserPanel: document.getElementById("collection-image-browser-panel"),
    collectionDiaryPanel: document.getElementById("collection-diary-panel"),
    imageLibraryLoadSummary: document.getElementById("image-library-load-summary"),
    aiUsageSection: document.getElementById("ai-usage-section"),
    embeddingsSection: document.getElementById("embeddings-section"),
    loansSection: document.getElementById("loans-section"),
    auditSection: document.getElementById("audit-section"),
    ipBlocksSection: document.getElementById("ip-blocks-section"),
    logoutButton: document.getElementById("logout-button"),
    userCreateForm: document.getElementById("user-create-form"),
    userEditForm: document.getElementById("user-edit-form"),
    userEditSaveButton: document.getElementById("user-edit-save"),
    userEditCancelButton: document.getElementById("user-edit-cancel"),
    editUserId: document.getElementById("edit-user-id"),
    editUserEmail: document.getElementById("edit-user-email"),
    editUserDisplayName: document.getElementById("edit-user-display-name"),
    userRolesCheckboxes: document.getElementById("user-roles-checkboxes"),
    editUserRolesCheckboxes: document.getElementById("edit-user-roles-checkboxes"),
    editUserActive: document.getElementById("edit-user-active"),
    editUserPassword: document.getElementById("edit-user-password"),
    usersTableBody: document.getElementById("users-table-body"),
    jigsawCreateForm: document.getElementById("jigsaw-create-form"),
    jigsawEditForm: document.getElementById("jigsaw-edit-form"),
    jigsawEditSaveButton: document.getElementById("jigsaw-edit-save"),
    jigsawEditEnrichButton: document.getElementById("jigsaw-edit-enrich"),
    jigsawEditCancelButton: document.getElementById("jigsaw-edit-cancel"),
    editJigsawId: document.getElementById("edit-jigsaw-id"),
    editJigsawTitle: document.getElementById("edit-jigsaw-title"),
    editJigsawSeriesName: document.getElementById("edit-jigsaw-series-name"),
    editJigsawSeriesNumber: document.getElementById("edit-jigsaw-series-number"),
    editJigsawPieceCount: document.getElementById("edit-jigsaw-piece-count"),
    editJigsawManufacturer: document.getElementById("edit-jigsaw-manufacturer"),
    editJigsawArtist: document.getElementById("edit-jigsaw-artist"),
    editJigsawDimensionsCm: document.getElementById("edit-jigsaw-dimensions-cm"),
    editJigsawDescription: document.getElementById("edit-jigsaw-description"),
    editJigsawLastCompletedAt: document.getElementById("edit-jigsaw-last-completed-at"),
    editJigsawCondition: document.getElementById("edit-jigsaw-condition"),
    editJigsawStatus: document.getElementById("edit-jigsaw-status"),
    editJigsawTags: document.getElementById("edit-jigsaw-tags"),
    jigsawSearchInput: document.getElementById("jigsaw-search-input"),
    jigsawFilterNoDiary: document.getElementById("jigsaw-filter-no-diary"),
    jigsawsTableBody: document.getElementById("jigsaws-table-body"),
    jigsawsPaginationTop: document.getElementById("jigsaws-pagination-top"),
    jigsawsPagination: document.getElementById("jigsaws-pagination"),
    jigsawImageForm: document.getElementById("jigsaw-image-form"),
    jigsawImageJigsawId: document.getElementById("jigsaw-image-jigsaw-id"),
    jigsawImageTag: document.getElementById("jigsaw-image-tag"),
    jigsawImageFile: document.getElementById("jigsaw-image-file"),
    jigsawImagesTableBody: document.getElementById("jigsaw-images-table-body"),
    imageLibraryUploadForm: document.getElementById("image-library-upload-form"),
    imageLibraryJigsawId: document.getElementById("image-library-jigsaw-id"),
    imageLibraryTag: document.getElementById("image-library-tag"),
    imageLibraryBulkCreateWrap: document.getElementById("image-library-bulk-create-wrap"),
    imageLibraryBulkCreate: document.getElementById("image-library-bulk-create"),
    imageLibraryBulkCreateProgress: document.getElementById("image-library-bulk-create-progress"),
    imageLibraryBulkCreateProgressText: document.getElementById("image-library-bulk-create-progress-text"),
    imageLibraryDropzone: document.getElementById("image-library-dropzone"),
    imageLibraryBrowseButton: document.getElementById("image-library-browse-button"),
    imageLibraryFilesInput: document.getElementById("image-library-files"),
    imageLibraryFilesList: document.getElementById("image-library-files-list"),
    imageLibraryFilterAssigned: document.getElementById("image-library-filter-assigned"),
    imageLibraryFilterUnassigned: document.getElementById("image-library-filter-unassigned"),
    imageLibraryTagFilters: document.getElementById("image-library-tag-filters"),
    imageLibraryTableBody: document.getElementById("image-library-table-body"),
    imageLibraryPaginationTop: document.getElementById("image-library-pagination-top"),
    imageLibraryPagination: document.getElementById("image-library-pagination"),
    imageLibraryBulkCreateUnassignedBoxButton: document.getElementById("image-library-bulk-create-unassigned-box"),
    imageEmbeddingBackfillMissing: document.getElementById("image-embedding-backfill-missing"),
    imageEmbeddingBackfillStart: document.getElementById("image-embedding-backfill-start"),
    imageEmbeddingBackfillStatus: document.getElementById("image-embedding-backfill-status"),
    embeddingsModelKey: document.getElementById("embeddings-model-key"),
    embeddingsModelSource: document.getElementById("embeddings-model-source"),
    embeddingsLocalOnly: document.getElementById("embeddings-local-only"),
    embeddingsHealthTotalImages: document.getElementById("embeddings-health-total-images"),
    embeddingsHealthUpToDate: document.getElementById("embeddings-health-up-to-date"),
    embeddingsHealthStale: document.getElementById("embeddings-health-stale"),
    embeddingsHealthMissing: document.getElementById("embeddings-health-missing"),
    embeddingsHealthStatus: document.getElementById("embeddings-health-status"),
    embeddingsPerfSamples: document.getElementById("embeddings-perf-samples"),
    embeddingsPerfAvgMs: document.getElementById("embeddings-perf-avg-ms"),
    embeddingsPerfP95Ms: document.getElementById("embeddings-perf-p95-ms"),
    embeddingsPerfMinMaxMs: document.getElementById("embeddings-perf-min-max-ms"),
    embeddingsMissingGrid: document.getElementById("embeddings-missing-grid"),
    imageBrowserOpen: document.getElementById("image-browser-open"),
    imageBrowserModal: document.getElementById("image-browser-modal"),
    imageBrowserStatus: document.getElementById("image-browser-status"),
    imageBrowserFilterShowAll: document.getElementById("image-browser-filter-all"),
    imageBrowserFilterUnassigned: document.getElementById("image-browser-filter-unassigned"),
    imageBrowserFilterBox: document.getElementById("image-browser-filter-box"),
    imageBrowserFilterReference: document.getElementById("image-browser-filter-reference"),
    imageBrowserFilterCompleted: document.getElementById("image-browser-filter-completed"),
    imageBrowserFilterInProgress: document.getElementById("image-browser-filter-in-progress"),
    imageBrowserCanvas: document.getElementById("image-browser-canvas"),
    imageBrowserPrev: document.getElementById("image-browser-prev"),
    imageBrowserNext: document.getElementById("image-browser-next"),
    imageBrowserRotateLeft: document.getElementById("image-browser-rotate-left"),
    imageBrowserRotateRight: document.getElementById("image-browser-rotate-right"),
    imageBrowserMarkBox: document.getElementById("image-browser-mark-box"),
    imageBrowserMarkCompleted: document.getElementById("image-browser-mark-completed"),
    imageBrowserAssignPrevious: document.getElementById("image-browser-assign-previous"),
    imageBrowserAssignNext: document.getElementById("image-browser-assign-next"),
    imageBrowserMarkBoxSide: document.getElementById("image-browser-mark-box-side"),
    imageBrowserMarkBoxBack: document.getElementById("image-browser-mark-box-back"),
    imageBrowserMarkReference: document.getElementById("image-browser-mark-reference"),
    imageBrowserMarkInProgress: document.getElementById("image-browser-mark-in-progress"),
    imageBrowserFindSimilar: document.getElementById("image-browser-find-similar"),
    imageBrowserFindName: document.getElementById("image-browser-find-name"),
    imageBrowserCreateJigsaw: document.getElementById("image-browser-create-jigsaw"),
    imageBrowserDelete: document.getElementById("image-browser-delete"),
    imageBrowserCropToggle: document.getElementById("image-browser-crop-toggle"),
    imageBrowserCropApply: document.getElementById("image-browser-crop-apply"),
    imageBrowserSaveCreate: document.getElementById("image-browser-save-create"),
    imageBrowserSave: document.getElementById("image-browser-save"),
    imageBrowserSuggestionsModal: document.getElementById("image-browser-suggestions-modal"),
    imageBrowserSuggestionsSummary: document.getElementById("image-browser-suggestions-summary"),
    imageBrowserSuggestionsList: document.getElementById("image-browser-suggestions-list"),
    imageBrowserSuggestionsClose: document.getElementById("image-browser-suggestions-close"),
    imageBrowserNameAssignModal: document.getElementById("image-browser-name-assign-modal"),
    imageBrowserNameAssignSummary: document.getElementById("image-browser-name-assign-summary"),
    imageBrowserNameQuery: document.getElementById("image-browser-name-query"),
    imageBrowserNameResults: document.getElementById("image-browser-name-results"),
    imageBrowserNamePreview: document.getElementById("image-browser-name-preview"),
    imageBrowserNameAssign: document.getElementById("image-browser-name-assign"),
    imageBrowserNameAssignClose: document.getElementById("image-browser-name-assign-close"),
    imageBrowserClose: document.getElementById("image-browser-close"),
    diaryEntryForm: document.getElementById("diary-entry-form"),
    diaryEntrySubmitButton: document.getElementById("diary-entry-submit"),
    diaryEntryCancelButton: document.getElementById("diary-entry-cancel"),
    diaryJigsawId: document.getElementById("diary-jigsaw-id"),
    diaryCompletedAt: document.getElementById("diary-completed-at"),
    diaryDifficulty: document.getElementById("diary-difficulty"),
    diaryNotes: document.getElementById("diary-notes"),
    diaryViewModeButtons: Array.from(document.querySelectorAll("[data-diary-view-mode]")),
    diaryListRegion: document.getElementById("diary-list-region"),
    diaryCalendarRegion: document.getElementById("diary-calendar-region"),
    diaryCalendarControls: document.getElementById("diary-calendar-controls"),
    diaryCalendarPrevButton: document.getElementById("diary-calendar-prev"),
    diaryCalendarNextButton: document.getElementById("diary-calendar-next"),
    diaryCalendarTodayButton: document.getElementById("diary-calendar-today"),
    diaryCalendarMonthLabel: document.getElementById("diary-calendar-month-label"),
    diaryCalendarSummary: document.getElementById("diary-calendar-summary"),
    diaryCalendarGrid: document.getElementById("diary-calendar-grid"),
    diaryEntriesCaption: document.getElementById("diary-entries-caption"),
    diaryEntriesTableBody: document.getElementById("diary-entries-table-body"),
    diaryPaginationTop: document.getElementById("diary-pagination-top"),
    diaryPagination: document.getElementById("diary-pagination"),
    loanCreateForm: document.getElementById("loan-create-form"),
    loanBorrowerUserId: document.getElementById("loan-borrower-user-id"),
    loanJigsawId: document.getElementById("loan-jigsaw-id"),
    loansTableBody: document.getElementById("loans-table-body"),
    ipBlockCreateForm: document.getElementById("ip-block-create-form"),
    ipBlockHours: document.getElementById("ip-block-hours"),
    ipBlocksTableBody: document.getElementById("ip-blocks-table-body"),
    auditTableBody: document.getElementById("audit-table-body"),
    aiUsageTodayCost: document.getElementById("ai-usage-today-cost"),
    aiUsageTodayCalls: document.getElementById("ai-usage-today-calls"),
    aiUsageTodaySuccess: document.getElementById("ai-usage-today-success"),
    aiUsageTodayTokens: document.getElementById("ai-usage-today-tokens"),
    aiUsage7dCost: document.getElementById("ai-usage-7d-cost"),
    aiUsage7dCalls: document.getElementById("ai-usage-7d-calls"),
    aiUsage7dSuccess: document.getElementById("ai-usage-7d-success"),
    aiUsage7dTokens: document.getElementById("ai-usage-7d-tokens"),
    aiUsage30dCost: document.getElementById("ai-usage-30d-cost"),
    aiUsage30dCalls: document.getElementById("ai-usage-30d-calls"),
    aiUsage30dSuccess: document.getElementById("ai-usage-30d-success"),
    aiUsage30dTokens: document.getElementById("ai-usage-30d-tokens"),
    aiUsageDailyBudget: document.getElementById("ai-usage-daily-budget"),
    aiUsageDailySpend: document.getElementById("ai-usage-daily-spend"),
    aiUsageBudgetReached: document.getElementById("ai-usage-budget-reached"),
    aiUsageOperationBody: document.getElementById("ai-usage-operation-body"),
    aiUsageModelBody: document.getElementById("ai-usage-model-body"),
    aiUsageRecentBody: document.getElementById("ai-usage-recent-body"),
    aiUsageRecentPaginationTop: document.getElementById("ai-usage-recent-pagination-top"),
    aiUsageRecentPagination: document.getElementById("ai-usage-recent-pagination"),
    aiUsageDetailModal: document.getElementById("ai-usage-detail-modal"),
    aiUsageDetailSummary: document.getElementById("ai-usage-detail-summary"),
    aiUsageDetailPayload: document.getElementById("ai-usage-detail-payload"),
    aiUsageDetailCloseButton: document.getElementById("ai-usage-detail-close"),
    auditPaginationTop: document.getElementById("audit-pagination-top"),
    auditPagination: document.getElementById("audit-pagination"),
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

  function syncLoginUiForAuthMode() {
    if (!elements.authCredentialsWrap || !elements.loginSubmitButton) {
      return;
    }

    const stfdOnlyMode = state.stfdAuthEnabled && !state.stfdAllowLocalLogin;

    if (stfdOnlyMode) {
      elements.authCredentialsWrap.hidden = true;
      elements.loginSubmitButton.textContent = "Sign in with STFD";
      if (elements.loginEmail) {
        elements.loginEmail.required = false;
        elements.loginEmail.disabled = true;
      }
      if (elements.loginPassword) {
        elements.loginPassword.required = false;
        elements.loginPassword.disabled = true;
      }
      if (elements.stfdLoginButton) {
        elements.stfdLoginButton.hidden = true;
      }
      return;
    }

    elements.authCredentialsWrap.hidden = false;
    elements.loginSubmitButton.textContent = "Sign in";
    if (elements.loginEmail) {
      elements.loginEmail.disabled = false;
      elements.loginEmail.required = true;
    }
    if (elements.loginPassword) {
      elements.loginPassword.disabled = false;
      elements.loginPassword.required = true;
    }
    if (elements.stfdLoginButton) {
      elements.stfdLoginButton.hidden = !state.stfdAuthEnabled;
    }
  }

  function syncHeaderAuthControls() {
    const isSignedIn = Boolean(state.user);
    const isStfdSession = String(state.authProvider || "").toLowerCase() === "stfd";

    if (elements.signOutControls) {
      elements.signOutControls.hidden = !isSignedIn;
    }
    if (elements.logoutButton) {
      elements.logoutButton.hidden = !isSignedIn;
    }
    if (elements.accountNavButton) {
      elements.accountNavButton.hidden = !isSignedIn || isStfdSession;
    }
    if (elements.signInHeaderControls) {
      elements.signInHeaderControls.hidden = isSignedIn;
    }
  }

  function openAuthDialog() {
    if (!elements.authDialogBackdrop || state.user) {
      return;
    }
    state.authDialogOpen = true;
    elements.authDialogBackdrop.hidden = false;
    syncLoginUiForAuthMode();
    const targetInput = state.stfdAuthEnabled && !state.stfdAllowLocalLogin ? elements.loginSubmitButton : elements.loginEmail;
    if (targetInput) {
      targetInput.focus();
    }
  }

  function closeAuthDialog() {
    if (!elements.authDialogBackdrop) {
      return;
    }
    state.authDialogOpen = false;
    elements.authDialogBackdrop.hidden = true;
  }

  function setImageLibraryLoadSummary(message) {
    if (!elements.imageLibraryLoadSummary) {
      return;
    }
    elements.imageLibraryLoadSummary.textContent = String(message || "");
  }

  async function apiRequest(path, options = {}) {
    const { timeoutMs: timeoutMsOption, ...fetchOptions } = options || {};
    const headers = new Headers(options.headers || {});
    headers.set("Accept", "application/json");

    if (fetchOptions.body && !(fetchOptions.body instanceof FormData) && !headers.has("Content-Type")) {
      headers.set("Content-Type", "application/json");
    }

    const method = (fetchOptions.method || "GET").toUpperCase();
    if (["POST", "PUT", "PATCH", "DELETE"].includes(method) && state.csrfToken) {
      headers.set("X-CSRF-Token", state.csrfToken);
    }

    const parsedTimeoutMs = Number(timeoutMsOption);
    const timeoutMs = Number.isFinite(parsedTimeoutMs) && parsedTimeoutMs > 0 ? parsedTimeoutMs : 120000;
    const timeoutSeconds = Math.max(1, Math.round(timeoutMs / 1000));
    const abortController = new AbortController();
    const parentSignal = fetchOptions.signal;
    if (parentSignal) {
      if (parentSignal.aborted) {
        abortController.abort(parentSignal.reason);
      } else {
        parentSignal.addEventListener(
          "abort",
          () => {
            abortController.abort(parentSignal.reason);
          },
          { once: true }
        );
      }
    }

    let timeoutHandle = null;
    timeoutHandle = setTimeout(() => {
      abortController.abort();
    }, timeoutMs);

    let response;
    try {
      response = await fetch(path, {
        credentials: "same-origin",
        ...fetchOptions,
        method,
        headers,
        signal: abortController.signal,
      });
    } catch (error) {
      if (error?.name === "AbortError") {
        throw new Error(`Request timed out after ${timeoutSeconds}s.`);
      }
      throw error;
    } finally {
      if (timeoutHandle !== null) {
        clearTimeout(timeoutHandle);
      }
    }

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

  function clearPagination(container) {
    if (!container) {
      return;
    }
    container.innerHTML = "";
  }

  function clampPageNumber(page, totalItems, pageSize) {
    const totalPages = Math.max(1, Math.ceil(totalItems / pageSize));
    const normalizedPage = Number.isFinite(page) ? Math.trunc(page) : 1;
    return Math.min(Math.max(1, normalizedPage), totalPages);
  }

  function paginateItems(items, paginationKey) {
    const sourceItems = Array.isArray(items) ? items : [];
    const totalItems = sourceItems.length;
    const totalPages = Math.max(1, Math.ceil(totalItems / ADMIN_LIST_PAGE_SIZE));
    const currentPage = clampPageNumber(state.pagination[paginationKey], totalItems, ADMIN_LIST_PAGE_SIZE);
    const startIndex = (currentPage - 1) * ADMIN_LIST_PAGE_SIZE;
    const endIndex = startIndex + ADMIN_LIST_PAGE_SIZE;

    state.pagination[paginationKey] = currentPage;
    return {
      page: currentPage,
      totalItems,
      totalPages,
      startIndex,
      endIndex: Math.min(endIndex, totalItems),
      rows: sourceItems.slice(startIndex, endIndex),
    };
  }

  function renderPagination(container, paginationKey, pageResult) {
    if (!container) {
      return;
    }

    clearPagination(container);
    if (!pageResult || pageResult.totalItems <= 0) {
      return;
    }

    const summary = document.createElement("p");
    summary.className = "govuk-body-s app-pagination__summary";
    summary.textContent = `Showing ${pageResult.startIndex + 1}-${pageResult.endIndex} of ${pageResult.totalItems}`;
    container.appendChild(summary);

    if (pageResult.totalPages <= 1) {
      return;
    }

    const controls = document.createElement("div");
    controls.className = "app-pagination__controls";

    const previousButton = document.createElement("button");
    previousButton.type = "button";
    previousButton.className = "govuk-button govuk-button--secondary app-inline-button app-pagination__button";
    previousButton.setAttribute("data-module", "govuk-button");
    previousButton.dataset.paginationList = paginationKey;
    previousButton.dataset.paginationPage = String(pageResult.page - 1);
    previousButton.disabled = pageResult.page <= 1;
    previousButton.textContent = "Previous";
    controls.appendChild(previousButton);

    const pageLabel = document.createElement("span");
    pageLabel.className = "govuk-body-s app-pagination__page";
    pageLabel.textContent = `Page ${pageResult.page} of ${pageResult.totalPages}`;
    controls.appendChild(pageLabel);

    const nextButton = document.createElement("button");
    nextButton.type = "button";
    nextButton.className = "govuk-button govuk-button--secondary app-inline-button app-pagination__button";
    nextButton.setAttribute("data-module", "govuk-button");
    nextButton.dataset.paginationList = paginationKey;
    nextButton.dataset.paginationPage = String(pageResult.page + 1);
    nextButton.disabled = pageResult.page >= pageResult.totalPages;
    nextButton.textContent = "Next";
    controls.appendChild(nextButton);

    container.appendChild(controls);
  }

  function renderPaginationPair(topContainer, bottomContainer, paginationKey, pageResult) {
    renderPagination(topContainer, paginationKey, pageResult);
    renderPagination(bottomContainer, paginationKey, pageResult);
  }

  function rememberEditorScrollPosition(editorKey) {
    if (typeof window === "undefined") {
      return;
    }
    if (!Object.prototype.hasOwnProperty.call(state.editorScrollPositions, editorKey)) {
      return;
    }
    if (state.editorScrollPositions[editorKey] === null) {
      state.editorScrollPositions[editorKey] = window.scrollY;
    }
  }

  function scrollToEditor(editorElement) {
    if (!editorElement || typeof editorElement.scrollIntoView !== "function") {
      return;
    }
    editorElement.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function restoreEditorScrollPosition(editorKey) {
    if (typeof window === "undefined") {
      return;
    }
    const rememberedPosition = state.editorScrollPositions[editorKey];
    if (rememberedPosition === null || !Number.isFinite(rememberedPosition)) {
      return;
    }
    state.editorScrollPositions[editorKey] = null;
    window.scrollTo({ top: rememberedPosition, behavior: "smooth" });
  }

  const TABLE_SORT_CONFIG = {
    users: {
      defaultField: "id",
      defaultDirection: "asc",
      fields: {
        id: { type: "number", getValue: (row) => row?.id },
        email: { type: "string", getValue: (row) => row?.email },
        display_name: { type: "string", getValue: (row) => row?.display_name },
        roles: { type: "string", getValue: (row) => (Array.isArray(row?.roles) ? row.roles.join(", ") : "") },
        status: { type: "string", getValue: (row) => (row?.is_active ? "active" : "inactive") },
      },
    },
    jigsaws: {
      defaultField: "title",
      defaultDirection: "asc",
      fields: {
        title: { type: "string", getValue: (row) => row?.title },
        piece_count: { type: "number", getValue: (row) => row?.piece_count },
        last_completed_at: { type: "date", getValue: (row) => row?.last_completed_at },
      },
    },
    jigsawImages: {
      defaultField: "created_at",
      defaultDirection: "desc",
      fields: {
        tag: { type: "string", getValue: (row) => row?.tag },
        filename: { type: "string", getValue: (row) => row?.filename },
        created_at: { type: "date", getValue: (row) => row?.created_at },
      },
    },
    imageLibrary: {
      defaultField: "captured_at",
      defaultDirection: "desc",
      fields: {
        filename: { type: "string", getValue: (row) => row?.filename },
        associated_jigsaw: {
          type: "string",
          getValue: (row) => {
            const jigsawId = Number(row?.jigsaw_id || 0);
            if (!jigsawId) {
              return "unassigned";
            }
            const jigsaw = state.jigsaws.find((entry) => Number(entry?.id || 0) === jigsawId);
            if (!jigsaw) {
              return `id ${jigsawId}`;
            }
            return `${jigsaw.title || "(untitled)"} (id ${jigsaw.id})`;
          },
        },
        tag: { type: "string", getValue: (row) => row?.tag },
        captured_at: { type: "date", getValue: (row) => row?.captured_at },
      },
    },
    diary: {
      defaultField: "completed_at",
      defaultDirection: "desc",
      fields: {
        id: {
          type: "number",
          getValue: (row) => {
            const isOrphan = row?.entry_type === "orphan_completed_image";
            return isOrphan ? Number(row?.source_image_id || row?.id || 0) : Number(row?.id || 0);
          },
        },
        jigsaw_title: {
          type: "string",
          getValue: (row) => {
            if (row?.entry_type === "orphan_completed_image") {
              return "Unlinked completion";
            }
            return getJigsawTitleById(row?.jigsaw_id);
          },
        },
        completed_at: { type: "date", getValue: (row) => row?.completed_at },
        difficulty: { type: "number", getValue: (row) => row?.difficulty },
        notes: { type: "string", getValue: (row) => row?.notes },
      },
    },
    loans: {
      defaultField: "checked_out_at",
      defaultDirection: "desc",
      fields: {
        id: { type: "number", getValue: (row) => row?.id },
        borrower: {
          type: "string",
          getValue: (row) => {
            const user = state.users.find((entry) => Number(entry?.id || 0) === Number(row?.borrower_user_id || 0));
            return user ? `${user.email} (id ${user.id})` : `id ${row?.borrower_user_id || "-"}`;
          },
        },
        jigsaw: {
          type: "string",
          getValue: (row) => {
            const jigsaw = state.jigsaws.find((entry) => Number(entry?.id || 0) === Number(row?.jigsaw_id || 0));
            return jigsaw ? `${jigsaw.title} (id ${jigsaw.id})` : `id ${row?.jigsaw_id || "-"}`;
          },
        },
        checked_out_at: { type: "date", getValue: (row) => row?.checked_out_at },
        due_at: { type: "date", getValue: (row) => row?.due_at },
        status: { type: "string", getValue: (row) => row?.status },
      },
    },
    aiRecent: {
      defaultField: "created_at",
      defaultDirection: "desc",
      fields: {
        created_at: { type: "date", getValue: (row) => row?.created_at },
        operation: { type: "string", getValue: (row) => row?.operation },
        model: { type: "string", getValue: (row) => row?.model },
        status: { type: "string", getValue: (row) => row?.status },
        image_id: { type: "number", getValue: (row) => row?.image_id },
        total_tokens: { type: "number", getValue: (row) => row?.total_tokens },
        final_cost_usd: { type: "number", getValue: (row) => row?.final_cost_usd },
        request_id: { type: "string", getValue: (row) => row?.request_id },
        error_message: { type: "string", getValue: (row) => row?.error_message },
      },
    },
    audit: {
      defaultField: "created_at",
      defaultDirection: "desc",
      fields: {
        id: { type: "number", getValue: (row) => row?.id },
        action: { type: "string", getValue: (row) => row?.action },
        entity: { type: "string", getValue: (row) => `${row?.entity_type || "-"}:${row?.entity_id || "-"}` },
        actor_user_id: { type: "number", getValue: (row) => row?.actor_user_id },
        created_at: { type: "date", getValue: (row) => row?.created_at },
      },
    },
  };

  function normalizeSortDirection(direction) {
    return String(direction || "").toLowerCase() === "desc" ? "desc" : "asc";
  }

  function getTableSortState(listKey) {
    const config = TABLE_SORT_CONFIG[listKey];
    if (!config) {
      return null;
    }

    const existing = state.tableSorts[listKey] || {};
    const field = Object.prototype.hasOwnProperty.call(config.fields, existing.field)
      ? existing.field
      : config.defaultField;
    const direction = normalizeSortDirection(existing.direction || config.defaultDirection);
    return { field, direction };
  }

  function normalizeSortableValue(rawValue, valueType) {
    if (valueType === "number") {
      const parsed = Number(rawValue);
      return Number.isFinite(parsed) ? parsed : null;
    }
    if (valueType === "date") {
      if (!rawValue) {
        return null;
      }
      const timestamp = Date.parse(String(rawValue));
      return Number.isFinite(timestamp) ? timestamp : null;
    }
    return String(rawValue || "").toLocaleLowerCase();
  }

  function compareSortableValues(leftValue, rightValue, valueType) {
    const normalizedLeft = normalizeSortableValue(leftValue, valueType);
    const normalizedRight = normalizeSortableValue(rightValue, valueType);

    const leftMissing = normalizedLeft === null || normalizedLeft === undefined || normalizedLeft === "";
    const rightMissing = normalizedRight === null || normalizedRight === undefined || normalizedRight === "";
    if (leftMissing && rightMissing) {
      return 0;
    }
    if (leftMissing) {
      return 1;
    }
    if (rightMissing) {
      return -1;
    }

    if (valueType === "number" || valueType === "date") {
      return Number(normalizedLeft) - Number(normalizedRight);
    }
    return String(normalizedLeft).localeCompare(String(normalizedRight));
  }

  function sortRowsForTable(rows, listKey) {
    const sourceRows = Array.isArray(rows) ? rows : [];
    const config = TABLE_SORT_CONFIG[listKey];
    if (!config || sourceRows.length <= 1) {
      return [...sourceRows];
    }

    const sortState = getTableSortState(listKey);
    if (!sortState) {
      return [...sourceRows];
    }

    const fieldConfig = config.fields[sortState.field] || config.fields[config.defaultField];
    if (!fieldConfig || typeof fieldConfig.getValue !== "function") {
      return [...sourceRows];
    }

    const directionFactor = sortState.direction === "desc" ? -1 : 1;
    return sourceRows
      .map((row, index) => ({ row, index }))
      .sort((left, right) => {
        const comparison = compareSortableValues(
          fieldConfig.getValue(left.row),
          fieldConfig.getValue(right.row),
          fieldConfig.type,
        );
        if (comparison === 0) {
          return left.index - right.index;
        }
        return comparison * directionFactor;
      })
      .map((entry) => entry.row);
  }

  function updateSortableTableHeaders() {
    const sortableHeaders = document.querySelectorAll("th[data-sort-list][data-sort-field]");
    sortableHeaders.forEach((header) => {
      const listKey = String(header.getAttribute("data-sort-list") || "").trim();
      const field = String(header.getAttribute("data-sort-field") || "").trim();
      const sortState = getTableSortState(listKey);
      const isActive = Boolean(sortState && sortState.field === field);
      const direction = isActive ? sortState.direction : "none";

      header.setAttribute("tabindex", "0");
      header.setAttribute("role", "button");
      header.classList.add("app-sortable-header");
      header.dataset.sortDirection = direction;
      header.setAttribute(
        "aria-sort",
        direction === "asc" ? "ascending" : direction === "desc" ? "descending" : "none",
      );
      header.setAttribute(
        "title",
        isActive
          ? `Sorted ${direction === "asc" ? "ascending" : "descending"}. Click to sort ${direction === "asc" ? "descending" : "ascending"}.`
          : "Click to sort ascending.",
      );
    });
  }

  function rerenderSortedTable(listKey) {
    if (listKey === "users") {
      renderUsers(state.users);
      return;
    }
    if (listKey === "jigsaws") {
      renderJigsaws(state.jigsaws);
      return;
    }
    if (listKey === "jigsawImages") {
      renderJigsawImages(state.jigsawImages);
      return;
    }
    if (listKey === "imageLibrary") {
      renderImageLibraryImages(state.imageLibraryImages);
      return;
    }
    if (listKey === "diary") {
      const selectedJigsawId = Number(elements.diaryJigsawId?.value || "0");
      renderDiaryEntries(state.diaryEntries, getDiaryEntriesEmptyMessage(selectedJigsawId));
      return;
    }
    if (listKey === "loans") {
      renderLoans(state.loans);
      return;
    }
    if (listKey === "aiRecent") {
      renderAiUsageDiagnostics(state.aiUsageDiagnostics);
      return;
    }
    if (listKey === "audit") {
      renderAuditEvents(state.auditEvents);
    }
  }

  function applySortFromHeader(header) {
    const listKey = String(header.getAttribute("data-sort-list") || "").trim();
    const field = String(header.getAttribute("data-sort-field") || "").trim();
    const config = TABLE_SORT_CONFIG[listKey];
    if (!listKey || !field || !config || !Object.prototype.hasOwnProperty.call(config.fields, field)) {
      return;
    }

    const currentSort = getTableSortState(listKey) || { field: config.defaultField, direction: config.defaultDirection };
    const currentDirection = normalizeSortDirection(currentSort.direction);
    const nextDirection = currentSort.field === field && currentDirection === "asc" ? "desc" : "asc";

    state.tableSorts[listKey] = { field, direction: nextDirection };
    if (["jigsaws", "imageLibrary", "diary"].includes(listKey)) {
      state.pagination[listKey] = 1;
    }

    rerenderSortedTable(listKey);
    updateSortableTableHeaders();
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

  function buildThumbnailWidget(contentUrl, options = {}) {
    const container = document.createElement("div");
    container.className = "app-thumbnail-cell";

    const altText = String(options.altText || "Thumbnail image");
    const fallbackText = String(options.fallbackText || "No image");
    const previewUrl = String(options.previewUrl || contentUrl || "");
    const openUrl = String(options.openUrl || contentUrl || "");
    const displayWidth = Number(options.widthPx || THUMBNAIL_DISPLAY_WIDTH_PX);

    if (!contentUrl) {
      const fallback = document.createElement("div");
      fallback.className = "app-thumbnail-trigger";
      fallback.style.width = `${displayWidth}px`;

      const fallbackLabel = document.createElement("span");
      fallbackLabel.className = "app-thumbnail-fallback";
      fallbackLabel.textContent = fallbackText;
      fallback.appendChild(fallbackLabel);

      container.appendChild(fallback);
      return container;
    }

    const trigger = document.createElement("a");
    trigger.className = "app-thumbnail-trigger";
    trigger.style.width = `${displayWidth}px`;
    trigger.href = openUrl;
    trigger.target = "_blank";
    trigger.rel = "noopener noreferrer";
    trigger.setAttribute("aria-label", `Open ${altText}`);

    const image = document.createElement("img");
    image.className = "app-thumbnail-image";
    image.src = String(contentUrl);
    image.alt = altText;
    image.loading = "lazy";
    image.decoding = "async";
    trigger.appendChild(image);

    const preview = document.createElement("div");
    preview.className = "app-thumbnail-preview";
    preview.setAttribute("aria-hidden", "true");

    const previewImage = document.createElement("img");
    previewImage.dataset.previewSrc = previewUrl;
    previewImage.alt = "";
    previewImage.loading = "lazy";
    previewImage.decoding = "async";

    const loadPreviewImage = () => {
      const nextPreviewSrc = String(previewImage.dataset.previewSrc || "");
      if (!nextPreviewSrc || previewImage.src) {
        return;
      }
      previewImage.src = nextPreviewSrc;
    };

    trigger.addEventListener("mouseenter", loadPreviewImage, { once: true });
    trigger.addEventListener("focus", loadPreviewImage, { once: true });

    preview.appendChild(previewImage);

    container.appendChild(trigger);
    container.appendChild(preview);
    return container;
  }

  function buildThumbnailCell(contentUrl, options = {}) {
    const cell = document.createElement("td");
    cell.className = "govuk-table__cell app-thumbnail-cell";
    const widget = buildThumbnailWidget(contentUrl, options);
    cell.appendChild(widget);
    return cell;
  }

  function imageTagPriority(tag) {
    const normalized = toImageTagKey(tag);
    if (normalized === toImageTagKey(IMAGE_BROWSER_TAG_BOX)) {
      return 0;
    }
    if (normalized === toImageTagKey(IMAGE_BROWSER_TAG_COMPLETED)) {
      return 1;
    }
    return 2;
  }

  function buildPreferredJigsawImageByJigsawId(images) {
    const preferredByJigsawId = new Map();
    if (!Array.isArray(images)) {
      return preferredByJigsawId;
    }

    images.forEach((image) => {
      const jigsawId = Number(image?.jigsaw_id || 0);
      if (!jigsawId || !image?.content_url) {
        return;
      }

      const existing = preferredByJigsawId.get(jigsawId);
      if (!existing) {
        preferredByJigsawId.set(jigsawId, image);
        return;
      }

      const candidatePriority = imageTagPriority(image.tag);
      const existingPriority = imageTagPriority(existing.tag);
      const candidateId = Number(image.id || 0);
      const existingId = Number(existing.id || 0);

      if (candidatePriority < existingPriority || (candidatePriority === existingPriority && candidateId > existingId)) {
        preferredByJigsawId.set(jigsawId, image);
      }
    });

    return preferredByJigsawId;
  }

  function compareJigsawAssignedImages(left, right) {
    const leftPriority = imageTagPriority(left?.tag);
    const rightPriority = imageTagPriority(right?.tag);
    if (leftPriority !== rightPriority) {
      return leftPriority - rightPriority;
    }

    const leftId = Number(left?.id || 0);
    const rightId = Number(right?.id || 0);
    if (leftId !== rightId) {
      return rightId - leftId;
    }

    const leftCreatedAt = String(left?.created_at || "");
    const rightCreatedAt = String(right?.created_at || "");
    return rightCreatedAt.localeCompare(leftCreatedAt);
  }

  function buildAssignedJigsawImagesByJigsawId(images) {
    const imagesByJigsawId = new Map();
    if (!Array.isArray(images)) {
      return imagesByJigsawId;
    }

    images.forEach((image) => {
      const jigsawId = Number(image?.jigsaw_id || 0);
      if (!jigsawId || !image?.content_url) {
        return;
      }

      const existing = imagesByJigsawId.get(jigsawId);
      if (existing) {
        existing.push(image);
      } else {
        imagesByJigsawId.set(jigsawId, [image]);
      }
    });

    imagesByJigsawId.forEach((entries, jigsawId) => {
      imagesByJigsawId.set(jigsawId, [...entries].sort(compareJigsawAssignedImages));
    });
    return imagesByJigsawId;
  }

  function getAdditionalAssignedImagesForJigsaw(jigsawId, preferredImage, imagesByJigsawId) {
    const assignedImages = imagesByJigsawId.get(Number(jigsawId)) || [];
    if (assignedImages.length === 0) {
      return [];
    }

    const preferredImageId = Number(preferredImage?.id || 0);
    if (preferredImageId > 0) {
      return assignedImages.filter((image) => Number(image?.id || 0) !== preferredImageId);
    }

    if (assignedImages.length <= 1) {
      return [];
    }
    return assignedImages.slice(1);
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

  function toIntegerLabel(value) {
    const parsed = Number(value || 0);
    if (!Number.isFinite(parsed)) {
      return "0";
    }
    return Math.trunc(parsed).toLocaleString();
  }

  function toUsdLabel(value) {
    const parsed = Number.parseFloat(String(value ?? "0"));
    if (!Number.isFinite(parsed)) {
      return "$0.0000";
    }
    return `$${parsed.toFixed(4)}`;
  }

  function toMillisecondsLabel(value) {
    const parsed = Number(value);
    if (!Number.isFinite(parsed) || parsed < 0) {
      return "-";
    }
    return `${Math.trunc(parsed).toLocaleString()} ms`;
  }

  function buildAiStatusTag(statusValue) {
    const normalizedStatus = String(statusValue || "").trim().toLowerCase();
    const tag = document.createElement("span");
    tag.className = "app-ai-status-tag";

    if (normalizedStatus === "success") {
      tag.classList.add("app-ai-status-tag--success");
      tag.textContent = "OK";
      return tag;
    }

    if (normalizedStatus === "error") {
      tag.classList.add("app-ai-status-tag--error");
      tag.textContent = "ERROR";
      return tag;
    }

    tag.classList.add("app-ai-status-tag--blocked");
    tag.textContent = normalizedStatus ? normalizedStatus.toUpperCase() : "-";
    return tag;
  }

  function buildAiFailureHintForImage(imageId, requestId) {
    const diagnostics = state.aiUsageDiagnostics;
    const recentCalls = Array.isArray(diagnostics?.recent_calls) ? diagnostics.recent_calls : [];
    if (recentCalls.length === 0) {
      return "";
    }

    let matchingCall = null;
    if (requestId) {
      matchingCall = recentCalls.find((entry) => String(entry?.request_id || "") === String(requestId));
    }
    if (!matchingCall && imageId) {
      matchingCall = recentCalls.find((entry) => Number(entry?.image_id || 0) === Number(imageId) && String(entry?.status || "") === "error");
    }
    if (!matchingCall) {
      return "";
    }

    const parts = [];
    if (matchingCall.error_code) {
      parts.push(matchingCall.error_code);
    }
    if (matchingCall.provider_http_status) {
      parts.push(`HTTP ${matchingCall.provider_http_status}`);
    }
    if (matchingCall.error_message) {
      parts.push(matchingCall.error_message);
    }

    return parts.length > 0 ? parts.join(" | ") : "";
  }

  function closeAiUsageDetailModal() {
    if (elements.aiUsageDetailModal) {
      elements.aiUsageDetailModal.hidden = true;
    }
  }

  function openAiUsageDetailModal(entry) {
    if (!entry || !elements.aiUsageDetailModal || !elements.aiUsageDetailPayload || !elements.aiUsageDetailSummary) {
      return;
    }

    const summaryParts = [
      `id ${entry.id}`,
      entry.operation || "-",
      entry.status || "-",
      entry.model || "-",
      toLocalTimestamp(entry.created_at),
      entry.request_id ? `request ${entry.request_id}` : "request -",
    ];
    elements.aiUsageDetailSummary.textContent = summaryParts.join(" | ");

    const payloadText = JSON.stringify(entry.payload ?? null, null, 2);
    elements.aiUsageDetailPayload.textContent = payloadText;
    elements.aiUsageDetailModal.hidden = false;
  }

  function toCapturedLabel(image) {
    if (!image || !image.captured_at) {
      return "-";
    }
    const parsedDate = new Date(image.captured_at);
    if (Number.isNaN(parsedDate.valueOf())) {
      return "-";
    }
    return parsedDate.toLocaleDateString();
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

  function jigsawMatchesSearchQuery(jigsaw, query) {
    const normalizedQuery = String(query || "").trim().toLowerCase();
    if (!normalizedQuery) {
      return true;
    }

    const searchableText = [jigsaw?.title, jigsaw?.artist, jigsaw?.manufacturer, jigsaw?.tags, jigsaw?.piece_count]
      .filter((value) => value !== null && value !== undefined)
      .map((value) => String(value).toLowerCase())
      .join(" ");

    const searchTerms = normalizedQuery.split(/\s+/).filter(Boolean);
    return searchTerms.every((term) => searchableText.includes(term));
  }

  function jigsawMatchesDiaryFilter(jigsaw, onlyWithoutDiaryEntries) {
    if (!onlyWithoutDiaryEntries) {
      return true;
    }
    return !jigsaw?.last_completed_at;
  }

  function normalizeImageTagLabel(value) {
    const rawValue = String(value || "").trim();
    if (!rawValue) {
      return "untagged";
    }

    const collapsed = rawValue.toLowerCase().replace(/[^a-z0-9]+/g, "");
    if (collapsed === "box") {
      return IMAGE_BROWSER_TAG_BOX;
    }
    if (collapsed === "boxfront") {
      return IMAGE_BROWSER_TAG_BOX_FRONT;
    }
    if (collapsed === "boxside") {
      return IMAGE_BROWSER_TAG_BOX_SIDE;
    }
    if (collapsed === "boxback") {
      return IMAGE_BROWSER_TAG_BOX_BACK;
    }
    if (collapsed.startsWith("reference")) {
      return IMAGE_BROWSER_TAG_REFERENCE;
    }
    if (collapsed === "completed") {
      return IMAGE_BROWSER_TAG_COMPLETED;
    }
    if (collapsed === "complete") {
      return IMAGE_BROWSER_TAG_COMPLETED;
    }
    if (collapsed === "inprogress") {
      return IMAGE_BROWSER_TAG_IN_PROGRESS;
    }

    return rawValue;
  }

  function toImageTagKey(value) {
    return normalizeImageTagLabel(value).toLowerCase();
  }

  function getImageTagDropdownValues(currentTag) {
    const options = [...IMAGE_LIBRARY_STANDARD_TAGS];
    const normalizedCurrentTag = normalizeImageTagLabel(currentTag);
    const hasCurrentTag = options.some((value) => toImageTagKey(value) === toImageTagKey(normalizedCurrentTag));
    if (!hasCurrentTag && normalizedCurrentTag) {
      options.push(normalizedCurrentTag);
    }
    return options;
  }

  function imageMatchesAssignmentFilters(image) {
    const isAssigned = Boolean(image?.jigsaw_id);
    if (isAssigned && !state.imageLibraryFilterAssigned) {
      return false;
    }
    if (!isAssigned && !state.imageLibraryFilterUnassigned) {
      return false;
    }
    return true;
  }

  function imageMatchesTagFilters(image) {
    const tagKey = toImageTagKey(image?.tag);
    return state.imageLibraryFilterTagSelections[tagKey] !== false;
  }

  function reconcileImageLibraryTagFilterState(images) {
    const availableTagMap = new Map();

    images.filter((image) => imageMatchesAssignmentFilters(image)).forEach((image) => {
      const tagLabel = normalizeImageTagLabel(image?.tag);
      const tagKey = toImageTagKey(tagLabel);
      if (!availableTagMap.has(tagKey)) {
        availableTagMap.set(tagKey, tagLabel);
      }
    });

    const nextSelections = {};
    availableTagMap.forEach((_tagLabel, tagKey) => {
      if (Object.prototype.hasOwnProperty.call(state.imageLibraryFilterTagSelections, tagKey)) {
        nextSelections[tagKey] = Boolean(state.imageLibraryFilterTagSelections[tagKey]);
      } else {
        nextSelections[tagKey] = tagKey === toImageTagKey("untagged");
      }
    });
    state.imageLibraryFilterTagSelections = nextSelections;

    return [...availableTagMap.entries()].sort((left, right) => left[1].localeCompare(right[1]));
  }

  function renderImageLibraryTagFilters(tagEntries) {
    const container = elements.imageLibraryTagFilters;
    if (!container) {
      return;
    }

    container.innerHTML = "";

    if (!Array.isArray(tagEntries) || tagEntries.length === 0) {
      const note = document.createElement("span");
      note.className = "govuk-hint";
      note.textContent = "No tags available yet.";
      container.appendChild(note);
      return;
    }

    tagEntries.forEach(([tagKey, tagLabel], index) => {
      const item = document.createElement("div");
      item.className = "govuk-checkboxes__item";

      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.className = "govuk-checkboxes__input";
      checkbox.id = `image-library-tag-filter-${index}`;
      checkbox.checked = state.imageLibraryFilterTagSelections[tagKey] !== false;
      checkbox.dataset.imageLibraryTagFilter = tagKey;

      const label = document.createElement("label");
      label.className = "govuk-label govuk-checkboxes__label";
      label.setAttribute("for", checkbox.id);
      label.textContent = tagLabel;

      item.appendChild(checkbox);
      item.appendChild(label);
      container.appendChild(item);
    });
  }

  function imageLibraryRowMatchesFilters(image) {
    return imageMatchesAssignmentFilters(image) && imageMatchesTagFilters(image);
  }

  function getSelectedRoles(formData) {
    return formData
      .getAll("roles")
      .map((value) => String(value || "").trim())
      .filter((value, index, values) => value && values.indexOf(value) === index);
  }

  function getCurrentUserCapabilities() {
    if (!state.user || !Array.isArray(state.user.capabilities)) {
      return [];
    }
    return state.user.capabilities
      .map((value) => String(value || "").trim())
      .filter((value) => Boolean(value));
  }

  function currentUserHasCapability(capability) {
    const target = String(capability || "").trim();
    if (!target) {
      return false;
    }
    return getCurrentUserCapabilities().includes(target);
  }

  function createInitialDiaryCalendarState() {
    const today = new Date();
    return {
      year: today.getFullYear(),
      month: today.getMonth(),
    };
  }

  function currentUserIsAdministrator() {
    return Array.isArray(state.user?.roles) && state.user.roles.includes("administrator");
  }

  function canCurrentUserDeleteImage(image) {
    if (!image) {
      return false;
    }
    if (!currentUserHasCapability("image.delete")) {
      return false;
    }
    if (currentUserIsAdministrator()) {
      return true;
    }
    return !image?.jigsaw_id;
  }

  function imageSupportsSimilarMatch(image) {
    return Boolean(
      currentUserHasCapability("image.assign")
      && !image?.jigsaw_id
      && toImageTagKey(image?.tag) === toImageTagKey(IMAGE_BROWSER_TAG_COMPLETED)
    );
  }

  function getDefaultCreateRoleNames() {
    const availableRoleNames = state.roleDefinitions.map((role) => String(role?.name || "").trim()).filter(Boolean);
    if (availableRoleNames.includes("member")) {
      return ["member"];
    }
    if (availableRoleNames.includes("borrower")) {
      return ["borrower"];
    }
    return [];
  }

  function createRoleSlug(roleName) {
    return String(roleName || "")
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "");
  }

  function renderRoleCheckboxes(container, { selectedRoleNames = [], idPrefix = "role" } = {}) {
    if (!container) {
      return;
    }

    const selected = new Set(
      (Array.isArray(selectedRoleNames) ? selectedRoleNames : [])
        .map((value) => String(value || "").trim())
        .filter(Boolean),
    );

    container.innerHTML = "";

    let roleDefinitions = Array.isArray(state.roleDefinitions) ? state.roleDefinitions : [];
    if (roleDefinitions.length === 0) {
      roleDefinitions = [
        { name: "member" },
        { name: "borrower" },
        { name: "administrator" },
      ];
    }
    roleDefinitions.forEach((roleDefinition, index) => {
      const roleName = String(roleDefinition?.name || "").trim();
      if (!roleName) {
        return;
      }

      const slug = createRoleSlug(roleName) || `role-${index}`;
      const inputId = `${idPrefix}-${slug}`;

      const item = document.createElement("div");
      item.className = "govuk-checkboxes__item";

      const input = document.createElement("input");
      input.id = inputId;
      input.name = "roles";
      input.className = "govuk-checkboxes__input";
      input.type = "checkbox";
      input.value = roleName;
      input.checked = selected.has(roleName);

      const label = document.createElement("label");
      label.className = "govuk-label govuk-checkboxes__label";
      label.setAttribute("for", inputId);
      label.textContent = roleName;

      item.appendChild(input);
      item.appendChild(label);
      container.appendChild(item);
    });
  }

  function renderUserRoleSelectors() {
    renderRoleCheckboxes(elements.userRolesCheckboxes, {
      selectedRoleNames: getDefaultCreateRoleNames(),
      idPrefix: "user-role",
    });
    renderRoleCheckboxes(elements.editUserRolesCheckboxes, {
      selectedRoleNames: getDefaultCreateRoleNames(),
      idPrefix: "edit-user-role",
    });
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
          (user.roles.includes("member") || user.roles.includes("borrower") || user.roles.includes("administrator")),
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
    placeholder.textContent = "All completed jigsaws (recent first)";
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

    if (!state.diarySelectionTouchedByUser) {
      elements.diaryJigsawId.value = "";
    }
  }

  function getJigsawTitleById(jigsawId) {
    const resolvedJigsawId = Number(jigsawId || "0");
    if (!resolvedJigsawId) {
      return "-";
    }

    const matchingJigsaw = Array.isArray(state.jigsaws)
      ? state.jigsaws.find((jigsaw) => Number(jigsaw.id) === resolvedJigsawId)
      : null;

    if (matchingJigsaw && matchingJigsaw.title) {
      return String(matchingJigsaw.title);
    }

    return `Jigsaw #${resolvedJigsawId}`;
  }

  function setDiaryEntriesCaption(selectedJigsawId) {
    if (!elements.diaryEntriesCaption) {
      return;
    }

    const resolvedJigsawId = Number(selectedJigsawId || "0");
    if (!resolvedJigsawId) {
      elements.diaryEntriesCaption.textContent = "Recent diary entries and unlinked completed images (most recent first)";
      return;
    }

    const jigsawTitle = getJigsawTitleById(resolvedJigsawId);
    elements.diaryEntriesCaption.textContent = `Diary entries for ${jigsawTitle} (most recent first)`;
  }

  function getDiaryEntriesEmptyMessage(selectedJigsawId) {
    return Number(selectedJigsawId || "0") > 0
      ? "No diary entries found for this jigsaw. Select 'All completed jigsaws' to include unlinked completed images."
      : "No diary entries or unlinked completed images found.";
  }

  function normalizeDiaryViewMode(mode) {
    const normalizedMode = String(mode || "").trim().toLowerCase();
    return normalizedMode === DIARY_VIEW_MODE_CALENDAR ? DIARY_VIEW_MODE_CALENDAR : DIARY_VIEW_MODE_LIST;
  }

  function updateDiaryViewUi() {
    const activeMode = normalizeDiaryViewMode(state.diaryViewMode);
    state.diaryViewMode = activeMode;
    const isCalendarMode = activeMode === DIARY_VIEW_MODE_CALENDAR;

    elements.diaryViewModeButtons.forEach((button) => {
      const buttonMode = normalizeDiaryViewMode(button.dataset.diaryViewMode);
      const isActive = buttonMode === activeMode;
      button.classList.toggle("is-active", isActive);
      button.setAttribute("aria-pressed", isActive ? "true" : "false");
    });

    if (elements.diaryListRegion) {
      elements.diaryListRegion.hidden = isCalendarMode;
    }
    if (elements.diaryCalendarRegion) {
      elements.diaryCalendarRegion.hidden = !isCalendarMode;
    }
    if (elements.diaryCalendarControls) {
      elements.diaryCalendarControls.hidden = !isCalendarMode;
    }
  }

  function setDiaryViewMode(mode) {
    state.diaryViewMode = normalizeDiaryViewMode(mode);
    updateDiaryViewUi();
  }

  function shiftDiaryCalendarMonth(monthOffset) {
    const offset = Number(monthOffset || 0);
    if (!Number.isFinite(offset) || Math.trunc(offset) === 0) {
      return;
    }

    const currentMonth = new Date(state.diaryCalendar.year, state.diaryCalendar.month, 1);
    currentMonth.setMonth(currentMonth.getMonth() + Math.trunc(offset));
    state.diaryCalendar.year = currentMonth.getFullYear();
    state.diaryCalendar.month = currentMonth.getMonth();
  }

  function resetDiaryCalendarToCurrentMonth() {
    const todayMonth = createInitialDiaryCalendarState();
    state.diaryCalendar.year = todayMonth.year;
    state.diaryCalendar.month = todayMonth.month;
  }

  function resetDiaryEntryFormEditingState({ keepJigsawSelection = true } = {}) {
    state.diaryEditingEntryId = null;

    if (elements.diaryEntrySubmitButton) {
      elements.diaryEntrySubmitButton.textContent = "Add diary entry";
    }
    if (elements.diaryEntryCancelButton) {
      elements.diaryEntryCancelButton.hidden = true;
    }
    if (elements.diaryJigsawId) {
      elements.diaryJigsawId.disabled = false;
      if (!keepJigsawSelection) {
        elements.diaryJigsawId.value = "";
      }
    }
    if (elements.diaryCompletedAt) {
      elements.diaryCompletedAt.value = "";
    }
    if (elements.diaryDifficulty) {
      elements.diaryDifficulty.value = "";
    }
    if (elements.diaryNotes) {
      elements.diaryNotes.value = "";
    }
  }

  function beginDiaryEntryEdit(entryId) {
    const resolvedEntryId = Number(entryId || "0");
    if (!resolvedEntryId) {
      return;
    }

    const entry = Array.isArray(state.diaryEntries)
      ? state.diaryEntries.find(
        (candidate) => candidate?.entry_type !== "orphan_completed_image" && Number(candidate.id) === resolvedEntryId,
      )
      : null;
    if (!entry) {
      showFeedback("Diary entry was not found.", true);
      return;
    }

    const canUpdateAny = currentUserHasCapability("diary.update_any");
    const canUpdateOwn = currentUserHasCapability("diary.update_own");
    const canEdit =
      canUpdateAny || (canUpdateOwn && Number(entry.created_by_user_id || 0) === Number(state.user?.id || 0));
    if (!canEdit) {
      showFeedback("You do not have permission to edit this diary entry.", true);
      return;
    }

    state.diaryEditingEntryId = resolvedEntryId;
    rememberEditorScrollPosition("diary");
    if (elements.diaryJigsawId) {
      elements.diaryJigsawId.value = String(entry.jigsaw_id || "");
      elements.diaryJigsawId.disabled = true;
    }
    if (elements.diaryCompletedAt) {
      elements.diaryCompletedAt.value = toDatetimeLocalValue(entry.completed_at);
    }
    if (elements.diaryDifficulty) {
      elements.diaryDifficulty.value = entry.difficulty === null || entry.difficulty === undefined ? "" : String(entry.difficulty);
    }
    if (elements.diaryNotes) {
      elements.diaryNotes.value = String(entry.notes || "");
    }
    if (elements.diaryEntrySubmitButton) {
      elements.diaryEntrySubmitButton.textContent = "Save diary entry";
    }
    if (elements.diaryEntryCancelButton) {
      elements.diaryEntryCancelButton.hidden = false;
    }
    if (elements.diaryEntryForm) {
      scrollToEditor(elements.diaryEntryForm);
    }
  }

  function getDiaryEntryImageUrls(entry) {
    const sourceImage = entry?.source_image;
    if (sourceImage) {
      const sourceImageId = Number(sourceImage?.id || entry?.source_image_id || 0);
      const sourceImageVersion = Number(sourceImage?.content_version || 0);
      const versionQuery = sourceImageVersion > 0 ? `&v=${sourceImageVersion}` : "";
      return {
        thumbnailUrl: String(sourceImage?.thumbnail_url || (sourceImageId ? `/api/v1/images/${sourceImageId}/content?variant=thumbnail${versionQuery}` : "")),
        previewUrl: String(sourceImage?.preview_url || (sourceImageId ? `/api/v1/images/${sourceImageId}/content?variant=preview${versionQuery}` : "")),
        openUrl: String(sourceImage?.content_url || (sourceImageId ? `/api/v1/images/${sourceImageId}/content${sourceImageVersion > 0 ? `?v=${sourceImageVersion}` : ""}` : "")),
      };
    }

    const sourceImageId = Number(entry?.source_image_id || 0);
    if (!sourceImageId) {
      return {
        thumbnailUrl: "",
        previewUrl: "",
        openUrl: "",
      };
    }

    const matchingImage = Array.isArray(state.imageLibraryImages)
      ? state.imageLibraryImages.find((image) => Number(image.id) === sourceImageId)
      : null;
    const sourceImageVersion = Number(matchingImage?.content_version || 0);
    const versionQuery = sourceImageVersion > 0 ? `&v=${sourceImageVersion}` : "";

    return {
      thumbnailUrl: String(matchingImage?.thumbnail_url || `/api/v1/images/${sourceImageId}/content?variant=thumbnail${versionQuery}`),
      previewUrl: String(matchingImage?.preview_url || `/api/v1/images/${sourceImageId}/content?variant=preview${versionQuery}`),
      openUrl: String(matchingImage?.content_url || `/api/v1/images/${sourceImageId}/content${sourceImageVersion > 0 ? `?v=${sourceImageVersion}` : ""}`),
    };
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

    syncBulkCreateFromUploadVisibility();
  }

  function getFirstVisibleWorkspaceTab() {
    const tabOrder = ["collection", "account", "admin", "activity-log", "loans"];
    return tabOrder.find((tabName) => state.workspaceTabVisibility[tabName]) || null;
  }

  function getFirstVisibleCollectionTab() {
    const tabOrder = ["jigsaws", "quick-create", "images", "image-browser", "diary"];
    return tabOrder.find((tabName) => state.collectionTabVisibility[tabName]) || null;
  }

  function getFirstVisibleAdminTab() {
    const tabOrder = ["users", "ai", "embeddings", "ip-blocks"];
    return tabOrder.find((tabName) => state.adminTabVisibility[tabName]) || null;
  }

  function normalizeWorkspaceTab(tabName) {
    if (typeof tabName !== "string") {
      return null;
    }
    const normalized = tabName.trim().toLowerCase();
    return state.workspaceTabVisibility[normalized] ? normalized : null;
  }

  function normalizeCollectionTab(tabName) {
    if (typeof tabName !== "string") {
      return null;
    }
    const normalized = tabName.trim().toLowerCase();
    return state.collectionTabVisibility[normalized] ? normalized : null;
  }

  function normalizeAdminTab(tabName) {
    if (typeof tabName !== "string") {
      return null;
    }
    const normalized = tabName.trim().toLowerCase();
    return state.adminTabVisibility[normalized] ? normalized : null;
  }

  function setActiveWorkspaceTab(tabName, { updateHash = true } = {}) {
    const nextTab = normalizeWorkspaceTab(tabName) || getFirstVisibleWorkspaceTab();
    state.activeWorkspaceTab = nextTab;

    if (updateHash && typeof window !== "undefined") {
      const expectedHash = nextTab ? `#${nextTab}` : "";
      if (window.location.hash !== expectedHash) {
        if (expectedHash) {
          window.history.replaceState(null, "", expectedHash);
        } else {
          window.history.replaceState(null, "", window.location.pathname + window.location.search);
        }
      }
    }
  }

  function setActiveCollectionTab(tabName) {
    state.activeCollectionTab = normalizeCollectionTab(tabName) || getFirstVisibleCollectionTab();
  }

  function setActiveAdminTab(tabName) {
    state.activeAdminTab = normalizeAdminTab(tabName) || getFirstVisibleAdminTab();
  }

  function updateWorkspaceTabsUi() {
    const hasVisibleTabs = Boolean(getFirstVisibleWorkspaceTab());
    if (elements.workspaceTabs) {
      elements.workspaceTabs.hidden = !state.user || !hasVisibleTabs;
    }

    elements.workspaceTabButtons.forEach((button) => {
      const tabName = String(button.dataset.workspaceTab || "").trim().toLowerCase();
      const isVisible = state.workspaceTabVisibility[tabName] === true;
      const isSelected = isVisible && state.activeWorkspaceTab === tabName;
      button.hidden = !isVisible;
      button.setAttribute("aria-selected", isSelected ? "true" : "false");
      button.setAttribute("tabindex", isSelected ? "0" : "-1");
      button.classList.toggle("is-active", isSelected);
    });
  }

  function updateCollectionTabsUi() {
    const hasVisibleTabs = Boolean(getFirstVisibleCollectionTab());
    if (elements.collectionSubtabs) {
      elements.collectionSubtabs.hidden = !state.workspaceSectionAccess.collection || state.activeWorkspaceTab !== "collection" || !hasVisibleTabs;
    }

    elements.collectionTabButtons.forEach((button) => {
      const tabName = String(button.dataset.collectionTab || "").trim().toLowerCase();
      const isVisible = state.collectionTabVisibility[tabName] === true;
      const isSelected = isVisible && state.activeCollectionTab === tabName;
      button.hidden = !isVisible;
      button.setAttribute("aria-selected", isSelected ? "true" : "false");
      button.setAttribute("tabindex", isSelected ? "0" : "-1");
      button.classList.toggle("is-active", isSelected);
    });
  }

  function updateAdminTabsUi() {
    const hasVisibleTabs = Boolean(getFirstVisibleAdminTab());
    if (elements.adminSubtabs) {
      elements.adminSubtabs.hidden = !state.workspaceSectionAccess.admin || state.activeWorkspaceTab !== "admin" || !hasVisibleTabs;
    }

    elements.adminTabButtons.forEach((button) => {
      const tabName = String(button.dataset.adminTab || "").trim().toLowerCase();
      const isVisible = state.adminTabVisibility[tabName] === true;
      const isSelected = isVisible && state.activeAdminTab === tabName;
      button.hidden = !isVisible;
      button.setAttribute("aria-selected", isSelected ? "true" : "false");
      button.setAttribute("tabindex", isSelected ? "0" : "-1");
      button.classList.toggle("is-active", isSelected);
    });
  }

  function applyCollectionPanelVisibility() {
    const activeCollectionTab = state.activeCollectionTab;

    if (elements.collectionQuickCreatePanel) {
      elements.collectionQuickCreatePanel.hidden = !(state.collectionTabVisibility["quick-create"] && activeCollectionTab === "quick-create");
    }
    if (elements.collectionJigsawsPanel) {
      elements.collectionJigsawsPanel.hidden = !(state.collectionTabVisibility.jigsaws && activeCollectionTab === "jigsaws");
    }
    if (elements.collectionImagesPanel) {
      elements.collectionImagesPanel.hidden = !(state.collectionTabVisibility.images && activeCollectionTab === "images");
    }
    if (elements.collectionImageBrowserPanel) {
      elements.collectionImageBrowserPanel.hidden = !(state.collectionTabVisibility["image-browser"] && activeCollectionTab === "image-browser");
    }
    if (elements.collectionDiaryPanel) {
      elements.collectionDiaryPanel.hidden = !(state.collectionTabVisibility.diary && activeCollectionTab === "diary");
    }
  }

  function applyAdminPanelVisibility() {
    if (state.activeWorkspaceTab !== "admin") {
      if (elements.usersSection) {
        elements.usersSection.hidden = true;
      }
      if (elements.aiUsageSection) {
        elements.aiUsageSection.hidden = true;
      }
      if (elements.embeddingsSection) {
        elements.embeddingsSection.hidden = true;
      }
      if (elements.ipBlocksSection) {
        elements.ipBlocksSection.hidden = true;
      }
      return;
    }

    const activeAdminTab = state.activeAdminTab;

    if (elements.usersSection) {
      elements.usersSection.hidden = !(state.adminTabVisibility.users && activeAdminTab === "users");
    }
    if (elements.aiUsageSection) {
      elements.aiUsageSection.hidden = !(state.adminTabVisibility.ai && activeAdminTab === "ai");
    }
    if (elements.embeddingsSection) {
      elements.embeddingsSection.hidden = !(state.adminTabVisibility.embeddings && activeAdminTab === "embeddings");
    }
    if (elements.ipBlocksSection) {
      elements.ipBlocksSection.hidden = !(state.adminTabVisibility["ip-blocks"] && activeAdminTab === "ip-blocks");
    }
  }

  function applyWorkspaceSectionVisibility() {
    const activeTab = state.activeWorkspaceTab;
    const showCollectionWorkspace = state.workspaceSectionAccess.collection && activeTab === "collection";
    const showAdminWorkspace = state.workspaceSectionAccess.admin && activeTab === "admin";

    if (elements.accountSection) {
      elements.accountSection.hidden = !(state.workspaceSectionAccess.account && activeTab === "account");
    }
    if (elements.jigsawsSection) {
      elements.jigsawsSection.hidden = !showCollectionWorkspace;
    }
    if (elements.adminSections) {
      elements.adminSections.hidden = !(showCollectionWorkspace || showAdminWorkspace);
    }
    if (elements.loansSection) {
      elements.loansSection.hidden = !(state.workspaceSectionAccess.loans && activeTab === "loans");
    }
    if (elements.auditSection) {
      elements.auditSection.hidden = !(state.workspaceSectionAccess.activityLog && activeTab === "activity-log");
    }

    applyCollectionPanelVisibility();
    applyAdminPanelVisibility();
  }

  function setWorkspaceSectionAccess(sectionName, isVisible) {
    state.workspaceSectionAccess[sectionName] = Boolean(isVisible);
  }

  function handleWorkspaceTabClick(event) {
    const button = event.target?.closest("[data-workspace-tab]");
    if (!button) {
      return;
    }
    event.preventDefault();
    const tabName = String(button.dataset.workspaceTab || "").trim().toLowerCase();
    if (!state.workspaceTabVisibility[tabName]) {
      return;
    }
    setActiveWorkspaceTab(tabName);
    updateWorkspaceTabsUi();
    updateCollectionTabsUi();
    updateAdminTabsUi();
    applyWorkspaceSectionVisibility();
  }

  function handleCollectionTabClick(event) {
    const button = event.target?.closest("[data-collection-tab]");
    if (!button) {
      return;
    }
    event.preventDefault();
    const tabName = String(button.dataset.collectionTab || "").trim().toLowerCase();
    if (!state.collectionTabVisibility[tabName]) {
      return;
    }
    setActiveCollectionTab(tabName);
    updateCollectionTabsUi();
    applyCollectionPanelVisibility();
    if (
      (tabName === "images" || tabName === "image-browser")
      && currentUserHasCapability("image.manage_library")
      && (!Array.isArray(state.imageLibraryImages) || state.imageLibraryImages.length === 0)
    ) {
      loadImageLibraryImages().catch(() => {
        // Loader reports its own errors to feedback UI.
      });
    }
    if (tabName === "image-browser") {
      openImageBrowser();
    }
  }

  function handleAccountNavClick(event) {
    event.preventDefault();
    setActiveWorkspaceTab("account");
    updateWorkspaceTabsUi();
    updateCollectionTabsUi();
    updateAdminTabsUi();
    applyWorkspaceSectionVisibility();
  }

  function handleAdminTabClick(event) {
    const button = event.target?.closest("[data-admin-tab]");
    if (!button) {
      return;
    }
    event.preventDefault();
    const tabName = String(button.dataset.adminTab || "").trim().toLowerCase();
    if (!state.adminTabVisibility[tabName]) {
      return;
    }
    setActiveAdminTab(tabName);
    updateAdminTabsUi();
    applyAdminPanelVisibility();
  }

  function handleWorkspaceHashChange() {
    const hashTab = typeof window !== "undefined" ? String(window.location.hash || "").replace(/^#/, "") : "";
    const normalizedHashTab = normalizeWorkspaceTab(hashTab);
    if (!normalizedHashTab || normalizedHashTab === state.activeWorkspaceTab) {
      return;
    }
    state.activeWorkspaceTab = normalizedHashTab;
    updateWorkspaceTabsUi();
    updateCollectionTabsUi();
    updateAdminTabsUi();
    applyWorkspaceSectionVisibility();
  }

  function setSessionSummary() {
    if (!elements.sessionSummary) {
      return;
    }

    if (!state.user) {
      resetDiaryEntryFormEditingState({ keepJigsawSelection: false });
      state.authProvider = null;
      elements.sessionSummary.textContent = "Not signed in.";
      setWorkspaceSectionAccess("account", false);
      setWorkspaceSectionAccess("collection", true);
      setWorkspaceSectionAccess("admin", false);
      setWorkspaceSectionAccess("activityLog", false);
      setWorkspaceSectionAccess("loans", false);
      state.workspaceTabVisibility.account = false;
      state.workspaceTabVisibility.collection = true;
      state.workspaceTabVisibility.admin = false;
      state.workspaceTabVisibility["activity-log"] = false;
      state.workspaceTabVisibility.loans = false;
      state.collectionTabVisibility["quick-create"] = false;
      state.collectionTabVisibility.jigsaws = true;
      state.collectionTabVisibility.images = false;
      state.collectionTabVisibility["image-browser"] = false;
      state.collectionTabVisibility.diary = false;
      state.adminTabVisibility.users = false;
      state.adminTabVisibility.ai = false;
      state.adminTabVisibility.embeddings = false;
      state.adminTabVisibility["ip-blocks"] = false;
      state.editorScrollPositions.user = null;
      state.editorScrollPositions.jigsaw = null;
      state.editorScrollPositions.diary = null;
      setActiveCollectionTab("jigsaws");
      setActiveAdminTab(null);
      setActiveWorkspaceTab("collection");
      updateWorkspaceTabsUi();
      updateCollectionTabsUi();
      updateAdminTabsUi();
      applyWorkspaceSectionVisibility();
      if (elements.userEditForm) {
        elements.userEditForm.hidden = true;
      }
      if (elements.jigsawEditForm) {
        elements.jigsawEditForm.hidden = true;
      }
      if (elements.signInControls) {
        elements.signInControls.hidden = false;
      }
      if (elements.signOutControls) {
        elements.signOutControls.hidden = true;
      }
      if (elements.accountNavButton) {
        elements.accountNavButton.hidden = true;
      }
      if (elements.logoutButton) {
        elements.logoutButton.hidden = true;
      }
      closeAuthDialog();
      syncLoginUiForAuthMode();
      syncHeaderAuthControls();
      populateLoanFormOptions();
      populateJigsawImageOptions();
      populateDiaryJigsawOptions();
      populateImageLibraryJigsawOptions();
      return;
    }

    const roleText = Array.isArray(state.user.roles) ? state.user.roles.join(", ") : "none";
    elements.sessionSummary.textContent = `Signed in as ${state.user.email} (${roleText}).`;
    const isStfdSession = String(state.authProvider || "").toLowerCase() === "stfd";

    const isAdministrator = Array.isArray(state.user.roles) && state.user.roles.includes("administrator");
    const canReadJigsaw = currentUserHasCapability("jigsaw.read");
    const canCreateJigsaw = currentUserHasCapability("jigsaw.create");
    const canUpdateJigsaw = currentUserHasCapability("jigsaw.update");
    const canEnrichJigsaw = currentUserHasCapability("jigsaw.enrich");
    const canReadDiary = currentUserHasCapability("diary.read");
    const canCreateDiary = currentUserHasCapability("diary.create");
    const canUpdateDiaryAny = currentUserHasCapability("diary.update_any");
    const canUpdateDiaryOwn = currentUserHasCapability("diary.update_own");
    const canManageUsers = currentUserHasCapability("user.manage");
    const canManageLoans = currentUserHasCapability("loan.manage");
    const canManageImages = currentUserHasCapability("image.manage_library") || currentUserHasCapability("image.upload");
    const canUploadImages = currentUserHasCapability("image.upload");
    const canManageAi = currentUserHasCapability("ai.manage");
    const canReadAudit = currentUserHasCapability("audit.read");
    const canManageSecurity = Array.isArray(state.user?.roles) && state.user.roles.includes("administrator");
    const canAccessCollection = canReadJigsaw || canReadDiary || canManageImages || canCreateJigsaw;
    const canAccessAdminUsers = canManageUsers;
    const canAccessAdminAi = canManageAi;
    const canAccessAdminEmbeddings = isAdministrator;
    const canAccessAdminIpBlocks = canManageSecurity;
    const canAccessAdmin = canAccessAdminUsers || canAccessAdminAi || canAccessAdminEmbeddings || canAccessAdminIpBlocks;
    const canAccessActivityLog = canReadAudit;
    const canAccessLoans = Boolean(isAdministrator && canManageLoans);

    setWorkspaceSectionAccess("account", !isStfdSession);
    setWorkspaceSectionAccess("collection", canAccessCollection);
    setWorkspaceSectionAccess("admin", canAccessAdmin);
    setWorkspaceSectionAccess("activityLog", canAccessActivityLog);
    setWorkspaceSectionAccess("loans", canAccessLoans);

    state.workspaceTabVisibility.account = !isStfdSession;
    state.workspaceTabVisibility.collection = canAccessCollection;
    state.workspaceTabVisibility.admin = canAccessAdmin;
    state.workspaceTabVisibility["activity-log"] = canAccessActivityLog;
    state.workspaceTabVisibility.loans = canAccessLoans;

    state.collectionTabVisibility["quick-create"] = canCreateJigsaw;
    state.collectionTabVisibility.jigsaws = canReadJigsaw || canReadDiary;
    state.collectionTabVisibility.images = canReadJigsaw || canReadDiary || canManageImages;
    state.collectionTabVisibility["image-browser"] = canReadJigsaw || canReadDiary || canManageImages;
    state.collectionTabVisibility.diary = canReadDiary;

    state.adminTabVisibility.users = canAccessAdminUsers;
    state.adminTabVisibility.ai = canAccessAdminAi;
    state.adminTabVisibility.embeddings = canAccessAdminEmbeddings;
    state.adminTabVisibility["ip-blocks"] = canAccessAdminIpBlocks;

    setActiveCollectionTab(state.activeCollectionTab);
    setActiveAdminTab(state.activeAdminTab);

    const requestedTab = typeof window !== "undefined" ? String(window.location.hash || "").replace(/^#/, "") : "";
    const preferredTab = normalizeWorkspaceTab(requestedTab) || state.activeWorkspaceTab;
    setActiveWorkspaceTab(preferredTab);
    updateWorkspaceTabsUi();
    updateCollectionTabsUi();
    updateAdminTabsUi();
    applyWorkspaceSectionVisibility();
    if (elements.signInControls) {
      elements.signInControls.hidden = true;
    }
    syncHeaderAuthControls();
    closeAuthDialog();
    if (elements.authCredentialsWrap) {
      elements.authCredentialsWrap.hidden = true;
    }
    if (state.diaryEditingEntryId && !canUpdateDiaryAny && !canUpdateDiaryOwn) {
      resetDiaryEntryFormEditingState({ keepJigsawSelection: true });
    }
    if (elements.jigsawCreateForm) {
      elements.jigsawCreateForm.hidden = !canCreateJigsaw;
    }
    if (!canUpdateJigsaw) {
      closeJigsawEditor();
    }
    if (elements.jigsawEditEnrichButton) {
      elements.jigsawEditEnrichButton.hidden = !canEnrichJigsaw;
    }
    if (elements.jigsawImageForm) {
      elements.jigsawImageForm.hidden = !canUploadImages;
    }
    if (elements.imageLibraryUploadForm) {
      elements.imageLibraryUploadForm.hidden = !canUploadImages;
    }
    if (elements.imageLibraryBulkCreateWrap) {
      elements.imageLibraryBulkCreateWrap.hidden = !canManageAi;
    }
    if (elements.imageLibraryBulkCreateUnassignedBoxButton) {
      elements.imageLibraryBulkCreateUnassignedBoxButton.hidden = !canManageAi;
    }
    if (!isAdministrator) {
      closeUserEditor();
    }
    if (elements.diaryEntrySubmitButton) {
      elements.diaryEntrySubmitButton.disabled = !canCreateDiary;
    }
    if (elements.diaryEntryCancelButton && !canUpdateDiaryAny && !canUpdateDiaryOwn) {
      elements.diaryEntryCancelButton.hidden = true;
    }
    if (elements.diaryJigsawId) {
      elements.diaryJigsawId.disabled = !canCreateDiary;
    }
    if (elements.diaryCompletedAt) {
      elements.diaryCompletedAt.disabled = !canCreateDiary;
    }
    if (elements.diaryDifficulty) {
      elements.diaryDifficulty.disabled = !canCreateDiary;
    }
    if (elements.diaryNotes) {
      elements.diaryNotes.disabled = !canCreateDiary;
    }
    if (elements.accountUsername) {
      elements.accountUsername.value = state.user.display_name || "";
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
    renderRoleCheckboxes(elements.editUserRolesCheckboxes, {
      selectedRoleNames: getDefaultCreateRoleNames(),
      idPrefix: "edit-user-role",
    });
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
    if (elements.editJigsawSeriesName) {
      elements.editJigsawSeriesName.value = "";
    }
    if (elements.editJigsawSeriesNumber) {
      elements.editJigsawSeriesNumber.value = "";
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
    if (elements.jigsawEditEnrichButton) {
      elements.jigsawEditEnrichButton.disabled = false;
    }
  }

  function renderUsers(users) {
    const tableBody = elements.usersTableBody;
    clearTableBody(tableBody);

    if (!Array.isArray(users) || users.length === 0) {
      appendEmptyRow(tableBody, 6, "No users found.");
      return;
    }

    const sortedUsers = sortRowsForTable(users, "users");
    sortedUsers.forEach((user) => {
      const row = document.createElement("tr");
      row.className = "govuk-table__row app-image-library-data-row";

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
      clearPagination(elements.jigsawsPagination);
      appendEmptyRow(tableBody, 5, "No jigsaws found.");
      return;
    }

    const filteredJigsaws = jigsaws.filter(
      (jigsaw) =>
        jigsawMatchesSearchQuery(jigsaw, state.jigsawSearchQuery)
        && jigsawMatchesDiaryFilter(jigsaw, state.jigsawFilterWithoutDiaryEntries),
    );
    if (filteredJigsaws.length === 0) {
      clearPagination(elements.jigsawsPagination);
      appendEmptyRow(
        tableBody,
        5,
        state.jigsawFilterWithoutDiaryEntries
          ? "No matching jigsaws found without diary entries."
          : "No matching jigsaws found.",
      );
      return;
    }

    const sortedJigsawsRows = sortRowsForTable(filteredJigsaws, "jigsaws");
    const pageResult = paginateItems(sortedJigsawsRows, "jigsaws");
    const preferredImagesByJigsawId = buildPreferredJigsawImageByJigsawId(state.jigsawThumbnailImages);
    const assignedImagesByJigsawId = buildAssignedJigsawImagesByJigsawId(state.imageLibraryImages);
    const canEditJigsaw = currentUserHasCapability("jigsaw.update");
    const canEnrichJigsaw = currentUserHasCapability("jigsaw.enrich");
    const canDetachJigsawImages = currentUserHasCapability("image.assign");
    const canRetireOrDelete = Array.isArray(state.user?.roles) && state.user.roles.includes("administrator");
    const canOpenOriginalImages = Boolean(state.user);

    pageResult.rows.forEach((jigsaw) => {
      const row = document.createElement("tr");
      row.className = "govuk-table__row app-jigsaw-data-row";

      const preferredImage = preferredImagesByJigsawId.get(Number(jigsaw.id));
      const additionalImages = getAdditionalAssignedImagesForJigsaw(jigsaw.id, preferredImage, assignedImagesByJigsawId);
      const additionalImageCount = additionalImages.length;
      const isExpanded = Boolean(state.jigsawExpandedImageRowsById?.[Number(jigsaw.id)]);
      row.appendChild(
        buildThumbnailCell(preferredImage?.thumbnail_url || preferredImage?.content_url, {
          altText: `Thumbnail for ${jigsaw.title || "jigsaw"}`,
          previewUrl: preferredImage?.preview_url || preferredImage?.content_url,
          openUrl: canOpenOriginalImages
            ? preferredImage?.content_url
            : (preferredImage?.preview_url || preferredImage?.thumbnail_url || ""),
        })
      );
      const titleCell = document.createElement("td");
      titleCell.className = "govuk-table__cell";

      const titleWrap = document.createElement("div");
      titleWrap.className = "app-jigsaw-title-cell";

      const titleText = document.createElement("span");
      titleText.textContent = String(jigsaw.title || "-");
      titleWrap.appendChild(titleText);

      if (canDetachJigsawImages && preferredImage?.id) {
        const detachMainImageButton = document.createElement("button");
        detachMainImageButton.type = "button";
        detachMainImageButton.className = "govuk-button govuk-button--secondary app-inline-button app-jigsaw-image-detach-button";
        detachMainImageButton.setAttribute("data-module", "govuk-button");
        detachMainImageButton.dataset.jigsawImageDetach = String(preferredImage.id);
        detachMainImageButton.textContent = "Detach image";
        titleWrap.appendChild(detachMainImageButton);
      }

      titleCell.appendChild(titleWrap);
      row.appendChild(titleCell);
      const piecesCell = buildCell(String(jigsaw.piece_count || "-"));
      piecesCell.dataset.mobileLabel = "Pieces";
      row.appendChild(piecesCell);

      const lastCompletedCell = buildCell(toLocalTimestamp(jigsaw.last_completed_at));
      lastCompletedCell.dataset.mobileLabel = "Last completed";
      row.appendChild(lastCompletedCell);

      const actionCell = document.createElement("td");
      actionCell.className = "govuk-table__cell";
      actionCell.classList.add("app-cell-actions");
      actionCell.dataset.mobileLabel = "Actions";

      const controlsWrap = document.createElement("div");
      controlsWrap.className = "app-inline-controls";

      if (additionalImageCount > 0) {
        const toggleImagesButton = document.createElement("button");
        toggleImagesButton.type = "button";
        toggleImagesButton.className = "govuk-button govuk-button--secondary app-inline-button app-jigsaw-images-toggle";
        toggleImagesButton.setAttribute("data-module", "govuk-button");
        toggleImagesButton.dataset.jigsawImagesToggle = String(jigsaw.id);
        toggleImagesButton.textContent = isExpanded
          ? `Hide images (${additionalImageCount})`
          : `Show images (${additionalImageCount})`;
        controlsWrap.appendChild(toggleImagesButton);
      }

      if (canEditJigsaw) {
        const editButton = document.createElement("button");
        editButton.type = "button";
        editButton.className = "govuk-button govuk-button--secondary app-inline-button";
        editButton.setAttribute("data-module", "govuk-button");
        editButton.dataset.jigsawEdit = String(jigsaw.id);
        editButton.textContent = "Edit";
        controlsWrap.appendChild(editButton);
      }

      if (canRetireOrDelete) {
        const retireButton = document.createElement("button");
        retireButton.type = "button";
        retireButton.className = "govuk-button govuk-button--secondary app-inline-button";
        retireButton.setAttribute("data-module", "govuk-button");
        retireButton.dataset.jigsawRetire = String(jigsaw.id);
        retireButton.textContent = "Retire";
        controlsWrap.appendChild(retireButton);
      }

      if (canEnrichJigsaw) {
        const enrichButton = document.createElement("button");
        enrichButton.type = "button";
        enrichButton.className = "govuk-button govuk-button--secondary app-inline-button";
        enrichButton.setAttribute("data-module", "govuk-button");
        enrichButton.dataset.jigsawEnrich = String(jigsaw.id);
        enrichButton.textContent = "Enrich";
        controlsWrap.appendChild(enrichButton);
      }

      if (canRetireOrDelete) {
        const deleteButton = document.createElement("button");
        deleteButton.type = "button";
        deleteButton.className = "govuk-button govuk-button--secondary app-inline-button";
        deleteButton.setAttribute("data-module", "govuk-button");
        deleteButton.dataset.jigsawDelete = String(jigsaw.id);
        deleteButton.textContent = "Delete";
        controlsWrap.appendChild(deleteButton);
      }

      actionCell.appendChild(controlsWrap);

      row.appendChild(actionCell);
      tableBody.appendChild(row);

      if (isExpanded && additionalImageCount > 0) {
        const expandedRow = document.createElement("tr");
        expandedRow.className = "govuk-table__row app-jigsaw-images-row";

        const expandedCell = document.createElement("td");
        expandedCell.className = "govuk-table__cell app-jigsaw-images-row__cell";
        expandedCell.colSpan = 5;

        const heading = document.createElement("p");
        heading.className = "govuk-body-s app-jigsaw-images-row__heading";
        heading.textContent = "Other assigned images";
        expandedCell.appendChild(heading);

        const grid = document.createElement("div");
        grid.className = "app-jigsaw-images-grid";

        additionalImages.forEach((image) => {
          const item = document.createElement("div");
          item.className = "app-jigsaw-images-grid__item";

          const thumbnail = buildThumbnailWidget(image.thumbnail_url || image.content_url, {
            altText: `${jigsaw.title || "Jigsaw"} image ${image.id}`,
            previewUrl: image.preview_url || image.content_url,
            openUrl: canOpenOriginalImages
              ? image.content_url
              : (image.preview_url || image.thumbnail_url || ""),
            widthPx: 120,
          });
          item.appendChild(thumbnail);

          const metadata = document.createElement("p");
          metadata.className = "govuk-body-s app-jigsaw-images-grid__meta";
          metadata.textContent = image.tag || "untagged";
          item.appendChild(metadata);

          if (canDetachJigsawImages && image.id) {
            const detachButton = document.createElement("button");
            detachButton.type = "button";
            detachButton.className = "govuk-button govuk-button--secondary app-inline-button app-jigsaw-image-detach-button";
            detachButton.setAttribute("data-module", "govuk-button");
            detachButton.dataset.jigsawImageDetach = String(image.id);
            detachButton.textContent = "Detach";
            item.appendChild(detachButton);
          }

          grid.appendChild(item);
        });

        expandedCell.appendChild(grid);
        expandedRow.appendChild(expandedCell);
        tableBody.appendChild(expandedRow);
      }
    });

    renderPaginationPair(elements.jigsawsPaginationTop, elements.jigsawsPagination, "jigsaws", pageResult);
  }

  function renderAuditEvents(events) {
    const tableBody = elements.auditTableBody;
    clearTableBody(tableBody);

    if (!Array.isArray(events) || events.length === 0) {
      clearPagination(elements.auditPagination);
      appendEmptyRow(tableBody, 5, "No audit events found.");
      return;
    }

    const apiMeta = state.auditEventsMeta;
    const hasApiPagination =
      apiMeta &&
      Number.isFinite(Number(apiMeta.page)) &&
      Number.isFinite(Number(apiMeta.page_size)) &&
      Number.isFinite(Number(apiMeta.total_items)) &&
      Number.isFinite(Number(apiMeta.total_pages));

    const sortedEvents = sortRowsForTable(events, "audit");
    const pageResult = hasApiPagination
      ? {
          page: Number(apiMeta.page),
          totalItems: Number(apiMeta.total_items),
          totalPages: Number(apiMeta.total_pages),
          startIndex: Math.max(0, (Number(apiMeta.page) - 1) * Number(apiMeta.page_size)),
          endIndex: Math.min(Number(apiMeta.total_items), ((Number(apiMeta.page) - 1) * Number(apiMeta.page_size)) + sortedEvents.length),
          rows: sortedEvents,
        }
      : paginateItems(sortedEvents, "audit");

    pageResult.rows.forEach((event) => {
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

    renderPaginationPair(elements.auditPaginationTop, elements.auditPagination, "audit", pageResult);
  }

  function renderBlockedIps(blockedIps) {
    const tableBody = elements.ipBlocksTableBody;
    clearTableBody(tableBody);

    if (!Array.isArray(blockedIps) || blockedIps.length === 0) {
      appendEmptyRow(tableBody, 6, "No blocked IPs found.");
      return;
    }

    blockedIps.forEach((entry) => {
      const row = document.createElement("tr");
      row.className = "govuk-table__row";

      row.appendChild(buildCell(String(entry.ip_address || "-")));
      row.appendChild(buildCell(entry.blocked_until ? new Date(entry.blocked_until).toLocaleString() : "-"));
      row.appendChild(buildCell(String(entry.block_source || "-")));
      row.appendChild(buildCell(String(entry.block_reason || "-")));
      row.appendChild(buildCell(toIntegerLabel(entry.hit_count)));

      const actionCell = document.createElement("td");
      actionCell.className = "govuk-table__cell";

      const removeButton = document.createElement("button");
      removeButton.type = "button";
      removeButton.className = "govuk-button govuk-button--warning govuk-!-margin-bottom-0";
      removeButton.setAttribute("data-module", "govuk-button");
      removeButton.setAttribute("data-ip-block-remove", String(entry.id));
      removeButton.textContent = "Unblock";
      actionCell.appendChild(removeButton);

      row.appendChild(actionCell);
      tableBody.appendChild(row);
    });
  }

  function renderAiUsageDiagnostics(diagnostics) {
    const windows = diagnostics?.windows || {};
    const today = windows.today || {};
    const sevenDays = windows.last_7_days || {};
    const thirtyDays = windows.last_30_days || {};

    if (elements.aiUsageTodayCost) {
      elements.aiUsageTodayCost.textContent = toUsdLabel(today.cost_usd);
    }
    if (elements.aiUsageTodayCalls) {
      elements.aiUsageTodayCalls.textContent = toIntegerLabel(today.calls);
    }
    if (elements.aiUsageTodaySuccess) {
      elements.aiUsageTodaySuccess.textContent = toIntegerLabel(today.success);
    }
    if (elements.aiUsageTodayTokens) {
      elements.aiUsageTodayTokens.textContent = toIntegerLabel(today.tokens);
    }

    if (elements.aiUsage7dCost) {
      elements.aiUsage7dCost.textContent = toUsdLabel(sevenDays.cost_usd);
    }
    if (elements.aiUsage7dCalls) {
      elements.aiUsage7dCalls.textContent = toIntegerLabel(sevenDays.calls);
    }
    if (elements.aiUsage7dSuccess) {
      elements.aiUsage7dSuccess.textContent = toIntegerLabel(sevenDays.success);
    }
    if (elements.aiUsage7dTokens) {
      elements.aiUsage7dTokens.textContent = toIntegerLabel(sevenDays.tokens);
    }

    if (elements.aiUsage30dCost) {
      elements.aiUsage30dCost.textContent = toUsdLabel(thirtyDays.cost_usd);
    }
    if (elements.aiUsage30dCalls) {
      elements.aiUsage30dCalls.textContent = toIntegerLabel(thirtyDays.calls);
    }
    if (elements.aiUsage30dSuccess) {
      elements.aiUsage30dSuccess.textContent = toIntegerLabel(thirtyDays.success);
    }
    if (elements.aiUsage30dTokens) {
      elements.aiUsage30dTokens.textContent = toIntegerLabel(thirtyDays.tokens);
    }

    if (elements.aiUsageDailyBudget) {
      elements.aiUsageDailyBudget.textContent = diagnostics?.daily_budget_usd ? toUsdLabel(diagnostics.daily_budget_usd) : "Not configured";
    }
    if (elements.aiUsageDailySpend) {
      elements.aiUsageDailySpend.textContent = toUsdLabel(diagnostics?.daily_spend_usd);
    }
    if (elements.aiUsageBudgetReached) {
      elements.aiUsageBudgetReached.textContent = diagnostics?.daily_budget_reached ? "Yes" : "No";
    }

    const operationTableBody = elements.aiUsageOperationBody;
    clearTableBody(operationTableBody);
    const byOperation = Array.isArray(diagnostics?.by_operation_30d) ? diagnostics.by_operation_30d : [];
    if (byOperation.length === 0) {
      appendEmptyRow(operationTableBody, 5, "No AI calls found for this period.");
    } else {
      byOperation.forEach((entry) => {
        const row = document.createElement("tr");
        row.className = "govuk-table__row";
        row.appendChild(buildCell(String(entry.operation || "-")));
        row.appendChild(buildCell(toIntegerLabel(entry.calls)));
        row.appendChild(buildCell(toIntegerLabel(entry.success)));
        row.appendChild(buildCell(toIntegerLabel(entry.tokens)));
        row.appendChild(buildCell(toUsdLabel(entry.cost_usd)));
        operationTableBody.appendChild(row);
      });
    }

    const modelTableBody = elements.aiUsageModelBody;
    clearTableBody(modelTableBody);
    const byModel = Array.isArray(diagnostics?.by_model_30d) ? diagnostics.by_model_30d : [];
    if (byModel.length === 0) {
      appendEmptyRow(modelTableBody, 5, "No AI calls found for this period.");
    } else {
      byModel.forEach((entry) => {
        const row = document.createElement("tr");
        row.className = "govuk-table__row";
        row.appendChild(buildCell(String(entry.model || "(unspecified)")));
        row.appendChild(buildCell(toIntegerLabel(entry.calls)));
        row.appendChild(buildCell(toIntegerLabel(entry.success)));
        row.appendChild(buildCell(toIntegerLabel(entry.tokens)));
        row.appendChild(buildCell(toUsdLabel(entry.cost_usd)));
        modelTableBody.appendChild(row);
      });
    }

    const recentTableBody = elements.aiUsageRecentBody;
    clearTableBody(recentTableBody);
    const recentCalls = Array.isArray(diagnostics?.recent_calls) ? diagnostics.recent_calls : [];
    const recentCallsPagination = diagnostics?.recent_calls_pagination || null;
    state.aiUsageRecentById = {};
    recentCalls.forEach((entry) => {
      state.aiUsageRecentById[String(entry.id)] = entry;
    });
    if (recentCalls.length === 0) {
      clearPagination(elements.aiUsageRecentPagination);
      appendEmptyRow(recentTableBody, 9, "No AI calls found.");
      return;
    }

    const hasApiPagination =
      recentCallsPagination &&
      Number.isFinite(Number(recentCallsPagination.page)) &&
      Number.isFinite(Number(recentCallsPagination.page_size)) &&
      Number.isFinite(Number(recentCallsPagination.total_items)) &&
      Number.isFinite(Number(recentCallsPagination.total_pages));

    const sortedRecentCalls = sortRowsForTable(recentCalls, "aiRecent");
    const pageResult = hasApiPagination
      ? {
          page: Number(recentCallsPagination.page),
          totalItems: Number(recentCallsPagination.total_items),
          totalPages: Number(recentCallsPagination.total_pages),
          startIndex: Math.max(0, (Number(recentCallsPagination.page) - 1) * Number(recentCallsPagination.page_size)),
          endIndex: Math.min(
            Number(recentCallsPagination.total_items),
            ((Number(recentCallsPagination.page) - 1) * Number(recentCallsPagination.page_size)) + sortedRecentCalls.length,
          ),
          rows: sortedRecentCalls,
        }
      : paginateItems(sortedRecentCalls, "aiRecent");

    pageResult.rows.forEach((entry) => {
      const row = document.createElement("tr");
      row.className = "govuk-table__row";

      row.appendChild(buildCell(toLocalTimestamp(entry.created_at)));
      row.appendChild(buildCell(String(entry.operation || "-")));
      row.appendChild(buildCell(String(entry.model || "-")));

      const statusCell = document.createElement("td");
      statusCell.className = "govuk-table__cell";
      const statusTag = buildAiStatusTag(entry.status);
      const hasPayload = entry.payload !== null && entry.payload !== undefined;
      if (hasPayload) {
        const detailButton = document.createElement("button");
        detailButton.type = "button";
        detailButton.className = "app-ai-status-button";
        detailButton.dataset.aiUsageDetail = String(entry.id);
        detailButton.title = "View AI call details";
        detailButton.appendChild(statusTag);
        statusCell.appendChild(detailButton);
      } else {
        statusCell.appendChild(statusTag);
      }
      row.appendChild(statusCell);

      const image = entry?.image || {};
      const imageLabelParts = [];
      if (entry.image_id) {
        imageLabelParts.push(`#${entry.image_id}`);
      }
      if (image.filename) {
        imageLabelParts.push(image.filename);
      }
      if (image.mime_type) {
        imageLabelParts.push(image.mime_type);
      }
      if (image.size_bytes) {
        imageLabelParts.push(`${toIntegerLabel(image.size_bytes)} bytes`);
      }
      row.appendChild(buildCell(imageLabelParts.length > 0 ? imageLabelParts.join(" | ") : "-"));

      row.appendChild(buildCell(toIntegerLabel(entry.total_tokens)));
      row.appendChild(buildCell(toUsdLabel(entry.final_cost_usd)));
      row.appendChild(buildCell(String(entry.request_id || "-")));

      const errorParts = [];
      if (entry.error_code) {
        errorParts.push(entry.error_code);
      }
      if (entry.provider_http_status) {
        errorParts.push(`HTTP ${entry.provider_http_status}`);
      }
      if (entry.error_message) {
        errorParts.push(entry.error_message);
      }
      row.appendChild(buildCell(errorParts.length > 0 ? errorParts.join(" | ") : "-"));

      recentTableBody.appendChild(row);
    });

    renderPaginationPair(elements.aiUsageRecentPaginationTop, elements.aiUsageRecentPagination, "aiRecent", pageResult);
  }

  function renderImageEmbeddingDiagnostics(diagnostics) {
    const model = diagnostics?.model || {};
    const health = diagnostics?.health || {};
    const performance = diagnostics?.performance || {};
    const hasDiagnostics = Boolean(diagnostics);

    if (elements.embeddingsModelKey) {
      elements.embeddingsModelKey.textContent = String(model.model_key || "-");
    }
    if (elements.embeddingsModelSource) {
      const localPath = String(model.local_path || "").trim();
      elements.embeddingsModelSource.textContent = localPath || String(model.name || "-");
    }
    if (elements.embeddingsLocalOnly) {
      elements.embeddingsLocalOnly.textContent = hasDiagnostics ? (model.local_files_only ? "Yes" : "No") : "-";
    }

    if (elements.embeddingsHealthTotalImages) {
      elements.embeddingsHealthTotalImages.textContent = toIntegerLabel(health.total_images);
    }
    if (elements.embeddingsHealthUpToDate) {
      elements.embeddingsHealthUpToDate.textContent = toIntegerLabel(health.up_to_date_embeddings);
    }
    if (elements.embeddingsHealthStale) {
      elements.embeddingsHealthStale.textContent = toIntegerLabel(health.stale_embeddings);
    }
    if (elements.embeddingsHealthMissing) {
      elements.embeddingsHealthMissing.textContent = toIntegerLabel(health.missing_embeddings);
    }
    if (elements.embeddingsHealthStatus) {
      elements.embeddingsHealthStatus.textContent = !hasDiagnostics
        ? "Unknown"
        : health.all_images_up_to_date
          ? "Healthy (all up to date)"
          : "Attention needed";
    }

    if (elements.embeddingsPerfSamples) {
      elements.embeddingsPerfSamples.textContent = toIntegerLabel(performance.samples);
    }
    if (elements.embeddingsPerfAvgMs) {
      elements.embeddingsPerfAvgMs.textContent = toMillisecondsLabel(performance.avg_ms);
    }
    if (elements.embeddingsPerfP95Ms) {
      elements.embeddingsPerfP95Ms.textContent = toMillisecondsLabel(performance.p95_ms);
    }
    if (elements.embeddingsPerfMinMaxMs) {
      const minMs = toMillisecondsLabel(performance.min_ms);
      const maxMs = toMillisecondsLabel(performance.max_ms);
      elements.embeddingsPerfMinMaxMs.textContent = minMs === "-" && maxMs === "-" ? "-" : `${minMs} / ${maxMs}`;
    }

    if (elements.embeddingsMissingGrid) {
      elements.embeddingsMissingGrid.innerHTML = "";
      const missingImages = Array.isArray(diagnostics?.missing_images) ? diagnostics.missing_images : [];
      if (missingImages.length === 0) {
        const emptyState = document.createElement("p");
        emptyState.className = "govuk-body govuk-!-margin-bottom-0";
        emptyState.textContent = "No missing embeddings in preview.";
        elements.embeddingsMissingGrid.appendChild(emptyState);
      } else {
        missingImages.forEach((image) => {
          const card = document.createElement("article");
          card.className = "app-embedding-missing-card";

          const thumbWrap = document.createElement("div");
          thumbWrap.className = "app-embedding-missing-thumb";
          thumbWrap.appendChild(
            buildThumbnailWidget(String(image.thumbnail_url || ""), {
              altText: String(image.filename || `Image #${image.id || "?"}`),
              openUrl: String(image.content_url || ""),
              previewUrl: String(image.preview_url || image.content_url || ""),
              widthPx: 120,
            }),
          );

          const meta = document.createElement("p");
          meta.className = "govuk-body-s govuk-!-margin-bottom-0";
          meta.textContent = `#${image.id} ${String(image.filename || "(unnamed)")}`;

          card.appendChild(thumbWrap);
          card.appendChild(meta);
          elements.embeddingsMissingGrid.appendChild(card);
        });
      }
    }
  }

  function renderLoans(loans) {
    const tableBody = elements.loansTableBody;
    clearTableBody(tableBody);

    if (!Array.isArray(loans) || loans.length === 0) {
      appendEmptyRow(tableBody, 7, "No loans found.");
      return;
    }

    const usersById = new Map(state.users.map((user) => [Number(user.id), user]));
    const jigsawsById = new Map(state.jigsaws.map((jigsaw) => [Number(jigsaw.id), jigsaw]));

    const sortedLoans = sortRowsForTable(loans, "loans");
    sortedLoans.forEach((loan) => {
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

      const actionCell = document.createElement("td");
      actionCell.className = "govuk-table__cell";

      if (loan.status === "active" || loan.status === "overdue") {
        const returnButton = document.createElement("button");
        returnButton.type = "button";
        returnButton.className = "govuk-button govuk-button--secondary app-inline-button";
        returnButton.setAttribute("data-module", "govuk-button");
        returnButton.dataset.loanReturn = String(loan.id);
        returnButton.textContent = "Return";
        actionCell.appendChild(returnButton);
      } else {
        actionCell.textContent = "-";
      }

      row.appendChild(actionCell);

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

    const sortedImages = sortRowsForTable(images, "jigsawImages");
    sortedImages.forEach((image) => {
      const row = document.createElement("tr");
      row.className = "govuk-table__row";

      row.appendChild(
        buildThumbnailCell(image.thumbnail_url || image.content_url, {
          altText: `Tagged image ${image.filename || "image"}`,
          previewUrl: image.preview_url || image.content_url,
          openUrl: image.content_url,
        })
      );
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
      state.imageLibraryFilterTagSelections = {};
      renderImageLibraryTagFilters([]);
      clearPagination(elements.imageLibraryPagination);
      appendEmptyRow(tableBody, 6, "No image library items found.");
      return;
    }

    const tagEntries = reconcileImageLibraryTagFilterState(images);
    renderImageLibraryTagFilters(tagEntries);

    const filteredImages = images.filter((image) => imageLibraryRowMatchesFilters(image));
    if (filteredImages.length === 0) {
      clearPagination(elements.imageLibraryPagination);
      appendEmptyRow(tableBody, 6, "No matching image library items found.");
      return;
    }

    const sortedFilteredImages = sortRowsForTable(filteredImages, "imageLibrary");
    const pageResult = paginateItems(sortedFilteredImages, "imageLibrary");
    const sortedJigsaws = [...state.jigsaws].sort((left, right) => String(left.title || "").localeCompare(String(right.title || "")));
    const jigsawsById = new Map(state.jigsaws.map((jigsaw) => [Number(jigsaw.id), jigsaw]));
    const canSetTag = currentUserHasCapability("image.tag");
    const canAssign = currentUserHasCapability("image.assign");
    const canUseAi = currentUserHasCapability("ai.manage");
    pageResult.rows.forEach((image) => {
      const row = document.createElement("tr");
      row.className = "govuk-table__row";

      const associatedJigsaw = image.jigsaw_id ? jigsawsById.get(Number(image.jigsaw_id)) : null;
      const associationLabel = associatedJigsaw
        ? `${associatedJigsaw.title || "(untitled)"} (id ${associatedJigsaw.id})`
        : image.jigsaw_id
          ? `id ${image.jigsaw_id}`
          : "unassigned";

      row.appendChild(
        buildThumbnailCell(image.thumbnail_url || image.content_url, {
          altText: `Library image ${image.filename || "image"}`,
          previewUrl: image.preview_url || image.content_url,
          openUrl: image.content_url,
        })
      );
      row.appendChild(buildCell(String(image.filename || "-")));
      row.appendChild(buildCell(associationLabel));

      const tagCell = document.createElement("td");
      tagCell.className = "govuk-table__cell";
      const tagControls = document.createElement("div");
      tagControls.className = "app-inline-controls app-image-actions__row";

      if (canSetTag) {
        const tagSelect = document.createElement("select");
        tagSelect.className = "govuk-select app-image-tag-select";
        tagSelect.dataset.imageTagSelect = String(image.id);

        const normalizedCurrentTag = normalizeImageTagLabel(image.tag);
        getImageTagDropdownValues(image.tag).forEach((tagValue) => {
          const option = document.createElement("option");
          option.value = tagValue;
          option.textContent = tagValue;
          if (toImageTagKey(tagValue) === toImageTagKey(normalizedCurrentTag)) {
            option.selected = true;
          }
          tagSelect.appendChild(option);
        });

        const tagButton = document.createElement("button");
        tagButton.type = "button";
        tagButton.className = "govuk-button govuk-button--secondary app-inline-button";
        tagButton.setAttribute("data-module", "govuk-button");
        tagButton.dataset.imageTagSet = String(image.id);
        tagButton.textContent = "Set tag";

        tagControls.appendChild(tagSelect);
        tagControls.appendChild(tagButton);
      } else {
        const tagReadOnly = document.createElement("span");
        tagReadOnly.textContent = String(image.tag || "-");
        tagControls.appendChild(tagReadOnly);
      }
      tagCell.appendChild(tagControls);
      row.appendChild(tagCell);

      row.appendChild(buildCell(toCapturedLabel(image)));

      const actionCell = document.createElement("td");
      actionCell.className = "govuk-table__cell";

      const controlsWrap = document.createElement("div");
      controlsWrap.className = "app-inline-controls app-image-actions";
      const assignControls = document.createElement("div");
      assignControls.className = "app-inline-controls app-image-actions__row";
      const suggestControls = document.createElement("div");
      suggestControls.className = "app-inline-controls app-image-actions__row govuk-!-margin-top-1";
      const actionButtons = document.createElement("div");
      actionButtons.className = "app-inline-controls app-image-actions__row";

      if (canAssign && !image.jigsaw_id && sortedJigsaws.length > 0) {
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

        assignControls.appendChild(select);
        assignControls.appendChild(button);
      } else if (!image.jigsaw_id) {
        const note = document.createElement("span");
        note.textContent = canAssign ? "No jigsaws available" : "Assign unavailable";
        assignControls.appendChild(note);
      } else {
        const assignedNote = document.createElement("span");
        assignedNote.textContent = "Assigned";
        assignControls.appendChild(assignedNote);

        if (canAssign) {
          const unassignButton = document.createElement("button");
          unassignButton.type = "button";
          unassignButton.className = "govuk-button govuk-button--secondary app-inline-button";
          unassignButton.setAttribute("data-module", "govuk-button");
          unassignButton.dataset.imageUnassign = String(image.id);
          unassignButton.textContent = "Unassign";
          assignControls.appendChild(unassignButton);
        }
      }

      if (canUseAi && !image.jigsaw_id) {
        const createButton = document.createElement("button");
        createButton.type = "button";
        createButton.className = "govuk-button govuk-button--secondary app-inline-button";
        createButton.setAttribute("data-module", "govuk-button");
        createButton.dataset.imageCreate = String(image.id);
        createButton.textContent = "Create";
        actionButtons.appendChild(createButton);
      }

      if (imageSupportsSimilarMatch(image)) {
        const suggestButton = document.createElement("button");
        suggestButton.type = "button";
        suggestButton.className = "govuk-button govuk-button--secondary app-inline-button";
        suggestButton.setAttribute("data-module", "govuk-button");
        suggestButton.dataset.imageSuggest = String(image.id);
        suggestButton.textContent = "Find similar";
        suggestControls.appendChild(suggestButton);

        const suggestWrap = document.createElement("div");
        suggestWrap.className = "app-inline-controls app-image-actions__row";
        suggestWrap.dataset.imageSuggestWrap = String(image.id);
        suggestControls.appendChild(suggestWrap);
      }

      const link = document.createElement("a");
      link.className = "govuk-button govuk-button--secondary app-inline-button";
      link.setAttribute("role", "button");
      link.setAttribute("data-module", "govuk-button");
      link.href = String(image.content_url || "#");
      link.textContent = "Open";
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      actionButtons.appendChild(link);

      if (canCurrentUserDeleteImage(image)) {
        const deleteButton = document.createElement("button");
        deleteButton.type = "button";
        deleteButton.className = "govuk-button govuk-button--warning app-inline-button";
        deleteButton.setAttribute("data-module", "govuk-button");
        deleteButton.dataset.imageDelete = String(image.id);
        deleteButton.textContent = "Delete";
        actionButtons.appendChild(deleteButton);
      }

      controlsWrap.appendChild(assignControls);
      controlsWrap.appendChild(suggestControls);
      controlsWrap.appendChild(actionButtons);

      actionCell.appendChild(controlsWrap);
      row.appendChild(actionCell);
      tableBody.appendChild(row);
    });

    renderPaginationPair(elements.imageLibraryPaginationTop, elements.imageLibraryPagination, "imageLibrary", pageResult);
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

  function imageMatchesBrowserFilters(image) {
    if (state.imageBrowser.filterShowAll) {
      return true;
    }

    const isUnassigned = !image?.jigsaw_id;
    const tagKey = toImageTagKey(image?.tag);
    const isBoxFamilyTag = [
      IMAGE_BROWSER_TAG_BOX,
      IMAGE_BROWSER_TAG_BOX_FRONT,
      IMAGE_BROWSER_TAG_BOX_SIDE,
      IMAGE_BROWSER_TAG_BOX_BACK,
    ].some((value) => tagKey === toImageTagKey(value));

    const predicates = {
      unassigned: isUnassigned,
      box: isBoxFamilyTag,
      reference: tagKey === toImageTagKey(IMAGE_BROWSER_TAG_REFERENCE),
      completed: tagKey === toImageTagKey(IMAGE_BROWSER_TAG_COMPLETED),
      inProgress: tagKey === toImageTagKey(IMAGE_BROWSER_TAG_IN_PROGRESS),
    };

    const filterModes = state.imageBrowser.filterModes || {};
    const activeModes = Object.values(filterModes).filter((mode) => mode !== BROWSER_FILTER_MODE_IGNORE);
    if (activeModes.length === 0) {
      return true;
    }

    return Object.entries(predicates).every(([filterKey, predicateValue]) => {
      const mode = String(filterModes[filterKey] || BROWSER_FILTER_MODE_IGNORE);
      if (mode === BROWSER_FILTER_MODE_INCLUDE) {
        return Boolean(predicateValue);
      }
      if (mode === BROWSER_FILTER_MODE_EXCLUDE) {
        return !Boolean(predicateValue);
      }
      return true;
    });
  }

  function getImageBrowserTagSortRank(tag) {
    const tagKey = toImageTagKey(tag);
    const isBoxFamilyTag = [
      IMAGE_BROWSER_TAG_BOX,
      IMAGE_BROWSER_TAG_BOX_FRONT,
      IMAGE_BROWSER_TAG_BOX_SIDE,
      IMAGE_BROWSER_TAG_BOX_BACK,
    ].some((value) => tagKey === toImageTagKey(value));
    if (isBoxFamilyTag) {
      return 0;
    }
    if (tagKey === toImageTagKey(IMAGE_BROWSER_TAG_COMPLETED)) {
      return 1;
    }
    if (tagKey === toImageTagKey(IMAGE_BROWSER_TAG_REFERENCE)) {
      return 2;
    }
    return 3;
  }

  function compareImageBrowserRows(left, right) {
    const leftAssigned = Number(left?.jigsaw_id || 0) > 0;
    const rightAssigned = Number(right?.jigsaw_id || 0) > 0;
    if (leftAssigned !== rightAssigned) {
      return leftAssigned ? -1 : 1;
    }

    if (leftAssigned && rightAssigned) {
      const leftJigsawId = Number(left?.jigsaw_id || 0);
      const rightJigsawId = Number(right?.jigsaw_id || 0);
      if (leftJigsawId !== rightJigsawId) {
        return leftJigsawId - rightJigsawId;
      }

      const leftTagRank = getImageBrowserTagSortRank(left?.tag);
      const rightTagRank = getImageBrowserTagSortRank(right?.tag);
      if (leftTagRank !== rightTagRank) {
        return leftTagRank - rightTagRank;
      }

      const leftId = Number(left?.id || 0);
      const rightId = Number(right?.id || 0);
      if (leftId !== rightId) {
        return leftId - rightId;
      }

      return String(left?.filename || "").localeCompare(String(right?.filename || ""), undefined, { sensitivity: "base" });
    }

    const filenameCompare = String(left?.filename || "").localeCompare(String(right?.filename || ""), undefined, { sensitivity: "base" });
    if (filenameCompare !== 0) {
      return filenameCompare;
    }
    return Number(left?.id || 0) - Number(right?.id || 0);
  }

  function getImageBrowserFilteredImages() {
    if (!Array.isArray(state.imageLibraryImages) || state.imageLibraryImages.length === 0) {
      return [];
    }
    return state.imageLibraryImages
      .filter((image) => imageMatchesBrowserFilters(image))
      .sort(compareImageBrowserRows);
  }

  function getCurrentImageBrowserItem() {
    const filtered = getImageBrowserFilteredImages();
    if (filtered.length === 0) {
      state.imageBrowser.index = 0;
      return null;
    }
    const index = Math.max(0, Math.min(state.imageBrowser.index, filtered.length - 1));
    state.imageBrowser.index = index;
    return filtered[index] || null;
  }

  function setImageBrowserIndexByImageId(imageId) {
    const filtered = getImageBrowserFilteredImages();
    if (!imageId || filtered.length === 0) {
      state.imageBrowser.index = 0;
      return false;
    }
    const foundIndex = filtered.findIndex((image) => Number(image.id) === Number(imageId));
    if (foundIndex >= 0) {
      state.imageBrowser.index = foundIndex;
      return true;
    }
    state.imageBrowser.index = 0;
    return false;
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

  function isImageBrowserSaveInFlight(imageId) {
    if (!imageId) {
      return false;
    }
    return Boolean(state.imageBrowserSavingImageIds[String(imageId)]);
  }

  function getImageBrowserInFlightSaveCount() {
    return Object.keys(state.imageBrowserSavingImageIds).length;
  }

  function hasActiveImageBrowserCropSelection() {
    const cropRect = state.imageBrowser.cropRect;
    return Boolean(cropRect && cropRect.width >= 8 && cropRect.height >= 8);
  }

  function canFindByNameForImage(image) {
    return Boolean(currentUserHasCapability("image.assign") && !image?.jigsaw_id);
  }

  function closeImageBrowserSuggestionModal() {
    state.imageBrowser.suggestionsImageId = null;
    if (elements.imageBrowserSuggestionsModal) {
      elements.imageBrowserSuggestionsModal.hidden = true;
    }
    if (elements.imageBrowserSuggestionsSummary) {
      elements.imageBrowserSuggestionsSummary.textContent = "";
    }
    if (elements.imageBrowserSuggestionsList) {
      while (elements.imageBrowserSuggestionsList.firstChild) {
        elements.imageBrowserSuggestionsList.removeChild(elements.imageBrowserSuggestionsList.firstChild);
      }
    }
  }

  function clearImageBrowserNameResults(message = "Type at least 2 characters") {
    if (!elements.imageBrowserNameResults) {
      return;
    }
    while (elements.imageBrowserNameResults.firstChild) {
      elements.imageBrowserNameResults.removeChild(elements.imageBrowserNameResults.firstChild);
    }
    const placeholder = document.createElement("option");
    placeholder.value = "";
    placeholder.textContent = message;
    elements.imageBrowserNameResults.appendChild(placeholder);
  }

  function getPreferredThumbnailImageForJigsawId(jigsawId) {
    const normalizedJigsawId = Number(jigsawId || 0);
    if (!normalizedJigsawId) {
      return null;
    }
    const thumbnailIndex = buildPreferredJigsawImageByJigsawId(state.jigsawThumbnailImages);
    const preferredFromThumbnailFeed = thumbnailIndex.get(normalizedJigsawId) || null;
    if (preferredFromThumbnailFeed) {
      return preferredFromThumbnailFeed;
    }

    const libraryIndex = buildPreferredJigsawImageByJigsawId(state.imageLibraryImages);
    return libraryIndex.get(normalizedJigsawId) || null;
  }

  function renderImageBrowserNameSelectionPreview() {
    const previewWrap = elements.imageBrowserNamePreview;
    if (!previewWrap) {
      return;
    }

    previewWrap.innerHTML = "";
    const selectedValue = String(elements.imageBrowserNameResults?.value || "").trim();
    let selectedJigsawId = Number.parseInt(selectedValue, 10);
    if (!Number.isFinite(selectedJigsawId) || selectedJigsawId <= 0) {
      const firstOptionValue = String(elements.imageBrowserNameResults?.options?.[0]?.value || "").trim();
      selectedJigsawId = Number.parseInt(firstOptionValue, 10);
    }
    if (!selectedJigsawId) {
      previewWrap.textContent = "Select a jigsaw to preview its thumbnail.";
      return;
    }

    const selectedJigsaw = (Array.isArray(state.jigsaws) ? state.jigsaws : []).find(
      (jigsaw) => Number(jigsaw?.id || 0) === selectedJigsawId,
    );
    const title = selectedJigsaw?.title || `(id ${selectedJigsawId})`;

    const titleLine = document.createElement("div");
    titleLine.className = "app-image-browser-name-preview__title govuk-body govuk-!-margin-bottom-2";
    titleLine.textContent = title;
    previewWrap.appendChild(titleLine);

    const preferredImage = getPreferredThumbnailImageForJigsawId(selectedJigsawId);
    const thumbnail = buildThumbnailWidget(preferredImage?.thumbnail_url || preferredImage?.content_url || "", {
      altText: `Thumbnail for ${title}`,
      previewUrl: preferredImage?.preview_url || preferredImage?.content_url || "",
      openUrl: preferredImage?.content_url || "",
      fallbackText: "No image",
      widthPx: 120,
    });
    thumbnail.classList.add("app-image-browser-name-preview__thumb");
    previewWrap.appendChild(thumbnail);
  }

  function closeImageBrowserNameAssignModal() {
    state.imageBrowser.nameAssignImageId = null;
    if (elements.imageBrowserNameAssignModal) {
      elements.imageBrowserNameAssignModal.hidden = true;
    }
    if (elements.imageBrowserNameAssignSummary) {
      elements.imageBrowserNameAssignSummary.textContent = "";
    }
    if (elements.imageBrowserNameQuery) {
      elements.imageBrowserNameQuery.value = "";
    }
    clearImageBrowserNameResults();
    if (elements.imageBrowserNamePreview) {
      elements.imageBrowserNamePreview.textContent = "Select a jigsaw to preview its thumbnail.";
    }
  }

  function renderImageBrowserNameMatchResults() {
    const query = String(elements.imageBrowserNameQuery?.value || "").trim().toLowerCase();
    if (!query || query.length < 2) {
      clearImageBrowserNameResults("Type at least 2 characters");
      renderImageBrowserNameSelectionPreview();
      return;
    }

    const matches = (Array.isArray(state.jigsaws) ? state.jigsaws : [])
      .filter((jigsaw) => Number(jigsaw?.id || 0) > 0)
      .filter((jigsaw) => String(jigsaw?.title || "").toLowerCase().includes(query))
      .sort((left, right) => String(left?.title || "").localeCompare(String(right?.title || ""), undefined, { sensitivity: "base" }))
      .slice(0, 50);

    if (!elements.imageBrowserNameResults) {
      return;
    }
    while (elements.imageBrowserNameResults.firstChild) {
      elements.imageBrowserNameResults.removeChild(elements.imageBrowserNameResults.firstChild);
    }

    if (matches.length === 0) {
      const option = document.createElement("option");
      option.value = "";
      option.textContent = "No matching jigsaws";
      elements.imageBrowserNameResults.appendChild(option);
      renderImageBrowserNameSelectionPreview();
      return;
    }

    matches.forEach((jigsaw) => {
      const option = document.createElement("option");
      const jigsawId = Number.parseInt(String(jigsaw.id), 10);
      option.value = String(jigsawId);
      option.textContent = `${jigsaw.title || "(untitled)"} (id ${jigsawId})`;
      elements.imageBrowserNameResults.appendChild(option);
    });
    const firstMatchId = Number.parseInt(String(matches[0]?.id || 0), 10);
    if (Number.isFinite(firstMatchId) && firstMatchId > 0) {
      elements.imageBrowserNameResults.value = String(firstMatchId);
    } else {
      elements.imageBrowserNameResults.selectedIndex = 0;
    }
    renderImageBrowserNameSelectionPreview();
  }

  function openImageBrowserNameAssignModal() {
    const item = getCurrentImageBrowserItem();
    if (!item || !item.id) {
      showFeedback("Could not determine which image to assign.", true);
      return;
    }
    if (!canFindByNameForImage(item)) {
      showFeedback("Find - Name is available only for unassigned images.", true);
      return;
    }

    closeImageBrowserSuggestionModal();
    state.imageBrowser.nameAssignImageId = Number(item.id);
    if (elements.imageBrowserNameAssignSummary) {
      elements.imageBrowserNameAssignSummary.textContent = `Search jigsaw titles to assign image #${Number(item.id)}.`;
    }
    if (elements.imageBrowserNameAssignModal) {
      elements.imageBrowserNameAssignModal.hidden = false;
    }
    if (elements.imageBrowserNameQuery) {
      elements.imageBrowserNameQuery.value = "";
      elements.imageBrowserNameQuery.focus();
    }
    clearImageBrowserNameResults();
    renderImageBrowserNameSelectionPreview();
  }

  async function assignCurrentImageByNameSelection() {
    const imageId = Number(state.imageBrowser.nameAssignImageId || 0);
    if (!imageId) {
      showFeedback("No image is selected for name assignment.", true);
      return;
    }
    const jigsawId = Number(elements.imageBrowserNameResults?.value || 0);
    if (!jigsawId) {
      showFeedback("Choose a jigsaw from the matches before assigning.", true);
      return;
    }

    try {
      await assignImageToJigsaw(imageId, jigsawId);
      closeImageBrowserNameAssignModal();
      showFeedback(`Image #${imageId} assigned to jigsaw #${jigsawId}.`);
      await Promise.all([loadDiaryEntriesForSelected(), loadImageLibraryImages(), loadJigsawImagesForSelected(), loadJigsaws(), loadAuditEvents()]);
      setImageBrowserIndexByImageId(imageId);
      await loadCurrentImageIntoBrowser();
    } catch (error) {
      showFeedback(error.message, true);
    }
  }

  function renderImageBrowserSuggestionModal(imageId, candidates) {
    const modal = elements.imageBrowserSuggestionsModal;
    const list = elements.imageBrowserSuggestionsList;
    if (!modal || !list) {
      return false;
    }

    state.imageBrowser.suggestionsImageId = Number(imageId || 0) || null;
    modal.hidden = false;

    while (list.firstChild) {
      list.removeChild(list.firstChild);
    }

    if (elements.imageBrowserSuggestionsSummary) {
      const candidateCount = Array.isArray(candidates) ? candidates.length : 0;
      elements.imageBrowserSuggestionsSummary.textContent = candidateCount > 0
        ? `Select a candidate to assign image #${Number(imageId)}.`
        : `No matches found for image #${Number(imageId)}.`;
    }

    if (!Array.isArray(candidates) || candidates.length === 0) {
      const note = document.createElement("p");
      note.className = "govuk-body govuk-!-margin-bottom-2";
      note.textContent = "No candidates";
      list.appendChild(note);
      return true;
    }

    candidates.forEach((candidate) => {
      const jigsawId = Number(candidate?.jigsaw_id || 0);
      if (!jigsawId) {
        return;
      }

      const scorePct = Math.max(0, Math.min(100, Math.round((Number(candidate?.score) || 0) * 1000) / 10));
      const confidence = String(candidate?.confidence || "low");

      const row = document.createElement("div");
      row.className = "app-diary-suggestion-row";

      const referenceImage = candidate?.reference_image || {};
      const thumb = buildThumbnailWidget(referenceImage.thumbnail_url || "", {
        altText: `Reference image for ${candidate?.jigsaw_title || `jigsaw ${jigsawId}`}`,
        previewUrl: referenceImage.preview_url || referenceImage.content_url || "",
        openUrl: referenceImage.content_url || "",
        fallbackText: "No ref",
        widthPx: 92,
      });
      thumb.classList.add("app-diary-suggestion-thumb");
      row.appendChild(thumb);

      const details = document.createElement("div");
      details.className = "app-diary-suggestion-details";

      const title = document.createElement("div");
      title.className = "app-diary-suggestion-title";
      title.textContent = candidate?.jigsaw_title || `(id ${jigsawId})`;
      details.appendChild(title);

      const meta = document.createElement("div");
      meta.className = "app-diary-suggestion-meta";
      meta.textContent = `${scorePct}% ${confidence} (${candidate?.reference_tag || "reference"})`;
      details.appendChild(meta);

      const assignButton = document.createElement("button");
      assignButton.type = "button";
      assignButton.className = "govuk-button govuk-button--secondary app-inline-button";
      assignButton.setAttribute("data-module", "govuk-button");
      assignButton.dataset.imageBrowserSuggestAssign = String(Number(imageId));
      assignButton.dataset.imageBrowserSuggestJigsawId = String(jigsawId);
      assignButton.textContent = "Assign";
      details.appendChild(assignButton);

      row.appendChild(details);
      list.appendChild(row);
    });

    return true;
  }

  function syncImageBrowserActionButtons() {
    const item = getCurrentImageBrowserItem();

    if (elements.imageBrowserDelete) {
      const canDeleteCurrent = Boolean(item && canCurrentUserDeleteImage(item));
      elements.imageBrowserDelete.hidden = !canDeleteCurrent;
      elements.imageBrowserDelete.disabled = !canDeleteCurrent;
    }

    if (elements.imageBrowserFindSimilar) {
      const canFindSimilar = Boolean(item && imageSupportsSimilarMatch(item));
      elements.imageBrowserFindSimilar.hidden = !canFindSimilar;
      elements.imageBrowserFindSimilar.disabled = !canFindSimilar;
    }

    if (elements.imageBrowserFindName) {
      const canFindByName = Boolean(item && canFindByNameForImage(item));
      elements.imageBrowserFindName.hidden = !canFindByName;
      elements.imageBrowserFindName.disabled = !canFindByName;
    }

    if (elements.imageBrowserCropApply) {
      const showApplyCrop = state.imageBrowser.cropMode && hasActiveImageBrowserCropSelection();
      elements.imageBrowserCropApply.hidden = !showApplyCrop;
      elements.imageBrowserCropApply.disabled = !showApplyCrop;
    }

    const currentImageId = Number(item?.id || 0);
    if (state.imageBrowser.suggestionsImageId && Number(state.imageBrowser.suggestionsImageId) !== currentImageId) {
      closeImageBrowserSuggestionModal();
    }
    if (state.imageBrowser.nameAssignImageId && Number(state.imageBrowser.nameAssignImageId) !== currentImageId) {
      closeImageBrowserNameAssignModal();
    }
  }

  function syncImageBrowserSaveButton() {
    if (!elements.imageBrowserSave) {
      return;
    }

    const currentImageId = Number(getCurrentImageBrowserItem()?.id || 0);
    const isCurrentSaveInFlight = isImageBrowserSaveInFlight(currentImageId);
    const canUploadImages = currentUserHasCapability("image.upload");
    elements.imageBrowserSave.disabled = !currentImageId || isCurrentSaveInFlight || !canUploadImages;
    elements.imageBrowserSave.textContent = isCurrentSaveInFlight ? "Saving..." : "Save overwrite";

    if (elements.imageBrowserSaveCreate) {
      const currentJigsawId = Number(getCurrentImageBrowserItem()?.jigsaw_id || 0);
      elements.imageBrowserSaveCreate.disabled = !currentImageId || !currentJigsawId || isCurrentSaveInFlight || !canUploadImages;
      elements.imageBrowserSaveCreate.textContent = isCurrentSaveInFlight ? "Saving..." : "Save create";
    }
  }

  function updateImageBrowserStatus() {
    if (!elements.imageBrowserStatus) {
      return;
    }

    const item = getCurrentImageBrowserItem();
    if (!item) {
      elements.imageBrowserStatus.textContent = "No images match the active browser filters.";
      closeImageBrowserSuggestionModal();
      closeImageBrowserNameAssignModal();
      syncImageBrowserActionButtons();
      syncImageBrowserSaveButton();
      return;
    }

    const filtered = getImageBrowserFilteredImages();
    const total = filtered.length;
    const totalUnfiltered = Array.isArray(state.imageLibraryImages) ? state.imageLibraryImages.length : 0;
    const index = state.imageBrowser.index + 1;
    const association = item.jigsaw_id ? `assigned to jigsaw ${item.jigsaw_id}` : "unassigned";
    const capturedAtLabel = item.captured_at ? toLocalTimestamp(item.captured_at) : "-";
    const captureSourceLabel = item.captured_at_source || "unknown";
    const dirty = browserHasPendingEdits() ? " | unsaved edits" : "";
    const currentSave = isImageBrowserSaveInFlight(item.id) ? " | saving image..." : "";
    const inFlightTotal = getImageBrowserInFlightSaveCount();
    const backgroundSaves = Math.max(0, inFlightTotal - (isImageBrowserSaveInFlight(item.id) ? 1 : 0));
    const backgroundSaveLabel = backgroundSaves > 0
      ? ` | ${backgroundSaves} save${backgroundSaves === 1 ? "" : "s"} running in background`
      : "";
    elements.imageBrowserStatus.textContent = `Image ${index}/${total} (filtered from ${totalUnfiltered}) | id: ${item.id || "-"} | ${item.filename || "(unnamed)"} | tag: ${item.tag || "-"} | ${association} | captured: ${capturedAtLabel} (${captureSourceLabel})${dirty}${currentSave}${backgroundSaveLabel}`;
    syncImageBrowserActionButtons();
    syncImageBrowserSaveButton();
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
    closeImageBrowserSuggestionModal();
    closeImageBrowserNameAssignModal();
  }

  function getCachedImageBrowserContent(imageId) {
    if (!imageId) {
      return null;
    }
    return state.imageBrowserContentCacheByImageId[String(imageId)] || null;
  }

  function setCachedImageBrowserContent(imageId, cachedContent) {
    if (!imageId || !cachedContent) {
      return;
    }
    state.imageBrowserContentCacheByImageId[String(imageId)] = cachedContent;
  }

  function clearCachedImageBrowserContent(imageId) {
    if (!imageId) {
      return;
    }
    delete state.imageBrowserContentCacheByImageId[String(imageId)];
  }

  function pruneImageBrowserContentCache(images) {
    const validIds = new Set((Array.isArray(images) ? images : []).map((image) => String(image.id)));
    Object.keys(state.imageBrowserContentCacheByImageId).forEach((imageId) => {
      if (!validIds.has(imageId)) {
        delete state.imageBrowserContentCacheByImageId[imageId];
      }
    });
  }

  async function prefetchImageBrowserByIndex(index) {
    const filtered = getImageBrowserFilteredImages();
    if (filtered.length === 0) {
      return;
    }

    const normalizedIndex = ((index % filtered.length) + filtered.length) % filtered.length;
    const item = filtered[normalizedIndex];
    if (!item || !item.id || getCachedImageBrowserContent(item.id)) {
      return;
    }

    try {
      const response = await fetch(String(item.content_url || ""), { credentials: "same-origin" });
      if (!response.ok) {
        return;
      }
      const blob = await response.blob();
      const dataUrl = await blobToDataUrl(blob);
      setCachedImageBrowserContent(item.id, {
        dataUrl,
        mimeType: String(blob.type || item.mime_type || "image/png").toLowerCase(),
        filename: item.filename || `image-${item.id}.png`,
      });
    } catch (_error) {
      // Ignore prefetch failures; browser will fetch on demand.
    }
  }

  async function loadCurrentImageIntoBrowser() {
    const item = getCurrentImageBrowserItem();
    clearImageBrowserWorkingState();

    if (!item) {
      await redrawImageBrowserCanvas();
      return;
    }

    const cached = getCachedImageBrowserContent(item.id);
    if (cached && cached.dataUrl) {
      state.imageBrowser.sourceDataUrl = cached.dataUrl;
      state.imageBrowser.workingDataUrl = cached.dataUrl;
      state.imageBrowser.workingImage = await loadImageElementFromDataUrl(cached.dataUrl);
      state.imageBrowser.mimeType = cached.mimeType || String(item.mime_type || "image/png").toLowerCase();
      state.imageBrowser.filename = cached.filename || item.filename || `image-${item.id}.png`;
    } else {
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
      setCachedImageBrowserContent(item.id, {
        dataUrl,
        mimeType: state.imageBrowser.mimeType,
        filename: state.imageBrowser.filename,
      });
    }

    await redrawImageBrowserCanvas();

    const currentIndex = state.imageBrowser.index;
    prefetchImageBrowserByIndex(currentIndex + 1);
    prefetchImageBrowserByIndex(currentIndex - 1);
  }

  async function openImageBrowser() {
    if (!elements.imageBrowserModal) {
      return;
    }
    let filtered = getImageBrowserFilteredImages();
    if (filtered.length === 0) {
      const hasAnyImages = Array.isArray(state.imageLibraryImages) && state.imageLibraryImages.length > 0;
      const hasActiveBrowserFilter =
        state.imageBrowser.filterShowAll ||
        Object.values(state.imageBrowser.filterModes || {}).some((mode) => mode !== BROWSER_FILTER_MODE_IGNORE);

      if (!hasAnyImages) {
        showFeedback("No images are available in the image library yet.", true);
        return;
      }

      if (hasActiveBrowserFilter) {
        state.imageBrowser.filterShowAll = false;
        state.imageBrowser.filterModes.unassigned = BROWSER_FILTER_MODE_IGNORE;
        state.imageBrowser.filterModes.box = BROWSER_FILTER_MODE_IGNORE;
        state.imageBrowser.filterModes.reference = BROWSER_FILTER_MODE_IGNORE;
        state.imageBrowser.filterModes.completed = BROWSER_FILTER_MODE_IGNORE;
        state.imageBrowser.filterModes.inProgress = BROWSER_FILTER_MODE_IGNORE;
        setImageBrowserFilterInputsFromState();
        filtered = getImageBrowserFilteredImages();

        if (filtered.length > 0) {
          showFeedback("No images matched the current browser filters, so all images are shown.");
        }
      }

      if (filtered.length === 0) {
        showFeedback("No images match the active browser filters.", true);
        return;
      }
    }

    state.imageBrowser.isOpen = true;
    elements.imageBrowserModal.hidden = false;

    try {
      await loadCurrentImageIntoBrowser();
    } catch (error) {
      if (error.status === 502) {
        await loadAiUsageDiagnostics();
        const requestId = error?.payload?.meta?.request_id;
        const hint = buildAiFailureHintForImage(getCurrentImageBrowserItem()?.id, requestId);
        if (hint) {
          showFeedback(`${error.message} Diagnostic: ${hint}`, true);
          return;
        }
      }
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
    const filtered = getImageBrowserFilteredImages();
    if (filtered.length === 0) {
      return;
    }

    if (browserHasPendingEdits()) {
      const shouldDiscard = window.confirm("Discard unsaved image edits and navigate?");
      if (!shouldDiscard) {
        return;
      }
    }

    const total = filtered.length;
    const current = state.imageBrowser.index;
    state.imageBrowser.index = (current + direction + total) % total;

    try {
      await loadCurrentImageIntoBrowser();
    } catch (error) {
      if (error.status === 502) {
        await loadAiUsageDiagnostics();
      }
      showFeedback(error.message, true);
    }
  }

  async function setImageBrowserTag(tag) {
    const item = getCurrentImageBrowserItem();
    if (!item) {
      return;
    }

    try {
      const payload = await apiRequest(`/api/v1/image-library/images/${item.id}/tag`, {
        method: "PATCH",
        body: JSON.stringify({ tag }),
      });

      const updated = payload?.data;
      if (updated && Number(updated.id)) {
        const imageId = Number(updated.id);
        state.imageLibraryImages = state.imageLibraryImages.map((entry) =>
          Number(entry.id) === imageId ? { ...entry, ...updated } : entry,
        );
      }

      showFeedback(`Image tagged as ${tag}.`);
      renderImageLibraryImages(state.imageLibraryImages);
      await loadCurrentImageIntoBrowser();
    } catch (error) {
      showFeedback(error.message, true);
    }
  }

  async function assignCurrentImageUsingNeighbor(offset) {
    const item = getCurrentImageBrowserItem();
    if (!item) {
      return;
    }

    const filtered = getImageBrowserFilteredImages();
    if (filtered.length === 0) {
      showFeedback("No images match the active browser filters.", true);
      return;
    }

    const neighborLabel = offset < 0 ? "previous" : "next";
    const neighborIndex = state.imageBrowser.index + offset;

    if (neighborIndex < 0 || neighborIndex >= filtered.length) {
      showFeedback(`No ${neighborLabel} image available to copy assignment from.`);
      return;
    }

    if (item.jigsaw_id) {
      showFeedback("Current image is already assigned to a jigsaw.");
      return;
    }

    const neighbor = filtered[neighborIndex];
    if (!neighbor?.jigsaw_id) {
      showFeedback(`${neighborLabel.charAt(0).toUpperCase()}${neighborLabel.slice(1)} image is not assigned to a jigsaw.`);
      return;
    }

    try {
      await apiRequest(`/api/v1/image-library/images/${item.id}/assign`, {
        method: "PATCH",
        body: JSON.stringify({ jigsaw_id: Number(neighbor.jigsaw_id) }),
      });

      showFeedback(`Image assigned to jigsaw from ${neighborLabel} image.`);
      await Promise.all([loadImageLibraryImages(), loadJigsawImagesForSelected(), loadAuditEvents()]);

      setImageBrowserIndexByImageId(item.id);
      await loadCurrentImageIntoBrowser();
    } catch (error) {
      showFeedback(error.message, true);
    }
  }

  async function createJigsawFromCurrentBrowserImage() {
    const item = getCurrentImageBrowserItem();
    if (!item) {
      return;
    }

    if (item.jigsaw_id) {
      showFeedback("This image is already assigned to a jigsaw; create-from-image requires an unassigned image.", true);
      return;
    }

    try {
      const payload = await apiRequest(`/api/v1/image-library/images/${item.id}/create-jigsaw`, {
        method: "POST",
        body: JSON.stringify({}),
      });
      const createdTitle = payload?.data?.jigsaw?.title || "(untitled)";
      showFeedback(`Jigsaw created from image: ${createdTitle}.`);

      await Promise.all([loadJigsaws(), loadImageLibraryImages(), loadJigsawImagesForSelected(), loadAuditEvents(), loadAiUsageDiagnostics()]);
      setImageBrowserIndexByImageId(item.id);
      await loadCurrentImageIntoBrowser();
    } catch (error) {
      showFeedback(error.message, true);
    }
  }

  async function deleteCurrentBrowserImage() {
    const item = getCurrentImageBrowserItem();
    if (!item) {
      return;
    }

    if (!canCurrentUserDeleteImage(item)) {
      showFeedback("You can only delete unassigned images.", true);
      return;
    }

    const confirmMessage = item.jigsaw_id
      ? "This image is assigned to a jigsaw. Delete it anyway? This cannot be undone."
      : "Delete this image? This cannot be undone.";
    const shouldDelete = window.confirm(confirmMessage);
    if (!shouldDelete) {
      return;
    }

    try {
      await apiRequest(`/api/v1/image-library/images/${item.id}`, { method: "DELETE" });
      clearCachedImageBrowserContent(item.id);
      showFeedback("Image deleted.");

      const previousItemId = item.id;
      await Promise.all([loadImageLibraryImages(), loadJigsawImagesForSelected(), loadAuditEvents()]);

      const filtered = getImageBrowserFilteredImages();
      if (filtered.length === 0) {
        closeImageBrowser();
        return;
      }

      if (!setImageBrowserIndexByImageId(previousItemId)) {
        state.imageBrowser.index = Math.min(state.imageBrowser.index, filtered.length - 1);
      }
      await loadCurrentImageIntoBrowser();
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
    if (!hasActiveImageBrowserCropSelection()) {
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

  function canvasToBlob(canvas, mimeType, quality = undefined) {
    return new Promise((resolve, reject) => {
      canvas.toBlob((blob) => {
        if (!blob) {
          reject(new Error("Failed to serialize image."));
          return;
        }
        resolve(blob);
      }, mimeType, quality);
    });
  }

  async function saveImageBrowserOverwrite() {
    if (!currentUserHasCapability("image.upload")) {
      showFeedback("You do not have permission to overwrite images.", true);
      return;
    }

    const item = getCurrentImageBrowserItem();
    if (!item) {
      return;
    }

    const savedImageId = Number(item.id || 0);
    if (!savedImageId) {
      return;
    }
    if (isImageBrowserSaveInFlight(savedImageId)) {
      showFeedback("Save overwrite is already in progress for this image.", true);
      return;
    }

    const shouldOverwrite = window.confirm("Overwrite this image with the current edits? This cannot be undone.");
    if (!shouldOverwrite) {
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

    state.imageBrowserSavingImageIds[String(savedImageId)] = true;
    updateImageBrowserStatus();

    try {
      const payload = await apiRequest(`/api/v1/image-library/images/${item.id}/content`, {
        method: "PUT",
        body: formData,
      });

      const updatedImage = payload?.data || null;
      if (updatedImage && Number(updatedImage.id) > 0) {
        const updatedImageId = Number(updatedImage.id);

        state.imageLibraryImages = Array.isArray(state.imageLibraryImages)
          ? state.imageLibraryImages.map((entry) => (Number(entry.id) === updatedImageId ? { ...entry, ...updatedImage } : entry))
          : [];

        if (Array.isArray(state.jigsawThumbnailImages)) {
          let didReplaceThumbnail = false;
          state.jigsawThumbnailImages = state.jigsawThumbnailImages.map((entry) => {
            if (Number(entry.id) === updatedImageId) {
              didReplaceThumbnail = true;
              return { ...entry, ...updatedImage };
            }
            return entry;
          });

          if (!didReplaceThumbnail && Number(updatedImage.jigsaw_id || 0) > 0) {
            state.jigsawThumbnailImages.push(updatedImage);
          }
        }

        renderImageLibraryImages(state.imageLibraryImages);
        renderJigsaws(state.jigsaws);
      }

      clearCachedImageBrowserContent(savedImageId);
      showFeedback("Image overwritten successfully.");
      const activeImageId = Number(getCurrentImageBrowserItem()?.id || 0);
      if (activeImageId === savedImageId) {
        setImageBrowserIndexByImageId(savedImageId);
        await loadCurrentImageIntoBrowser();
      }

      Promise.all([loadImageLibraryImages({ skipBrowserReload: true }), loadJigsawImagesForSelected(), loadAuditEvents()]).catch(() => {
        // Background refresh errors are surfaced by individual loaders.
      });
    } catch (error) {
      showFeedback(error.message, true);
    } finally {
      delete state.imageBrowserSavingImageIds[String(savedImageId)];
      updateImageBrowserStatus();
    }
  }

  async function saveImageBrowserCreateReference() {
    if (!currentUserHasCapability("image.upload")) {
      showFeedback("You do not have permission to create reference images.", true);
      return;
    }

    const item = getCurrentImageBrowserItem();
    if (!item) {
      return;
    }

    const sourceImageId = Number(item.id || 0);
    if (!sourceImageId) {
      return;
    }
    if (isImageBrowserSaveInFlight(sourceImageId)) {
      showFeedback("Save action is already in progress for this image.", true);
      return;
    }

    const jigsawId = Number(item.jigsaw_id || 0);
    if (!jigsawId) {
      showFeedback("Assign this image to a jigsaw before creating a Reference image.", true);
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

    const baseFilename = String(state.imageBrowser.filename || item.filename || `image-${sourceImageId}.png`);
    const referenceFilename = baseFilename.includes(".")
      ? baseFilename.replace(/(\.[a-z0-9]+)$/i, "-reference$1")
      : `${baseFilename}-reference.png`;

    const formData = new FormData();
    formData.append("tag", IMAGE_BROWSER_TAG_REFERENCE);
    formData.append("defer_processing", "1");
    formData.append("image", blob, referenceFilename);

    state.imageBrowserSavingImageIds[String(sourceImageId)] = true;
    state.imageBrowser.sourceDataUrl = state.imageBrowser.workingDataUrl;
    state.imageBrowser.rotationDegrees = 0;
    state.imageBrowser.cropMode = false;
    state.imageBrowser.cropRect = null;
    updateImageBrowserStatus();

    showFeedback("Reference image save started in background.");
    try {
      const payload = await apiRequest(`/api/v1/jigsaws/${jigsawId}/images`, {
        method: "POST",
        body: formData,
        timeoutMs: 120000,
      });

      const createdReference = payload?.data || null;
      if (!createdReference || !Number(createdReference.id || 0)) {
        showFeedback("Reference image create did not return a created image.", true);
        return;
      }

      showFeedback(`Reference image created as image #${createdReference.id}.`);
      Promise.all([loadImageLibraryImages(), loadJigsawImagesForSelected(), loadAuditEvents()]).catch(() => {
        // Background refresh errors are surfaced by individual loaders.
      });
    } catch (error) {
      showFeedback(error.message, true);
    } finally {
      delete state.imageBrowserSavingImageIds[String(sourceImageId)];
      updateImageBrowserStatus();
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
    if (event.key === "r" || event.key === "R") {
      event.preventDefault();
      setImageBrowserTag(IMAGE_BROWSER_TAG_REFERENCE);
      return;
    }
    if (event.code === "Comma" || event.key === ",") {
      event.preventDefault();
      assignCurrentImageUsingNeighbor(-1);
      return;
    }
    if (event.code === "Period" || event.key === ".") {
      event.preventDefault();
      assignCurrentImageUsingNeighbor(1);
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
    if (event.key === "Delete" || event.key === "Backspace") {
      event.preventDefault();
      deleteCurrentBrowserImage();
      return;
    }
    if (event.key === "j" || event.key === "J") {
      event.preventDefault();
      createJigsawFromCurrentBrowserImage();
      return;
    }
    if (event.key === "v" || event.key === "V") {
      event.preventDefault();
      saveImageBrowserCreateReference();
      return;
    }
    if (event.key === "Escape") {
      event.preventDefault();
      if (elements.imageBrowserNameAssignModal && !elements.imageBrowserNameAssignModal.hidden) {
        closeImageBrowserNameAssignModal();
        return;
      }
      if (elements.imageBrowserSuggestionsModal && !elements.imageBrowserSuggestionsModal.hidden) {
        closeImageBrowserSuggestionModal();
        return;
      }
      closeImageBrowser();
    }
  }

  function renderDiaryEntriesList(entries, emptyMessage = "No diary entries found.") {
    const tableBody = elements.diaryEntriesTableBody;
    clearTableBody(tableBody);

    if (!Array.isArray(entries) || entries.length === 0) {
      clearPagination(elements.diaryPagination);
      appendEmptyRow(tableBody, 7, emptyMessage);
      return;
    }

    const sortedEntries = sortRowsForTable(entries, "diary");
    const pageResult = paginateItems(sortedEntries, "diary");

    pageResult.rows.forEach((entry) => {
      const row = document.createElement("tr");
      row.className = "govuk-table__row";
      const isFormalDiaryEntry = entry?.entry_type !== "orphan_completed_image";

      const sourceImageUrls = getDiaryEntryImageUrls(entry);
      const jigsawLabel = isFormalDiaryEntry
        ? getJigsawTitleById(entry.jigsaw_id)
        : "Unlinked completion";
      const identifierLabel = isFormalDiaryEntry
        ? String(entry.id)
        : `Image #${Number(entry?.source_image_id || entry?.id || 0)}`;

      row.appendChild(buildCell(identifierLabel));
      row.appendChild(buildCell(jigsawLabel));
      row.appendChild(
        buildThumbnailCell(sourceImageUrls.thumbnailUrl, {
          altText: `Completed image for diary entry ${entry.id}`,
          previewUrl: sourceImageUrls.previewUrl,
          openUrl: sourceImageUrls.openUrl,
          fallbackText: "No image",
        })
      );
      row.appendChild(buildCell(toLocalTimestamp(entry.completed_at)));
      row.appendChild(
        buildCell(
          isFormalDiaryEntry && entry.difficulty !== null && entry.difficulty !== undefined
            ? String(entry.difficulty)
            : "-",
        ),
      );
      row.appendChild(buildCell(isFormalDiaryEntry ? String(entry.notes || "-") : "-"));

      const actionCell = document.createElement("td");
      actionCell.className = "govuk-table__cell";

      const canUpdateDiaryAny = currentUserHasCapability("diary.update_any");
      const canUpdateDiaryOwn = currentUserHasCapability("diary.update_own");
      const canDeleteDiaryAny = currentUserHasCapability("diary.delete_any");
      const canAssignImages = currentUserHasCapability("image.assign");
      const canDeleteUnassignedImages = canCurrentUserDeleteImage({ jigsaw_id: null });
      const canEditThisEntry =
        isFormalDiaryEntry && (
          canUpdateDiaryAny ||
          (canUpdateDiaryOwn && Number(entry?.created_by_user_id || 0) === Number(state.user?.id || 0))
        );

      if (canEditThisEntry || (isFormalDiaryEntry && canDeleteDiaryAny)) {
        const editButton = document.createElement("button");
        editButton.type = "button";
        editButton.className = "govuk-button govuk-button--secondary app-inline-button";
        editButton.setAttribute("data-module", "govuk-button");
        editButton.dataset.diaryEdit = String(entry.id);
        editButton.textContent = "Edit";
        editButton.disabled = !canEditThisEntry;

        const deleteButton = document.createElement("button");
        deleteButton.type = "button";
        deleteButton.className = "govuk-button govuk-button--warning app-inline-button";
        deleteButton.setAttribute("data-module", "govuk-button");
        deleteButton.dataset.diaryDelete = String(entry.id);
        deleteButton.textContent = "Delete";
        deleteButton.disabled = !canDeleteDiaryAny;

        actionCell.appendChild(editButton);
        if (canDeleteDiaryAny) {
          actionCell.appendChild(deleteButton);
        }
      } else if (!isFormalDiaryEntry && (canAssignImages || canDeleteUnassignedImages)) {
        const suggestImageId = Number(entry?.source_image_id || entry?.id || 0);
        if (suggestImageId <= 0) {
          actionCell.textContent = "-";
          row.appendChild(actionCell);
          tableBody.appendChild(row);
          return;
        }

        if (canAssignImages) {
          const suggestButton = document.createElement("button");
          suggestButton.type = "button";
          suggestButton.className = "govuk-button govuk-button--secondary app-inline-button";
          suggestButton.setAttribute("data-module", "govuk-button");
          suggestButton.dataset.diarySuggestImage = String(suggestImageId);
          suggestButton.textContent = "Find similar";

          const assignWrap = document.createElement("div");
          assignWrap.className = "app-inline-controls app-image-actions__row govuk-!-margin-top-2";
          assignWrap.dataset.diarySuggestWrap = String(suggestImageId);

          actionCell.appendChild(suggestButton);
          actionCell.appendChild(assignWrap);
        }

        if (canDeleteUnassignedImages) {
          const deleteOrphanButton = document.createElement("button");
          deleteOrphanButton.type = "button";
          deleteOrphanButton.className = "govuk-button govuk-button--warning app-inline-button";
          deleteOrphanButton.setAttribute("data-module", "govuk-button");
          deleteOrphanButton.dataset.diaryDeleteImage = String(suggestImageId);
          deleteOrphanButton.textContent = "Delete image";
          actionCell.appendChild(deleteOrphanButton);
        }
      } else {
        actionCell.textContent = "-";
      }

      row.appendChild(actionCell);
      tableBody.appendChild(row);
    });

    renderPaginationPair(elements.diaryPaginationTop, elements.diaryPagination, "diary", pageResult);
  }

  function toLocalDateKey(value) {
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
    return `${year}-${month}-${day}`;
  }

  function toDiaryCalendarMonthLabel(year, month) {
    const monthStart = new Date(Number(year), Number(month), 1);
    return monthStart.toLocaleDateString(undefined, {
      month: "long",
      year: "numeric",
    });
  }

  function getDiaryCalendarImageUrls(entry, preferredImagesByJigsawId) {
    const sourceImageUrls = getDiaryEntryImageUrls(entry);
    if (sourceImageUrls.thumbnailUrl) {
      return sourceImageUrls;
    }

    const preferredImage = preferredImagesByJigsawId.get(Number(entry?.jigsaw_id || 0));
    return {
      thumbnailUrl: String(preferredImage?.thumbnail_url || preferredImage?.content_url || ""),
      previewUrl: String(preferredImage?.preview_url || preferredImage?.content_url || ""),
      openUrl: String(preferredImage?.content_url || ""),
    };
  }

  function renderDiaryCalendar(entries, emptyMessage = "No diary entries found.") {
    if (!elements.diaryCalendarGrid) {
      return;
    }

    clearTableBody(elements.diaryEntriesTableBody);
    clearPagination(elements.diaryPaginationTop);
    clearPagination(elements.diaryPagination);

    const calendarEntries = Array.isArray(entries)
      ? entries.filter((entry) => entry?.entry_type !== "orphan_completed_image" && Number(entry?.jigsaw_id || 0) > 0)
      : [];

    const entriesByDate = new Map();
    calendarEntries.forEach((entry) => {
      const dateKey = toLocalDateKey(entry?.completed_at);
      if (!dateKey) {
        return;
      }
      if (!entriesByDate.has(dateKey)) {
        entriesByDate.set(dateKey, []);
      }
      entriesByDate.get(dateKey).push(entry);
    });

    const sortedDays = Array.from(entriesByDate.keys()).sort();
    if (elements.diaryCalendarSummary) {
      if (sortedDays.length > 0) {
        const monthKey = `${state.diaryCalendar.year}-${String(state.diaryCalendar.month + 1).padStart(2, "0")}`;
        const monthEntryCount = sortedDays.filter((dateKey) => dateKey.startsWith(monthKey)).reduce((count, dateKey) => {
          const dayEntries = entriesByDate.get(dateKey) || [];
          return count + dayEntries.length;
        }, 0);
        elements.diaryCalendarSummary.textContent = `${monthEntryCount} completion${monthEntryCount === 1 ? "" : "s"} in this month.`;
      } else {
        elements.diaryCalendarSummary.textContent = emptyMessage;
      }
    }

    if (elements.diaryCalendarMonthLabel) {
      elements.diaryCalendarMonthLabel.textContent = toDiaryCalendarMonthLabel(
        state.diaryCalendar.year,
        state.diaryCalendar.month,
      );
    }

    while (elements.diaryCalendarGrid.firstChild) {
      elements.diaryCalendarGrid.removeChild(elements.diaryCalendarGrid.firstChild);
    }

    const firstDayOfMonth = new Date(state.diaryCalendar.year, state.diaryCalendar.month, 1);
    const monthStartWeekday = firstDayOfMonth.getDay();
    const gridStartDate = new Date(state.diaryCalendar.year, state.diaryCalendar.month, 1 - monthStartWeekday);
    const preferredImagesByJigsawId = buildPreferredJigsawImageByJigsawId(state.jigsawThumbnailImages);

    for (let dayOffset = 0; dayOffset < 42; dayOffset += 1) {
      const cellDate = new Date(gridStartDate.getFullYear(), gridStartDate.getMonth(), gridStartDate.getDate() + dayOffset);
      const cellDateKey = toLocalDateKey(cellDate);
      const isCurrentMonth = cellDate.getMonth() === state.diaryCalendar.month && cellDate.getFullYear() === state.diaryCalendar.year;
      const dayEntries = entriesByDate.get(cellDateKey) || [];
      const sortedDayEntries = [...dayEntries].sort((left, right) => {
        const leftTime = new Date(left?.completed_at || 0).valueOf();
        const rightTime = new Date(right?.completed_at || 0).valueOf();
        return rightTime - leftTime;
      });
      const primaryEntry = sortedDayEntries[0] || null;

      const dayCell = document.createElement("article");
      dayCell.className = "app-diary-calendar-day";
      dayCell.setAttribute("role", "gridcell");
      if (!isCurrentMonth) {
        dayCell.classList.add("app-diary-calendar-day--outside-month");
      }
      if (primaryEntry) {
        dayCell.classList.add("app-diary-calendar-day--has-entry");
      }

      const dayLabel = document.createElement("p");
      dayLabel.className = "app-diary-calendar-day__number";
      dayLabel.classList.add("govuk-body", "govuk-!-margin-bottom-0");
      dayLabel.style.fontFamily = '"GDS Transport", arial, sans-serif';
      dayLabel.textContent = String(cellDate.getDate());
      dayCell.appendChild(dayLabel);

      if (primaryEntry) {
        const thumbnailUrls = getDiaryCalendarImageUrls(primaryEntry, preferredImagesByJigsawId);
        const jigsawTitle = getJigsawTitleById(primaryEntry?.jigsaw_id);
        const thumbnail = buildThumbnailWidget(thumbnailUrls.thumbnailUrl, {
          altText: `Completion image for ${jigsawTitle}`,
          previewUrl: thumbnailUrls.previewUrl,
          openUrl: thumbnailUrls.openUrl,
          fallbackText: "Logged",
          widthPx: 96,
        });
        thumbnail.classList.add("app-diary-calendar-thumb");
        dayCell.appendChild(thumbnail);

        const dayMeta = document.createElement("p");
        dayMeta.className = "app-diary-calendar-day__meta";
        dayMeta.classList.add("govuk-body-s", "govuk-!-margin-bottom-0");
        dayMeta.textContent = sortedDayEntries.length > 1
          ? `${jigsawTitle} (+${sortedDayEntries.length - 1} more)`
          : jigsawTitle;
        dayCell.appendChild(dayMeta);
      }

      elements.diaryCalendarGrid.appendChild(dayCell);
    }
  }

  function renderDiaryEntries(entries, emptyMessage = "No diary entries found.") {
    updateDiaryViewUi();
    if (normalizeDiaryViewMode(state.diaryViewMode) === DIARY_VIEW_MODE_CALENDAR) {
      renderDiaryCalendar(entries, emptyMessage);
      return;
    }
    renderDiaryEntriesList(entries, emptyMessage);
  }

  async function refreshSession() {
    try {
      const payload = await apiRequest("/api/v1/auth/me");
      state.user = payload.data.user;
      state.csrfToken = payload.data.csrf_token || null;
      state.authProvider = String(payload.data.auth_provider || "local").toLowerCase();
      closeAuthDialog();
      setSessionSummary();
      return true;
    } catch (error) {
      state.user = null;
      state.csrfToken = null;
      state.authProvider = null;
      state.roleDefinitions = [];
      renderUserRoleSelectors();
      setSessionSummary();
      if (error.status !== 401) {
        showFeedback(error.message, true);
      }
      return false;
    }
  }

  async function fetchStfdLoginInfo() {
    try {
      const payload = await apiRequest("/api/v1/auth/stfd/login-url");
      state.stfdAuthEnabled = Boolean(payload?.data?.enabled);
      state.stfdAllowLocalLogin = Boolean(payload?.data?.allow_local_login ?? true);
      state.stfdLoginUrl =
        state.stfdAuthEnabled && typeof payload?.data?.login_url === "string" && payload.data.login_url
          ? payload.data.login_url
          : null;
    } catch (_error) {
      state.stfdAuthEnabled = false;
      state.stfdAllowLocalLogin = true;
      state.stfdLoginUrl = null;
    }
    syncLoginUiForAuthMode();
  }

  async function consumeStfdTokenFromUrl() {
    if (!state.stfdAuthEnabled) {
      return false;
    }

    const url = new URL(window.location.href);
    const token = String(url.searchParams.get("token") || "").trim();
    if (!token) {
      return false;
    }

    try {
      const payload = await apiRequest("/api/v1/auth/login", {
        method: "POST",
        body: JSON.stringify({ token }),
      });
      state.user = payload.data.user;
      state.csrfToken = payload.data.csrf_token;
      state.authProvider = String(payload.data.auth_provider || "stfd").toLowerCase();
      closeAuthDialog();
      setSessionSummary();

      url.searchParams.delete("token");
      window.history.replaceState({}, document.title, url.pathname + url.search + url.hash);
      showFeedback("Signed in successfully.");
      return true;
    } catch (error) {
      url.searchParams.delete("token");
      window.history.replaceState({}, document.title, url.pathname + url.search + url.hash);
      showFeedback(error.message, true);
      return false;
    }
  }

  async function loadRoles() {
    if (!state.user) {
      state.roleDefinitions = [];
      renderUserRoleSelectors();
      return;
    }

    if (!currentUserHasCapability("user.manage")) {
      state.roleDefinitions = [];
      renderUserRoleSelectors();
      return;
    }

    try {
      const payload = await apiRequest("/api/v1/roles");
      const fetchedRoles = Array.isArray(payload.data) ? payload.data : [];
      state.roleDefinitions = fetchedRoles
        .map((entry) => ({
          name: String(entry?.name || "").trim(),
          description: String(entry?.description || "").trim() || null,
        }))
        .filter((entry) => Boolean(entry.name));
      renderUserRoleSelectors();
    } catch (error) {
      if (error.status === 403) {
        state.roleDefinitions = [];
        renderUserRoleSelectors();
        return;
      }
      showFeedback(error.message, true);
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
    try {
      const payload = await apiRequest("/api/v1/jigsaws");
      state.jigsaws = Array.isArray(payload.data) ? payload.data : [];
      renderJigsaws(state.jigsaws);
      populateLoanFormOptions();
      populateJigsawImageOptions();
      populateDiaryJigsawOptions();
      populateImageLibraryJigsawOptions();
    } catch (error) {
      state.jigsaws = [];
      renderJigsaws([]);
      closeJigsawEditor();
      populateLoanFormOptions();
      populateJigsawImageOptions();
      populateDiaryJigsawOptions();
      populateImageLibraryJigsawOptions();
      showFeedback(error.message, true);
    }
  }

  async function loadJigsawThumbnailImages() {
    try {
      const payload = await apiRequest("/api/v1/jigsaws/thumbnail-images");
      state.jigsawThumbnailImages = Array.isArray(payload.data) ? payload.data : [];
      if (elements.imageBrowserNameAssignModal && !elements.imageBrowserNameAssignModal.hidden) {
        renderImageBrowserNameSelectionPreview();
      }
      renderJigsaws(state.jigsaws);
    } catch (_error) {
      state.jigsawThumbnailImages = [];
      if (elements.imageBrowserNameAssignModal && !elements.imageBrowserNameAssignModal.hidden) {
        renderImageBrowserNameSelectionPreview();
      }
      renderJigsaws(state.jigsaws);
    }
  }

  async function loadJigsawImagesForSelected() {
    if (!currentUserHasCapability("image.manage_library")) {
      state.jigsawImages = [];
      renderJigsawImages([]);
      return;
    }

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

  async function loadImageLibraryImages(options = {}) {
    const shouldSkipBrowserReload = Boolean(options && options.skipBrowserReload);

    if (!state.user) {
      state.imageLibraryImages = [];
      state.jigsawThumbnailImages = [];
      state.imageBrowserContentCacheByImageId = {};
      state.imageBrowserSavingImageIds = {};
      setImageLibraryLoadSummary("Sign in to load images for the browser.");
      renderImageLibraryImages([]);
      renderJigsaws(state.jigsaws);
      return;
    }

    if (!currentUserHasCapability("image.manage_library")) {
      state.imageLibraryImages = [];
      state.jigsawThumbnailImages = [];
      state.imageBrowserContentCacheByImageId = {};
      state.imageBrowserSavingImageIds = {};
      setImageLibraryLoadSummary("You do not have access to image library data.");
      renderImageLibraryImages([]);
      renderJigsaws(state.jigsaws);
      return;
    }

    try {
      const pageSize = 500;
      const maxPageRequests = 200;
      const allImages = [];
      let page = 1;
      let totalPages = 1;

      while (page <= totalPages && page <= maxPageRequests) {
        const payload = await apiRequest(`/api/v1/image-library/images?page=${page}&page_size=${pageSize}`);
        const pageImages = Array.isArray(payload?.data) ? payload.data : [];
        allImages.push(...pageImages);

        const metaTotalPages = Number(payload?.meta?.pagination?.total_pages || 0);
        if (Number.isFinite(metaTotalPages) && metaTotalPages > 0) {
          totalPages = metaTotalPages;
        } else if (pageImages.length < pageSize) {
          totalPages = page;
        }

        page += 1;
      }

      state.imageLibraryImages = allImages;
      setImageLibraryLoadSummary(`Loaded ${allImages.length.toLocaleString()} images for the browser.`);
      pruneImageBrowserContentCache(state.imageLibraryImages);
      renderImageLibraryImages(state.imageLibraryImages);
      await loadJigsawThumbnailImages();
      if (state.imageBrowser.isOpen && !shouldSkipBrowserReload) {
        await loadCurrentImageIntoBrowser();
      }
    } catch (error) {
      if (error.status === 403) {
        state.imageLibraryImages = [];
        state.jigsawThumbnailImages = [];
        state.imageBrowserContentCacheByImageId = {};
        state.imageBrowserSavingImageIds = {};
        setImageLibraryLoadSummary("You do not have access to image library data.");
        renderImageLibraryImages([]);
        renderJigsaws(state.jigsaws);
        if (state.imageBrowser.isOpen && !shouldSkipBrowserReload) {
          await loadCurrentImageIntoBrowser();
        }
        return;
      }
      state.imageLibraryImages = [];
      state.jigsawThumbnailImages = [];
      state.imageBrowserContentCacheByImageId = {};
      state.imageBrowserSavingImageIds = {};
      setImageLibraryLoadSummary("Could not load image library data.");
      renderImageLibraryImages([]);
      renderJigsaws(state.jigsaws);
      if (state.imageBrowser.isOpen && !shouldSkipBrowserReload) {
        await loadCurrentImageIntoBrowser();
      }
      showFeedback(error.message, true);
    }
  }

  async function loadDiaryEntriesForSelected() {
    const selectedJigsawId = Number(elements.diaryJigsawId?.value || "0");
    const effectiveSelectedJigsawId = state.diarySelectionTouchedByUser ? selectedJigsawId : 0;
    if (!state.user) {
      state.diaryEntries = [];
      state.pagination.diary = 1;
      setDiaryEntriesCaption(0);
      renderDiaryEntries([], getDiaryEntriesEmptyMessage(0));
      return;
    }

    if (!currentUserHasCapability("diary.read")) {
      state.diaryEntries = [];
      state.pagination.diary = 1;
      setDiaryEntriesCaption(0);
      renderDiaryEntries([], getDiaryEntriesEmptyMessage(0));
      return;
    }

    if (!state.diarySelectionTouchedByUser && elements.diaryJigsawId) {
      elements.diaryJigsawId.value = "";
    }
    setDiaryEntriesCaption(effectiveSelectedJigsawId);

    try {
      const query = effectiveSelectedJigsawId > 0
        ? `?jigsaw_id=${effectiveSelectedJigsawId}&limit=500`
        : "?limit=500";
      const payload = await apiRequest(`/api/v1/diary-feed${query}`);
      state.diaryEntries = Array.isArray(payload.data) ? payload.data : [];

      state.pagination.diary = 1;
      renderDiaryEntries(state.diaryEntries, getDiaryEntriesEmptyMessage(effectiveSelectedJigsawId));
    } catch (error) {
      state.diaryEntries = [];
      state.pagination.diary = 1;
      renderDiaryEntries([], getDiaryEntriesEmptyMessage(effectiveSelectedJigsawId));
      showFeedback(error.message, true);
    }
  }

  function renderDiarySuggestionOptions(imageId, candidates) {
    if (!elements.diaryEntriesTableBody) {
      return false;
    }
    const wrap = elements.diaryEntriesTableBody.querySelector(`[data-diary-suggest-wrap="${Number(imageId)}"]`);
    if (!wrap) {
      return false;
    }

    while (wrap.firstChild) {
      wrap.removeChild(wrap.firstChild);
    }
    wrap.classList.add("app-diary-suggestions");

    if (!Array.isArray(candidates) || candidates.length === 0) {
      const note = document.createElement("span");
      note.textContent = "No candidates";
      wrap.appendChild(note);
      return true;
    }

    wrap.classList.add("app-diary-suggestions");

    candidates.forEach((candidate) => {
      const jigsawId = Number(candidate?.jigsaw_id || 0);
      if (!jigsawId) {
        return;
      }

      const scorePct = Math.max(0, Math.min(100, Math.round((Number(candidate?.score) || 0) * 1000) / 10));
      const confidence = String(candidate?.confidence || "low");

      const candidateRow = document.createElement("div");
      candidateRow.className = "app-diary-suggestion-row";

      const referenceImage = candidate?.reference_image || {};
      const thumb = buildThumbnailWidget(referenceImage.thumbnail_url || "", {
        altText: `Reference image for ${candidate?.jigsaw_title || `jigsaw ${jigsawId}`}`,
        previewUrl: referenceImage.preview_url || referenceImage.content_url || "",
        openUrl: referenceImage.content_url || "",
        fallbackText: "No ref",
        widthPx: 92,
      });
      thumb.classList.add("app-diary-suggestion-thumb");
      candidateRow.appendChild(thumb);

      const details = document.createElement("div");
      details.className = "app-diary-suggestion-details";

      const title = document.createElement("div");
      title.className = "app-diary-suggestion-title";
      title.textContent = candidate?.jigsaw_title || `(id ${jigsawId})`;
      details.appendChild(title);

      const meta = document.createElement("div");
      meta.className = "app-diary-suggestion-meta";
      meta.textContent = `${scorePct}% ${confidence} (${candidate?.reference_tag || "reference"})`;
      details.appendChild(meta);

      const assignButton = document.createElement("button");
      assignButton.type = "button";
      assignButton.className = "govuk-button govuk-button--secondary app-inline-button";
      assignButton.setAttribute("data-module", "govuk-button");
      assignButton.dataset.diarySuggestAssign = String(Number(imageId));
      assignButton.dataset.diarySuggestJigsawId = String(jigsawId);
      assignButton.textContent = "Assign";
      details.appendChild(assignButton);

      candidateRow.appendChild(details);
      wrap.appendChild(candidateRow);
    });

    return true;
  }

  async function handleDiarySuggestMatch(imageId) {
    const resolvedImageId = Number(imageId || 0);
    if (!resolvedImageId) {
      showFeedback("Could not determine which completed image to match.", true);
      return;
    }

    showFeedback(`Finding similar matches for image #${resolvedImageId}...`);

    try {
      const payload = await apiRequest(`/api/v1/image-library/images/${resolvedImageId}/match-suggestions?limit=3`);
      const candidates = Array.isArray(payload?.data?.candidates) ? payload.data.candidates : [];
      const rendered = renderDiarySuggestionOptions(resolvedImageId, candidates);
      if (!rendered) {
        showFeedback("Suggestions loaded, but the image row changed before results were shown. Please click Find similar again.", true);
        return;
      }
      if (candidates.length > 0) {
        showFeedback(`Loaded ${candidates.length} similar match candidate(s) for image #${resolvedImageId}.`);
      } else {
        showFeedback(`No suggested matches found for image #${resolvedImageId}.`);
      }
    } catch (error) {
      showFeedback(error.message, true);
    }
  }

  async function handleDiaryAssignSuggested(imageId, explicitJigsawId = null) {
    const resolvedImageId = Number(imageId || 0);
    if (!resolvedImageId) {
      return;
    }

    const selectedJigsawId = Number(explicitJigsawId || 0);
    if (!selectedJigsawId) {
      showFeedback("Choose a suggested jigsaw before assigning.", true);
      return;
    }

    try {
      await assignImageToJigsaw(resolvedImageId, selectedJigsawId);
      showFeedback(`Completed image #${resolvedImageId} assigned to jigsaw #${selectedJigsawId}.`);
      await Promise.all([loadDiaryEntriesForSelected(), loadImageLibraryImages(), loadJigsaws(), loadAuditEvents()]);
    } catch (error) {
      showFeedback(error.message, true);
    }
  }

  async function handleImageBrowserSuggestMatch() {
    const item = getCurrentImageBrowserItem();
    if (!item || !item.id) {
      showFeedback("Could not determine which image to match.", true);
      return;
    }
    if (!imageSupportsSimilarMatch(item)) {
      showFeedback("Find similar is only available for unassigned Completed images.", true);
      return;
    }

    const imageId = Number(item.id);
    closeImageBrowserNameAssignModal();
    showFeedback(`Finding similar matches for image #${imageId}...`);

    try {
      const payload = await apiRequest(`/api/v1/image-library/images/${imageId}/match-suggestions?limit=3`);
      const candidates = Array.isArray(payload?.data?.candidates) ? payload.data.candidates : [];
      renderImageBrowserSuggestionModal(imageId, candidates);
      if (candidates.length > 0) {
        showFeedback(`Loaded ${candidates.length} similar match candidate(s) for image #${imageId}.`);
      } else {
        showFeedback(`No suggested matches found for image #${imageId}.`);
      }
    } catch (error) {
      closeImageBrowserSuggestionModal();
      showFeedback(error.message, true);
    }
  }

  async function handleImageBrowserAssignSuggested(imageId, explicitJigsawId = null) {
    const resolvedImageId = Number(imageId || 0);
    if (!resolvedImageId) {
      return;
    }

    const selectedJigsawId = Number(explicitJigsawId || 0);
    if (!selectedJigsawId) {
      showFeedback("Choose a suggested jigsaw before assigning.", true);
      return;
    }

    try {
      await assignImageToJigsaw(resolvedImageId, selectedJigsawId);
      closeImageBrowserSuggestionModal();
      showFeedback(`Completed image #${resolvedImageId} assigned to jigsaw #${selectedJigsawId}.`);
      await Promise.all([loadDiaryEntriesForSelected(), loadImageLibraryImages(), loadJigsawImagesForSelected(), loadJigsaws(), loadAuditEvents()]);
      setImageBrowserIndexByImageId(resolvedImageId);
      await loadCurrentImageIntoBrowser();
    } catch (error) {
      showFeedback(error.message, true);
    }
  }

  async function assignImageToJigsaw(imageId, jigsawId) {
    await apiRequest(`/api/v1/image-library/images/${Number(imageId)}/assign`, {
      method: "PATCH",
      body: JSON.stringify({ jigsaw_id: Number(jigsawId) }),
    });
  }

  async function unassignImageFromJigsaw(imageId) {
    await apiRequest(`/api/v1/image-library/images/${Number(imageId)}/assign`, {
      method: "PATCH",
      body: JSON.stringify({ jigsaw_id: null }),
    });
  }

  function renderImageLibrarySuggestionOptions(imageId, candidates) {
    if (!elements.imageLibraryTableBody) {
      return false;
    }

    const wrap = elements.imageLibraryTableBody.querySelector(`[data-image-suggest-wrap="${Number(imageId)}"]`);
    if (!wrap) {
      return false;
    }

    while (wrap.firstChild) {
      wrap.removeChild(wrap.firstChild);
    }
    wrap.classList.add("app-diary-suggestions");

    if (!Array.isArray(candidates) || candidates.length === 0) {
      const note = document.createElement("span");
      note.textContent = "No candidates";
      wrap.appendChild(note);
      return true;
    }

    candidates.forEach((candidate) => {
      const jigsawId = Number(candidate?.jigsaw_id || 0);
      if (!jigsawId) {
        return;
      }

      const scorePct = Math.max(0, Math.min(100, Math.round((Number(candidate?.score) || 0) * 1000) / 10));
      const confidence = String(candidate?.confidence || "low");

      const row = document.createElement("div");
      row.className = "app-diary-suggestion-row";

      const referenceImage = candidate?.reference_image || {};
      const thumb = buildThumbnailWidget(referenceImage.thumbnail_url || "", {
        altText: `Reference image for ${candidate?.jigsaw_title || `jigsaw ${jigsawId}`}`,
        previewUrl: referenceImage.preview_url || referenceImage.content_url || "",
        openUrl: referenceImage.content_url || "",
        fallbackText: "No ref",
        widthPx: 92,
      });
      thumb.classList.add("app-diary-suggestion-thumb");
      row.appendChild(thumb);

      const details = document.createElement("div");
      details.className = "app-diary-suggestion-details";

      const title = document.createElement("div");
      title.className = "app-diary-suggestion-title";
      title.textContent = candidate?.jigsaw_title || `(id ${jigsawId})`;
      details.appendChild(title);

      const meta = document.createElement("div");
      meta.className = "app-diary-suggestion-meta";
      meta.textContent = `${scorePct}% ${confidence} (${candidate?.reference_tag || "reference"})`;
      details.appendChild(meta);

      const assignButton = document.createElement("button");
      assignButton.type = "button";
      assignButton.className = "govuk-button govuk-button--secondary app-inline-button";
      assignButton.setAttribute("data-module", "govuk-button");
      assignButton.dataset.imageSuggestAssign = String(Number(imageId));
      assignButton.dataset.imageSuggestJigsawId = String(jigsawId);
      assignButton.textContent = "Assign";
      details.appendChild(assignButton);

      row.appendChild(details);
      wrap.appendChild(row);
    });

    return true;
  }

  async function handleImageLibrarySuggestMatch(imageId) {
    const resolvedImageId = Number(imageId || 0);
    if (!resolvedImageId) {
      showFeedback("Could not determine which image to match.", true);
      return;
    }

    showFeedback(`Finding similar matches for image #${resolvedImageId}...`);

    try {
      const payload = await apiRequest(`/api/v1/image-library/images/${resolvedImageId}/match-suggestions?limit=3`);
      const candidates = Array.isArray(payload?.data?.candidates) ? payload.data.candidates : [];
      const rendered = renderImageLibrarySuggestionOptions(resolvedImageId, candidates);
      if (!rendered) {
        showFeedback("Suggestions loaded, but the image row changed before results were shown. Please click Find similar again.", true);
        return;
      }
      showFeedback(`Loaded ${candidates.length} similar match candidate(s) for image #${resolvedImageId}.`);
    } catch (error) {
      showFeedback(error.message, true);
    }
  }

  async function handleImageLibraryAssignSuggested(imageId, explicitJigsawId = null) {
    const resolvedImageId = Number(imageId || 0);
    if (!resolvedImageId) {
      return;
    }

    const selectedJigsawId = Number(explicitJigsawId || 0);
    if (!selectedJigsawId) {
      showFeedback("Choose a suggested jigsaw before assigning.", true);
      return;
    }

    try {
      await assignImageToJigsaw(resolvedImageId, selectedJigsawId);
      showFeedback(`Completed image #${resolvedImageId} assigned to jigsaw #${selectedJigsawId}.`);
      await Promise.all([loadDiaryEntriesForSelected(), loadImageLibraryImages(), loadJigsawImagesForSelected(), loadJigsaws(), loadAuditEvents()]);
    } catch (error) {
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
      state.auditEvents = [];
      state.auditEventsMeta = null;
      renderAuditEvents([]);
      return;
    }

    try {
      const payload = await apiRequest(
        `/api/v1/audit-events?page=${state.pagination.audit}&page_size=${ADMIN_LIST_PAGE_SIZE}`,
      );
      state.auditEvents = Array.isArray(payload.data) ? payload.data : [];
      state.auditEventsMeta = payload?.meta || null;
      renderAuditEvents(state.auditEvents);
    } catch (error) {
      if (error.status === 403) {
        state.auditEvents = [];
        state.auditEventsMeta = null;
        renderAuditEvents([]);
        return;
      }
      state.auditEvents = [];
      state.auditEventsMeta = null;
      renderAuditEvents([]);
      showFeedback(error.message, true);
    }
  }

  async function loadBlockedIps() {
    if (!state.user) {
      state.blockedIps = [];
      renderBlockedIps([]);
      return;
    }

    const isAdministrator = Array.isArray(state.user?.roles) && state.user.roles.includes("administrator");
    if (!isAdministrator) {
      state.blockedIps = [];
      renderBlockedIps([]);
      return;
    }

    try {
      const payload = await apiRequest("/api/v1/security/blocked-ips");
      state.blockedIps = Array.isArray(payload.data) ? payload.data : [];
      renderBlockedIps(state.blockedIps);
    } catch (error) {
      if (error.status === 403) {
        state.blockedIps = [];
        renderBlockedIps([]);
        return;
      }
      showFeedback(error.message, true);
    }
  }

  async function loadAiUsageDiagnostics() {
    if (!state.user) {
      state.aiUsageDiagnostics = null;
      renderAiUsageDiagnostics(null);
      return;
    }

    try {
      const payload = await apiRequest(
        `/api/v1/ai-usage/diagnostics?page=${state.pagination.aiRecent}&page_size=${ADMIN_LIST_PAGE_SIZE}`,
      );
      state.aiUsageDiagnostics = payload?.data || null;
      renderAiUsageDiagnostics(state.aiUsageDiagnostics);
    } catch (error) {
      if (error.status === 403) {
        state.aiUsageDiagnostics = null;
        renderAiUsageDiagnostics(null);
        return;
      }
      showFeedback(error.message, true);
    }
  }

  async function loadImageEmbeddingDiagnostics() {
    if (!state.user) {
      state.imageEmbeddingDiagnostics = null;
      renderImageEmbeddingDiagnostics(null);
      return;
    }

    try {
      const payload = await apiRequest("/api/v1/image-embeddings/diagnostics");
      state.imageEmbeddingDiagnostics = payload?.data || null;
      renderImageEmbeddingDiagnostics(state.imageEmbeddingDiagnostics);
    } catch (error) {
      if (error.status === 403) {
        state.imageEmbeddingDiagnostics = null;
        renderImageEmbeddingDiagnostics(null);
        return;
      }
      showFeedback(error.message, true);
    }
  }

  async function handleLoginSubmit(event) {
    event.preventDefault();
    clearFeedback();

    if (state.stfdAuthEnabled && !state.stfdAllowLocalLogin) {
      if (!state.stfdLoginUrl) {
        showFeedback("STFD sign-in is enabled but not configured correctly.", true);
        return;
      }
      window.location.assign(state.stfdLoginUrl);
      return;
    }

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
      state.authProvider = String(payload.data.auth_provider || "local").toLowerCase();
      closeAuthDialog();
      setSessionSummary();
      showFeedback("Signed in successfully.");
      await Promise.all([
        loadRoles(),
        loadUsers(),
        loadJigsaws(),
        loadLoans(),
        loadAuditEvents(),
        loadBlockedIps(),
        loadAiUsageDiagnostics(),
        loadImageEmbeddingDiagnostics(),
        loadImageLibraryImages(),
      ]);
      await Promise.all([loadJigsawImagesForSelected(), loadDiaryEntriesForSelected()]);
    } catch (error) {
      showFeedback(error.message, true);
    }
  }

  function handleStfdLoginClick() {
    clearFeedback();
    if (!state.stfdAuthEnabled) {
      return;
    }
    if (!state.stfdLoginUrl) {
      showFeedback("STFD sign-in is enabled but not configured correctly.", true);
      return;
    }
    window.location.assign(state.stfdLoginUrl);
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
      state.authProvider = null;
      closeAuthDialog();
      setSessionSummary();
      state.users = [];
      state.roleDefinitions = [];
      state.jigsaws = [];
      state.loans = [];
      state.blockedIps = [];
      state.auditEvents = [];
      state.auditEventsMeta = null;
      state.jigsawThumbnailImages = [];
      state.jigsawImages = [];
      state.imageLibraryImages = [];
      state.imageLibraryFilterAssigned = true;
      state.imageLibraryFilterUnassigned = true;
      state.imageLibraryFilterTagSelections = {};
      state.aiUsageDiagnostics = null;
      state.imageEmbeddingDiagnostics = null;
      state.imageBrowserContentCacheByImageId = {};
      state.imageBrowserSavingImageIds = {};
      state.tableSorts = createDefaultTableSortState();
      state.diaryEntries = [];
      state.jigsawSearchQuery = "";
      state.jigsawFilterWithoutDiaryEntries = false;
      state.pagination = {
        jigsaws: 1,
        imageLibrary: 1,
        diary: 1,
        aiRecent: 1,
        audit: 1,
      };
      renderUsers([]);
      renderUserRoleSelectors();
      closeUserEditor();
      renderJigsaws([]);
      closeJigsawEditor();
      renderLoans([]);
      renderBlockedIps([]);
      renderJigsawImages([]);
      renderImageLibraryImages([]);
      renderDiaryEntries([]);
      renderAiUsageDiagnostics(null);
      renderImageEmbeddingDiagnostics(null);
      closeAiUsageDetailModal();
      clearBulkUploadFiles();
      clearBulkCreateProgress();
      closeImageBrowser();
      if (elements.jigsawSearchInput) {
        elements.jigsawSearchInput.value = "";
      }
      if (elements.jigsawFilterNoDiary) {
        elements.jigsawFilterNoDiary.checked = false;
      }
      if (elements.imageLibraryFilterAssigned) {
        elements.imageLibraryFilterAssigned.checked = true;
      }
      if (elements.imageLibraryFilterUnassigned) {
        elements.imageLibraryFilterUnassigned.checked = true;
      }
      populateLoanFormOptions();
      populateJigsawImageOptions();
      populateDiaryJigsawOptions();
      populateImageLibraryJigsawOptions();
      renderAuditEvents([]);
      updateSortableTableHeaders();
      await Promise.all([loadJigsaws(), loadJigsawThumbnailImages()]);
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
      renderRoleCheckboxes(elements.userRolesCheckboxes, {
        selectedRoleNames: getDefaultCreateRoleNames(),
        idPrefix: "user-role",
      });
      showFeedback("User created.");
      await Promise.all([loadUsers(), loadAuditEvents()]);
    } catch (error) {
      showFeedback(error.message, true);
    }
  }

  function openUserEditor(userId, { scrollToForm = true } = {}) {
    const selectedUser = state.users.find((entry) => Number(entry.id) === Number(userId));
    if (!selectedUser || !elements.userEditForm) {
      return;
    }

    if (scrollToForm) {
      rememberEditorScrollPosition("user");
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
    const roles = Array.isArray(selectedUser.roles) ? selectedUser.roles : [];
    renderRoleCheckboxes(elements.editUserRolesCheckboxes, {
      selectedRoleNames: roles,
      idPrefix: "edit-user-role",
    });
    if (elements.editUserActive) {
      elements.editUserActive.checked = Boolean(selectedUser.is_active);
    }
    if (elements.editUserPassword) {
      elements.editUserPassword.value = "";
    }
    if (scrollToForm) {
      scrollToEditor(elements.userEditForm);
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
      openUserEditor(userId, { scrollToForm: false });
      restoreEditorScrollPosition("user");
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
    restoreEditorScrollPosition("user");
  }

  async function handleAccountUpdate(event) {
    event.preventDefault();
    clearFeedback();

    if (!state.user) {
      showFeedback("You must be signed in to update your account.", true);
      return;
    }

    if (String(state.authProvider || "").toLowerCase() === "stfd") {
      showFeedback("Account profile updates are managed by STFD for this session.", true);
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
      state.authProvider = String(response.data.auth_provider || state.authProvider || "local").toLowerCase();
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

    if (!currentUserHasCapability("jigsaw.create")) {
      showFeedback("You do not have permission to create jigsaws.", true);
      return;
    }

    const form = event.currentTarget;
    const formData = new FormData(form);
    const payload = {
      title: String(formData.get("title") || "").trim(),
      series_name: String(formData.get("series_name") || "").trim() || null,
      series_number: String(formData.get("series_number") || "").trim() || null,
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

    if (!currentUserHasCapability("diary.create")) {
      showFeedback("You do not have permission to create diary entries.", true);
      return;
    }

    const form = event.currentTarget;
    const formData = new FormData(form);
    const editingEntryId = Number(state.diaryEditingEntryId || "0");
    const jigsawId = Number(formData.get("jigsaw_id") || "0");

    if (!editingEntryId && !jigsawId) {
      showFeedback("Select a jigsaw before adding a diary entry.", true);
      return;
    }

    const payload = {
      completed_at: normalizeDatetimeLocal(formData.get("completed_at")),
      difficulty: parseOptionalIntegerFormValue(formData.get("difficulty")),
      notes: String(formData.get("notes") || "").trim() || null,
    };

    if (editingEntryId && !payload.completed_at) {
      showFeedback("Completed at is required when editing a diary entry.", true);
      return;
    }

    try {
      if (editingEntryId) {
        await apiRequest(`/api/v1/diary-entries/${editingEntryId}`, {
          method: "PATCH",
          body: JSON.stringify(payload),
        });
        showFeedback("Diary entry updated.");
        resetDiaryEntryFormEditingState({ keepJigsawSelection: true });
        restoreEditorScrollPosition("diary");
      } else {
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
      }
      await Promise.all([loadDiaryEntriesForSelected(), loadJigsaws(), loadAuditEvents()]);
    } catch (error) {
      showFeedback(error.message, true);
    }
  }

  async function handleCreateJigsawImage(event) {
    event.preventDefault();
    clearFeedback();

    if (!currentUserHasCapability("image.upload")) {
      showFeedback("You do not have permission to upload images.", true);
      return;
    }

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

  function shouldShowBulkCreateFromUploadOption() {
    const selectedJigsawId = String(elements.imageLibraryJigsawId?.value || "").trim();
    const selectedTag = normalizeImageTagLabel(elements.imageLibraryTag?.value || "");
    return !selectedJigsawId && toImageTagKey(selectedTag) === toImageTagKey(IMAGE_BROWSER_TAG_BOX);
  }

  function syncBulkCreateFromUploadVisibility() {
    const shouldShow = currentUserHasCapability("ai.manage") && shouldShowBulkCreateFromUploadOption();
    if (elements.imageLibraryBulkCreateWrap) {
      elements.imageLibraryBulkCreateWrap.hidden = !shouldShow;
    }
    if (!shouldShow && elements.imageLibraryBulkCreate) {
      elements.imageLibraryBulkCreate.checked = false;
    }
  }

  function setBulkCreateProgressText(message, isVisible = true) {
    if (elements.imageLibraryBulkCreateProgressText) {
      elements.imageLibraryBulkCreateProgressText.textContent = String(message || "");
    }
    if (elements.imageLibraryBulkCreateProgress) {
      elements.imageLibraryBulkCreateProgress.hidden = !isVisible;
    }
  }

  function clearBulkCreateProgress() {
    if (state.bulkCreateJobPollTimer) {
      window.clearTimeout(state.bulkCreateJobPollTimer);
      state.bulkCreateJobPollTimer = null;
    }
    state.bulkCreateJobId = null;
    setBulkCreateProgressText("", false);
  }

  async function pollBulkCreateJobStatus(jobId) {
    if (!jobId) {
      return;
    }

    try {
      const payload = await apiRequest(`/api/v1/image-library/bulk-create-jigsaws/${Number(jobId)}`);
      const job = payload?.data?.job || null;
      if (!job) {
        clearBulkCreateProgress();
        return;
      }

      const summary = `Bulk AI create job #${job.id}: ${job.processed_items}/${job.total_items} processed, ${job.succeeded_items} succeeded, ${job.failed_items} failed.`;

      if (job.status === "queued" || job.status === "running") {
        setBulkCreateProgressText(`${summary} (${job.status})`);
        state.bulkCreateJobPollTimer = window.setTimeout(() => {
          pollBulkCreateJobStatus(job.id);
        }, 1500);
        return;
      }

      setBulkCreateProgressText(`${summary} (${job.status})`, true);
      if (job.status === "completed") {
        showFeedback(`Bulk AI create completed. ${summary}`);
      } else if (job.status === "failed") {
        showFeedback(`Bulk AI create finished with failures. ${summary}`, true);
      }

      await Promise.all([
        loadImageLibraryImages(),
        loadJigsaws(),
        loadJigsawImagesForSelected(),
        loadDiaryEntriesForSelected(),
        loadAuditEvents(),
        loadAiUsageDiagnostics(),
      ]);
      state.bulkCreateJobPollTimer = window.setTimeout(() => {
        clearBulkCreateProgress();
      }, 4000);
    } catch (error) {
      setBulkCreateProgressText(`Bulk AI create status check failed: ${error.message}`, true);
      state.bulkCreateJobPollTimer = window.setTimeout(() => {
        pollBulkCreateJobStatus(jobId);
      }, 2500);
    }
  }

  async function startBulkCreateJobForUploadedImages(uploadPayloadData) {
    const createdItems = Array.isArray(uploadPayloadData?.created) ? uploadPayloadData.created : [];
    const unassignedImageIds = createdItems
      .map((item) => Number(item?.id || 0))
      .filter((imageId, index, values) => imageId > 0 && values.indexOf(imageId) === index);
    return startBulkCreateJobForImageIds(unassignedImageIds);
  }

  async function startBulkCreateJobForImageIds(imageIds) {
    const uniqueImageIds = Array.isArray(imageIds)
      ? imageIds.filter((imageId, index, values) => Number(imageId) > 0 && values.indexOf(imageId) === index)
      : [];

    if (uniqueImageIds.length === 0) {
      return null;
    }

    clearBulkCreateProgress();

    const response = await apiRequest("/api/v1/image-library/bulk-create-jigsaws", {
      method: "POST",
      body: JSON.stringify({ image_ids: uniqueImageIds }),
    });

    const job = response?.data?.job || null;
    if (!job || !job.id) {
      return null;
    }

    state.bulkCreateJobId = Number(job.id);
    setBulkCreateProgressText(`Bulk AI create job #${job.id} queued for ${uniqueImageIds.length} image(s).`);
    pollBulkCreateJobStatus(state.bulkCreateJobId);
    return state.bulkCreateJobId;
  }

  function setImageEmbeddingBackfillStatus(message) {
    if (!elements.imageEmbeddingBackfillStatus) {
      return;
    }
    elements.imageEmbeddingBackfillStatus.textContent = String(message || "");
  }

  function clearImageEmbeddingBackfillProgress() {
    if (state.imageEmbeddingBackfillPollTimer) {
      window.clearTimeout(state.imageEmbeddingBackfillPollTimer);
      state.imageEmbeddingBackfillPollTimer = null;
    }
    state.imageEmbeddingBackfillJobId = null;
  }

  async function pollImageEmbeddingBackfillJobStatus(jobId) {
    if (!jobId) {
      return;
    }

    try {
      const payload = await apiRequest(`/api/v1/image-embeddings/backfill/${Number(jobId)}`);
      const job = payload?.data?.job || null;
      if (!job) {
        clearImageEmbeddingBackfillProgress();
        setImageEmbeddingBackfillStatus("Embedding backfill status unavailable.");
        return;
      }

      const scopeLabel = String(job.scope || "all") === "missing" ? "missing-only" : "all";
      const summary = `Embedding job #${job.id} (${scopeLabel}): ${job.processed_items}/${job.total_items} processed, ${job.succeeded_items} succeeded, ${job.failed_items} failed.`;
      if (job.status === "queued" || job.status === "running") {
        setImageEmbeddingBackfillStatus(`${summary} (${job.status})`);
        state.imageEmbeddingBackfillPollTimer = window.setTimeout(() => {
          pollImageEmbeddingBackfillJobStatus(job.id);
        }, 1500);
        return;
      }

      setImageEmbeddingBackfillStatus(`${summary} (${job.status})`);
      if (job.status === "completed") {
        showFeedback(`Image embedding backfill completed. ${summary}`);
      } else if (job.status === "failed") {
        showFeedback(`Image embedding backfill finished with failures. ${summary}`, true);
      }

      await Promise.all([loadImageLibraryImages(), loadDiaryEntriesForSelected(), loadAuditEvents(), loadImageEmbeddingDiagnostics()]);
      state.imageEmbeddingBackfillPollTimer = window.setTimeout(() => {
        clearImageEmbeddingBackfillProgress();
      }, 4000);
    } catch (error) {
      setImageEmbeddingBackfillStatus(`Embedding backfill status check failed: ${error.message}`);
      state.imageEmbeddingBackfillPollTimer = window.setTimeout(() => {
        pollImageEmbeddingBackfillJobStatus(jobId);
      }, 2500);
    }
  }

  async function handleImageEmbeddingBackfillStart(event) {
    clearFeedback();
    clearImageEmbeddingBackfillProgress();

    const requestedScope = String(event?.currentTarget?.dataset?.embeddingBackfillScope || "all").trim().toLowerCase();
    const scope = requestedScope === "missing" ? "missing" : "all";

    try {
      const payload = await apiRequest("/api/v1/image-embeddings/backfill", {
        method: "POST",
        body: JSON.stringify({ scope }),
      });
      const job = payload?.data?.job || null;
      if (!job?.id) {
        showFeedback("Could not queue image embedding backfill job.", true);
        return;
      }

      state.imageEmbeddingBackfillJobId = Number(job.id);
      const scopeLabel = scope === "missing" ? "missing-only" : "all";
      setImageEmbeddingBackfillStatus(`Embedding backfill job #${job.id} queued (${scopeLabel}).`);
      pollImageEmbeddingBackfillJobStatus(state.imageEmbeddingBackfillJobId);
    } catch (error) {
      showFeedback(error.message, true);
    }
  }

  async function handleImageLibraryUpload(event) {
    event.preventDefault();
    clearFeedback();

    if (!currentUserHasCapability("image.upload")) {
      showFeedback("You do not have permission to upload image library items.", true);
      return;
    }

    if (!Array.isArray(state.bulkUploadFiles) || state.bulkUploadFiles.length === 0) {
      showFeedback("Choose one or more files before uploading to the image library.", true);
      return;
    }

    const formData = new FormData();
    const jigsawIdValue = String(elements.imageLibraryJigsawId?.value || "").trim();
    const tagValue = String(elements.imageLibraryTag?.value || "").trim();
    const shouldCreateJigsaws = Boolean(
      elements.imageLibraryBulkCreate?.checked && shouldShowBulkCreateFromUploadOption(),
    );
    if (jigsawIdValue) {
      formData.append("jigsaw_id", jigsawIdValue);
    }
    if (tagValue) {
      formData.append("tag", tagValue);
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
      const metadataBackfilledCount = Number(payload?.data?.metadata_backfilled_count || 0);
      const skippedItems = Array.isArray(payload?.data?.skipped) ? payload.data.skipped : [];
      let bulkCreateSummary = "";
      let skippedReasonSuffix = "";

      let metadataSuffix = "";
      if (metadataBackfilledCount > 0) {
        const backfilledNames = skippedItems
          .filter((item) => Boolean(item?.metadata_backfilled))
          .map((item) => String(item?.filename || "(unnamed)"));
        const previewNames = backfilledNames.slice(0, 4).join(", ");
        const overflow = Math.max(0, backfilledNames.length - 4);
        const namesSuffix = previewNames
          ? ` (${previewNames}${overflow > 0 ? ` +${overflow} more` : ""})`
          : "";
        metadataSuffix = ` Backfilled metadata on ${metadataBackfilledCount} existing image(s)${namesSuffix}.`;
      }

      if (skippedCount > 0 && skippedItems.length > 0) {
        const reasonPreview = skippedItems
          .slice(0, 3)
          .map((item) => {
            const filename = String(item?.filename || "(unnamed)");
            let reason = String(item?.reason || item?.issue || "Skipped").trim();
            const assignedMatch = reason.match(/attached to jigsaw #(\d+)\.?$/i);
            if (assignedMatch) {
              const assignedJigsawId = Number(assignedMatch[1]);
              const assignedJigsaw = (Array.isArray(state.jigsaws) ? state.jigsaws : []).find(
                (jigsaw) => Number(jigsaw?.id) === assignedJigsawId,
              );
              const assignedTitle = String(assignedJigsaw?.title || "").trim();
              if (assignedTitle) {
                reason = `Image already exists, attached to jigsaw "${assignedTitle}".`;
              }
            }

            if (reason && !/[.!?]$/.test(reason)) {
              reason = `${reason}.`;
            }

            return `${filename}: ${reason}`;
          })
          .join("; ");
        const overflow = Math.max(0, skippedItems.length - 3);
        skippedReasonSuffix = ` Reasons: ${reasonPreview}${overflow > 0 ? `; +${overflow} more` : ""}`;
      }

      showFeedback(`Image library upload complete. Added ${createdCount} image(s), skipped ${skippedCount}.${skippedReasonSuffix}${metadataSuffix}${bulkCreateSummary}`);
      clearBulkUploadFiles();
      if (elements.imageLibraryBulkCreate) {
        elements.imageLibraryBulkCreate.checked = false;
      }

      if (shouldCreateJigsaws) {
        clearBulkCreateProgress();
        await Promise.all([loadImageLibraryImages(), loadAuditEvents()]);
        const jobId = await startBulkCreateJobForUploadedImages(payload?.data);
        if (!jobId) {
          showFeedback("Bulk AI create could not be started because no valid uploaded image ids were available.", true);
        }
      } else {
        clearBulkCreateProgress();
        await Promise.all([loadImageLibraryImages(), loadJigsaws(), loadAuditEvents()]);
      }
    } catch (error) {
      showFeedback(error.message, true);
    }
  }

  async function handleBulkCreateAllUnassignedBoxImages() {
    clearFeedback();
    clearBulkCreateProgress();

    if (!currentUserHasCapability("ai.manage")) {
      showFeedback("You do not have permission to run bulk AI create.", true);
      return;
    }

    const shouldStart = window.confirm(
      "Queue AI create for all unassigned images tagged exactly as Box?",
    );
    if (!shouldStart) {
      return;
    }

    try {
      const response = await apiRequest("/api/v1/image-library/bulk-create-jigsaws/unassigned-box", {
        method: "POST",
        body: JSON.stringify({}),
      });

      const job = response?.data?.job || null;
      if (!job || !job.id) {
        showFeedback("Could not queue bulk AI create for unassigned Box images.", true);
        return;
      }

      state.bulkCreateJobId = Number(job.id);
      setBulkCreateProgressText(`Bulk AI create job #${job.id} queued for ${job.total_items} image(s).`);
      pollBulkCreateJobStatus(state.bulkCreateJobId);
      showFeedback(`Queued bulk AI create job #${job.id} for ${job.total_items} unassigned Box image(s).`);
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

  async function handleCreateBlockedIp(event) {
    event.preventDefault();
    clearFeedback();

    const formData = new FormData(event.currentTarget);
    const ipAddress = String(formData.get("ip_address") || "").trim();
    const durationHours = Number(formData.get("duration_hours") || "0");
    const reason = String(formData.get("reason") || "").trim();

    if (!ipAddress) {
      showFeedback("IP address is required.", true);
      return;
    }
    if (!Number.isFinite(durationHours) || durationHours < 1 || durationHours > 720) {
      showFeedback("Duration must be between 1 and 720 hours.", true);
      return;
    }

    try {
      await apiRequest("/api/v1/security/blocked-ips", {
        method: "POST",
        body: JSON.stringify({
          ip_address: ipAddress,
          duration_hours: Math.trunc(durationHours),
          reason: reason || null,
        }),
      });
      showFeedback(`Blocked ${ipAddress}.`);
      event.currentTarget.reset();
      if (elements.ipBlockHours) {
        elements.ipBlockHours.value = "24";
      }
      await Promise.all([loadBlockedIps(), loadAuditEvents()]);
    } catch (error) {
      showFeedback(error.message, true);
    }
  }

  function openJigsawEditor(jigsawId, { scrollToForm = true } = {}) {
    const selectedJigsaw = state.jigsaws.find((entry) => Number(entry.id) === Number(jigsawId));
    if (!selectedJigsaw || !elements.jigsawEditForm) {
      return;
    }

    if (scrollToForm) {
      rememberEditorScrollPosition("jigsaw");
    }
    elements.jigsawEditForm.hidden = false;
    if (elements.editJigsawId) {
      elements.editJigsawId.value = String(selectedJigsaw.id);
    }
    if (elements.editJigsawTitle) {
      elements.editJigsawTitle.value = selectedJigsaw.title || "";
    }
    if (elements.editJigsawSeriesName) {
      elements.editJigsawSeriesName.value = selectedJigsaw.series_name || "";
    }
    if (elements.editJigsawSeriesNumber) {
      elements.editJigsawSeriesNumber.value = selectedJigsaw.series_number || "";
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
    if (scrollToForm) {
      scrollToEditor(elements.jigsawEditForm);
    }
  }

  async function handleEditJigsaw(event) {
    event.preventDefault();
    clearFeedback();

    if (!currentUserHasCapability("jigsaw.update")) {
      showFeedback("You do not have permission to edit jigsaws.", true);
      return;
    }

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
      series_name: String(formData.get("series_name") || "").trim() || null,
      series_number: String(formData.get("series_number") || "").trim() || null,
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
      openJigsawEditor(jigsawId, { scrollToForm: false });
      restoreEditorScrollPosition("jigsaw");
    } catch (error) {
      showFeedback(error.message, true);
    } finally {
      if (elements.jigsawEditSaveButton) {
        elements.jigsawEditSaveButton.disabled = false;
      }
    }
  }

  async function enrichJigsawById(jigsawId) {
    if (!jigsawId) {
      return;
    }

    try {
      const response = await apiRequest(`/api/v1/jigsaws/${jigsawId}/enrich-from-images`, {
        method: "POST",
        body: JSON.stringify({ overwrite_existing: false }),
      });
      const appliedFields = Array.isArray(response?.data?.applied_fields) ? response.data.applied_fields : [];
      if (appliedFields.length > 0) {
        showFeedback(`Jigsaw enriched. Updated fields: ${appliedFields.join(", ")}.`);
      } else {
        showFeedback("Jigsaw enrichment completed. No empty fields could be updated.");
      }
      await Promise.all([loadJigsaws(), loadJigsawImagesForSelected(), loadAuditEvents(), loadAiUsageDiagnostics()]);
      openJigsawEditor(jigsawId);
    } catch (error) {
      showFeedback(error.message, true);
    }
  }

  async function handleEnrichJigsaw() {
    clearFeedback();

    if (!currentUserHasCapability("jigsaw.enrich")) {
      showFeedback("You do not have permission to enrich jigsaws.", true);
      return;
    }

    const jigsawId = Number(elements.editJigsawId?.value || "0");
    if (!jigsawId) {
      showFeedback("Open a jigsaw in the editor before running enrichment.", true);
      return;
    }

    if (elements.jigsawEditEnrichButton) {
      elements.jigsawEditEnrichButton.disabled = true;
    }
    try {
      await enrichJigsawById(jigsawId);
    } finally {
      if (elements.jigsawEditEnrichButton) {
        elements.jigsawEditEnrichButton.disabled = false;
      }
    }
  }

  function handleCancelJigsawEdit() {
    clearFeedback();
    closeJigsawEditor();
    restoreEditorScrollPosition("jigsaw");
  }

  async function handleTableActions(event) {
    const aiUsageDetailButton = event.target.closest("[data-ai-usage-detail]");
    if (aiUsageDetailButton) {
      event.preventDefault();
      const eventId = String(aiUsageDetailButton.getAttribute("data-ai-usage-detail") || "");
      const entry = state.aiUsageRecentById[eventId];
      if (entry) {
        openAiUsageDetailModal(entry);
      }
      return;
    }

    const editJigsawButton = event.target.closest("[data-jigsaw-edit]");
    const toggleJigsawImagesButton = event.target.closest("[data-jigsaw-images-toggle]");
    if (toggleJigsawImagesButton) {
      event.preventDefault();
      const jigsawId = Number(toggleJigsawImagesButton.getAttribute("data-jigsaw-images-toggle"));
      toggleJigsawInventoryImagesRow(jigsawId);
      return;
    }

    const detachJigsawImageButton = event.target.closest("[data-jigsaw-image-detach]");
    if (detachJigsawImageButton) {
      event.preventDefault();
      clearFeedback();

      if (!currentUserHasCapability("image.assign")) {
        showFeedback("You do not have permission to detach images.", true);
        return;
      }

      const imageId = Number(detachJigsawImageButton.getAttribute("data-jigsaw-image-detach"));
      if (!imageId) {
        showFeedback("Could not determine image to detach.", true);
        return;
      }

      try {
        await unassignImageFromJigsaw(imageId);
        showFeedback("Image detached from jigsaw.");
        await Promise.all([loadImageLibraryImages(), loadJigsawImagesForSelected(), loadAuditEvents()]);
      } catch (error) {
        showFeedback(error.message, true);
      }
      return;
    }

    if (editJigsawButton) {
      event.preventDefault();
      clearFeedback();

      if (!currentUserHasCapability("jigsaw.update")) {
        showFeedback("You do not have permission to edit jigsaws.", true);
        return;
      }

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

    const loanReturnButton = event.target.closest("[data-loan-return]");
    if (loanReturnButton) {
      event.preventDefault();
      clearFeedback();

      const loanId = Number(loanReturnButton.getAttribute("data-loan-return"));
      try {
        await apiRequest(`/api/v1/loans/${loanId}/return`, { method: "POST" });
        showFeedback("Loan returned.");
        await Promise.all([loadJigsaws(), loadLoans(), loadAuditEvents()]);
      } catch (error) {
        showFeedback(error.message, true);
      }
      return;
    }

    const blockedIpRemoveButton = event.target.closest("[data-ip-block-remove]");
    if (blockedIpRemoveButton) {
      event.preventDefault();
      clearFeedback();

      const blockedIpId = Number(blockedIpRemoveButton.getAttribute("data-ip-block-remove") || "0");
      if (!blockedIpId) {
        showFeedback("Invalid blocked IP selection.", true);
        return;
      }

      try {
        await apiRequest(`/api/v1/security/blocked-ips/${blockedIpId}`, { method: "DELETE" });
        showFeedback("IP block removed.");
        await Promise.all([loadBlockedIps(), loadAuditEvents()]);
      } catch (error) {
        showFeedback(error.message, true);
      }
      return;
    }

    const retireButton = event.target.closest("[data-jigsaw-retire]");
    if (retireButton) {
      event.preventDefault();
      clearFeedback();

      if (!Array.isArray(state.user?.roles) || !state.user.roles.includes("administrator")) {
        showFeedback("You do not have permission to retire jigsaws.", true);
        return;
      }

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

    const enrichButton = event.target.closest("[data-jigsaw-enrich]");
    if (enrichButton) {
      event.preventDefault();
      clearFeedback();

      if (!currentUserHasCapability("jigsaw.enrich")) {
        showFeedback("You do not have permission to enrich jigsaws.", true);
        return;
      }

      const jigsawId = Number(enrichButton.getAttribute("data-jigsaw-enrich"));
      await enrichJigsawById(jigsawId);
      return;
    }

    const deleteButton = event.target.closest("[data-jigsaw-delete]");
    if (deleteButton) {
      event.preventDefault();
      clearFeedback();

      if (!Array.isArray(state.user?.roles) || !state.user.roles.includes("administrator")) {
        showFeedback("You do not have permission to delete jigsaws.", true);
        return;
      }

      const jigsawId = Number(deleteButton.getAttribute("data-jigsaw-delete"));
      const shouldDelete = window.confirm(
        "Permanently delete this jigsaw and all of its images, diary entries, and loans? This cannot be undone.",
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

    const diaryEditButton = event.target.closest("[data-diary-edit]");
    if (diaryEditButton) {
      event.preventDefault();
      clearFeedback();

      if (!currentUserHasCapability("diary.update_any") && !currentUserHasCapability("diary.update_own")) {
        showFeedback("You do not have permission to edit diary entries.", true);
        return;
      }

      const entryId = Number(diaryEditButton.getAttribute("data-diary-edit"));
      beginDiaryEntryEdit(entryId);
      return;
    }

    const diaryDeleteButton = event.target.closest("[data-diary-delete]");
    if (diaryDeleteButton) {
      event.preventDefault();
      clearFeedback();

      if (!currentUserHasCapability("diary.delete_any")) {
        showFeedback("You do not have permission to delete diary entries.", true);
        return;
      }

      const entryId = Number(diaryDeleteButton.getAttribute("data-diary-delete"));
      const shouldDelete = window.confirm("Delete this diary entry? This cannot be undone.");
      if (!shouldDelete) {
        return;
      }

      try {
        await apiRequest(`/api/v1/diary-entries/${entryId}`, { method: "DELETE" });
        if (state.diaryEditingEntryId === entryId) {
          resetDiaryEntryFormEditingState({ keepJigsawSelection: true });
        }
        showFeedback("Diary entry deleted.");
        await Promise.all([loadDiaryEntriesForSelected(), loadJigsaws(), loadAuditEvents()]);
      } catch (error) {
        showFeedback(error.message, true);
      }
      return;
    }

    const diarySuggestButton = event.target.closest("[data-diary-suggest-image]");
    if (diarySuggestButton) {
      event.preventDefault();
      clearFeedback();

      const imageId = Number(diarySuggestButton.getAttribute("data-diary-suggest-image"));
      await handleDiarySuggestMatch(imageId);
      return;
    }

    const diarySuggestAssignButton = event.target.closest("[data-diary-suggest-assign]");
    if (diarySuggestAssignButton) {
      event.preventDefault();
      clearFeedback();

      const imageId = Number(diarySuggestAssignButton.getAttribute("data-diary-suggest-assign"));
      const jigsawId = Number(diarySuggestAssignButton.getAttribute("data-diary-suggest-jigsaw-id") || "0");
      await handleDiaryAssignSuggested(imageId, jigsawId);
      return;
    }

    const diaryDeleteImageButton = event.target.closest("[data-diary-delete-image]");
    if (diaryDeleteImageButton) {
      event.preventDefault();
      clearFeedback();

      if (!canCurrentUserDeleteImage({ jigsaw_id: null })) {
        showFeedback("You do not have permission to delete images.", true);
        return;
      }

      const imageId = Number(diaryDeleteImageButton.getAttribute("data-diary-delete-image"));
      const shouldDelete = window.confirm("Delete this unlinked completion image? This cannot be undone.");
      if (!shouldDelete) {
        return;
      }

      try {
        await apiRequest(`/api/v1/image-library/images/${imageId}`, { method: "DELETE" });
        showFeedback("Unlinked completion image deleted.");
        await Promise.all([loadDiaryEntriesForSelected(), loadImageLibraryImages(), loadAuditEvents()]);
      } catch (error) {
        showFeedback(error.message, true);
      }
      return;
    }

    const imageSuggestButton = event.target.closest("[data-image-suggest]");
    if (imageSuggestButton) {
      event.preventDefault();
      clearFeedback();

      if (!currentUserHasCapability("image.assign")) {
        showFeedback("You do not have permission to access image suggestions.", true);
        return;
      }

      const imageId = Number(imageSuggestButton.getAttribute("data-image-suggest"));
      await handleImageLibrarySuggestMatch(imageId);
      return;
    }

    const imageSuggestAssignButton = event.target.closest("[data-image-suggest-assign]");
    if (imageSuggestAssignButton) {
      event.preventDefault();
      clearFeedback();

      if (!currentUserHasCapability("image.assign")) {
        showFeedback("You do not have permission to assign images.", true);
        return;
      }

      const imageId = Number(imageSuggestAssignButton.getAttribute("data-image-suggest-assign"));
      const jigsawId = Number(imageSuggestAssignButton.getAttribute("data-image-suggest-jigsaw-id") || "0");
      await handleImageLibraryAssignSuggested(imageId, jigsawId);
      return;
    }

    const imageBrowserSuggestAssignButton = event.target.closest("[data-image-browser-suggest-assign]");
    if (imageBrowserSuggestAssignButton) {
      event.preventDefault();
      clearFeedback();

      if (!currentUserHasCapability("image.assign")) {
        showFeedback("You do not have permission to assign images.", true);
        return;
      }

      const imageId = Number(imageBrowserSuggestAssignButton.getAttribute("data-image-browser-suggest-assign"));
      const jigsawId = Number(imageBrowserSuggestAssignButton.getAttribute("data-image-browser-suggest-jigsaw-id") || "0");
      await handleImageBrowserAssignSuggested(imageId, jigsawId);
      return;
    }

    const imageAssignButton = event.target.closest("[data-image-assign]");
    if (imageAssignButton) {
      event.preventDefault();
      clearFeedback();

      if (!currentUserHasCapability("image.assign")) {
        showFeedback("You do not have permission to assign images.", true);
        return;
      }

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

    const imageTagButton = event.target.closest("[data-image-tag-set]");
    if (imageTagButton) {
      event.preventDefault();
      clearFeedback();

      if (!currentUserHasCapability("image.tag")) {
        showFeedback("You do not have permission to tag images.", true);
        return;
      }

      const imageId = Number(imageTagButton.getAttribute("data-image-tag-set"));
      const select = elements.imageLibraryTableBody?.querySelector(
        `[data-image-tag-select="${imageId}"]`,
      );
      const selectedTag = String(select?.value || "").trim();

      if (!selectedTag) {
        showFeedback("Choose a tag before saving.", true);
        return;
      }

      try {
        await apiRequest(`/api/v1/image-library/images/${imageId}/tag`, {
          method: "PATCH",
          body: JSON.stringify({ tag: selectedTag }),
        });
        showFeedback(`Image tagged as ${selectedTag}.`);
        const shouldRefreshDiary = toImageTagKey(selectedTag) === toImageTagKey(IMAGE_BROWSER_TAG_COMPLETED);
        const refreshTasks = [loadImageLibraryImages(), loadJigsawImagesForSelected(), loadAuditEvents()];
        if (shouldRefreshDiary) {
          refreshTasks.push(loadDiaryEntriesForSelected());
        }
        await Promise.all(refreshTasks);
      } catch (error) {
        showFeedback(error.message, true);
      }
      return;
    }

    const imageUnassignButton = event.target.closest("[data-image-unassign]");
    if (imageUnassignButton) {
      event.preventDefault();
      clearFeedback();

      if (!currentUserHasCapability("image.assign")) {
        showFeedback("You do not have permission to unassign images.", true);
        return;
      }

      const imageId = Number(imageUnassignButton.getAttribute("data-image-unassign"));
      try {
        await unassignImageFromJigsaw(imageId);
        showFeedback("Image unassigned from jigsaw.");
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

      if (!currentUserHasCapability("ai.manage")) {
        showFeedback("You do not have permission to create jigsaws from images.", true);
        return;
      }

      const imageId = Number(imageCreateButton.getAttribute("data-image-create"));
      try {
        const jobId = await startBulkCreateJobForImageIds([imageId]);
        if (!jobId) {
          showFeedback("Could not queue AI create for this image.", true);
          return;
        }
        showFeedback(`AI create queued for image #${imageId} (job #${jobId}).`);
      } catch (error) {
        showFeedback(error.message, true);
      }
      return;
    }

    const imageDeleteButton = event.target.closest("[data-image-delete]");
    if (imageDeleteButton) {
      event.preventDefault();
      clearFeedback();

      const imageId = Number(imageDeleteButton.getAttribute("data-image-delete"));
      const image = Array.isArray(state.imageLibraryImages)
        ? state.imageLibraryImages.find((entry) => Number(entry.id) === imageId)
        : null;

      if (!canCurrentUserDeleteImage(image)) {
        showFeedback("You can only delete unassigned images.", true);
        return;
      }

      const confirmMessage = image && image.jigsaw_id
        ? "This image is assigned to a jigsaw. Delete it anyway? This cannot be undone."
        : "Delete this image? This cannot be undone.";
      const shouldDelete = window.confirm(confirmMessage);
      if (!shouldDelete) {
        return;
      }

      try {
        await apiRequest(`/api/v1/image-library/images/${imageId}`, { method: "DELETE" });
        showFeedback("Image deleted.");
        await Promise.all([loadImageLibraryImages(), loadJigsawImagesForSelected(), loadAuditEvents()]);
      } catch (error) {
        showFeedback(error.message, true);
      }
      return;
    }
  }

  function handleDiarySelectionChange() {
    clearFeedback();
    state.diarySelectionTouchedByUser = true;
    state.pagination.diary = 1;
    loadDiaryEntriesForSelected();
  }

  function handleDiaryViewModeClick(event) {
    const button = event.target?.closest("[data-diary-view-mode]");
    if (!(button instanceof HTMLButtonElement)) {
      return;
    }

    const selectedMode = normalizeDiaryViewMode(button.dataset.diaryViewMode);
    if (selectedMode === state.diaryViewMode) {
      return;
    }

    setDiaryViewMode(selectedMode);
    const selectedJigsawId = Number(elements.diaryJigsawId?.value || "0");
    renderDiaryEntries(state.diaryEntries, getDiaryEntriesEmptyMessage(selectedJigsawId));
  }

  function handleDiaryCalendarPreviousMonth() {
    shiftDiaryCalendarMonth(-1);
    const selectedJigsawId = Number(elements.diaryJigsawId?.value || "0");
    renderDiaryEntries(state.diaryEntries, getDiaryEntriesEmptyMessage(selectedJigsawId));
  }

  function handleDiaryCalendarNextMonth() {
    shiftDiaryCalendarMonth(1);
    const selectedJigsawId = Number(elements.diaryJigsawId?.value || "0");
    renderDiaryEntries(state.diaryEntries, getDiaryEntriesEmptyMessage(selectedJigsawId));
  }

  function handleDiaryCalendarCurrentMonth() {
    resetDiaryCalendarToCurrentMonth();
    const selectedJigsawId = Number(elements.diaryJigsawId?.value || "0");
    renderDiaryEntries(state.diaryEntries, getDiaryEntriesEmptyMessage(selectedJigsawId));
  }

  function handleDiaryEntryCancelEdit() {
    clearFeedback();
    resetDiaryEntryFormEditingState({ keepJigsawSelection: true });
    restoreEditorScrollPosition("diary");
  }

  function handleJigsawImageSelectionChange() {
    clearFeedback();
    loadJigsawImagesForSelected();
  }

  function handleJigsawSearchInput(event) {
    state.jigsawSearchQuery = String(event.currentTarget?.value || "").trim().toLowerCase();
    state.pagination.jigsaws = 1;
    renderJigsaws(state.jigsaws);
  }

  function handleJigsawDiaryFilterChange(event) {
    state.jigsawFilterWithoutDiaryEntries = Boolean(event.currentTarget?.checked);
    state.pagination.jigsaws = 1;
    renderJigsaws(state.jigsaws);
  }

  function toggleJigsawInventoryImagesRow(jigsawId) {
    const normalizedJigsawId = Number(jigsawId || 0);
    if (normalizedJigsawId <= 0) {
      return;
    }

    const previousScrollY = Number(window.scrollY || window.pageYOffset || 0);
    const jigsawsTableWrap = document.getElementById("jigsaws-table")?.closest(".table-scroll-wrap") || null;
    const previousScrollLeft = jigsawsTableWrap ? Number(jigsawsTableWrap.scrollLeft || 0) : 0;

    state.jigsawExpandedImageRowsById[normalizedJigsawId] = !Boolean(state.jigsawExpandedImageRowsById[normalizedJigsawId]);
    renderJigsaws(state.jigsaws);

    window.requestAnimationFrame(() => {
      if (jigsawsTableWrap) {
        jigsawsTableWrap.scrollLeft = previousScrollLeft;
      }
      window.scrollTo({ top: previousScrollY });

      const toggledButton = elements.jigsawsTableBody?.querySelector(
        `[data-jigsaw-images-toggle="${normalizedJigsawId}"]`,
      );
      if (toggledButton instanceof HTMLButtonElement) {
        toggledButton.focus({ preventScroll: true });
      }
    });
  }

  function handleImageLibraryFilterChange(event) {
    const target = event.target;
    if (!(target instanceof HTMLInputElement)) {
      return;
    }

    if (target === elements.imageLibraryFilterAssigned) {
      state.imageLibraryFilterAssigned = target.checked;
    } else if (target === elements.imageLibraryFilterUnassigned) {
      state.imageLibraryFilterUnassigned = target.checked;
    } else {
      const tagKey = String(target.dataset.imageLibraryTagFilter || "").trim().toLowerCase();
      if (!tagKey) {
        return;
      }
      state.imageLibraryFilterTagSelections[tagKey] = target.checked;
    }

    state.pagination.imageLibrary = 1;
    renderImageLibraryImages(state.imageLibraryImages);
  }

  function handleSortableHeaderClick(event) {
    const header = event.target.closest("th[data-sort-list][data-sort-field]");
    if (!(header instanceof HTMLTableCellElement)) {
      return;
    }
    event.preventDefault();
    applySortFromHeader(header);
  }

  function handleSortableHeaderKeyDown(event) {
    if (event.key !== "Enter" && event.key !== " ") {
      return;
    }
    const header = event.target.closest("th[data-sort-list][data-sort-field]");
    if (!(header instanceof HTMLTableCellElement)) {
      return;
    }
    event.preventDefault();
    applySortFromHeader(header);
  }

  async function handlePaginationClick(event) {
    const targetButton = event.target.closest("button[data-pagination-list][data-pagination-page]");
    if (!(targetButton instanceof HTMLButtonElement)) {
      return;
    }

    const paginationKey = String(targetButton.dataset.paginationList || "").trim();
    const requestedPage = Number(targetButton.dataset.paginationPage || "0");
    if (!paginationKey || !Number.isFinite(requestedPage) || requestedPage < 1) {
      return;
    }

    state.pagination[paginationKey] = Math.trunc(requestedPage);

    if (paginationKey === "jigsaws") {
      renderJigsaws(state.jigsaws);
      return;
    }
    if (paginationKey === "imageLibrary") {
      renderImageLibraryImages(state.imageLibraryImages);
      return;
    }
    if (paginationKey === "diary") {
      const selectedJigsawId = Number(elements.diaryJigsawId?.value || "0");
      renderDiaryEntries(state.diaryEntries, getDiaryEntriesEmptyMessage(selectedJigsawId));
      return;
    }
    if (paginationKey === "aiRecent") {
      await loadAiUsageDiagnostics();
      return;
    }
    if (paginationKey === "audit") {
      await loadAuditEvents();
      return;
    }
  }

  function setImageBrowserFilterInputsFromState() {
    if (elements.imageBrowserFilterShowAll) {
      elements.imageBrowserFilterShowAll.checked = Boolean(state.imageBrowser.filterShowAll);
    }

    setTriStateFilterInputMode(elements.imageBrowserFilterUnassigned, state.imageBrowser.filterModes.unassigned);
    setTriStateFilterInputMode(elements.imageBrowserFilterBox, state.imageBrowser.filterModes.box);
    setTriStateFilterInputMode(elements.imageBrowserFilterReference, state.imageBrowser.filterModes.reference);
    setTriStateFilterInputMode(elements.imageBrowserFilterCompleted, state.imageBrowser.filterModes.completed);
    setTriStateFilterInputMode(elements.imageBrowserFilterInProgress, state.imageBrowser.filterModes.inProgress);

    updateImageBrowserFilterInputsDisabledState();
  }

  function setTriStateFilterInputMode(input, mode) {
    if (!input) {
      return;
    }
    const resolvedMode = normalizeBrowserFilterMode(mode);
    input.indeterminate = resolvedMode === BROWSER_FILTER_MODE_EXCLUDE;
    input.checked = resolvedMode === BROWSER_FILTER_MODE_INCLUDE;
    input.dataset.filterMode = resolvedMode;
    input.setAttribute("aria-checked", resolvedMode === BROWSER_FILTER_MODE_EXCLUDE ? "mixed" : (input.checked ? "true" : "false"));
    const item = input.closest(".govuk-checkboxes__item");
    if (item) {
      item.classList.toggle("app-filter-tristate--exclude", resolvedMode === BROWSER_FILTER_MODE_EXCLUDE);
    }
  }

  function normalizeBrowserFilterMode(mode) {
    const resolvedMode = String(mode || "").trim().toLowerCase();
    if (resolvedMode === BROWSER_FILTER_MODE_INCLUDE || resolvedMode === BROWSER_FILTER_MODE_EXCLUDE) {
      return resolvedMode;
    }
    return BROWSER_FILTER_MODE_IGNORE;
  }

  function getNextBrowserFilterMode(mode) {
    const resolvedMode = normalizeBrowserFilterMode(mode);
    if (resolvedMode === BROWSER_FILTER_MODE_IGNORE) {
      return BROWSER_FILTER_MODE_INCLUDE;
    }
    if (resolvedMode === BROWSER_FILTER_MODE_INCLUDE) {
      return BROWSER_FILTER_MODE_EXCLUDE;
    }
    return BROWSER_FILTER_MODE_IGNORE;
  }

  function updateImageBrowserFilterInputsDisabledState() {
    const useShowAll = Boolean(state.imageBrowser.filterShowAll);
    [
      elements.imageBrowserFilterUnassigned,
      elements.imageBrowserFilterBox,
      elements.imageBrowserFilterReference,
      elements.imageBrowserFilterCompleted,
      elements.imageBrowserFilterInProgress,
    ].forEach((checkbox) => {
      if (checkbox) {
        checkbox.disabled = useShowAll;
      }
    });
  }

  function syncImageBrowserFilterStateFromInputs() {
    state.imageBrowser.filterShowAll = Boolean(elements.imageBrowserFilterShowAll?.checked);

    state.imageBrowser.filterModes.unassigned = normalizeBrowserFilterMode(elements.imageBrowserFilterUnassigned?.dataset?.filterMode);
    state.imageBrowser.filterModes.box = normalizeBrowserFilterMode(elements.imageBrowserFilterBox?.dataset?.filterMode);
    state.imageBrowser.filterModes.reference = normalizeBrowserFilterMode(elements.imageBrowserFilterReference?.dataset?.filterMode);
    state.imageBrowser.filterModes.completed = normalizeBrowserFilterMode(elements.imageBrowserFilterCompleted?.dataset?.filterMode);
    state.imageBrowser.filterModes.inProgress = normalizeBrowserFilterMode(elements.imageBrowserFilterInProgress?.dataset?.filterMode);

    updateImageBrowserFilterInputsDisabledState();
  }

  async function applyImageBrowserFilterChange(previousItemId, previousIndex, hadPendingEdits, previousFilters) {
    if (state.imageBrowser.isOpen && hadPendingEdits) {
      const willKeepCurrent = previousItemId ? setImageBrowserIndexByImageId(previousItemId) : false;
      if (!willKeepCurrent) {
        const shouldDiscard = window.confirm("Discard unsaved image edits and apply browser filters?");
        if (!shouldDiscard) {
          state.imageBrowser.filterShowAll = previousFilters.showAll;
          state.imageBrowser.filterModes.unassigned = previousFilters.modes.unassigned;
          state.imageBrowser.filterModes.box = previousFilters.modes.box;
          state.imageBrowser.filterModes.reference = previousFilters.modes.reference;
          state.imageBrowser.filterModes.completed = previousFilters.modes.completed;
          state.imageBrowser.filterModes.inProgress = previousFilters.modes.inProgress;
          state.imageBrowser.index = previousIndex;
          setImageBrowserFilterInputsFromState();
          return;
        }
      }
    }

    if (previousItemId) {
      setImageBrowserIndexByImageId(previousItemId);
    } else {
      state.imageBrowser.index = 0;
    }

    if (!state.imageBrowser.isOpen) {
      return;
    }

    try {
      await loadCurrentImageIntoBrowser();
    } catch (error) {
      showFeedback(error.message, true);
    }
  }

  async function handleImageBrowserFilterChange() {
    const previousItemId = getCurrentImageBrowserItem()?.id || null;
    const previousIndex = state.imageBrowser.index;
    const hadPendingEdits = browserHasPendingEdits();
    const previousFilters = {
      showAll: state.imageBrowser.filterShowAll,
      modes: {
        unassigned: state.imageBrowser.filterModes.unassigned,
        box: state.imageBrowser.filterModes.box,
        reference: state.imageBrowser.filterModes.reference,
        completed: state.imageBrowser.filterModes.completed,
        inProgress: state.imageBrowser.filterModes.inProgress,
      },
    };
    syncImageBrowserFilterStateFromInputs();
    await applyImageBrowserFilterChange(previousItemId, previousIndex, hadPendingEdits, previousFilters);
  }

  async function handleImageBrowserTriStateToggle(event) {
    const input = event.currentTarget;
    const filterKey = String(input?.dataset?.imageBrowserFilterKey || "").trim();
    if (!filterKey) {
      return;
    }

    const previousItemId = getCurrentImageBrowserItem()?.id || null;
    const previousIndex = state.imageBrowser.index;
    const hadPendingEdits = browserHasPendingEdits();
    const previousFilters = {
      showAll: state.imageBrowser.filterShowAll,
      modes: {
        unassigned: state.imageBrowser.filterModes.unassigned,
        box: state.imageBrowser.filterModes.box,
        reference: state.imageBrowser.filterModes.reference,
        completed: state.imageBrowser.filterModes.completed,
        inProgress: state.imageBrowser.filterModes.inProgress,
      },
    };

    state.imageBrowser.filterModes[filterKey] = getNextBrowserFilterMode(input.dataset.filterMode);
    setImageBrowserFilterInputsFromState();
    await applyImageBrowserFilterChange(previousItemId, previousIndex, hadPendingEdits, previousFilters);
  }

  function attachEvents() {
    if (elements.loginOpenButton) {
      elements.loginOpenButton.addEventListener("click", openAuthDialog);
    }

    if (elements.authDialogCloseButton) {
      elements.authDialogCloseButton.addEventListener("click", closeAuthDialog);
    }

    if (elements.authDialogBackdrop) {
      elements.authDialogBackdrop.addEventListener("click", (event) => {
        if (event.target === elements.authDialogBackdrop) {
          closeAuthDialog();
        }
      });
    }

    window.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && state.authDialogOpen) {
        closeAuthDialog();
      }
    });

    if (elements.loginForm) {
      elements.loginForm.addEventListener("submit", handleLoginSubmit);
    }

    if (elements.stfdLoginButton) {
      elements.stfdLoginButton.addEventListener("click", handleStfdLoginClick);
    }

    if (elements.logoutButton) {
      elements.logoutButton.addEventListener("click", handleLogout);
    }

    if (elements.accountNavButton) {
      elements.accountNavButton.addEventListener("click", handleAccountNavClick);
    }

    if (elements.workspaceTabs) {
      elements.workspaceTabs.addEventListener("click", handleWorkspaceTabClick);
    }

    if (elements.collectionSubtabs) {
      elements.collectionSubtabs.addEventListener("click", handleCollectionTabClick);
    }

    if (elements.adminSubtabs) {
      elements.adminSubtabs.addEventListener("click", handleAdminTabClick);
    }

    window.addEventListener("hashchange", handleWorkspaceHashChange);

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

    if (elements.ipBlockCreateForm) {
      elements.ipBlockCreateForm.addEventListener("submit", handleCreateBlockedIp);
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

    if (elements.imageLibraryJigsawId) {
      elements.imageLibraryJigsawId.addEventListener("change", syncBulkCreateFromUploadVisibility);
    }

    if (elements.imageLibraryTag) {
      elements.imageLibraryTag.addEventListener("change", syncBulkCreateFromUploadVisibility);
    }

    if (elements.imageLibraryDropzone) {
      elements.imageLibraryDropzone.addEventListener("dragover", handleImageLibraryDropzoneDragOver);
      elements.imageLibraryDropzone.addEventListener("dragleave", handleImageLibraryDropzoneDragLeave);
      elements.imageLibraryDropzone.addEventListener("drop", handleImageLibraryDropzoneDrop);
      elements.imageLibraryDropzone.addEventListener("keydown", handleImageLibraryDropzoneKeyDown);
    }

    if (elements.imageLibraryFilterAssigned) {
      elements.imageLibraryFilterAssigned.addEventListener("change", handleImageLibraryFilterChange);
    }

    if (elements.imageLibraryFilterUnassigned) {
      elements.imageLibraryFilterUnassigned.addEventListener("change", handleImageLibraryFilterChange);
    }

    if (elements.imageLibraryTagFilters) {
      elements.imageLibraryTagFilters.addEventListener("change", handleImageLibraryFilterChange);
    }

    if (elements.jigsawsPagination) {
      elements.jigsawsPagination.addEventListener("click", handlePaginationClick);
    }
    if (elements.jigsawsPaginationTop) {
      elements.jigsawsPaginationTop.addEventListener("click", handlePaginationClick);
    }

    if (elements.imageLibraryPagination) {
      elements.imageLibraryPagination.addEventListener("click", handlePaginationClick);
    }
    if (elements.imageLibraryPaginationTop) {
      elements.imageLibraryPaginationTop.addEventListener("click", handlePaginationClick);
    }

    if (elements.diaryPagination) {
      elements.diaryPagination.addEventListener("click", handlePaginationClick);
    }
    if (elements.diaryPaginationTop) {
      elements.diaryPaginationTop.addEventListener("click", handlePaginationClick);
    }

    if (elements.aiUsageRecentPagination) {
      elements.aiUsageRecentPagination.addEventListener("click", handlePaginationClick);
    }
    if (elements.aiUsageRecentPaginationTop) {
      elements.aiUsageRecentPaginationTop.addEventListener("click", handlePaginationClick);
    }

    if (elements.auditPagination) {
      elements.auditPagination.addEventListener("click", handlePaginationClick);
    }
    if (elements.auditPaginationTop) {
      elements.auditPaginationTop.addEventListener("click", handlePaginationClick);
    }

    if (elements.adminSections) {
      elements.adminSections.addEventListener("click", handleSortableHeaderClick);
      elements.adminSections.addEventListener("keydown", handleSortableHeaderKeyDown);
    }

    if (elements.imageBrowserOpen) {
      elements.imageBrowserOpen.addEventListener("click", () => {
        openImageBrowser();
      });
    }

    if (elements.imageLibraryBulkCreateUnassignedBoxButton) {
      elements.imageLibraryBulkCreateUnassignedBoxButton.addEventListener("click", handleBulkCreateAllUnassignedBoxImages);
    }

    if (elements.imageEmbeddingBackfillStart) {
      elements.imageEmbeddingBackfillStart.addEventListener("click", handleImageEmbeddingBackfillStart);
    }
    if (elements.imageEmbeddingBackfillMissing) {
      elements.imageEmbeddingBackfillMissing.addEventListener("click", handleImageEmbeddingBackfillStart);
    }

    if (elements.imageBrowserFilterShowAll) {
      elements.imageBrowserFilterShowAll.addEventListener("change", handleImageBrowserFilterChange);
    }

    if (elements.imageBrowserFilterBox) {
      elements.imageBrowserFilterBox.addEventListener("click", handleImageBrowserTriStateToggle);
    }

    if (elements.imageBrowserFilterReference) {
      elements.imageBrowserFilterReference.addEventListener("click", handleImageBrowserTriStateToggle);
    }

    if (elements.imageBrowserFilterCompleted) {
      elements.imageBrowserFilterCompleted.addEventListener("click", handleImageBrowserTriStateToggle);
    }

    if (elements.imageBrowserFilterInProgress) {
      elements.imageBrowserFilterInProgress.addEventListener("click", handleImageBrowserTriStateToggle);
    }

    if (elements.imageBrowserFilterUnassigned) {
      elements.imageBrowserFilterUnassigned.addEventListener("click", handleImageBrowserTriStateToggle);
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

    if (elements.imageBrowserAssignPrevious) {
      elements.imageBrowserAssignPrevious.addEventListener("click", () => {
        assignCurrentImageUsingNeighbor(-1);
      });
    }

    if (elements.imageBrowserAssignNext) {
      elements.imageBrowserAssignNext.addEventListener("click", () => {
        assignCurrentImageUsingNeighbor(1);
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

    if (elements.imageBrowserMarkReference) {
      elements.imageBrowserMarkReference.addEventListener("click", () => {
        setImageBrowserTag(IMAGE_BROWSER_TAG_REFERENCE);
      });
    }

    if (elements.imageBrowserMarkInProgress) {
      elements.imageBrowserMarkInProgress.addEventListener("click", () => {
        setImageBrowserTag(IMAGE_BROWSER_TAG_IN_PROGRESS);
      });
    }

    if (elements.imageBrowserCreateJigsaw) {
      elements.imageBrowserCreateJigsaw.addEventListener("click", () => {
        createJigsawFromCurrentBrowserImage();
      });
    }

    if (elements.imageBrowserFindSimilar) {
      elements.imageBrowserFindSimilar.addEventListener("click", () => {
        handleImageBrowserSuggestMatch();
      });
    }

    if (elements.imageBrowserFindName) {
      elements.imageBrowserFindName.addEventListener("click", () => {
        openImageBrowserNameAssignModal();
      });
    }

    if (elements.imageBrowserDelete) {
      elements.imageBrowserDelete.addEventListener("click", () => {
        deleteCurrentBrowserImage();
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

    if (elements.imageBrowserSaveCreate) {
      elements.imageBrowserSaveCreate.addEventListener("click", () => {
        saveImageBrowserCreateReference();
      });
    }

    if (elements.imageBrowserSave) {
      elements.imageBrowserSave.addEventListener("click", () => {
        saveImageBrowserOverwrite();
      });
    }

    if (elements.imageBrowserSuggestionsClose) {
      elements.imageBrowserSuggestionsClose.addEventListener("click", () => {
        closeImageBrowserSuggestionModal();
      });
    }

    if (elements.imageBrowserSuggestionsModal) {
      elements.imageBrowserSuggestionsModal.addEventListener("click", (event) => {
        if (event.target === elements.imageBrowserSuggestionsModal) {
          closeImageBrowserSuggestionModal();
        }
      });
    }

    if (elements.imageBrowserNameQuery) {
      elements.imageBrowserNameQuery.addEventListener("input", () => {
        renderImageBrowserNameMatchResults();
      });
      elements.imageBrowserNameQuery.addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
          event.preventDefault();
          assignCurrentImageByNameSelection();
        }
      });
    }

    if (elements.imageBrowserNameResults) {
      elements.imageBrowserNameResults.addEventListener("change", () => {
        renderImageBrowserNameSelectionPreview();
      });
    }

    if (elements.imageBrowserNameAssign) {
      elements.imageBrowserNameAssign.addEventListener("click", () => {
        assignCurrentImageByNameSelection();
      });
    }

    if (elements.imageBrowserNameAssignClose) {
      elements.imageBrowserNameAssignClose.addEventListener("click", () => {
        closeImageBrowserNameAssignModal();
      });
    }

    if (elements.imageBrowserNameAssignModal) {
      elements.imageBrowserNameAssignModal.addEventListener("click", (event) => {
        if (event.target === elements.imageBrowserNameAssignModal) {
          closeImageBrowserNameAssignModal();
        }
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

    if (elements.diaryEntryCancelButton) {
      elements.diaryEntryCancelButton.addEventListener("click", handleDiaryEntryCancelEdit);
    }

    if (elements.diaryJigsawId) {
      elements.diaryJigsawId.addEventListener("change", handleDiarySelectionChange);
    }

    if (elements.diaryViewModeButtons.length > 0) {
      elements.diaryViewModeButtons.forEach((button) => {
        button.addEventListener("click", handleDiaryViewModeClick);
      });
    }

    if (elements.diaryCalendarPrevButton) {
      elements.diaryCalendarPrevButton.addEventListener("click", handleDiaryCalendarPreviousMonth);
    }

    if (elements.diaryCalendarNextButton) {
      elements.diaryCalendarNextButton.addEventListener("click", handleDiaryCalendarNextMonth);
    }

    if (elements.diaryCalendarTodayButton) {
      elements.diaryCalendarTodayButton.addEventListener("click", handleDiaryCalendarCurrentMonth);
    }

    if (elements.diaryEntriesTableBody) {
      elements.diaryEntriesTableBody.addEventListener("click", handleTableActions);
    }

    if (elements.imageLibraryTableBody) {
      elements.imageLibraryTableBody.addEventListener("click", handleTableActions);
    }

    if (elements.imageBrowserSuggestionsList) {
      elements.imageBrowserSuggestionsList.addEventListener("click", handleTableActions);
    }

    if (elements.loansTableBody) {
      elements.loansTableBody.addEventListener("click", handleTableActions);
    }

    if (elements.ipBlocksTableBody) {
      elements.ipBlocksTableBody.addEventListener("click", handleTableActions);
    }

    if (elements.jigsawEditForm) {
      elements.jigsawEditForm.addEventListener("submit", handleEditJigsaw);
    }

    if (elements.jigsawEditCancelButton) {
      elements.jigsawEditCancelButton.addEventListener("click", handleCancelJigsawEdit);
    }

    if (elements.jigsawEditEnrichButton) {
      elements.jigsawEditEnrichButton.addEventListener("click", handleEnrichJigsaw);
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

    if (elements.jigsawSearchInput) {
      elements.jigsawSearchInput.addEventListener("input", handleJigsawSearchInput);
    }

    if (elements.jigsawFilterNoDiary) {
      elements.jigsawFilterNoDiary.addEventListener("change", handleJigsawDiaryFilterChange);
    }

    if (elements.aiUsageRecentBody) {
      elements.aiUsageRecentBody.addEventListener("click", handleTableActions);
    }

    if (elements.aiUsageDetailCloseButton) {
      elements.aiUsageDetailCloseButton.addEventListener("click", closeAiUsageDetailModal);
    }

    if (elements.aiUsageDetailModal) {
      elements.aiUsageDetailModal.addEventListener("click", (event) => {
        if (event.target === elements.aiUsageDetailModal) {
          closeAiUsageDetailModal();
        }
      });
    }
  }

  async function init() {
    syncHeaderAuthControls();
    state.diarySelectionTouchedByUser = false;
    setDiaryViewMode(state.diaryViewMode);
    renderUserRoleSelectors();
    setImageBrowserFilterInputsFromState();
    syncImageBrowserFilterStateFromInputs();
    attachEvents();
    await fetchStfdLoginInfo();
    const consumedToken = await consumeStfdTokenFromUrl();
    updateSortableTableHeaders();
    renderBulkUploadFiles();
    syncBulkCreateFromUploadVisibility();
    const isAuthenticated = consumedToken ? true : await refreshSession();
    if (isAuthenticated) {
      clearImageEmbeddingBackfillProgress();
      setImageEmbeddingBackfillStatus("");
      await Promise.all([
        loadRoles(),
        loadUsers(),
        loadJigsaws(),
        loadJigsawThumbnailImages(),
        loadLoans(),
        loadAuditEvents(),
        loadBlockedIps(),
        loadAiUsageDiagnostics(),
        loadImageEmbeddingDiagnostics(),
      ]);
      await Promise.all([loadJigsawImagesForSelected(), loadDiaryEntriesForSelected()]);
      if (currentUserHasCapability("image.manage_library")) {
        loadImageLibraryImages().catch(() => {
          // Background refresh errors are surfaced by the image-library loader.
        });
      }
    } else {
      clearImageEmbeddingBackfillProgress();
      setImageEmbeddingBackfillStatus("");
      await Promise.all([loadJigsaws(), loadJigsawThumbnailImages()]);
      renderUsers([]);
      renderUserRoleSelectors();
      renderLoans([]);
      renderBlockedIps([]);
      renderJigsawImages([]);
      renderImageLibraryImages([]);
      renderDiaryEntries([]);
      renderAuditEvents([]);
      renderAiUsageDiagnostics(null);
      renderImageEmbeddingDiagnostics(null);
      closeAiUsageDetailModal();
      renderBulkUploadFiles();
      clearBulkCreateProgress();
      populateLoanFormOptions();
      populateJigsawImageOptions();
      populateDiaryJigsawOptions();
      populateImageLibraryJigsawOptions();
    }
  }

  init();
})();
