import { useState } from "react";

const tabs = [
  {
    type: "all",
    label: "All",
    icon: null,
  },
  {
    type: "customer",
    label: "Customers",
    icon: "fa-user",
  },
  {
    type: "vehicle",
    label: "Vehicles",
    icon: "fa-car",
  },
  {
    type: "service",
    label: "Services",
    icon: "fa-concierge-bell",
  },
  {
    type: "product",
    label: "Products",
    icon: "fa-box",
  },
  {
    type: "supplier",
    label: "Suppliers",
    icon: "fa-truck",
  },
];

function buildUrl(itemType, search = "", page = null) {
  const params = new URLSearchParams();

  params.set("type", itemType);

  if (search) {
    params.set("q", search);
  }

  if (page) {
    params.set("page", page);
  }

  return `${window.location.pathname}?${params.toString()}`;
}

async function readJsonResponse(response) {
  try {
    return await response.json();
  } catch {
    if (response.redirected) {
      return {
        success: false,
        error: "Your session may have expired. Please sign in again.",
      };
    }

    return {
      success: false,
      error: "The server returned an unexpected response.",
    };
  }
}

function displayToast(message, type = "success") {
  if (typeof window.showToast === "function") {
    window.showToast(message, type);
    return;
  }

  window.alert(message);
}

function Modal({ children, onClose }) {
  return (
    <>
      <div
        className="modal fade show d-block"
        tabIndex="-1"
        role="dialog"
        aria-modal="true"
        onMouseDown={onClose}
      >
        <div
          className="modal-dialog"
          role="document"
          onMouseDown={(event) => event.stopPropagation()}
        >
          {children}
        </div>
      </div>

      <div className="modal-backdrop fade show" />
    </>
  );
}

export default function TrashPage({ data, csrfToken }) {
  const [selectedItem, setSelectedItem] = useState(null);
  const [modalType, setModalType] = useState(null);

  const [restoreError, setRestoreError] = useState("");
  const [purgeError, setPurgeError] = useState("");

  const [confirmation, setConfirmation] = useState("");
  const [password, setPassword] = useState("");

  const [submitting, setSubmitting] = useState(false);

  const openRestoreModal = (item) => {
    setSelectedItem(item);
    setRestoreError("");
    setModalType("restore");
  };

  const openPurgeModal = (item) => {
    setSelectedItem(item);
    setPurgeError("");
    setConfirmation("");
    setPassword("");
    setModalType("purge");
  };

  const closeModal = () => {
    if (submitting) {
      return;
    }

    setModalType(null);
    setSelectedItem(null);
    setRestoreError("");
    setPurgeError("");
  };

  const restoreItem = async () => {
    if (!selectedItem) {
      return;
    }

    setRestoreError("");
    setSubmitting(true);

    try {
      const response = await fetch(selectedItem.restoreUrl, {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "X-CSRFToken": csrfToken,
          Accept: "application/json",
        },
      });

      const result = await readJsonResponse(response);

      if (!response.ok || !result.success) {
        setRestoreError(result.error || "The item could not be restored.");
        return;
      }

      displayToast(result.message, "success");

      window.setTimeout(() => {
        window.location.reload();
      }, 600);
    } catch (error) {
      console.error(error);
      setRestoreError("A network error occurred. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  const purgeItem = async () => {
    if (!selectedItem) {
      return;
    }

    setPurgeError("");

    if (confirmation.trim() !== "DELETE") {
      setPurgeError('Type "DELETE" exactly to confirm.');
      return;
    }

    if (!password.trim()) {
      setPurgeError("Password required.");
      return;
    }

    const formData = new FormData();
    formData.append("confirm", confirmation.trim());
    formData.append("password", password);

    setSubmitting(true);

    try {
      const response = await fetch(selectedItem.purgeUrl, {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "X-CSRFToken": csrfToken,
          Accept: "application/json",
        },
        body: formData,
      });

      const result = await readJsonResponse(response);

      if (!response.ok || !result.success) {
        setPurgeError(
          result.error || "The item could not be permanently deleted."
        );
        return;
      }

      displayToast(result.message, "success");

      window.setTimeout(() => {
        window.location.reload();
      }, 600);
    } catch (error) {
      console.error(error);
      setPurgeError("A network error occurred. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <>
      <div className="warning-banner">
        <i className="fas fa-shield-alt me-2" />

        <strong>Super Admin Only:</strong>{" "}
        Items in trash can be restored or permanently deleted. Permanent
        deletion is only allowed if the item has no historical financial
        records.
      </div>

      <div className="card">
        <div className="card-header">
          <strong>
            <i className="fas fa-trash me-2 aq-text-danger" />
            Deleted Items
          </strong>
        </div>

        <div className="card-body">
          <div className="trash-tabs">
            {tabs.map((tab) => (
              <a
                key={tab.type}
                href={buildUrl(tab.type, data.search)}
                className={`trash-tab ${
                  data.itemType === tab.type ? "active" : ""
                }`}
              >
                {tab.icon && <i className={`fas ${tab.icon} me-1`} />}

                {tab.label}

                <span className="count">{data.counts[tab.type] ?? 0}</span>
              </a>
            ))}
          </div>

          <form method="GET" className="mb-3">
            <input type="hidden" name="type" value={data.itemType} />

            <div className="input-group">
              <input
                type="text"
                name="q"
                className="form-control"
                placeholder="Search deleted items..."
                defaultValue={data.search}
              />

              <button type="submit" className="btn btn-primary">
                <i className="fas fa-search me-1" />
                Search
              </button>

              {data.search && (
                <a
                  href={buildUrl(data.itemType)}
                  className="btn btn-outline-secondary"
                >
                  Clear
                </a>
              )}
            </div>
          </form>

          {data.items.length > 0 ? (
            <>
              <div>
                {data.items.map((item) => (
                  <div
                    className="trash-item"
                    key={`${item.type}-${item.id}`}
                  >
                    <div className={`trash-icon ${item.color}`}>
                      <i className={`fas ${item.icon}`} />
                    </div>

                    <div className="trash-info">
                      <div className="trash-name">{item.name}</div>

                      <div className="trash-meta">
                        <span className="badge bg-light text-dark border me-1">
                          {item.typeLabel}
                        </span>

                        {item.meta}
                      </div>

                      <div className="trash-deleted">
                        <i className="fas fa-clock me-1" />

                        Deleted {item.deletedAt}

                        {item.deletedBy && ` by ${item.deletedBy}`}
                      </div>
                    </div>

                    <div className="trash-actions">
                      <button
                        type="button"
                        className="btn btn-sm btn-success"
                        onClick={() => openRestoreModal(item)}
                      >
                        <i className="fas fa-undo me-1" />
                        Restore
                      </button>

                      <button
                        type="button"
                        className="btn btn-sm btn-outline-danger"
                        onClick={() => openPurgeModal(item)}
                      >
                        <i className="fas fa-times me-1" />
                        Delete Forever
                      </button>
                    </div>
                  </div>
                ))}
              </div>

              {data.pagination.hasOtherPages && (
                <nav className="mt-3" aria-label="Trash pagination">
                  <ul className="pagination pagination-sm justify-content-center">
                    {data.pagination.hasPrevious && (
                      <li className="page-item">
                        <a
                          className="page-link"
                          href={buildUrl(
                            data.itemType,
                            data.search,
                            data.pagination.previousPage
                          )}
                        >
                          Previous
                        </a>
                      </li>
                    )}

                    <li className="page-item disabled">
                      <span className="page-link">
                        Page {data.pagination.number}
                      </span>
                    </li>

                    {data.pagination.hasNext && (
                      <li className="page-item">
                        <a
                          className="page-link"
                          href={buildUrl(
                            data.itemType,
                            data.search,
                            data.pagination.nextPage
                          )}
                        >
                          Next
                        </a>
                      </li>
                    )}
                  </ul>
                </nav>
              )}
            </>
          ) : (
            <div className="text-center py-5">
              <i className="fas fa-check-circle fa-3x text-success mb-3" />

              <h5 className="text-muted">Trash is empty</h5>

              <p className="text-muted">No deleted items to show.</p>
            </div>
          )}
        </div>
      </div>

      {modalType === "restore" && selectedItem && (
        <Modal onClose={closeModal}>
          <div className="modal-content">
            <div className="modal-header bg-success text-white">
              <h5 className="modal-title">
                <i className="fas fa-undo me-2" />
                Restore Item
              </h5>

              <button
                type="button"
                className="btn-close btn-close-white"
                aria-label="Close"
                disabled={submitting}
                onClick={closeModal}
              />
            </div>

            <div className="modal-body">
              <p>
                Restore <strong>{selectedItem.name}</strong>?
              </p>

              <p className="text-muted">
                The item will be moved back to active records.
              </p>

              {restoreError && (
                <div className="alert alert-danger">{restoreError}</div>
              )}
            </div>

            <div className="modal-footer">
              <button
                type="button"
                className="btn btn-secondary"
                disabled={submitting}
                onClick={closeModal}
              >
                Cancel
              </button>

              <button
                type="button"
                className="btn btn-success"
                disabled={submitting}
                onClick={restoreItem}
              >
                <i className="fas fa-undo me-1" />

                {submitting ? "Restoring..." : "Restore"}
              </button>
            </div>
          </div>
        </Modal>
      )}

      {modalType === "purge" && selectedItem && (
        <Modal onClose={closeModal}>
          <div className="modal-content">
            <div className="modal-header bg-danger text-white">
              <h5 className="modal-title">
                <i className="fas fa-exclamation-triangle me-2" />
                Permanent Delete
              </h5>

              <button
                type="button"
                className="btn-close btn-close-white"
                aria-label="Close"
                disabled={submitting}
                onClick={closeModal}
              />
            </div>

            <div className="modal-body">
              <div className="alert alert-danger">
                <strong>⚠ CRITICAL WARNING:</strong> This action cannot be
                undone.
                <br />
                The item will be permanently removed from the database.
              </div>

              <p>
                Delete <strong>{selectedItem.name}</strong> forever?
              </p>

              <div className="mb-3">
                <label htmlFor="purge-confirm" className="form-label fw-semibold">
                  Type "DELETE" to confirm
                </label>

                <input
                  id="purge-confirm"
                  type="text"
                  className="form-control"
                  placeholder="DELETE"
                  value={confirmation}
                  disabled={submitting}
                  onChange={(event) => setConfirmation(event.target.value)}
                />
              </div>

              <div className="mb-3">
                <label
                  htmlFor="purge-password"
                  className="form-label fw-semibold"
                >
                  Your Password
                </label>

                <input
                  id="purge-password"
                  type="password"
                  className="form-control"
                  placeholder="Enter your password"
                  autoComplete="current-password"
                  value={password}
                  disabled={submitting}
                  onChange={(event) => setPassword(event.target.value)}
                />
              </div>

              {purgeError && (
                <div className="alert alert-danger">{purgeError}</div>
              )}
            </div>

            <div className="modal-footer">
              <button
                type="button"
                className="btn btn-secondary"
                disabled={submitting}
                onClick={closeModal}
              >
                Cancel
              </button>

              <button
                type="button"
                className="btn btn-danger"
                disabled={submitting}
                onClick={purgeItem}
              >
                <i className="fas fa-times me-1" />

                {submitting ? "Deleting..." : "Delete Forever"}
              </button>
            </div>
          </div>
        </Modal>
      )}
    </>
  );
}