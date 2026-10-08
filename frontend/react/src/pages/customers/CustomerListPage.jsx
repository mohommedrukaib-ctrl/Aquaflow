import { useEffect, useRef, useState } from "react";

function notify(message, type = "success") {
  if (typeof window.showToast === "function") {
    window.showToast(message, type);
  } else {
    window.alert(message);
  }
}

function makeListUrl(listUrl, search, status, page = null) {
  const url = new URL(listUrl, window.location.origin);
  url.search = "";

  if (search.trim()) {
    url.searchParams.set("q", search.trim());
  }

  if (status) {
    url.searchParams.set("status", status);
  }

  if (page) {
    url.searchParams.set("page", page);
  }

  return `${url.pathname}${url.search}`;
}

async function readJson(response) {
  try {
    return await response.json();
  } catch {
    return {
      success: false,
      error: response.redirected
        ? "Your session may have expired. Please sign in again."
        : "The server returned an unexpected response.",
    };
  }
}

function getFieldErrors(errors, field) {
  const value = errors?.[field];

  if (Array.isArray(value)) {
    return value.map(String);
  }

  return value ? [String(value)] : [];
}

function FieldError({ messages }) {
  if (!messages.length) {
    return null;
  }

  return <div className="invalid-feedback">{messages.join(" ")}</div>;
}

function showBootstrapModal(ref) {
  if (!ref.current || !window.bootstrap?.Modal) {
    notify("The modal could not be opened. Please refresh the page.", "error");
    return;
  }

  window.bootstrap.Modal.getOrCreateInstance(ref.current).show();
}

export default function CustomerListPage({ data, csrfToken }) {
  const [search, setSearch] = useState(data.search || "");
  const [status, setStatus] = useState(data.status || "active");

  const [formErrors, setFormErrors] = useState({});
  const [formError, setFormError] = useState("");
  const [saving, setSaving] = useState(false);

  const [selectedCustomer, setSelectedCustomer] = useState(null);
  const [deleteError, setDeleteError] = useState("");
  const [deleting, setDeleting] = useState(false);

  const searchTimer = useRef(null);
  const addModalRef = useRef(null);
  const deleteModalRef = useRef(null);
  const addFormRef = useRef(null);

  useEffect(() => {
    const addModal = addModalRef.current;
    const deleteModal = deleteModalRef.current;

    const resetAddForm = () => {
      addFormRef.current?.reset();
      setFormErrors({});
      setFormError("");
      setSaving(false);
    };

    const resetDeleteModal = () => {
      setSelectedCustomer(null);
      setDeleteError("");
      setDeleting(false);
    };

    addModal?.addEventListener("hidden.bs.modal", resetAddForm);
    deleteModal?.addEventListener("hidden.bs.modal", resetDeleteModal);

    return () => {
      addModal?.removeEventListener("hidden.bs.modal", resetAddForm);
      deleteModal?.removeEventListener("hidden.bs.modal", resetDeleteModal);
      window.clearTimeout(searchTimer.current);
    };
  }, []);

  useEffect(() => {
    if (selectedCustomer && deleteModalRef.current) {
      showBootstrapModal(deleteModalRef);
    }
  }, [selectedCustomer]);

  const goToList = (nextSearch = search, nextStatus = status, page = null) => {
    window.location.assign(
      makeListUrl(data.listUrl, nextSearch, nextStatus, page)
    );
  };

  const handleSearchChange = (event) => {
    const value = event.target.value;
    setSearch(value);

    window.clearTimeout(searchTimer.current);

    searchTimer.current = window.setTimeout(() => {
      goToList(value, status);
    }, 450);
  };

  const handleSearchSubmit = (event) => {
    event.preventDefault();
    window.clearTimeout(searchTimer.current);
    goToList(search, status);
  };

  const handleStatusChange = (event) => {
    const nextStatus = event.target.value;
    setStatus(nextStatus);
    window.clearTimeout(searchTimer.current);
    goToList(search, nextStatus);
  };

  const openAddCustomer = () => {
    setFormErrors({});
    setFormError("");
    addFormRef.current?.reset();
    showBootstrapModal(addModalRef);
  };

  const submitCustomerForm = async (event) => {
    event.preventDefault();

    const form = addFormRef.current;
    if (!form) return;

    setFormErrors({});
    setFormError("");
    setSaving(true);

    try {
      const response = await fetch(data.createUrl, {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "X-CSRFToken": csrfToken,
          "X-Requested-With": "XMLHttpRequest",
          Accept: "application/json",
        },
        body: new FormData(form),
      });

      const result = await readJson(response);

      if (!response.ok || !result.success) {
        if (result.errors) {
          const { __all__: nonFieldErrors, ...fieldErrors } = result.errors;

          setFormErrors(fieldErrors);

          if (nonFieldErrors) {
            setFormError(getFieldErrors(
              { error: nonFieldErrors },
              "error"
            ).join(" "));
          }
        } else {
          setFormError(result.error || "Failed to save the customer.");
        }

        return;
      }

      window.bootstrap?.Modal
        .getInstance(addModalRef.current)
        ?.hide();

      notify(result.message, "success");
      window.setTimeout(() => window.location.reload(), 800);
    } catch (error) {
      console.error(error);
      setFormError("Network error. Please try again.");
    } finally {
      setSaving(false);
    }
  };

  const openDeleteCustomer = (customer) => {
    setDeleteError("");
    setSelectedCustomer(customer);
  };

  const deleteCustomer = async () => {
    if (!selectedCustomer) return;

    setDeleting(true);
    setDeleteError("");

    try {
      const response = await fetch(selectedCustomer.deleteUrl, {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "X-CSRFToken": csrfToken,
          "X-Requested-With": "XMLHttpRequest",
          Accept: "application/json",
        },
      });

      const result = await readJson(response);

      if (!response.ok || !result.success) {
        setDeleteError(result.error || "The customer could not be deleted.");
        return;
      }

      window.bootstrap?.Modal
        .getInstance(deleteModalRef.current)
        ?.hide();

      notify(result.message, "success");
      window.setTimeout(() => window.location.reload(), 800);
    } catch (error) {
      console.error(error);
      setDeleteError("Network error. Please try again.");
    } finally {
      setDeleting(false);
    }
  };

  const clearSearchUrl = makeListUrl(data.listUrl, "", "active");
  const customers = data.customers || [];
  const page = data.pagination;

  return (
    <>
      <div className="aq-panel">
        <div className="aq-panel-head">
          <div className="aq-chips">
            <span className="aq-chip pri">
              <i className="fas fa-users" aria-hidden="true" /> Total{" "}
              <b>{data.totalCount}</b>
            </span>
          </div>

          {data.canCreate && (
            <button
              type="button"
              className="btn btn-primary btn-sm"
              onClick={openAddCustomer}
            >
              <i className="fas fa-plus me-1" />
              Add Customer
            </button>
          )}
        </div>

        <form className="aq-toolbar" onSubmit={handleSearchSubmit}>
          <div className="input-group" style={{ width: 300 }}>
            <span className="input-group-text">
              <i className="fas fa-search" />
            </span>

            <input
              type="text"
              name="q"
              className="form-control"
              placeholder="Name, phone, email, code…"
              value={search}
              onChange={handleSearchChange}
            />

            {search && (
              <a
                href={clearSearchUrl}
                className="btn btn-outline-secondary btn-sm"
                aria-label="Clear search"
              >
                <i className="fas fa-times" />
              </a>
            )}
          </div>

          <select
            name="status"
            className="form-select"
            style={{ width: 130 }}
            value={status}
            onChange={handleStatusChange}
          >
            <option value="all">All Status</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
          </select>

          <button type="submit" className="btn btn-outline-primary btn-sm">
            <i className="fas fa-filter me-1" />
            Filter
          </button>
        </form>

        <div className="aq-panel-body flush">
          {customers.length > 0 ? (
            <>
              <div className="aq-table-scroll">
                <table className="table table-hover">
                  <thead>
                    <tr>
                      <th>Code</th>
                      <th>Name</th>
                      <th>Phone</th>
                      <th>Email</th>
                      <th className="num">Vehicles</th>
                      <th className="num">Points</th>
                      <th>Status</th>
                      <th className="nowrap">Joined</th>
                      <th style={{ width: 80 }} />
                    </tr>
                  </thead>

                  <tbody>
                    {customers.map((customer) => (
                      <tr key={customer.id}>
                        <td className="nowrap">
                          <code>{customer.customerCode}</code>
                        </td>

                        <td>
                          <a
                            href={customer.detailUrl}
                            className="fw-semibold"
                          >
                            {customer.name}
                          </a>
                        </td>

                        <td className="nowrap">
                          {customer.phone ? (
                            <a href={`tel:${customer.phone}`}>
                              {customer.phone}
                            </a>
                          ) : (
                            <span className="text-muted">—</span>
                          )}
                        </td>

                        <td title={customer.email}>
                          {customer.emailDisplay}
                        </td>

                        <td className="num">{customer.vehicleCount}</td>
                        <td className="num">{customer.loyaltyPoints}</td>

                        <td>
                          <span className={customer.statusClass}>
                            {customer.statusDisplay}
                          </span>
                        </td>

                        <td className="nowrap text-muted">
                          {customer.createdAt}
                        </td>

                        <td className="nowrap text-end">
                          <a
                            href={customer.detailUrl}
                            className="btn btn-sm btn-outline-primary btn-icon"
                            title="View"
                            aria-label={`View ${customer.name}`}
                          >
                            <i className="fas fa-eye" />
                          </a>

                          {data.canEdit && (
                            <a
                              href={customer.editUrl}
                              className="btn btn-sm btn-outline-secondary btn-icon"
                              title="Edit"
                              aria-label={`Edit ${customer.name}`}
                            >
                              <i className="fas fa-pen" />
                            </a>
                          )}

                          {data.canDelete && (
                            <button
                              type="button"
                              className="btn btn-sm btn-outline-danger btn-icon"
                              title="Delete"
                              aria-label={`Delete ${customer.name}`}
                              onClick={() => openDeleteCustomer(customer)}
                            >
                              <i className="fas fa-trash" />
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="aq-pagebar">
                <span>
                  {page.recordCount ?? data.totalCount} record
                  {(page.recordCount ?? data.totalCount) === 1 ? "" : "s"} ·
                  Page {page.number}/{page.numPages}
                </span>

                {page.hasOtherPages && (
                  <ul className="pagination pagination-sm mb-0">
                    {page.hasPrevious && (
                      <li className="page-item">
                        <a
                          className="page-link"
                          href={makeListUrl(
                            data.listUrl,
                            search,
                            status,
                            page.previousPage
                          )}
                          aria-label="Previous page"
                        >
                          ‹
                        </a>
                      </li>
                    )}

                    <li className="page-item disabled">
                      <span className="page-link">{page.number}</span>
                    </li>

                    {page.hasNext && (
                      <li className="page-item">
                        <a
                          className="page-link"
                          href={makeListUrl(
                            data.listUrl,
                            search,
                            status,
                            page.nextPage
                          )}
                          aria-label="Next page"
                        >
                          ›
                        </a>
                      </li>
                    )}
                  </ul>
                )}
              </div>
            </>
          ) : (
            <div className="aq-empty">
              <i className="fas fa-users" aria-hidden="true" />
              <h5>No customers found</h5>

              {search ? (
                <>
                  <p>
                    No results for <strong>"{search}"</strong>
                  </p>
                  <a
                    href={clearSearchUrl}
                    className="btn btn-sm btn-outline-secondary"
                  >
                    Clear Search
                  </a>
                </>
              ) : (
                data.canCreate && (
                  <button
                    type="button"
                    className="btn btn-sm btn-primary"
                    onClick={openAddCustomer}
                  >
                    <i className="fas fa-plus me-1" />
                    Add First Customer
                  </button>
                )
              )}
            </div>
          )}
        </div>
      </div>

      {/* Add customer modal */}
      <div
        className="modal fade"
        ref={addModalRef}
        tabIndex="-1"
        aria-labelledby="addCustomerModalTitle"
        aria-hidden="true"
      >
        <div className="modal-dialog modal-lg">
          <div className="modal-content">
            <div className="modal-header">
              <h5 className="modal-title" id="addCustomerModalTitle">
                <i className="fas fa-user-plus me-2" />
                Add New Customer
              </h5>
              <button
                type="button"
                className="btn-close"
                data-bs-dismiss="modal"
                aria-label="Close"
              />
            </div>

            <div className="modal-body">
              <form
                id="addCustomerForm"
                ref={addFormRef}
                noValidate
                onSubmit={submitCustomerForm}
              >
                <div className="row g-3">
                  <div className="col-md-12">
                    <label
                      htmlFor="customer-name"
                      className="form-label fw-semibold text-dark"
                    >
                      Full Name <span className="text-danger">*</span>
                    </label>
                    <input
                      id="customer-name"
                      type="text"
                      name="name"
                      className={`form-control ${
                        getFieldErrors(formErrors, "name").length
                          ? "is-invalid"
                          : ""
                      }`}
                      placeholder="Customer name"
                      required
                    />
                    <FieldError messages={getFieldErrors(formErrors, "name")} />
                  </div>

                  <div className="col-md-6">
                    <label
                      htmlFor="customer-phone"
                      className="form-label fw-semibold text-dark"
                    >
                      Phone Number <span className="text-danger">*</span>
                    </label>
                    <input
                      id="customer-phone"
                      type="text"
                      name="phone"
                      className={`form-control ${
                        getFieldErrors(formErrors, "phone").length
                          ? "is-invalid"
                          : ""
                      }`}
                      placeholder="Primary phone"
                      required
                    />
                    <FieldError messages={getFieldErrors(formErrors, "phone")} />
                  </div>

                  <div className="col-md-6">
                    <label
                      htmlFor="customer-phone2"
                      className="form-label fw-semibold text-dark"
                    >
                      Secondary Phone
                    </label>
                    <input
                      id="customer-phone2"
                      type="text"
                      name="phone2"
                      className="form-control"
                      placeholder="Optional"
                    />
                  </div>

                  <div className="col-md-6">
                    <label
                      htmlFor="customer-email"
                      className="form-label fw-semibold text-dark"
                    >
                      Email
                    </label>
                    <input
                      id="customer-email"
                      type="email"
                      name="email"
                      className={`form-control ${
                        getFieldErrors(formErrors, "email").length
                          ? "is-invalid"
                          : ""
                      }`}
                      placeholder="Optional"
                    />
                    <FieldError messages={getFieldErrors(formErrors, "email")} />
                  </div>

                  <div className="col-md-6">
                    <label
                      htmlFor="customer-status"
                      className="form-label fw-semibold text-dark"
                    >
                      Status
                    </label>
                    <select
                      id="customer-status"
                      name="status"
                      className="form-select"
                      defaultValue="active"
                    >
                      <option value="active">Active</option>
                      <option value="inactive">Inactive</option>
                    </select>
                  </div>

                  <div className="col-md-12">
                    <label
                      htmlFor="customer-address"
                      className="form-label fw-semibold text-dark"
                    >
                      Address
                    </label>
                    <textarea
                      id="customer-address"
                      name="address"
                      rows="2"
                      className="form-control"
                      placeholder="Optional"
                    />
                  </div>
                </div>

                {formError && (
                  <div className="alert alert-danger mt-3" role="alert">
                    {formError}
                  </div>
                )}

                <div className="mt-4 d-flex justify-content-end gap-2">
                  <button
                    type="button"
                    className="btn btn-secondary"
                    data-bs-dismiss="modal"
                    disabled={saving}
                  >
                    Cancel
                  </button>

                  <button
                    type="submit"
                    className="btn btn-primary"
                    disabled={saving}
                  >
                    <i
                      className={`fas ${
                        saving ? "fa-spinner fa-spin" : "fa-save"
                      } me-1`}
                    />
                    {saving ? "Saving…" : "Save Customer"}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      </div>

      {/* Delete confirmation modal */}
      <div
        className="modal fade"
        ref={deleteModalRef}
        tabIndex="-1"
        aria-labelledby="deleteCustomerModalTitle"
        aria-hidden="true"
      >
        <div className="modal-dialog modal-sm">
          <div className="modal-content">
            <div className="modal-header">
              <h5
                className="modal-title text-danger"
                id="deleteCustomerModalTitle"
              >
                <i className="fas fa-triangle-exclamation me-2" />
                Confirm Delete
              </h5>
              <button
                type="button"
                className="btn-close"
                data-bs-dismiss="modal"
                aria-label="Close"
                disabled={deleting}
              />
            </div>

            <div className="modal-body">
              <p className="mb-1">
                Delete <strong>{selectedCustomer?.name}</strong>?
              </p>

              <p className="text-muted mb-0" style={{ fontSize: 10.5 }}>
                Moved to Trash. Restorable by Super Admin.
              </p>

              {deleteError && (
                <div className="alert alert-danger mt-3 mb-0" role="alert">
                  {deleteError}
                </div>
              )}
            </div>

            <div className="modal-footer">
              <button
                type="button"
                className="btn btn-sm btn-secondary"
                data-bs-dismiss="modal"
                disabled={deleting}
              >
                Cancel
              </button>

              <button
                type="button"
                className="btn btn-sm btn-danger"
                onClick={deleteCustomer}
                disabled={deleting}
              >
                <i
                  className={`fas ${
                    deleting ? "fa-spinner fa-spin" : "fa-trash"
                  } me-1`}
                />
                {deleting ? "Deleting…" : "Delete"}
              </button>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}