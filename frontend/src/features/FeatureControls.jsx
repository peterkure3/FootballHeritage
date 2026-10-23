function RoleRules({ flag, roles, busy, confirm }) {
  return (
    <fieldset>
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

function FeatureCard({
  flag,
  roles,
  overrides,
  selectedUser,
  busy,
  confirm,
}) {
  const maintenance = flag.key === "maintenance";
  return (
    <article className="feature-card">
      <div>
        <h2>{flag.key.replaceAll("_", " ")}</h2>
        <FeatureStatus flag={flag} />
      </div>
      <p>{flag.description}</p>
      <small>{flag.category}</small>
      <label>
        <input
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
        {maintenance ? "Maintenance active" : "Globally enabled"}
      </label>
      <label>
        <input
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
        Emergency restriction
      </label>
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
      <label>
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
        Available during maintenance
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

export function FeatureGrid({ features, search, category, ...props }) {
  return (
    <div className="feature-grid">
      {features
        .filter((flag) => matchesFeature(flag, search, category))
        .map((flag) => (
          <FeatureCard key={flag.key} flag={flag} {...props} />
        ))}
    </div>
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
}) {
  return (
    <div className="feature-filters">
      <label>
        Search features
        <input value={search} onChange={(e) => setSearch(e.target.value)} />
      </label>
      <label>
        Category
        <select value={category} onChange={(e) => setCategory(e.target.value)}>
          <option value="">All categories</option>
          {[...new Set(features.map((f) => f.category))].map((c) => (
            <option key={c}>{c}</option>
          ))}
        </select>
      </label>
      <label>
        Find user by email or name
        <input
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
  );
}

function FeatureStatus({ flag }) {
  const enabled = flag.enabled && !flag.emergency_disabled;
  return (
    <span className={`feature-status ${enabled ? "enabled" : ""}`}>
      {enabled ? "Enabled" : "Disabled"}
    </span>
  );
}
