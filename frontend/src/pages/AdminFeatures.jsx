import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { makeRequest } from "../utils/api";
import { FeatureGrid, FeatureFilters } from "../features/FeatureControls";
import {
  FeatureHistory,
  FeatureConfirmation,
  FeatureErrors,
} from "../features/FeatureHistory";
import "./AdminFeatures.css";

function useFeatureAdministration(userSearch, selectedUser, before, onSaved) {
  const client = useQueryClient();
  const flags = useQuery({
    queryKey: ["admin-features"],
    queryFn: () => makeRequest("/admin/features"),
  });
  const users = useQuery({
    queryKey: ["feature-users", userSearch],
    queryFn: () =>
      makeRequest(
        `/admin/users?limit=20&search=${encodeURIComponent(userSearch)}`,
      ),
    enabled: userSearch.length >= 2,
  });
  const access = useQuery({
    queryKey: ["admin-user-features", selectedUser],
    queryFn: () => makeRequest(`/admin/users/${selectedUser}/features`),
    enabled: !!selectedUser,
  });
  const audit = useQuery({
    queryKey: ["feature-audit", before],
    queryFn: () =>
      makeRequest(
        `/admin/features/audit${before ? `?before_id=${before}` : ""}`,
      ),
  });
  const mutation = useMutation({
    mutationFn: (change) =>
      makeRequest(change.url, {
        method: "PATCH",
        body: JSON.stringify(change.body),
      }),
    onSuccess: async () => {
      onSaved();
      await Promise.all(
        [
          "admin-features",
          "admin-user-features",
          "feature-access",
          "feature-audit",
        ].map((key) => client.invalidateQueries({ queryKey: [key] })),
      );
    },
  });
  return { flags, users, access, audit, mutation };
}

export default function AdminFeatures() {
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("");
  const [userSearch, setUserSearch] = useState("");
  const [selectedUser, setSelectedUser] = useState("");
  const [pending, setPending] = useState(null);
  const [before, setBefore] = useState(null);
  const { flags, users, access, audit, mutation } = useFeatureAdministration(
    userSearch,
    selectedUser,
    before,
    () => setPending(null),
  );
  const { features, roles } = flagData(flags);
  const userAccess = accessData(access, selectedUser);
  const confirm = (url, body, title) => {
    mutation.reset();
    setPending({ url, body, title });
  };
  const cancel = () => {
    if (!mutation.isPending) setPending(null);
  };
  return (
    <section className="feature-workspace">
      <header>
        <p>Platform controls</p>
        <h1>Feature Management</h1>
        <p>
          Global and emergency restrictions apply to every account, including
          administrators.
        </p>
      </header>
      <FeatureFeedback flags={flags} access={access} mutation={mutation} />
      <FeatureErrors queries={[flags, users, access, audit]} />
      <FeatureFilters
        features={features}
        search={search}
        setSearch={setSearch}
        category={category}
        setCategory={setCategory}
        userSearch={userSearch}
        setUserSearch={setUserSearch}
        selectedUser={selectedUser}
        setSelectedUser={setSelectedUser}
        users={userList(users)}
      />
      <FeatureGrid
        features={features}
        search={search}
        category={category}
        roles={roles}
        {...userAccess}
        busy={mutation.isPending}
        confirm={confirm}
      />
      <FeatureHistory
        rows={auditRows(audit)}
        loading={audit.isPending}
        before={before}
        setBefore={setBefore}
      />
      <FeatureConfirmation
        pending={pending}
        mutation={mutation}
        cancel={cancel}
      />
    </section>
  );
}

function flagData(query) {
  const { features = [], roles = [] } = query.data || {};
  return { features, roles };
}
function accessData(query, selectedUser) {
  return {
    selectedUser: query.isSuccess ? selectedUser : "",
    overrides: query.data?.overrides || {},
  };
}
function userList(query) {
  return query.data?.users || [];
}
function auditRows(query) {
  return query.data || [];
}
function FeatureFeedback({ flags, access, mutation }) {
  return (
    <>
      {flags.isPending && <p role="status">Loading features...</p>}
      {mutation.isSuccess && (
        <p role="status">
          Feature access updated and recorded in audit history.
        </p>
      )}
      {access.isFetching && <p role="status">Loading user access...</p>}
    </>
  );
}
