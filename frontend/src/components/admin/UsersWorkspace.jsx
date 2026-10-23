import { useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { adminService } from "../../services/adminService";
import AdminPage, { AdminTable } from "./AdminPage";

function UserConfirmation({ selection, onClose, onConfirm, mutation }) {
  const dialog = useRef(null);
  const [reason, setReason] = useState("");
  return (
    <dialog
      ref={(node) => {
        dialog.current = node;
        if (node && !node.open) node.showModal();
      }}
      className="admin-dialog"
      onCancel={(event) => {
        if (mutation.isPending) event.preventDefault();
        else onClose();
      }}
      aria-labelledby="user-action-heading"
    >
      <h2 id="user-action-heading">{selection.label} account?</h2>
      <p>{selection.user.email}</p>
      {selection.action === "status" && (
        <label>
          Reason
          <textarea
            value={reason}
            onChange={(event) => setReason(event.target.value)}
            maxLength={500}
          />
        </label>
      )}
      {mutation.isError && <p role="alert">{mutation.error.message}</p>}
      <div className="admin-actions">
        <button
          className="admin-button"
          disabled={mutation.isPending}
          onClick={onClose}
        >
          Cancel
        </button>
        <button
          className="admin-button"
          disabled={mutation.isPending}
          onClick={() => onConfirm(reason)}
        >
          {mutation.isPending
            ? "Saving…"
            : `Confirm ${selection.label.toLowerCase()}`}
        </button>
      </div>
    </dialog>
  );
}

function userColumns(select) {
  return [
    {
      key: "email",
      label: "Account",
      render: (row) => (
        <>
          {row.first_name} {row.last_name}
          <small>{row.email}</small>
        </>
      ),
    },
    { key: "role", label: "Role" },
    {
      key: "is_active",
      label: "Status",
      render: (row) => (row.is_active ? "Active" : "Suspended"),
    },
    {
      key: "is_verified",
      label: "Verification",
      render: (row) => (row.is_verified ? "Verified" : "Unverified"),
    },
    { key: "total_bets", label: "Bets" },
    {
      key: "actions",
      label: "Actions",
      render: (row) => (
        <div className="admin-actions">
          {!row.is_verified && (
            <button
              className="admin-button"
              onClick={() =>
                select({ user: row, action: "verify", label: "Verify" })
              }
            >
              Verify
            </button>
          )}
          <button
            className="admin-button"
            onClick={() =>
              select({
                user: row,
                action: "status",
                label: row.is_active ? "Suspend" : "Activate",
              })
            }
          >
            {row.is_active ? "Suspend" : "Activate"}
          </button>
        </div>
      ),
    },
  ];
}

export default function UsersWorkspace() {
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);
  const [selection, setSelection] = useState(null);
  const [notice, setNotice] = useState("");
  const client = useQueryClient();
  const query = useQuery({
    queryKey: ["admin-users", { search, status, page }],
    queryFn: ({ signal }) =>
      adminService.users({ search, status, page, limit: 25 }, signal),
    retry: false,
  });
  const mutation = useMutation({
    mutationFn: (reason) =>
      adminService.updateUser(
        selection.user.id,
        selection.action,
        selection.action === "status"
          ? { is_active: !selection.user.is_active, reason }
          : undefined,
      ),
    onSuccess: () => {
      setNotice("Account updated successfully.");
      setSelection(null);
      client.invalidateQueries({ queryKey: ["admin-users"] });
      client.invalidateQueries({ queryKey: ["admin-audit-logs"] });
      client.invalidateQueries({ queryKey: ["admin-platform-metrics"] });
    },
  });
  const select = (value) => {
    mutation.reset();
    setSelection(value);
  };
  return (
    <AdminPage
      title="User management."
      description="Search registered accounts and manage verified backend account states."
      query={query}
    >
      {notice && (
        <p role="status" className="admin-notice">
          {notice}
        </p>
      )}
      <div className="admin-toolbar">
        <label>
          Search users
          <input
            value={search}
            onChange={(event) => {
              setSearch(event.target.value);
              setPage(1);
            }}
            placeholder="Email or name"
          />
        </label>
        <label>
          Status
          <select
            value={status}
            onChange={(event) => {
              setStatus(event.target.value);
              setPage(1);
            }}
          >
            <option value="">All accounts</option>
            <option value="active">Active</option>
            <option value="suspended">Suspended</option>
          </select>
        </label>
      </div>
      {query.data && (
        <>
          <p className="admin-updated">{query.data.total} matching accounts</p>
          <AdminTable
            columns={userColumns(select)}
            rows={query.data.users}
            empty="No accounts match these filters."
          />
          <div className="admin-toolbar">
            <button
              className="admin-button"
              disabled={page <= 1}
              onClick={() => setPage(page - 1)}
            >
              Previous
            </button>
            <span>
              Page {page} of {Math.max(1, query.data.total_pages)}
            </span>
            <button
              className="admin-button"
              disabled={page >= query.data.total_pages}
              onClick={() => setPage(page + 1)}
            >
              Next
            </button>
          </div>
        </>
      )}
      {selection && (
        <UserConfirmation
          key={selection.user.id + selection.action}
          selection={selection}
          mutation={mutation}
          onClose={() => setSelection(null)}
          onConfirm={(reason) => mutation.mutate(reason)}
        />
      )}
    </AdminPage>
  );
}
