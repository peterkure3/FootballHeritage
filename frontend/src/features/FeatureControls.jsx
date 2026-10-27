import {
  Search,
  SlidersHorizontal,
  Users,
  ShieldAlert,
  Wrench,
  Layers3,
  X,
} from "lucide-react";

function RoleRules({ flag, roles, busy, confirm }) {
  return (
    <fieldset className="feature-role-rules">
      <legend>Role availability</legend>
      {["guest", "user", "admin", "superadmin"].map((role) => (
        <label key={role}>
          <input
            type="checkbox"
            disabled={busy}
            checked={
              roles.find((rule) => rule.key === flag.key && rule.role === role)
                ?.enabled ?? flag.default_enabled
            }
            onChange={(e) =>
              confirm(
                `/admin/features/${flag.key}/roles/${role}`,
                { enabled: e.target.checked },
                `Change ${role} access to ${flag.key}`,
              )
            }
          />
          {role}
        </label>
      ))}
    </fieldset>
  );
}

function UserOverride({ flag, overrides, selectedUser, busy, confirm }) {
  const value = overrides[flag.key];
  return (
    <label>
      Selected user override
      <select
        disabled={busy}
        value={value === undefined ? "inherit" : String(value)}
        onChange={(e) =>
          confirm(
            `/admin/users/${selectedUser}/features/${flag.key}`,
            {
              enabled:
                e.target.value === "inherit" ? null : e.target.value === "true",
            },
            `Change selected user access to ${flag.key}`,
          )
        }
      >
        <option value="inherit">Inherit</option>
        <option value="false">Restricted</option>
        <option value="true">Allowed within global and role rules</option>
      </select>
    </label>
  );
}

function FeatureCard({ flag, roles, overrides, selectedUser, busy, confirm }) {
  const maintenance = flag.key === "maintenance";
  return (
    <article
      className={`feature-card${flag.emergency_disabled ? " is-restricted" : ""}`}
    >
      <div className="feature-card-top">
        <span className="feature-category">{flag.category}</span>
        <FeatureStatus flag={flag} />
      </div>
      <h2>{flag.key.replaceAll("_", " ")}</h2>
      <p className="feature-description">{flag.description}</p>
      <div className="feature-card-controls">
        <label className="feature-toggle-row">
          <span>{maintenance ? "Maintenance active" : "Globally enabled"}</span>
          <span className="feature-switch-control">
            <input
              className="feature-switch"
              type="checkbox"
              checked={flag.enabled}
              disabled={busy}
              onChange={(e) =>
                confirm(
                  `/admin/features/${flag.key}`,
                  { enabled: e.target.checked },
                  `Change global availability for ${flag.key}`,
                )
              }
            />
            <span className="feature-switch-track" aria-hidden="true" />
          </span>
        </label>
        <label className="feature-toggle-row emergency">
          <span>
            <ShieldAlert size={15} aria-hidden="true" /> Emergency restriction
          </span>
          <span className="feature-switch-control">
            <input
              className="feature-switch"
              type="checkbox"
              checked={flag.emergency_disabled}
              disabled={busy}
              onChange={(e) =>
                confirm(
                  `/admin/features/${flag.key}`,
                  { emergency_disabled: e.target.checked },
                  `Change emergency restriction for ${flag.key}`,
                )
              }
            />
            <span className="feature-switch-track" aria-hidden="true" />
          </span>
        </label>
      </div>
      {!maintenance && (
        <FeatureAvailability
          flag={flag}
          roles={roles}
          overrides={overrides}
          selectedUser={selectedUser}
          busy={busy}
          confirm={confirm}
        />
      )}
    </article>
  );
}

function FeatureAvailability(props) {
  const { flag, selectedUser, busy, confirm } = props;
  return (
    <>
      <label className="feature-maintenance-rule">
        <input
          type="checkbox"
          checked={flag.maintenance_allowed}
          disabled={busy}
          onChange={(e) =>
            confirm(
              `/admin/features/${flag.key}`,
              { maintenance_allowed: e.target.checked },
              `Change maintenance access for ${flag.key}`,
            )
          }
        />
        <span>Available during maintenance</span>
        <Wrench size={14} aria-hidden="true" />
      </label>
      <RoleRules {...props} />
      {selectedUser && <UserOverride {...props} />}
    </>
  );
}

function matchesFeature(flag, search, category) {
  if (category && flag.category !== category) return false;
  return `${flag.key} ${flag.key.replaceAll("_", " ")} ${flag.description}`
    .toLowerCase()
    .includes(search.toLowerCase());
}

export function FeatureGrid({
  features,
  search,
  category,
  loading,
  failed,
  clearFilters,
  ...props
}) {
  const visible = features.filter((flag) =>
    matchesFeature(flag, search, category),
  );
  return (
    <section
      className="feature-catalog"
      aria-label="Feature controls"
      aria-busy={loading}
    >
      <div className="feature-section-heading">
        <div>
          <SlidersHorizontal size={18} aria-hidden="true" />
          <h2>Feature controls</h2>
          <span className="feature-count">
            {loading || failed ? "—" : visible.length}
          </span>
        </div>
        <p>Availability, roles & exceptions</p>
      </div>
      <div className="feature-grid">
        {visible.map((flag) => (
          <FeatureCard key={flag.key} flag={flag} {...props} />
        ))}
      </div>
      {!loading && !failed && visible.length === 0 && (
        <div className="feature-empty">
          <Layers3 size={28} aria-hidden="true" />
          <h3>
            {features.length
              ? "No matching features"
              : "No features configured"}
          </h3>
          <p>
            {features.length
              ? "Try another search or category to find a feature."
              : "Feature controls will appear here when they are available."}
          </p>
          {(search || category) && (
            <button className="admin-button" onClick={clearFilters}>
              Clear filters
            </button>
          )}
        </div>
      )}
    </section>
  );
}

export function FeatureFilters({
  features,
  search,
  setSearch,
  category,
  setCategory,
  userSearch,
  setUserSearch,
  selectedUser,
  setSelectedUser,
  users,
  usersLoading,
}) {
  return (
    <div className="feature-filter-panel">
      <div className="feature-filters">
        <label>
          Search features
          <span className="feature-search-input">
            <Search size={17} aria-hidden="true" />
            <input
              placeholder="Search by name or description…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </span>
        </label>
        <label>
          Category
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
          >
            <option value="">All categories</option>
            {[...new Set(features.map((f) => f.category))].map((c) => (
              <option key={c}>{c}</option>
            ))}
          </select>
        </label>
        {(search || category) && (
          <button
            className="feature-clear"
            onClick={() => {
              setSearch("");
              setCategory("");
            }}
          >
            <X size={15} aria-hidden="true" /> Reset filters
          </button>
        )}
      </div>
      <div className="feature-user-panel">
        <div className="feature-user-intro">
          <Users size={20} aria-hidden="true" />
          <div>
            <h2>User access</h2>
            <p>Select an account to manage individual exceptions.</p>
          </div>
        </div>
        <div className="feature-user-fields">
          <label>
            Find user by email or name
            <input
              placeholder="Enter at least 2 characters"
              value={userSearch}
              onChange={(e) => setUserSearch(e.target.value)}
            />
          </label>
          <label>
            Selected user
            <select
              value={selectedUser}
              onChange={(e) => setSelectedUser(e.target.value)}
            >
              <option value="">No user selected</option>
              {users.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.email}
                </option>
              ))}
            </select>
          </label>
        </div>
        {usersLoading && (
          <p className="feature-user-hint" role="status">
            Searching accounts…
          </p>
        )}
        {!usersLoading && userSearch.length >= 2 && users.length === 0 && (
          <p className="feature-user-hint">No matching accounts found.</p>
        )}
        {selectedUser && (
          <p className="feature-user-hint">
            User overrides are now shown on each feature. Global and role
            restrictions still apply.
          </p>
        )}
      </div>
    </div>
  );
}

function FeatureStatus({ flag }) {
  const maintenance = flag.key === "maintenance";
  const enabled = maintenance
    ? flag.enabled || flag.emergency_disabled
    : flag.enabled && !flag.emergency_disabled;
  return (
    <span
      className={`feature-status ${flag.emergency_disabled ? "restricted" : enabled ? (maintenance ? "restricted" : "enabled") : ""}`}
    >
      <span aria-hidden="true" />
      {flag.emergency_disabled && !maintenance
        ? "Restricted"
        : maintenance
          ? enabled
            ? "Active"
            : "Off"
          : enabled
            ? "Enabled"
            : "Disabled"}
    </span>
  );
}
