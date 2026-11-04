"""Mechanical extraction of reviewed JSX; preserve dashboard behavior and markup."""
from pathlib import Path

path = Path(__file__).resolve().parents[3] / 'frontend/src/components/admin/OperationsDashboard.jsx'
source = path.read_text(encoding='utf-8')


def extract(start, end, replacement):
    global source
    first = source.index(start)
    last = source.index(end, first)
    block = source[first:last]
    source = source[:first] + replacement + source[last:]
    return block.strip()


def add_function(code):
    global source
    marker = 'export default function OperationsDashboard()'
    source = source.replace(marker, code + '\n\n' + marker, 1)


header = extract('      <header className="ops-header">', '      <DataNotice query={operations}',
                 '      <OverviewHeader operations={operations} paper={paper} />\n')
add_function('function OverviewHeader({ operations, paper }) {\nconst data=operations.data;\n'
             'const refreshing=operations.isFetching || paper.isFetching;\nreturn (' + header + ');\n}')
metrics = extract('      <div className="ops-metrics">', '      <Collector data={data}',
                  '      <OverviewMetrics data={data} paper={paper.data} studies={studies} />\n')
helpers = '''function fixtureMetric(data) {
  if (!data) return {value: "—", detail: "Awaiting fixture coverage"};
  return {value: count(data.summary.upcoming_fixtures), detail: `${data.competitions.length} competitions · next ${timestamp(data.summary.next_kickoff)}`};
}
function bookmakerMetric(data) {
  if (!data) return {value: "— / —", detail: "Awaiting market coverage"};
  return {value: `${count(data.covered_bookmakers)} / ${count(data.configured_bookmakers)}`, detail: `${count(data.summary.fresh_quotes)} fresh fixture quotes`};
}
function forecastMetric(data) {
  if (!data) return {value: "—", detail: "Awaiting active-model coverage"};
  return {value: count(data.summary.current_forecasts), detail: `Active model v${data.active_model_version} · ${data.summary.upcoming_fixtures - data.summary.current_forecasts} missing or stale`};
}
function paperMetric(data, studies) {
  if (!data) return {value: "—", detail: "Awaiting trial evidence"};
  const selections=studies.reduce((total, study)=>total+study.pending_selections,0);
  const forecasts=data.trials.filter(isModelTrial).reduce((total, trial)=>total+trial.pending_forecasts,0);
  return {value: count(selections), detail: `${count(forecasts)} forecasts awaiting final results`};
}
function isModelTrial(record) {return record.policy?.selection !== "user_selected";}
function modelStudies(data) {return data ? data.studies.filter(isModelTrial) : [];}
function OverviewMetrics({data,paper,studies}) {
  return <div className="ops-metrics">
    <Metric icon={Activity} label="Upcoming fixtures" {...fixtureMetric(data)} />
    <Metric icon={Globe2} label="Sportsbook coverage" {...bookmakerMetric(data)} />
    <Metric icon={Layers3} label="Current forecasts" {...forecastMetric(data)} />
    <Metric icon={FlaskConical} label="Pending paper selections" {...paperMetric(paper, studies)} accent />
  </div>;
}'''
add_function(helpers)
# The old calculations were used only by the extracted metric/header blocks.
start = source.index('  const studies =', source.index('export default function OperationsDashboard'))
end = source.index('  return (', start)
source = source[:start] + '  const studies = modelStudies(paper.data);\n' + source[end:]

footer = extract('      <footer className="ops-footer">', '    </div>\n  );\n}',
                 '      <OverviewFooter />\n')
add_function('function OverviewFooter() { return (' + footer + '); }')

filters = extract('      <div className="ops-source-tools">', '      <div className="ops-table-scroll">',
                  '      <SourceFilters search={search} setSearch={setSearch} filter={filter} setFilter={setFilter} />\n')
add_function('function SourceFilters({search,setSearch,filter,setFilter}) {return (' + filters + ');}')

table = extract('      <div className="ops-table-scroll">', '      <footer className="ops-source-footer">',
                '      <SourcesTable visible={visible} data={data} />\n')
add_function('function SourcesTable({visible,data}) {return (' + table + ');}')

first = source.index('          <tbody>\n            {visible.map')
last = source.index('          </tbody>', first)
body = source[first:last]
row_start = body.index('              <tr')
row_end = body.index('              </tr>') + len('              </tr>')
row = body[row_start:row_end].strip().replace(' key={book.bookmaker}', '')
source = source[:first] + '          <tbody>{visible.map((book)=><SourceRow key={book.bookmaker} book={book} />)}\n' + source[last:]
add_function('function SourceRow({book}) {return (' + row + ');}')

start = source.index('  const books = (data?.bookmakers ?? []).filter(')
end = source.index('  const visible =', start)
source = source[:start] + '  const books = filteredSources(data,search,filter);\n' + source[end:]
add_function('''function filteredSources(data, search, filter) {
  if (!data) return [];
  return data.bookmakers.filter((book)=> {
    const match=book.name.toLowerCase().includes(search.toLowerCase());
    const states={all:true, fresh:book.fresh_quotes>0, missing:book.fresh_quotes===0};
    return match && states[filter];
  });
}''')

start = source.index('      ) : (\n        studies.map((study) => (')
end = source.index('\n      <footer className="ops-panel-footer">',start)
block = source[start:end]
card_start = block.index('          <article')
card_end = block.index('          </article>')+len('          </article>')
card = block[card_start:card_end].strip().replace(' key={study.study_id}', '')
source = source[:start] + '      ) : (studies.map((study)=><PaperStudy key={study.study_id} study={study} />))}\n' + source[end:]
add_function('function PaperStudy({study}) {return (' + card + ');}')
path.write_text(source, encoding='utf-8')
print('Extracted overview header, metrics, footer, source controls/table/rows, and paper study cards.')
