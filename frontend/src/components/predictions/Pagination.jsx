import { ChevronLeft, ChevronRight } from "lucide-react";
export default function Pagination({ page, total, pageSize, busy, onPage }) {
  const pages = Math.max(1, Math.ceil(total / pageSize));
  return (
    <div className="pd-pagination">
      <span>
        Page {page} of {pages} · {total} fixtures
      </span>
      <div>
        <button
          className="pd-button pd-button-outline"
          aria-label="Previous page"
          disabled={page <= 1 || busy}
          onClick={() => onPage(page - 1)}
        >
          <ChevronLeft size={16} />
          Previous
        </button>
        <button
          className="pd-button pd-button-outline"
          aria-label="Next page"
          disabled={page >= pages || busy}
          onClick={() => onPage(page + 1)}
        >
          Next
          <ChevronRight size={16} />
        </button>
      </div>
    </div>
  );
}
