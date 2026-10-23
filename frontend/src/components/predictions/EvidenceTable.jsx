export default function EvidenceTable({ headers, children }) {
  return (
    <div className="pd-table-scroll">
      <table className="pd-table">
        <thead>
          <tr>
            {headers.map((header) => (
              <th key={header}>{header}</th>
            ))}
          </tr>
        </thead>
        <tbody>{children}</tbody>
      </table>
    </div>
  );
}
