import { useId, useRef, useState } from "react";
import { ChevronDown } from "lucide-react";

export default function TeamSearch({ label, value, onChange, teams, excluded, disabled, loading, unavailable }) {
  const id = useId();
  const list = useRef(null);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const query = teams.includes(value) ? "" : value.trim().toLocaleLowerCase();
  const options = teams.filter((team) => team !== excluded && team.toLocaleLowerCase().includes(query));
  function choose(team) {
    onChange(team);
    setOpen(false);
    setActive(-1);
  }
  function move(index) {
    setActive(index);
    list.current?.children[index]?.scrollIntoView({ block: "nearest" });
  }
  function keyDown(event) {
    if (event.key === "Escape") {
      event.preventDefault();
      setOpen(false);
    } else if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      setOpen(true);
      const next = event.key === "ArrowDown" ? active + 1 : active < 0 ? options.length - 1 : active - 1;
      move(Math.max(0, Math.min(options.length - 1, next)));
    } else if (event.key === "Enter" && open) {
      event.preventDefault();
      if (options[active]) choose(options[active]);
    }
  }
  return (
    <div className="pd-team-search" onBlur={(event) => {
      if (!event.currentTarget.contains(event.relatedTarget)) setOpen(false);
    }}>
      <label htmlFor={id}>{label}</label>
      <div className="pd-team-input">
        <input
          id={id}
          role="combobox"
          aria-autocomplete="list"
          aria-expanded={open}
          aria-controls={`${id}-options`}
          aria-activedescendant={open && options[active] ? `${id}-option-${active}` : undefined}
          autoComplete="off"
          required
          maxLength={120}
          disabled={disabled}
          aria-busy={loading}
          value={value}
          placeholder="Search or choose a team"
          onFocus={() => { setOpen(true); setActive(-1); }}
          onClick={() => setOpen(true)}
          onChange={(event) => { onChange(event.target.value); setOpen(true); setActive(-1); }}
          onKeyDown={keyDown}
        />
        <ChevronDown size={15} aria-hidden="true" />
      </div>
      {open && (
        <>
          <div ref={list} id={`${id}-options`} className="pd-team-options" role="listbox" aria-label={label}>
            {options.map((team, index) => (
              <button
                type="button"
                role="option"
                aria-selected={team === value}
                id={`${id}-option-${index}`}
                key={team}
                tabIndex={-1}
                className={active === index ? "pd-team-active" : ""}
                onMouseDown={(event) => event.preventDefault()}
                onClick={() => choose(team)}
              >{team}</button>
            ))}
          </div>
          {options.length === 0 && <p className="pd-team-empty" role="status">
            {loading ? "Loading team suggestions…" : unavailable
              ? "Team suggestions unavailable. Retry the team list below."
              : "No matching teams. Try another name."}
          </p>}
        </>
      )}
    </div>
  );
}
