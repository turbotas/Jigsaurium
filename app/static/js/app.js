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
    users: [],
    jigsaws: [],
    jigsawSearchQuery: "",
    jigsawFilterWithoutDiaryEntries: false,
    loans: [],
    auditEvents: [],
    auditEventsMeta: null,
    jigsawThumbnailImages: [],
    jigsawImages: [],
    imageLibraryImages: [],
    imageLibraryFilterAssigned: true,
    imageLibraryFilterUnassigned: true,
    imageLibraryFilterTagSelections: {},
    aiUsageDiagnostics: null,
    aiUsageRecentById: {},
    imageBrowserContentCacheByImageId: {},
    imageBrowserSavingImageIds: {},
    diaryEntries: [],
    diaryEditingEntryId: null,
    diarySelectionTouchedByUser: false,
    bulkUploadFiles: [],
    bulkCreateJobId: null,
    bulkCreateJobPollTimer: null,
    imageEmbeddingBackfillJobId: null,
    imageEmbeddingBackfillPollTimer: null,
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
      filterUnassigned: true,
      filterBox: false,
      filterReference: false,
      filterCompleted: false,
      filterInProgress: false,
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
    imageLibraryPagination: document.getElementById("image-library-pagination"),
    imageLibraryBulkCreateUnassignedBoxButton: document.getElementById("image-library-bulk-create-unassigned-box"),
    imageEmbeddingBackfillStart: document.getElementById("image-embedding-backfill-start"),
    imageEmbeddingBackfillStatus: document.getElementById("image-embedding-backfill-status"),
    imageBrowserOpen: document.getElementById("image-browser-open"),
    imageBrowserModal: document.getElementById("image-browser-modal"),
    imageBrowserStatus: document.getElementById("image-browser-status"),
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
    imageBrowserCreateJigsaw: document.getElementById("image-browser-create-jigsaw"),
    imageBrowserDelete: document.getElementById("image-browser-delete"),
    imageBrowserCropToggle: document.getElementById("image-browser-crop-toggle"),
    imageBrowserCropApply: document.getElementById("image-browser-crop-apply"),
    imageBrowserSaveCreate: document.getElementById("image-browser-save-create"),
    imageBrowserSave: document.getElementById("image-browser-save"),
    imageBrowserClose: document.getElementById("image-browser-close"),
    diaryEntryForm: document.getElementById("diary-entry-form"),
    diaryEntrySubmitButton: document.getElementById("diary-entry-submit"),
    diaryEntryCancelButton: document.getElementById("diary-entry-cancel"),
    diaryJigsawId: document.getElementById("diary-jigsaw-id"),
    diaryCompletedAt: document.getElementById("diary-completed-at"),
    diaryDifficulty: document.getElementById("diary-difficulty"),
    diaryNotes: document.getElementById("diary-notes"),
    diaryEntriesCaption: document.getElementById("diary-entries-caption"),
    diaryEntriesTableBody: document.getElementById("diary-entries-table-body"),
    diaryPagination: document.getElementById("diary-pagination"),
    loanCreateForm: document.getElementById("loan-create-form"),
    loanBorrowerUserId: document.getElementById("loan-borrower-user-id"),
    loanJigsawId: document.getElementById("loan-jigsaw-id"),
    loansTableBody: document.getElementById("loans-table-body"),
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
    aiUsageRecentPagination: document.getElementById("ai-usage-recent-pagination"),
    aiUsageDetailModal: document.getElementById("ai-usage-detail-modal"),
    aiUsageDetailSummary: document.getElementById("ai-usage-detail-summary"),
    aiUsageDetailPayload: document.getElementById("ai-usage-detail-payload"),
    aiUsageDetailCloseButton: document.getElementById("ai-usage-detail-close"),
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

    state.diaryEditingEntryId = resolvedEntryId;
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
  }

  function getDiaryEntryImageUrls(entry) {
    const sourceImage = entry?.source_image;
    if (sourceImage) {
      const sourceImageId = Number(sourceImage?.id || entry?.source_image_id || 0);
      return {
        thumbnailUrl: String(sourceImage?.thumbnail_url || (sourceImageId ? `/api/v1/images/${sourceImageId}/content?variant=thumbnail` : "")),
        previewUrl: String(sourceImage?.preview_url || (sourceImageId ? `/api/v1/images/${sourceImageId}/content?variant=preview` : "")),
        openUrl: String(sourceImage?.content_url || (sourceImageId ? `/api/v1/images/${sourceImageId}/content` : "")),
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

    return {
      thumbnailUrl: String(matchingImage?.thumbnail_url || `/api/v1/images/${sourceImageId}/content?variant=thumbnail`),
      previewUrl: String(matchingImage?.preview_url || `/api/v1/images/${sourceImageId}/content?variant=preview`),
      openUrl: String(matchingImage?.content_url || `/api/v1/images/${sourceImageId}/content`),
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

  function setSessionSummary() {
    if (!elements.sessionSummary) {
      return;
    }

    if (!state.user) {
      resetDiaryEntryFormEditingState({ keepJigsawSelection: false });
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
    if (state.diaryEditingEntryId && (!Array.isArray(state.user.roles) || !state.user.roles.includes("administrator"))) {
      resetDiaryEntryFormEditingState({ keepJigsawSelection: true });
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

    pageResult.rows.forEach((jigsaw) => {
      const row = document.createElement("tr");
      row.className = "govuk-table__row";

      const preferredImage = preferredImagesByJigsawId.get(Number(jigsaw.id));
      row.appendChild(
        buildThumbnailCell(preferredImage?.thumbnail_url || preferredImage?.content_url, {
          altText: `Thumbnail for ${jigsaw.title || "jigsaw"}`,
          previewUrl: preferredImage?.preview_url || preferredImage?.content_url,
          openUrl: preferredImage?.content_url,
        })
      );
      row.appendChild(buildCell(String(jigsaw.title || "-")));
      row.appendChild(buildCell(String(jigsaw.piece_count || "-")));
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

      const enrichButton = document.createElement("button");
      enrichButton.type = "button";
      enrichButton.className = "govuk-button govuk-button--secondary app-inline-button";
      enrichButton.setAttribute("data-module", "govuk-button");
      enrichButton.dataset.jigsawEnrich = String(jigsaw.id);
      enrichButton.textContent = "Enrich";
      controlsWrap.appendChild(enrichButton);

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

    renderPagination(elements.jigsawsPagination, "jigsaws", pageResult);
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

    renderPagination(elements.auditPagination, "audit", pageResult);
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

    renderPagination(elements.aiUsageRecentPagination, "aiRecent", pageResult);
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

      const tagSelect = document.createElement("select");
      tagSelect.className = "govuk-select";
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

      if (!image.jigsaw_id && sortedJigsaws.length > 0) {
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
        note.textContent = "No jigsaws available";
        assignControls.appendChild(note);
      } else {
        const assignedNote = document.createElement("span");
        assignedNote.textContent = "Assigned";
        assignControls.appendChild(assignedNote);

        const unassignButton = document.createElement("button");
        unassignButton.type = "button";
        unassignButton.className = "govuk-button govuk-button--secondary app-inline-button";
        unassignButton.setAttribute("data-module", "govuk-button");
        unassignButton.dataset.imageUnassign = String(image.id);
        unassignButton.textContent = "Unassign";
        assignControls.appendChild(unassignButton);
      }

      if (!image.jigsaw_id) {
        const createButton = document.createElement("button");
        createButton.type = "button";
        createButton.className = "govuk-button govuk-button--secondary app-inline-button";
        createButton.setAttribute("data-module", "govuk-button");
        createButton.dataset.imageCreate = String(image.id);
        createButton.textContent = "Create";
        actionButtons.appendChild(createButton);

        if (toImageTagKey(image.tag) === toImageTagKey(IMAGE_BROWSER_TAG_COMPLETED)) {
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

      const deleteButton = document.createElement("button");
      deleteButton.type = "button";
      deleteButton.className = "govuk-button govuk-button--warning app-inline-button";
      deleteButton.setAttribute("data-module", "govuk-button");
      deleteButton.dataset.imageDelete = String(image.id);
      deleteButton.textContent = "Delete";
      actionButtons.appendChild(deleteButton);

      controlsWrap.appendChild(assignControls);
      controlsWrap.appendChild(suggestControls);
      controlsWrap.appendChild(actionButtons);

      actionCell.appendChild(controlsWrap);
      row.appendChild(actionCell);
      tableBody.appendChild(row);
    });

    renderPagination(elements.imageLibraryPagination, "imageLibrary", pageResult);
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
    const selected = [];
    if (state.imageBrowser.filterUnassigned) {
      selected.push("unassigned");
    }
    if (state.imageBrowser.filterBox) {
      selected.push("box");
    }
    if (state.imageBrowser.filterReference) {
      selected.push("reference");
    }
    if (state.imageBrowser.filterCompleted) {
      selected.push("completed");
    }
    if (state.imageBrowser.filterInProgress) {
      selected.push("in-progress");
    }
    if (selected.length === 0) {
      return false;
    }

    const isUnassigned = !image?.jigsaw_id;
    if (isUnassigned && state.imageBrowser.filterUnassigned) {
      return true;
    }

    const tagKey = toImageTagKey(image?.tag);
    const isBoxFamilyTag = [
      IMAGE_BROWSER_TAG_BOX,
      IMAGE_BROWSER_TAG_BOX_FRONT,
      IMAGE_BROWSER_TAG_BOX_SIDE,
      IMAGE_BROWSER_TAG_BOX_BACK,
    ].some((value) => tagKey === toImageTagKey(value));
    if (state.imageBrowser.filterBox && isBoxFamilyTag) {
      return true;
    }
    if (state.imageBrowser.filterReference && tagKey === toImageTagKey(IMAGE_BROWSER_TAG_REFERENCE)) {
      return true;
    }
    if (state.imageBrowser.filterCompleted && tagKey === toImageTagKey(IMAGE_BROWSER_TAG_COMPLETED)) {
      return true;
    }
    if (state.imageBrowser.filterInProgress && tagKey === toImageTagKey(IMAGE_BROWSER_TAG_IN_PROGRESS)) {
      return true;
    }
    return false;
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

  function syncImageBrowserSaveButton() {
    if (!elements.imageBrowserSave) {
      return;
    }

    const currentImageId = Number(getCurrentImageBrowserItem()?.id || 0);
    const isCurrentSaveInFlight = isImageBrowserSaveInFlight(currentImageId);
    elements.imageBrowserSave.disabled = !currentImageId || isCurrentSaveInFlight;
    elements.imageBrowserSave.textContent = isCurrentSaveInFlight ? "Saving..." : "Save overwrite";

    if (elements.imageBrowserSaveCreate) {
      const currentJigsawId = Number(getCurrentImageBrowserItem()?.jigsaw_id || 0);
      elements.imageBrowserSaveCreate.disabled = !currentImageId || !currentJigsawId || isCurrentSaveInFlight;
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
    const filtered = getImageBrowserFilteredImages();
    if (filtered.length === 0) {
      showFeedback("No images match the active browser filters.", true);
      return;
    }

    state.imageBrowser.isOpen = true;
    elements.imageBrowserModal.hidden = false;

    try {
      await loadCurrentImageIntoBrowser();
    } catch (error) {
      if (error.status === 502) {
        await loadAiUsageDiagnostics();
        const requestId = error?.payload?.meta?.request_id;
        const hint = buildAiFailureHintForImage(item.id, requestId);
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

    if (item.jigsaw_id) {
      const shouldDelete = window.confirm("This image is assigned to a jigsaw. Delete it anyway? This cannot be undone.");
      if (!shouldDelete) {
        return;
      }
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
    apiRequest(`/api/v1/jigsaws/${jigsawId}/images`, {
      method: "POST",
      body: formData,
    })
      .then((payload) => {
        const createdReference = payload?.data || null;
        if (!createdReference || !Number(createdReference.id || 0)) {
          showFeedback("Reference image create did not return a created image.", true);
          return;
        }

        showFeedback(`Reference image created as image #${createdReference.id}.`);
        Promise.all([loadImageLibraryImages(), loadJigsawImagesForSelected(), loadAuditEvents()]).catch(() => {
          // Background refresh errors are surfaced by individual loaders.
        });
      })
      .catch((error) => {
        showFeedback(error.message, true);
      })
      .finally(() => {
        delete state.imageBrowserSavingImageIds[String(sourceImageId)];
        updateImageBrowserStatus();
      });
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
      closeImageBrowser();
    }
  }

  function renderDiaryEntries(entries, emptyMessage = "No diary entries found.") {
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

      const isAdministrator = Array.isArray(state.user?.roles) && state.user.roles.includes("administrator");
      if (isFormalDiaryEntry && isAdministrator) {
        const editButton = document.createElement("button");
        editButton.type = "button";
        editButton.className = "govuk-button govuk-button--secondary app-inline-button";
        editButton.setAttribute("data-module", "govuk-button");
        editButton.dataset.diaryEdit = String(entry.id);
        editButton.textContent = "Edit";

        const deleteButton = document.createElement("button");
        deleteButton.type = "button";
        deleteButton.className = "govuk-button govuk-button--warning app-inline-button";
        deleteButton.setAttribute("data-module", "govuk-button");
        deleteButton.dataset.diaryDelete = String(entry.id);
        deleteButton.textContent = "Delete";
        actionCell.appendChild(editButton);
        actionCell.appendChild(deleteButton);
      } else if (!isFormalDiaryEntry && isAdministrator) {
        const suggestButton = document.createElement("button");
        suggestButton.type = "button";
        suggestButton.className = "govuk-button govuk-button--secondary app-inline-button";
        suggestButton.setAttribute("data-module", "govuk-button");
        suggestButton.dataset.diarySuggestImage = String(Number(entry?.source_image_id || entry?.id || 0));
        suggestButton.textContent = "Find similar";

        const assignWrap = document.createElement("div");
        assignWrap.className = "app-inline-controls app-image-actions__row govuk-!-margin-top-2";
        assignWrap.dataset.diarySuggestWrap = String(Number(entry?.source_image_id || entry?.id || 0));

        actionCell.appendChild(suggestButton);
        actionCell.appendChild(assignWrap);
      } else {
        actionCell.textContent = "-";
      }

      row.appendChild(actionCell);
      tableBody.appendChild(row);
    });

    renderPagination(elements.diaryPagination, "diary", pageResult);
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
    if (!state.user) {
      state.jigsawThumbnailImages = [];
      renderJigsaws(state.jigsaws);
      return;
    }

    try {
      const payload = await apiRequest("/api/v1/jigsaws/thumbnail-images");
      state.jigsawThumbnailImages = Array.isArray(payload.data) ? payload.data : [];
      renderJigsaws(state.jigsaws);
    } catch (_error) {
      state.jigsawThumbnailImages = [];
      renderJigsaws(state.jigsaws);
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

  async function loadImageLibraryImages(options = {}) {
    const shouldSkipBrowserReload = Boolean(options && options.skipBrowserReload);

    if (!state.user) {
      state.imageLibraryImages = [];
      state.jigsawThumbnailImages = [];
      state.imageBrowserContentCacheByImageId = {};
      state.imageBrowserSavingImageIds = {};
      renderImageLibraryImages([]);
      renderJigsaws(state.jigsaws);
      return;
    }

    try {
      const payload = await apiRequest("/api/v1/image-library/images?limit=200");
      state.imageLibraryImages = Array.isArray(payload.data) ? payload.data : [];
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
      return;
    }
    const wrap = elements.diaryEntriesTableBody.querySelector(`[data-diary-suggest-wrap="${Number(imageId)}"]`);
    if (!wrap) {
      return;
    }

    while (wrap.firstChild) {
      wrap.removeChild(wrap.firstChild);
    }
    wrap.classList.add("app-diary-suggestions");

    if (!Array.isArray(candidates) || candidates.length === 0) {
      const note = document.createElement("span");
      note.textContent = "No candidates";
      wrap.appendChild(note);
      return;
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
  }

  async function handleDiarySuggestMatch(imageId) {
    const resolvedImageId = Number(imageId || 0);
    if (!resolvedImageId) {
      return;
    }

    try {
      const payload = await apiRequest(`/api/v1/image-library/images/${resolvedImageId}/match-suggestions?limit=3`);
      const candidates = Array.isArray(payload?.data?.candidates) ? payload.data.candidates : [];
      renderDiarySuggestionOptions(resolvedImageId, candidates);
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

  async function assignImageToJigsaw(imageId, jigsawId) {
    await apiRequest(`/api/v1/image-library/images/${Number(imageId)}/assign`, {
      method: "PATCH",
      body: JSON.stringify({ jigsaw_id: Number(jigsawId) }),
    });
  }

  function renderImageLibrarySuggestionOptions(imageId, candidates) {
    if (!elements.imageLibraryTableBody) {
      return;
    }

    const wrap = elements.imageLibraryTableBody.querySelector(`[data-image-suggest-wrap="${Number(imageId)}"]`);
    if (!wrap) {
      return;
    }

    while (wrap.firstChild) {
      wrap.removeChild(wrap.firstChild);
    }

    if (!Array.isArray(candidates) || candidates.length === 0) {
      const note = document.createElement("span");
      note.textContent = "No candidates";
      wrap.appendChild(note);
      return;
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
  }

  async function handleImageLibrarySuggestMatch(imageId) {
    const resolvedImageId = Number(imageId || 0);
    if (!resolvedImageId) {
      return;
    }

    try {
      const payload = await apiRequest(`/api/v1/image-library/images/${resolvedImageId}/match-suggestions?limit=3`);
      const candidates = Array.isArray(payload?.data?.candidates) ? payload.data.candidates : [];
      renderImageLibrarySuggestionOptions(resolvedImageId, candidates);
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
      await Promise.all([loadUsers(), loadJigsaws(), loadLoans(), loadAuditEvents(), loadAiUsageDiagnostics(), loadImageLibraryImages()]);
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
      state.auditEvents = [];
      state.auditEventsMeta = null;
      state.jigsawThumbnailImages = [];
      state.jigsawImages = [];
      state.imageLibraryImages = [];
      state.imageLibraryFilterAssigned = true;
      state.imageLibraryFilterUnassigned = true;
      state.imageLibraryFilterTagSelections = {};
      state.aiUsageDiagnostics = null;
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
      closeUserEditor();
      renderJigsaws([]);
      closeJigsawEditor();
      renderLoans([]);
      renderJigsawImages([]);
      renderImageLibraryImages([]);
      renderDiaryEntries([]);
      renderAiUsageDiagnostics(null);
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
    const shouldShow = shouldShowBulkCreateFromUploadOption();
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

      const summary = `Embedding job #${job.id}: ${job.processed_items}/${job.total_items} processed, ${job.succeeded_items} succeeded, ${job.failed_items} failed.`;
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

      await Promise.all([loadImageLibraryImages(), loadDiaryEntriesForSelected(), loadAuditEvents()]);
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

  async function handleImageEmbeddingBackfillStart() {
    clearFeedback();
    clearImageEmbeddingBackfillProgress();

    try {
      const payload = await apiRequest("/api/v1/image-embeddings/backfill", {
        method: "POST",
        body: JSON.stringify({}),
      });
      const job = payload?.data?.job || null;
      if (!job?.id) {
        showFeedback("Could not queue image embedding backfill job.", true);
        return;
      }

      state.imageEmbeddingBackfillJobId = Number(job.id);
      setImageEmbeddingBackfillStatus(`Embedding backfill job #${job.id} queued.`);
      pollImageEmbeddingBackfillJobStatus(state.imageEmbeddingBackfillJobId);
    } catch (error) {
      showFeedback(error.message, true);
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
      let bulkCreateSummary = "";

      let metadataSuffix = "";
      if (metadataBackfilledCount > 0) {
        const skippedItems = Array.isArray(payload?.data?.skipped) ? payload.data.skipped : [];
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
      showFeedback(`Image library upload complete. Added ${createdCount} image(s), skipped ${skippedCount}.${metadataSuffix}${bulkCreateSummary}`);
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
      openJigsawEditor(jigsawId);
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

    const enrichButton = event.target.closest("[data-jigsaw-enrich]");
    if (enrichButton) {
      event.preventDefault();
      clearFeedback();

      const jigsawId = Number(enrichButton.getAttribute("data-jigsaw-enrich"));
      await enrichJigsawById(jigsawId);
      return;
    }

    const deleteButton = event.target.closest("[data-jigsaw-delete]");
    if (deleteButton) {
      event.preventDefault();
      clearFeedback();

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

      const entryId = Number(diaryEditButton.getAttribute("data-diary-edit"));
      beginDiaryEntryEdit(entryId);
      return;
    }

    const diaryDeleteButton = event.target.closest("[data-diary-delete]");
    if (diaryDeleteButton) {
      event.preventDefault();
      clearFeedback();

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

    const imageSuggestButton = event.target.closest("[data-image-suggest]");
    if (imageSuggestButton) {
      event.preventDefault();
      clearFeedback();

      const imageId = Number(imageSuggestButton.getAttribute("data-image-suggest"));
      await handleImageLibrarySuggestMatch(imageId);
      return;
    }

    const imageSuggestAssignButton = event.target.closest("[data-image-suggest-assign]");
    if (imageSuggestAssignButton) {
      event.preventDefault();
      clearFeedback();

      const imageId = Number(imageSuggestAssignButton.getAttribute("data-image-suggest-assign"));
      const jigsawId = Number(imageSuggestAssignButton.getAttribute("data-image-suggest-jigsaw-id") || "0");
      await handleImageLibraryAssignSuggested(imageId, jigsawId);
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

    const imageTagButton = event.target.closest("[data-image-tag-set]");
    if (imageTagButton) {
      event.preventDefault();
      clearFeedback();

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

      const imageId = Number(imageUnassignButton.getAttribute("data-image-unassign"));
      try {
        await apiRequest(`/api/v1/image-library/images/${imageId}/assign`, {
          method: "PATCH",
          body: JSON.stringify({ jigsaw_id: null }),
        });
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

      if (image && image.jigsaw_id) {
        const shouldDelete = window.confirm(
          "This image is assigned to a jigsaw. Delete it anyway? This cannot be undone.",
        );
        if (!shouldDelete) {
          return;
        }
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

  function handleDiaryEntryCancelEdit() {
    clearFeedback();
    resetDiaryEntryFormEditingState({ keepJigsawSelection: true });
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
    if (elements.imageBrowserFilterUnassigned) {
      elements.imageBrowserFilterUnassigned.checked = Boolean(state.imageBrowser.filterUnassigned);
    }
    if (elements.imageBrowserFilterBox) {
      elements.imageBrowserFilterBox.checked = Boolean(state.imageBrowser.filterBox);
    }
    if (elements.imageBrowserFilterReference) {
      elements.imageBrowserFilterReference.checked = Boolean(state.imageBrowser.filterReference);
    }
    if (elements.imageBrowserFilterCompleted) {
      elements.imageBrowserFilterCompleted.checked = Boolean(state.imageBrowser.filterCompleted);
    }
    if (elements.imageBrowserFilterInProgress) {
      elements.imageBrowserFilterInProgress.checked = Boolean(state.imageBrowser.filterInProgress);
    }
  }

  function syncImageBrowserFilterStateFromInputs() {
    state.imageBrowser.filterUnassigned = Boolean(elements.imageBrowserFilterUnassigned?.checked);
    state.imageBrowser.filterBox = Boolean(elements.imageBrowserFilterBox?.checked);
    state.imageBrowser.filterReference = Boolean(elements.imageBrowserFilterReference?.checked);
    state.imageBrowser.filterCompleted = Boolean(elements.imageBrowserFilterCompleted?.checked);
    state.imageBrowser.filterInProgress = Boolean(elements.imageBrowserFilterInProgress?.checked);
  }

  async function handleImageBrowserFilterChange() {
    const previousItemId = getCurrentImageBrowserItem()?.id || null;
    const previousIndex = state.imageBrowser.index;
    const hadPendingEdits = browserHasPendingEdits();
    const previousFilters = {
      unassigned: state.imageBrowser.filterUnassigned,
      box: state.imageBrowser.filterBox,
      reference: state.imageBrowser.filterReference,
      completed: state.imageBrowser.filterCompleted,
      inProgress: state.imageBrowser.filterInProgress,
    };
    syncImageBrowserFilterStateFromInputs();

    if (state.imageBrowser.isOpen && hadPendingEdits) {
      const willKeepCurrent = previousItemId ? setImageBrowserIndexByImageId(previousItemId) : false;
      if (!willKeepCurrent) {
        const shouldDiscard = window.confirm("Discard unsaved image edits and apply browser filters?");
        if (!shouldDiscard) {
          state.imageBrowser.filterUnassigned = previousFilters.unassigned;
          state.imageBrowser.filterBox = previousFilters.box;
          state.imageBrowser.filterReference = previousFilters.reference;
          state.imageBrowser.filterCompleted = previousFilters.completed;
          state.imageBrowser.filterInProgress = previousFilters.inProgress;
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

    if (elements.imageLibraryPagination) {
      elements.imageLibraryPagination.addEventListener("click", handlePaginationClick);
    }

    if (elements.diaryPagination) {
      elements.diaryPagination.addEventListener("click", handlePaginationClick);
    }

    if (elements.aiUsageRecentPagination) {
      elements.aiUsageRecentPagination.addEventListener("click", handlePaginationClick);
    }

    if (elements.auditPagination) {
      elements.auditPagination.addEventListener("click", handlePaginationClick);
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

    if (elements.imageBrowserFilterUnassigned) {
      elements.imageBrowserFilterUnassigned.addEventListener("change", handleImageBrowserFilterChange);
    }

    if (elements.imageBrowserFilterBox) {
      elements.imageBrowserFilterBox.addEventListener("change", handleImageBrowserFilterChange);
    }

    if (elements.imageBrowserFilterReference) {
      elements.imageBrowserFilterReference.addEventListener("change", handleImageBrowserFilterChange);
    }

    if (elements.imageBrowserFilterCompleted) {
      elements.imageBrowserFilterCompleted.addEventListener("change", handleImageBrowserFilterChange);
    }

    if (elements.imageBrowserFilterInProgress) {
      elements.imageBrowserFilterInProgress.addEventListener("change", handleImageBrowserFilterChange);
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

    if (elements.diaryEntriesTableBody) {
      elements.diaryEntriesTableBody.addEventListener("click", handleTableActions);
    }

    if (elements.imageLibraryTableBody) {
      elements.imageLibraryTableBody.addEventListener("click", handleTableActions);
    }

    if (elements.loansTableBody) {
      elements.loansTableBody.addEventListener("click", handleTableActions);
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
    state.diarySelectionTouchedByUser = false;
    setImageBrowserFilterInputsFromState();
    syncImageBrowserFilterStateFromInputs();
    attachEvents();
    updateSortableTableHeaders();
    renderBulkUploadFiles();
    syncBulkCreateFromUploadVisibility();
    const isAuthenticated = await refreshSession();
    if (isAuthenticated) {
      clearImageEmbeddingBackfillProgress();
      setImageEmbeddingBackfillStatus("");
      await Promise.all([loadUsers(), loadJigsaws(), loadLoans(), loadAuditEvents(), loadAiUsageDiagnostics(), loadImageLibraryImages()]);
      await Promise.all([loadJigsawImagesForSelected(), loadDiaryEntriesForSelected()]);
    } else {
      clearImageEmbeddingBackfillProgress();
      setImageEmbeddingBackfillStatus("");
      renderUsers([]);
      renderJigsaws([]);
      renderLoans([]);
      renderJigsawImages([]);
      renderImageLibraryImages([]);
      renderDiaryEntries([]);
      renderAuditEvents([]);
      renderAiUsageDiagnostics(null);
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
