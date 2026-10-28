import type { ComponentProps, ReactNode } from "react";
import { Link, useLocation } from "react-router-dom";
import { useFeatures } from "./useFeatures";
import { featureForPath, hasFeature } from "./policy";

type FeatureQuery = ReturnType<typeof useFeatures>;
function unavailable(query: FeatureQuery, feature: string | null) {
  if (!feature) return false;
  return query.isError || !hasFeature(query.data, feature);
}
function linkPath(to: ComponentProps<typeof Link>["to"]) {
  return typeof to === "string" ? to : to.pathname || "";
}
export function FeatureVisible({
  feature,
  children,
}: {
  feature: string;
  children: ReactNode;
}) {
  const query = useFeatures();
  return unavailable(query, feature) ? null : children;
}
export function FeatureLink(props: ComponentProps<typeof Link>) {
  const query = useFeatures();
  if (unavailable(query, featureForPath(linkPath(props.to)))) return null;
  return <Link {...props} />;
}
function UnavailableMessage({
  failed,
  retry,
}: {
  failed: boolean;
  retry: () => void;
}) {
  return (
    <main className="fh-container" style={{ padding: "3rem 1rem" }}>
      <h1>{failed ? "Connection interrupted" : "Feature unavailable"}</h1>
      <p>
        {failed
          ? "We could not check access. We’ll retry automatically, or you can check again now."
          : "This feature is currently unavailable for your account."}
      </p>
      <button className="fh-button" onClick={retry}>
        Check again
      </button>{" "}
      <Link to="/dashboard">Return to dashboard</Link>
    </main>
  );
}
export function FeatureBoundary({ children }: { children: ReactNode }) {
  const { pathname } = useLocation();
  const feature = featureForPath(pathname);
  const query = useFeatures({ poll: true });
  if (!feature) return children;
  if (query.isPending)
    return (
      <main className="fh-container" role="status">
        Checking availability…
      </main>
    );
  if (unavailable(query, feature))
    return (
      <UnavailableMessage
        failed={query.isError}
        retry={() => void query.refetch()}
      />
    );
  return children;
}
